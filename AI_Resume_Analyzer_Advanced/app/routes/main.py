import io
import secrets
import uuid
import warnings
from pathlib import Path
from urllib.parse import quote_plus

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import (
    CommunityComment,
    CommunityLike,
    CommunityPost,
    HomepageFeedback,
    Job,
    JobCategory,
    Match,
    ProfilePicture,
    Resume,
    SavedJob,
    User,
)
from app.services.nlp import extract_skills
from app.services.matcher import calculate_match

main_bp = Blueprint("main", __name__)
MAX_PROFILE_PICTURE_BYTES = 2 * 1024 * 1024
MAX_PROFILE_PICTURE_PIXELS = 12_000_000
MAX_COMMUNITY_POSTS = 30
MAX_COMMENTS_PER_POST = 3
PROFILE_PICTURE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


def _interaction_csrf_token():
    token = session.get("_interaction_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_interaction_csrf_token"] = token
    return token


def _has_valid_interaction_csrf_token():
    supplied = request.form.get("csrf_token", "")
    expected = session.get("_interaction_csrf_token", "")
    return bool(supplied and expected and secrets.compare_digest(supplied, expected))


def _normalize_profile_picture(upload):
    extension = Path(upload.filename).suffix.lower()
    expected_format = PROFILE_PICTURE_FORMATS.get(extension)
    if not expected_format:
        raise ValueError("Choose a JPG, PNG, or WebP image.")

    image_bytes = upload.stream.read(MAX_PROFILE_PICTURE_BYTES + 1)
    if len(image_bytes) > MAX_PROFILE_PICTURE_BYTES:
        raise ValueError("Profile pictures must be 2 MB or smaller.")
    if not image_bytes:
        raise ValueError("The selected image is empty.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as image:
                if image.format != expected_format:
                    raise ValueError("The selected image does not match its file type.")
                if image.width * image.height > MAX_PROFILE_PICTURE_PIXELS:
                    raise ValueError("Choose an image with dimensions under 12 megapixels.")
                image.verify()

            with Image.open(io.BytesIO(image_bytes)) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((512, 512))
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=88, optimize=True)
                return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("That image could not be read. Choose a valid JPG, PNG, or WebP file.") from error

def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def external_job_searches(query):
    keywords = quote_plus(query)
    return {
        "LinkedIn Jobs": f"https://www.linkedin.com/jobs/search/?keywords={keywords}",
        "Upwork": f"https://www.upwork.com/nx/search/jobs/?q={keywords}",
    }


@main_bp.route("/")
def home():
    featured_jobs = (
        Job.query.filter_by(is_active=True)
        .order_by(Job.created_at.desc())
        .limit(3)
        .all()
    )
    return render_template(
        "home.html",
        active_job_count=Job.query.filter_by(is_active=True).count(),
        featured_jobs=featured_jobs,
        external_job_searches=external_job_searches,
        candidate_count=User.query.filter_by(role="user").count(),
        analyzed_resume_count=Resume.query.count()
    )

@main_bp.route("/feedback", methods=["POST"])
def submit_homepage_feedback():
    rating = request.form.get("rating", type=int)
    topic = request.form.get("topic", "").strip()
    message = request.form.get("message", "").strip()
    honeypot = request.form.get("website", "").strip()
    topics = {"homepage", "resume-tools", "job-matching", "other"}

    if honeypot:
        return redirect(url_for("main.home", _anchor="feedback"))
    if rating not in {1, 2, 3, 4, 5} or topic not in topics or len(message) > 1000:
        flash("Please choose a rating and topic. Feedback must be 1,000 characters or fewer.")
        return redirect(url_for("main.home", _anchor="feedback"))
    if not message:
        flash("Please add a short note so we know what to improve.")
        return redirect(url_for("main.home", _anchor="feedback"))

    db.session.add(HomepageFeedback(rating=rating, topic=topic, message=message))
    db.session.commit()
    flash("Thank you — your feedback was sent to the InterviewIQ team.")
    return redirect(url_for("main.home", _anchor="feedback"))

@main_bp.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    resumes = Resume.query.filter_by(user_id=user.id).order_by(Resume.created_at.desc()).all()
    jobs = Job.query.filter_by(is_active=True).count()
    matches = Match.query.filter_by(user_id=user.id).count()
    latest_resume = resumes[0] if resumes else None
    skills = extract_skills(latest_resume.extracted_text) if latest_resume else []
    average_score = round(
        sum(resume.resume_score or 0 for resume in resumes) / len(resumes), 1
    ) if resumes else 0
    profile_steps = [
        ("Upload your resume", bool(latest_resume)),
        ("Add skills to your profile", bool(skills)),
        ("Review your job matches", bool(matches)),
        ("Build a strong resume score", bool(latest_resume and latest_resume.resume_score >= 70)),
    ]
    profile_progress = round(sum(complete for _, complete in profile_steps) * 100 / len(profile_steps))
    recent_matches = (
        db.session.query(Match, Job)
        .join(Job, Match.job_id == Job.id)
        .filter(Match.user_id == user.id)
        .order_by(Match.created_at.desc())
        .limit(6)
        .all()
    )
    career_activity = [
        {
            "date": user.created_at,
            "title": "Career workspace created",
            "detail": "Your InterviewIQ account is ready.",
            "kind": "account",
            "href": url_for("main.profile")
        }
    ]
    career_activity.extend(
        {
            "date": resume.created_at,
            "title": "Resume analyzed",
            "detail": f"{resume.filename} · {(resume.resume_score or 0):.0f}/100 quality score",
            "kind": "resume",
            "href": url_for("main.dashboard", _anchor="resume-library")
        }
        for resume in resumes[:4]
    )
    career_activity.extend(
        {
            "date": match.created_at,
            "title": f"Matched with {job.title}",
            "detail": f"{job.company} · {(match.final_score or 0):.0f}% match",
            "kind": "match",
            "href": url_for("main.matches")
        }
        for match, job in recent_matches[:4]
    )
    career_activity.sort(key=lambda activity: activity["date"], reverse=True)

    skill_gap_counts = {}
    for match, _ in recent_matches:
        for skill in (match.missing_skills or "").split(","):
            skill = skill.strip()
            if skill:
                skill_gap_counts[skill] = skill_gap_counts.get(skill, 0) + 1
    skill_gaps = sorted(
        skill_gap_counts.items(), key=lambda item: (-item[1], item[0].lower())
    )[:6]
    next_actions = []
    if not latest_resume:
        next_actions.append({
            "title": "Analyze your first resume",
            "detail": "Get a quality score and see the skills in your profile.",
            "label": "Upload resume",
            "href": url_for("main.dashboard", _anchor="uploadForm"),
            "kind": "resume"
        })
    elif not recent_matches:
        next_actions.append({
            "title": "Find roles that fit your resume",
            "detail": "Compare your latest resume with active opportunities.",
            "label": "Find matches",
            "resume_id": latest_resume.id,
            "kind": "match"
        })
    if latest_resume and latest_resume.resume_score < 70:
        next_actions.append({
            "title": "Polish your resume",
            "detail": "Review your resume sections and make relevant achievements clear.",
            "label": "Review resumes",
            "href": url_for("main.dashboard", _anchor="resume-library"),
            "kind": "improve"
        })
    if skills and not matches:
        next_actions.append({
            "title": "Browse jobs that use your skills",
            "detail": f"Explore roles connected to {skills[0]}.",
            "label": "Explore roles",
            "href": url_for("main.jobs", q=skills[0]),
            "kind": "jobs"
        })
    if not next_actions:
        next_actions.append({
            "title": "Explore your next opportunity",
            "detail": "Keep your shortlist fresh as new roles are added.",
            "label": "Browse jobs",
            "href": url_for("main.jobs"),
            "kind": "jobs"
        })
    return render_template(
        "USER/dashboard.html", user=user, resumes=resumes, jobs=jobs,
        matches=matches, skills=skills, recent_matches=recent_matches,
        average_score=average_score, profile_steps=profile_steps,
        profile_progress=profile_progress, skill_gaps=skill_gaps,
        career_activity=career_activity[:7], next_actions=next_actions[:3]
    )

@main_bp.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    is_admin_user = user.role == "admin"
    profile_template = "ADMIN/admin_profile.html" if is_admin_user else "USER/profile.html"
    profile_context = (
        {
            "admin": user,
            "tool": "profile",
            "title": "Administrator Profile",
            "csrf_token": _interaction_csrf_token(),
        }
        if is_admin_user
        else {"csrf_token": _interaction_csrf_token()}
    )

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        email_parts = email.rsplit("@", 1)
        valid_email = (
            len(email_parts) == 2
            and bool(email_parts[0])
            and "." in email_parts[1]
            and bool(email_parts[1].split(".", 1)[0])
        )

        if not name or len(name) > 120 or not valid_email or len(email) > 180:
            flash("Enter a name and valid email address.")
            return render_template(profile_template, user=user, **profile_context), 400
        if not user.check_password(current_password):
            flash("Enter your current password to save profile changes.")
            return render_template(profile_template, user=user, **profile_context), 400
        if User.query.filter(User.email == email, User.id != user.id).first():
            flash("That email address is already in use.")
            return render_template(profile_template, user=user, **profile_context), 409
        if new_password:
            if len(new_password) < 8:
                flash("Your new password must be at least 8 characters.")
                return render_template(profile_template, user=user, **profile_context), 400
            if new_password != confirm_password:
                flash("The new passwords do not match.")
                return render_template(profile_template, user=user, **profile_context), 400
            user.set_password(new_password)

        user.name = name
        user.email = email
        db.session.commit()
        flash("Your profile has been updated.")
        return redirect(url_for("admin.admin_profile" if is_admin_user else "main.profile"))

    return render_template(profile_template, user=user, **profile_context)


@main_bp.route("/profile/photo", methods=["POST"])
def update_profile_photo():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not _has_valid_interaction_csrf_token():
        abort(400, description="The profile photo form expired. Reload your profile and try again.")

    existing_picture = ProfilePicture.query.filter_by(user_id=user.id).first()
    action = request.form.get("action", "upload")
    if action == "remove":
        if existing_picture:
            old_filename = existing_picture.filename
            db.session.delete(existing_picture)
            db.session.commit()
            try:
                (Path(current_app.config["UPLOAD_FOLDER"]) / "profile-images" / old_filename).unlink(
                    missing_ok=True
                )
            except OSError:
                current_app.logger.exception("Could not remove the previous profile photo file.")
            flash("Your profile picture was removed.")
        else:
            flash("You do not have a profile picture to remove.")
        return redirect(url_for("main.profile"))
    if action != "upload":
        abort(400, description="Unsupported profile photo action.")

    upload = request.files.get("profile_picture")
    if not upload or not upload.filename:
        flash("Choose a JPG, PNG, or WebP image to upload.")
        return redirect(url_for("main.profile"))
    try:
        image_bytes = _normalize_profile_picture(upload)
    except ValueError as error:
        flash(str(error))
        return redirect(url_for("main.profile"))

    image_directory = Path(current_app.config["UPLOAD_FOLDER"]) / "profile-images"
    filename = f"{uuid.uuid4().hex}.jpg"
    image_path = image_directory / filename
    old_filename = existing_picture.filename if existing_picture else None
    try:
        image_directory.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(image_bytes)
    except OSError:
        current_app.logger.exception("Could not save a profile photo.")
        flash("The profile picture could not be saved. Please try again.")
        return redirect(url_for("main.profile"))

    try:
        if existing_picture:
            existing_picture.filename = filename
        else:
            db.session.add(ProfilePicture(user_id=user.id, filename=filename))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        try:
            image_path.unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Could not clean up an unsaved profile photo.")
        current_app.logger.exception("Could not update a profile picture.")
        flash("The profile picture could not be updated. Please try again.")
        return redirect(url_for("main.profile"))

    if old_filename:
        try:
            (image_directory / old_filename).unlink(missing_ok=True)
        except OSError:
            current_app.logger.exception("Could not remove the previous profile photo file.")
    flash("Your profile picture was updated.")
    return redirect(url_for("admin.admin_profile" if user.role == "admin" else "main.profile"))


@main_bp.route("/profile/photo/<string:filename>")
def profile_photo(filename):
    if not current_user():
        abort(404)
    picture = ProfilePicture.query.filter_by(filename=filename).first()
    if not picture or not filename.endswith(".jpg") or len(filename) != 36:
        abort(404)
    image_directory = Path(current_app.config["UPLOAD_FOLDER"]) / "profile-images"
    return send_from_directory(
        image_directory,
        filename,
        mimetype="image/jpeg",
        max_age=3600,
    )


@main_bp.route("/community")
def community():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))

    posts = CommunityPost.query.order_by(
        CommunityPost.created_at.desc(), CommunityPost.id.desc()
    ).limit(MAX_COMMUNITY_POSTS).all()
    post_ids = [post.id for post in posts]
    likes_by_post = {}
    comments_by_post = {}
    liked_post_ids = set()
    comments_by_id = {}

    if post_ids:
        likes_by_post = dict(
            db.session.query(CommunityLike.post_id, func.count(CommunityLike.id))
            .filter(CommunityLike.post_id.in_(post_ids))
            .group_by(CommunityLike.post_id)
            .all()
        )
        comments_by_post = dict(
            db.session.query(CommunityComment.post_id, func.count(CommunityComment.id))
            .filter(CommunityComment.post_id.in_(post_ids))
            .group_by(CommunityComment.post_id)
            .all()
        )
        liked_post_ids = {
            post_id
            for (post_id,) in db.session.query(CommunityLike.post_id).filter(
                CommunityLike.user_id == user.id,
                CommunityLike.post_id.in_(post_ids),
            )
        }
        ranked_comments = (
            db.session.query(
                CommunityComment.id.label("id"),
                func.row_number()
                .over(
                    partition_by=CommunityComment.post_id,
                    order_by=(CommunityComment.created_at.desc(), CommunityComment.id.desc()),
                )
                .label("position"),
            )
            .filter(CommunityComment.post_id.in_(post_ids))
            .subquery()
        )
        recent_comments = (
            db.session.query(CommunityComment, User)
            .join(User, CommunityComment.user_id == User.id)
            .join(ranked_comments, CommunityComment.id == ranked_comments.c.id)
            .filter(ranked_comments.c.position <= MAX_COMMENTS_PER_POST)
            .order_by(CommunityComment.created_at.asc(), CommunityComment.id.asc())
            .all()
        )
        for comment, author in recent_comments:
            comments_by_id.setdefault(comment.post_id, []).append((comment, author))

    feed = [
        {
            "post": post,
            "like_count": likes_by_post.get(post.id, 0),
            "comment_count": comments_by_post.get(post.id, 0),
            "liked": post.id in liked_post_ids,
            "comments": comments_by_id.get(post.id, []),
        }
        for post in posts
    ]
    return render_template(
        "USER/community.html",
        user=user,
        feed=feed,
        member_count=User.query.filter_by(role="user").count(),
        csrf_token=_interaction_csrf_token(),
    )


@main_bp.route("/community/posts", methods=["POST"])
def create_community_post():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not _has_valid_interaction_csrf_token():
        abort(400, description="The community form expired. Reload the page and try again.")

    body = request.form.get("body", "").strip()
    if not body:
        flash("Write a short update before sharing it.")
    elif len(body) > 1200:
        flash("Community posts must be 1,200 characters or fewer.")
    else:
        db.session.add(CommunityPost(user_id=user.id, body=body))
        db.session.commit()
        flash("Your update was shared with the community.")
    return redirect(url_for("main.community"))


@main_bp.route("/community/posts/<int:post_id>/like", methods=["POST"])
def toggle_community_like(post_id):
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not _has_valid_interaction_csrf_token():
        abort(400, description="The community form expired. Reload the page and try again.")
    post = db.session.get(CommunityPost, post_id)
    if not post:
        abort(404)

    like = CommunityLike.query.filter_by(post_id=post.id, user_id=user.id).first()
    if like:
        db.session.delete(like)
    elif post.user_id == user.id:
        flash("You cannot like your own update.")
    else:
        db.session.add(CommunityLike(post_id=post.id, user_id=user.id))
    db.session.commit()
    return redirect(url_for("main.community", _anchor=f"post-{post.id}"))


@main_bp.route("/community/posts/<int:post_id>/comments", methods=["POST"])
def create_community_comment(post_id):
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not _has_valid_interaction_csrf_token():
        abort(400, description="The community form expired. Reload the page and try again.")
    post = db.session.get(CommunityPost, post_id)
    if not post:
        abort(404)
    body = request.form.get("body", "").strip()
    if not body:
        flash("Write a reply before posting it.")
    elif len(body) > 600:
        flash("Replies must be 600 characters or fewer.")
    else:
        db.session.add(CommunityComment(post_id=post.id, user_id=user.id, body=body))
        db.session.commit()
        flash("Your reply was added.")
    return redirect(url_for("main.community", _anchor=f"post-{post.id}"))


@main_bp.route("/community/posts/<int:post_id>/delete", methods=["POST"])
def delete_community_post(post_id):
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not _has_valid_interaction_csrf_token():
        abort(400, description="The community form expired. Reload the page and try again.")
    post = db.session.get(CommunityPost, post_id)
    if not post:
        abort(404)
    if post.user_id != user.id:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Your update was deleted.")
    return redirect(url_for("main.community"))


@main_bp.route("/community/comments/<int:comment_id>/delete", methods=["POST"])
def delete_community_comment(comment_id):
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if not _has_valid_interaction_csrf_token():
        abort(400, description="The community form expired. Reload the page and try again.")
    comment = db.session.get(CommunityComment, comment_id)
    if not comment:
        abort(404)
    if comment.user_id != user.id:
        abort(403)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash("Your reply was removed.")
    return redirect(url_for("main.community", _anchor=f"post-{post_id}"))


@main_bp.route("/jobs")
def jobs():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    query = Job.query.filter_by(is_active=True)
    if category_id:
        query = query.filter(Job.categories.any(JobCategory.id == category_id))
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Job.title.ilike(term),
            Job.company.ilike(term),
            Job.location.ilike(term),
            Job.description.ilike(term),
            Job.required_skills.ilike(term)
        ))
    jobs = query.order_by(Job.created_at.desc()).all()
    user = current_user()
    saved_job_ids = {
        item.job_id for item in SavedJob.query.filter_by(user_id=user.id).all()
    } if user else set()
    return render_template(
        "USER/jobs.html",
        jobs=jobs,
        external_job_searches={
            job.id: external_job_searches(" ".join(
                part for part in (job.title, job.location or "") if part
            ))
            for job in jobs
        },
        fallback_job_searches=external_job_searches(search or "remote jobs"),
        search=search,
        categories=JobCategory.query.order_by(JobCategory.name.asc()).all(),
        selected_category=category_id,
        saved_job_ids=saved_job_ids,
    )


@main_bp.route("/jobs/<int:job_id>")
def job_details(job_id):
    job = Job.query.filter_by(id=job_id, is_active=True).first()
    if not job:
        abort(404)
    user = current_user()
    is_saved = bool(
        user and SavedJob.query.filter_by(user_id=user.id, job_id=job.id).first()
    )
    search_terms = " ".join(
        part for part in (job.title, job.location or "") if part
    )
    return render_template(
        "USER/job_details.html",
        job=job,
        user=user,
        is_saved=is_saved,
        external_job_sources=external_job_searches(search_terms),
    )

@main_bp.route("/matches")
def matches():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    matches = (
        db.session.query(Match, Job, Resume)
        .join(Job, Match.job_id == Job.id)
        .join(Resume, Match.resume_id == Resume.id)
        .filter(Match.user_id == user.id)
        .order_by(Match.created_at.desc())
        .all()
    )
    explained_matches = [
        (match, job, resume, calculate_match(
            resume.extracted_text, job.description, job.required_skills, job.min_experience
        ))
        for match, job, resume in matches
    ]
    return render_template("USER/matches.html", matches=explained_matches)

@main_bp.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")
