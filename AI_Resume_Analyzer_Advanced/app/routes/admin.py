from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import db
from app.models import User, Job

admin_bp = Blueprint("admin", __name__)

def is_admin():
    return session.get("role") == "admin"

@admin_bp.route("/")
def dashboard():
    if not is_admin():
        return redirect(url_for("auth.login"))
    return render_template("admin.html",
        users=User.query.count(),
        jobs=Job.query.count()
    )

@admin_bp.route("/jobs/new", methods=["POST"])
def add_job():
    if not is_admin():
        return redirect(url_for("auth.login"))
    job = Job(
        title=request.form["title"],
        company=request.form["company"],
        location=request.form.get("location","Remote"),
        description=request.form["description"],
        required_skills=request.form.get("required_skills",""),
        min_experience=float(request.form.get("min_experience",0))
    )
    db.session.add(job)
    db.session.commit()
    flash("Job added successfully.")
    return redirect(url_for("admin.dashboard"))
