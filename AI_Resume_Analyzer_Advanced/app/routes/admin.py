import csv
import io
import math
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func

from app import db
from app.models import (
    Application,
    AuditLog,
    InterviewQuestion,
    Job,
    JobCategory,
    HomepageFeedback,
    LearningResource,
    Match,
    Notification,
    Resume,
    SkillDefinition,
    User,
    UserSettings,
)
from app.services.nlp import SKILLS, extract_skills

admin_bp = Blueprint("admin", __name__)


def is_admin():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    return user if user and user.role == "admin" else None


def _audit(admin, action, target_type="", target_id=None, details=""):
    db.session.add(
        AuditLog(
            actor_id=admin.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details[:2000],
        )
    )


def _analytics():
    resumes = Resume.query.order_by(Resume.created_at.desc()).all()
    demanded = Counter()
    for job in Job.query.filter_by(is_active=True).all():
        demanded.update(extract_skills(job.required_skills or ""))
    missing = Counter()
    for match in Match.query.all():
        missing.update(skill.strip() for skill in (match.missing_skills or "").split(",") if skill.strip())
    skill_demand = demanded.most_common(8)
    top_missing = missing.most_common(8)
    return {
        "user_count": User.query.filter_by(role="user").count(),
        "resume_count": len(resumes),
        "job_count": Job.query.count(),
        "active_job_count": Job.query.filter_by(is_active=True).count(),
        "match_count": Match.query.count(),
        "average_score": round(sum(resume.resume_score or 0 for resume in resumes) / len(resumes), 1) if resumes else 0,
        "skill_demand": skill_demand,
        "top_missing": top_missing,
        "max_demand": max((count for _, count in skill_demand), default=1),
    }


@admin_bp.route("/")
def dashboard():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    analytics = _analytics()
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=6)
    first_moment = datetime.combine(first_day, datetime.min.time())
    end_moment = datetime.combine(today + timedelta(days=1), datetime.min.time())
    signups_by_day = Counter(
        user.created_at.date()
        for user in User.query.filter(
            User.role == "user",
            User.created_at >= first_moment,
            User.created_at < end_moment,
        ).all()
    )
    signup_activity = [
        {
            "label": (first_day + timedelta(days=offset)).strftime("%a"),
            "date": (first_day + timedelta(days=offset)).strftime("%b %d"),
            "count": signups_by_day[first_day + timedelta(days=offset)],
        }
        for offset in range(7)
    ]
    recent_activity = (
        db.session.query(AuditLog, User)
        .outerjoin(User, AuditLog.actor_id == User.id)
        .order_by(AuditLog.created_at.desc())
        .limit(6)
        .all()
    )
    return render_template(
        "ADMIN/admin.html",
        admin=admin,
        users=User.query.order_by(User.created_at.desc()).limit(10).all(),
        jobs=Job.query.order_by(Job.created_at.desc()).all(),
        categories=JobCategory.query.order_by(JobCategory.name.asc()).all(),
        signup_activity=signup_activity,
        signup_max=max((item["count"] for item in signup_activity), default=0),
        recent_activity=recent_activity,
        application_count=Application.query.count(),
        feedback_count=HomepageFeedback.query.count(),
        **analytics,
    )


@admin_bp.route("/jobs/new", methods=["POST"])
def add_job():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    title = request.form.get("title", "").strip()
    company = request.form.get("company", "").strip()
    description = request.form.get("description", "").strip()
    try:
        min_experience = float(request.form.get("min_experience") or 0)
        if not math.isfinite(min_experience) or min_experience < 0:
            raise ValueError
    except ValueError:
        flash("Minimum experience must be a non-negative number.")
        return redirect(url_for("admin.dashboard"))
    if not title or not company or not description:
        flash("Job title, company, and description are required.")
        return redirect(url_for("admin.dashboard"))
    job = Job(
        title=title[:180],
        company=company[:180],
        location=request.form.get("location", "").strip()[:180] or "Remote",
        description=description,
        required_skills=request.form.get("required_skills", "").strip()[:5000],
        min_experience=min_experience,
    )
    category_ids = request.form.getlist("category_ids", type=int)
    if category_ids:
        job.categories = JobCategory.query.filter(JobCategory.id.in_(category_ids)).all()
    db.session.add(job)
    db.session.flush()
    _audit(admin, "job.created", "job", job.id, f"{job.title} at {job.company}")
    db.session.commit()
    flash("Job added successfully.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/jobs/<int:job_id>/toggle", methods=["POST"])
def toggle_job(job_id):
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    job = db.session.get(Job, job_id)
    if not job:
        abort(404)
    job.is_active = not job.is_active
    _audit(admin, "job.toggled", "job", job.id, f"is_active={job.is_active}")
    db.session.commit()
    flash(f"{job.title} is now {'active' if job.is_active else 'inactive'}.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/jobs")
def manage_jobs():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    return render_template(
        "ADMIN/jobs_manage.html",
        admin=admin,
        tool="jobs",
        title="Job Management",
        jobs=Job.query.order_by(Job.created_at.desc()).all(),
        categories=JobCategory.query.order_by(JobCategory.name.asc()).all(),
    )


@admin_bp.route("/users", methods=["GET"])
def users():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    return render_template(
        "ADMIN/users.html",
        admin=admin,
        tool="users",
        title="User Management",
        users=User.query.order_by(User.created_at.desc()).all(),
    )


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
def toggle_user_role(user_id):
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == admin.id:
        flash("You cannot change your own administrator role here.")
        return redirect(url_for("admin.users"))
    next_role = "admin" if user.role == "user" else "user"
    if user.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        flash("The platform must keep at least one administrator.")
        return redirect(url_for("admin.users"))
    user.role = next_role
    _audit(admin, "user.role_changed", "user", user.id, f"role={next_role}")
    db.session.commit()
    flash(f"{user.email} now has the {next_role} role.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/resumes")
def resumes():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    rows = db.session.query(Resume, User).join(User, Resume.user_id == User.id).order_by(Resume.created_at.desc()).limit(250).all()
    return render_template("ADMIN/resumes.html", admin=admin, tool="resumes", title="Resume Management", resumes=rows)


@admin_bp.route("/analytics")
def analytics():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    return render_template("ADMIN/analytics.html", admin=admin, tool="analytics", title="AI/ML & Match Analytics", **_analytics())


@admin_bp.route("/ai-analytics")
def ai_analytics():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    return render_template("ADMIN/ai_analytics.html", admin=admin, tool="analytics", title="AI/ML Analytics", **_analytics())


@admin_bp.route("/match-analytics")
def match_analytics():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    return render_template("ADMIN/match_analytics.html", admin=admin, tool="analytics", title="Match Analytics", **_analytics())


@admin_bp.route("/skills", methods=["GET", "POST"])
def skills():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip().lower()
        if not name or len(name) > 100 or not all(character.isalnum() or character in " +-#./" for character in name):
            flash("Enter a skill name using letters, numbers, spaces, or common skill punctuation.")
        elif name in SKILLS or SkillDefinition.query.filter(func.lower(SkillDefinition.name) == name).first():
            flash("That skill is already in the skill dictionary.")
        else:
            item = SkillDefinition(name=name)
            db.session.add(item)
            db.session.flush()
            _audit(admin, "skill.created", "skill", item.id, item.name)
            db.session.commit()
            flash("Skill added to resume extraction and matching.")
        return redirect(url_for("admin.skills"))
    skill_counts = Counter()
    for job in Job.query.filter_by(is_active=True).all():
        skill_counts.update(extract_skills(job.required_skills or ""))
    return render_template(
        "ADMIN/skills_manage.html", admin=admin, tool="skills", title="Skills Database",
        skills=sorted(SKILLS), skill_counts=skill_counts,
        custom_skills=SkillDefinition.query.order_by(SkillDefinition.name.asc()).all(),
    )


@admin_bp.route("/skills/<int:skill_id>/toggle", methods=["POST"])
def toggle_skill(skill_id):
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    item = db.session.get(SkillDefinition, skill_id)
    if not item:
        abort(404)
    item.is_active = not item.is_active
    _audit(admin, "skill.toggled", "skill", item.id, f"is_active={item.is_active}")
    db.session.commit()
    return redirect(url_for("admin.skills"))


@admin_bp.route("/categories", methods=["GET", "POST"])
def categories():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name or len(name) > 100:
            flash("Enter a category name up to 100 characters.")
        elif JobCategory.query.filter(func.lower(JobCategory.name) == name.lower()).first():
            flash("That category already exists.")
        else:
            category = JobCategory(name=name, description=description[:500])
            db.session.add(category)
            db.session.flush()
            _audit(admin, "category.created", "category", category.id, category.name)
            db.session.commit()
            flash("Job category added.")
        return redirect(url_for("admin.categories"))
    return render_template(
        "ADMIN/categories.html", admin=admin, tool="categories", title="Job Categories",
        categories=JobCategory.query.order_by(JobCategory.name.asc()).all(),
    )


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
def delete_category(category_id):
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    category = db.session.get(JobCategory, category_id)
    if not category:
        abort(404)
    name = category.name
    category.jobs.clear()
    db.session.delete(category)
    _audit(admin, "category.deleted", "category", category_id, name)
    db.session.commit()
    flash("Category deleted.")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/resources", methods=["GET", "POST"])
def resources():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        skill = request.form.get("skill", "").strip()
        title = request.form.get("title", "").strip()
        provider = request.form.get("provider", "").strip() or "Self study"
        url = request.form.get("url", "").strip()
        difficulty = request.form.get("difficulty", "Beginner").strip()
        if not skill or len(skill) > 100 or not title or len(title) > 180 or not url.startswith(("https://", "http://")):
            flash("Provide a skill, title and valid HTTP(S) resource URL.")
        else:
            item = LearningResource(skill=skill, title=title, provider=provider[:120], url=url[:500], difficulty=difficulty[:32])
            db.session.add(item)
            db.session.flush()
            _audit(admin, "resource.created", "learning_resource", item.id, item.title)
            db.session.commit()
            flash("Learning resource added.")
        return redirect(url_for("admin.resources"))
    return render_template(
        "ADMIN/learning_resources.html", admin=admin, tool="resources", title="Learning Resources",
        resources=LearningResource.query.order_by(LearningResource.skill.asc()).all(),
    )


@admin_bp.route("/interview-questions", methods=["GET", "POST"])
def interview_questions():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        category = request.form.get("category", "").strip() or "General"
        question = request.form.get("question", "").strip()
        if not question or len(question) > 2000:
            flash("Enter an interview question up to 2,000 characters.")
        else:
            item = InterviewQuestion(category=category[:100], question=question)
            db.session.add(item)
            db.session.flush()
            _audit(admin, "interview_question.created", "interview_question", item.id, category)
            db.session.commit()
            flash("Interview question added.")
        return redirect(url_for("admin.interview_questions"))
    return render_template(
        "ADMIN/interview_questions.html", admin=admin, tool="questions", title="Interview Question Management",
        questions=InterviewQuestion.query.order_by(InterviewQuestion.category.asc()).all(),
    )


@admin_bp.route("/notifications", methods=["GET", "POST"])
def notifications():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        if not title or not message:
            flash("A notification title and message are required.")
        else:
            opted_out = {
                item.user_id
                for item in UserSettings.query.filter_by(email_notifications=False).all()
            }
            for user in User.query.filter_by(role="user").all():
                if user.id not in opted_out:
                    db.session.add(Notification(user_id=user.id, title=title[:180], message=message[:2000], category="admin"))
            _audit(admin, "notification.broadcast", "users", None, title)
            db.session.commit()
            flash("Notification sent to all candidate accounts.")
        return redirect(url_for("admin.notifications"))
    return render_template(
        "ADMIN/notifications.html", admin=admin, tool="notifications", title="Platform Notifications",
        user_count=User.query.filter_by(role="user").count(),
    )


@admin_bp.route("/reports")
def reports_page():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    return render_template(
        "ADMIN/reports.html", admin=admin, tool="reports",
        title="Reports", **_analytics(),
    )

@admin_bp.route("/feedback")
def homepage_feedback():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    feedback = HomepageFeedback.query.order_by(HomepageFeedback.created_at.desc()).limit(250).all()
    return render_template(
        "ADMIN/admin_tools.html",
        admin=admin,
        tool="feedback",
        title="Homepage Feedback",
        feedback=feedback,
    )


@admin_bp.route("/profile")
def admin_profile():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    return render_template(
        "ADMIN/admin_profile.html",
        admin=admin,
        user=admin,
        tool="profile",
        title="Administrator Profile",
        csrf_token=session.setdefault(
            "_interaction_csrf_token", secrets.token_urlsafe(32)
        ),
    )


@admin_bp.route("/audit")
def audit():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    rows = db.session.query(AuditLog, User).outerjoin(User, AuditLog.actor_id == User.id).order_by(AuditLog.created_at.desc()).limit(250).all()
    return render_template("ADMIN/activity_logs.html", admin=admin, tool="audit", title="Activity & Audit Logs", logs=rows)


@admin_bp.route("/settings")
def settings():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    database_kind = "SQLite" if uri.startswith("sqlite:") else "Configured SQL database"
    return render_template(
        "ADMIN/settings.html", admin=admin, tool="settings", title="System Settings",
        database_kind=database_kind,
        semantic_enabled=current_app.config.get("SEMANTIC_MATCHING", False),
        upload_limit_mb=current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
    )


@admin_bp.route("/reports.csv")
def report():
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    for key, value in _analytics().items():
        if isinstance(value, list):
            writer.writerow([key, "; ".join(f"{name}:{count}" for name, count in value)])
        else:
            writer.writerow([key, value])
    _audit(admin, "report.exported", "analytics")
    db.session.commit()
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=resumeai-report.csv"},
    )


@admin_bp.route("/resources/<int:resource_id>/toggle", methods=["POST"])
def toggle_resource(resource_id):
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    item = db.session.get(LearningResource, resource_id)
    if not item:
        abort(404)
    item.is_active = not item.is_active
    _audit(admin, "resource.toggled", "learning_resource", item.id, f"is_active={item.is_active}")
    db.session.commit()
    return redirect(url_for("admin.resources"))


@admin_bp.route("/interview-questions/<int:question_id>/toggle", methods=["POST"])
def toggle_interview_question(question_id):
    admin = is_admin()
    if not admin:
        return redirect(url_for("auth.login"))
    item = db.session.get(InterviewQuestion, question_id)
    if not item:
        abort(404)
    item.is_active = not item.is_active
    _audit(admin, "interview_question.toggled", "interview_question", item.id, f"is_active={item.is_active}")
    db.session.commit()
    return redirect(url_for("admin.interview_questions"))
