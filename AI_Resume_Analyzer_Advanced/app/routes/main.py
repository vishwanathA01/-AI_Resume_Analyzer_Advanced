from flask import Blueprint, render_template, session, redirect, url_for, request
from sqlalchemy import or_
from app import db
from app.models import User, Resume, Job, Match

main_bp = Blueprint("main", __name__)

def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

@main_bp.route("/")
def home():
    return render_template("home.html")

@main_bp.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    resumes = Resume.query.filter_by(user_id=user.id).order_by(Resume.created_at.desc()).all()
    jobs = Job.query.filter_by(is_active=True).count()
    matches = Match.query.filter_by(user_id=user.id).count()
    return render_template("dashboard.html", user=user, resumes=resumes, jobs=jobs, matches=matches)

@main_bp.route("/jobs")
def jobs():
    search = request.args.get("q", "").strip()
    query = Job.query.filter_by(is_active=True)
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
    return render_template("jobs.html", jobs=jobs, search=search)

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
    return render_template("matches.html", matches=matches)

@main_bp.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")
