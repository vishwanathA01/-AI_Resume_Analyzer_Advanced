from collections import Counter
from urllib.parse import quote

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app import db
from app.models import (
    Application,
    Job,
    InterviewQuestion,
    InterviewPractice,
    LearningResource,
    Match,
    Notification,
    Resume,
    SavedJob,
    User,
    UserSettings,
)
from app.services.matcher import calculate_match
from app.services.recommender import recommend
from app.services.resume_analysis import analyze_resume

workspace_bp = Blueprint("workspace", __name__, url_prefix="/workspace")
APPLICATION_STATUSES = ("Interested", "Applied", "Interviewing", "Offer", "Rejected")


def _user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _login_required():
    user = _user()
    if not user:
        return None
    return user


def _latest_resume(user):
    return Resume.query.filter_by(user_id=user.id).order_by(Resume.created_at.desc()).first()


def _record_notification(user_id, title, message, category="general"):
    preference = UserSettings.query.filter_by(user_id=user_id).first()
    if preference and not preference.email_notifications:
        return
    db.session.add(
        Notification(user_id=user_id, title=title, message=message, category=category)
    )


@workspace_bp.route("/resume")
@workspace_bp.route("/analyzer")
@workspace_bp.route("/ats")
@workspace_bp.route("/skills")
@workspace_bp.route("/improvement")
@workspace_bp.route("/history")
def resume_tools():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    tool = request.args.get("view", request.path.rsplit("/", 1)[-1])
    resume = _latest_resume(user)
    analysis = analyze_resume(resume.extracted_text) if resume else None
    labels = {
        "resume": "My Resume",
        "analyzer": "AI Resume Analyzer",
        "ats": "Resume Score & ATS Analysis",
        "skills": "Skills Intelligence",
        "improvement": "Resume Improvement",
        "history": "Resume Version History",
    }
    if tool not in labels:
        abort(404)
    templates = {
        "resume": "USER/resume.html",
        "analyzer": "USER/resume_analysis.html",
        "ats": "USER/ats_score.html",
        "skills": "USER/skills.html",
        "improvement": "USER/resume_improvement.html",
        "history": "USER/resume.html",
    }
    return render_template(
        templates[tool],
        user=user,
        tool=tool,
        title=labels[tool],
        resume=resume,
        analysis=analysis,
        resumes=Resume.query.filter_by(user_id=user.id).order_by(Resume.created_at.desc()).all()
        if tool == "history"
        else [],
    )


@workspace_bp.route("/learning")
def learning():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    missing = Counter()
    recent = (
        Match.query.filter_by(user_id=user.id)
        .order_by(Match.created_at.desc())
        .limit(20)
        .all()
    )
    for match in recent:
        missing.update(
            skill.strip()
            for skill in (match.missing_skills or "").split(",")
            if skill.strip()
        )
    resources = []
    for skill, _ in missing.most_common(12):
        matching = LearningResource.query.filter(
            LearningResource.is_active.is_(True),
            db.func.lower(LearningResource.skill) == skill.lower(),
        ).all()
        if matching:
            resources.extend(matching)
        else:
            resources.append(
                {
                    "skill": skill,
                    "title": f"Find a learning path for {skill}",
                    "provider": "Learning resource search",
                    "url": f"https://www.google.com/search?q={quote(skill + ' free course')}",
                    "difficulty": "All levels",
                }
            )
    return render_template(
        "USER/learning.html",
        user=user,
        tool="learning",
        title="AI Learning Recommendations",
        resume=_latest_resume(user),
        analysis=None,
        resources=resources,
        gaps=missing.most_common(12),
    )


@workspace_bp.route("/skill-gaps")
def skill_gaps():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    counts = Counter()
    recent_matches = (
        Match.query.filter_by(user_id=user.id)
        .order_by(Match.created_at.desc())
        .limit(40)
        .all()
    )
    for match in recent_matches:
        counts.update(
            skill.strip()
            for skill in (match.missing_skills or "").split(",")
            if skill.strip()
        )
    gaps = []
    for skill, count in counts.most_common(15):
        jobs = Job.query.filter(
            Job.is_active.is_(True),
            Job.required_skills.ilike(f"%{skill}%"),
        ).limit(3).all()
        gaps.append({"skill": skill, "count": count, "jobs": jobs})
    return render_template(
        "USER/skill_gap.html", user=user, tool="gaps", title="Skill Gap Analysis",
        resume=_latest_resume(user), analysis=None, gaps=gaps,
    )


@workspace_bp.route("/recommendations")
def recommendations():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    resume = _latest_resume(user)
    rows = []
    if resume:
        rows = recommend(resume.extracted_text, Job.query.filter_by(is_active=True).all())
        for result in rows:
            match = Match.query.filter_by(
                user_id=user.id, resume_id=resume.id, job_id=result["job"].id
            ).first()
            if match is None:
                match = Match(
                    user_id=user.id,
                    resume_id=resume.id,
                    job_id=result["job"].id,
                )
                db.session.add(match)
            match.similarity_score = result["semantic_score"]
            match.skill_score = result["skill_score"]
            match.final_score = result["final_score"]
            match.missing_skills = ", ".join(result["missing_skills"])
        if rows:
            db.session.commit()
    return render_template(
        "USER/recommendations.html", user=user, tool="recommendations",
        title="AI Job Recommendations", resume=resume, analysis=None,
        recommendations=rows,
    )


@workspace_bp.route("/saved")
def saved_jobs():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    jobs = (
        db.session.query(SavedJob, Job)
        .join(Job, SavedJob.job_id == Job.id)
        .filter(SavedJob.user_id == user.id)
        .order_by(SavedJob.created_at.desc())
        .all()
    )
    return render_template(
        "USER/saved_jobs.html", user=user, tool="saved", title="Saved Jobs",
        resume=_latest_resume(user), analysis=None, saved_jobs=jobs,
    )


@workspace_bp.post("/saved/<int:job_id>")
def toggle_saved_job(job_id):
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    job = db.session.get(Job, job_id)
    if not job or not job.is_active:
        flash("That job is no longer available.")
        return redirect(url_for("main.jobs"))
    saved = SavedJob.query.filter_by(user_id=user.id, job_id=job.id).first()
    if saved:
        db.session.delete(saved)
        flash("Job removed from your saved list.")
    else:
        db.session.add(SavedJob(user_id=user.id, job_id=job.id))
        _record_notification(user.id, "Job saved", f"{job.title} at {job.company} was added to your saved jobs.", "jobs")
        flash("Job saved.")
    db.session.commit()
    return_to = request.form.get("return_to", "")
    allowed_return_paths = {
        url_for("main.jobs"),
        url_for("workspace.saved_jobs"),
        url_for("workspace.recommendations"),
        url_for("workspace.compare_jobs"),
        url_for("main.job_details", job_id=job.id),
    }
    return redirect(return_to if return_to in allowed_return_paths else url_for("main.jobs"))


@workspace_bp.route("/applications", methods=["GET", "POST"])
def applications():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        job_id = request.form.get("job_id", type=int)
        application_id = request.form.get("application_id", type=int)
        status = request.form.get("status", "Interested").strip()
        notes = request.form.get("notes", "").strip()[:2000]
        if status not in APPLICATION_STATUSES:
            flash("Choose a valid application status.")
            return redirect(url_for("workspace.applications"))
        if application_id:
            application = Application.query.filter_by(id=application_id, user_id=user.id).first()
            if not application:
                return "Application not found", 404
            application.status = status
            application.notes = notes
            job = db.session.get(Job, application.job_id)
            job_title = job.title if job else "A saved role"
            _record_notification(user.id, "Application updated", f"Your application for {job_title} is now {status}.", "applications")
            flash("Application tracker updated.")
        else:
            job = db.session.get(Job, job_id) if job_id else None
            if not job or not job.is_active:
                flash("Choose an active job to track.")
                return redirect(url_for("workspace.applications"))
            application = Application.query.filter_by(user_id=user.id, job_id=job.id).first()
            if application:
                application.status = status
                application.notes = notes
                flash("Existing application tracker entry updated.")
            else:
                application = Application(user_id=user.id, job_id=job.id, status=status, notes=notes)
                db.session.add(application)
                _record_notification(user.id, "Application tracked", f"You started tracking {job.title} at {job.company}.", "applications")
                flash("Job added to your application tracker.")
        db.session.commit()
        return redirect(url_for("workspace.applications"))
    rows = (
        db.session.query(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.user_id == user.id)
        .order_by(Application.updated_at.desc())
        .all()
    )
    jobs = Job.query.filter_by(is_active=True).order_by(Job.title.asc()).all()
    return render_template(
        "USER/applications.html", user=user, tool="applications", title="Application Tracker",
        resume=_latest_resume(user), analysis=None, applications=rows, jobs=jobs,
        statuses=APPLICATION_STATUSES,
    )


@workspace_bp.route("/interview", methods=["GET", "POST"])
def interview():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    jobs = Job.query.filter_by(is_active=True).order_by(Job.title.asc()).all()
    questions = []
    selected_job = None
    if request.method == "POST":
        selected_job = db.session.get(Job, request.form.get("job_id", type=int))
        if not selected_job or not selected_job.is_active:
            flash("Choose an active role to prepare for.")
            return redirect(url_for("workspace.interview"))
        skills = [skill.strip() for skill in (selected_job.required_skills or "").split(",") if skill.strip()]
        questions = [
            f"Describe a project where you used {skill}. What was your contribution and result?"
            for skill in skills[:5]
        ]
        questions.extend(
            [
                f"What interests you about the {selected_job.title} role at {selected_job.company}?",
                f"How would you approach the main responsibilities described for this {selected_job.title} position?",
                "Tell me about a challenging problem you solved and how you measured the outcome.",
                "What skill are you currently developing, and how are you practicing it?",
            ]
        )
        custom_questions = InterviewQuestion.query.filter_by(is_active=True).all()
        selected_skills = {skill.lower() for skill in skills}
        questions.extend(
            item.question
            for item in custom_questions
            if item.category.lower() == "general"
            or item.category.lower() in selected_skills
        )
        questions = questions[:12]
        _record_notification(user.id, "Interview practice ready", f"Practice questions generated for {selected_job.title}.", "interview")
        practice = InterviewPractice(
            user_id=user.id,
            job_id=selected_job.id,
            questions=questions,
        )
        db.session.add(practice)
        db.session.commit()
        return redirect(url_for("workspace.interview_result", practice_id=practice.id))
    return render_template(
        "USER/interview.html", user=user, tool="interview", title="Interview Preparation",
        resume=_latest_resume(user), analysis=None, jobs=jobs,
        selected_job=selected_job, questions=questions,
    )


@workspace_bp.route("/interview/result/<int:practice_id>")
def interview_result(practice_id):
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    result = InterviewPractice.query.filter_by(id=practice_id, user_id=user.id).first()
    if not result:
        flash("Generate interview practice questions to view your result.")
        return redirect(url_for("workspace.interview"))
    job = db.session.get(Job, result.job_id)
    if not job:
        flash("That role is no longer available.")
        return redirect(url_for("workspace.interview"))
    return render_template(
        "USER/interview_result.html",
        user=user,
        tool="interview_result",
        title="AI Interview Questions",
        resume=_latest_resume(user),
        analysis=None,
        selected_job=job,
        questions=result.questions,
        practice=result,
    )


@workspace_bp.route("/notifications", methods=["GET", "POST"])
def notifications():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        notification_id = request.form.get("notification_id", type=int)
        query = Notification.query.filter_by(user_id=user.id)
        if notification_id:
            notification = query.filter_by(id=notification_id).first()
            if notification:
                notification.is_read = True
        else:
            query.update({"is_read": True}, synchronize_session=False)
        db.session.commit()
        return redirect(url_for("workspace.notifications"))
    rows = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template(
        "USER/notifications.html", user=user, tool="notifications", title="Notifications",
        resume=_latest_resume(user), analysis=None, notifications=rows,
        unread_count=sum(not item.is_read for item in rows),
    )


@workspace_bp.route("/settings", methods=["GET", "POST"])
def settings():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    preferences = UserSettings.query.filter_by(user_id=user.id).first()
    if not preferences:
        preferences = UserSettings(user_id=user.id)
        db.session.add(preferences)
        db.session.commit()
    if request.method == "POST":
        preferences.preferred_location = request.form.get("preferred_location", "").strip()[:180]
        preferences.email_notifications = request.form.get("email_notifications") == "on"
        db.session.commit()
        flash("Settings saved.")
        return redirect(url_for("workspace.settings"))
    return render_template(
        "USER/settings.html", user=user, tool="settings", title="Settings",
        resume=_latest_resume(user), analysis=None, preferences=preferences,
    )


@workspace_bp.route("/compare")
def compare_jobs():
    user = _login_required()
    if not user:
        return redirect(url_for("auth.login"))
    resume = _latest_resume(user)
    raw_ids = request.args.getlist("job_id")
    ids = []
    for raw_id in raw_ids:
        try:
            candidate = int(raw_id)
        except ValueError:
            continue
        if candidate not in ids:
            ids.append(candidate)
    jobs = Job.query.filter(Job.id.in_(ids), Job.is_active.is_(True)).all() if ids else []
    if len(ids) > 4:
        flash("Choose no more than four jobs for a comparison.")
    comparisons = []
    if resume:
        for job in jobs[:4]:
            comparisons.append(
                (job, calculate_match(resume.extracted_text, job.description, job.required_skills, job.min_experience))
            )
    return render_template(
        "USER/workspace.html", user=user, tool="compare", title="Job Match Comparison",
        resume=resume, analysis=None, jobs=Job.query.filter_by(is_active=True).order_by(Job.title.asc()).all(),
        comparisons=comparisons,
    )
