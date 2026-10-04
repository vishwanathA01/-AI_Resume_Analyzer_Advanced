import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import User, Resume, Job, Match, Notification, UserSettings
from app.services.parser import extract_text
from app.services.resume_analysis import analyze_resume
from app.services.recommender import recommend

api_bp = Blueprint("api", __name__)

def auth_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None

@api_bp.post("/resume/upload")
def upload_resume():
    user = auth_user()
    if not user:
        return jsonify({"error":"Login required"}), 401

    file = request.files.get("resume")
    if not file or not file.filename:
        return jsonify({"error":"Choose a PDF or DOCX resume"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf",".docx"}:
        return jsonify({"error":"Only PDF and DOCX are allowed"}), 400

    safe = secure_filename(file.filename)
    if not safe:
        return jsonify({"error":"The selected filename is not valid"}), 400
    filename = f"{uuid.uuid4().hex}_{safe}"
    path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    file.save(path)

    try:
        text = extract_text(path)
        if not text.strip():
            raise ValueError("No readable text was found in the selected resume.")
        analysis = analyze_resume(text)

        resume = Resume(
            user_id=user.id,
            filename=safe,
            extracted_text=text,
            resume_score=analysis["quality_score"]
        )
        db.session.add(resume)
        preference = UserSettings.query.filter_by(user_id=user.id).first()
        if not preference or preference.email_notifications:
            db.session.add(Notification(
                user_id=user.id,
                title="Resume analysis complete",
                message=f"{safe} was analyzed with an ATS-style score of {analysis['ats_score']}%.",
                category="resume",
            ))
        db.session.commit()

        return jsonify({
            "message":"Resume analyzed successfully",
            "resume_id":resume.id,
            "score":analysis["quality_score"],
            "ats_score":analysis["ats_score"],
            "skills":analysis["skills"],
            "experience_years":analysis["experience_years"],
            "education_extracted":bool(analysis["sections"]["education"]),
            "projects_extracted":bool(analysis["sections"]["projects"]),
            "certifications_extracted":bool(analysis["sections"]["certifications"]),
        })
    except ValueError as error:
        db.session.rollback()
        if path.exists():
            path.unlink()
        return jsonify({"error":str(error)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        if path.exists():
            path.unlink()
        current_app.logger.exception("Could not save the analyzed resume.")
        return jsonify({"error":"The resume could not be saved. Please try again."}), 500

@api_bp.get("/jobs")
def jobs():
    rows = Job.query.filter_by(is_active=True).order_by(Job.created_at.desc()).all()
    return jsonify([{
        "id":j.id, "title":j.title, "company":j.company,
        "location":j.location, "skills":j.required_skills,
        "description":j.description
    } for j in rows])

@api_bp.get("/recommendations/<int:resume_id>")
def recommendations(resume_id):
    user = auth_user()
    if not user:
        return jsonify({"error":"Login required"}), 401
    resume = Resume.query.filter_by(id=resume_id, user_id=user.id).first()
    if not resume:
        return jsonify({"error":"Resume not found"}), 404

    rows = Job.query.filter_by(is_active=True).all()
    recs = recommend(resume.extracted_text, rows)
    output = []
    for r in recs:
        missing = ", ".join(r["missing_skills"])
        match = Match.query.filter_by(
            user_id=user.id, resume_id=resume.id, job_id=r["job"].id
        ).first()
        if match is None:
            match = Match(user_id=user.id, resume_id=resume.id, job_id=r["job"].id)
            db.session.add(match)
        match.similarity_score = r["semantic_score"]
        match.skill_score = r["skill_score"]
        match.final_score = r["final_score"]
        match.missing_skills = missing
        output.append({
            "job_id":r["job"].id,
            "title":r["job"].title,
            "company":r["job"].company,
            "location":r["job"].location,
            "final_score":r["final_score"],
            "semantic_score":r["semantic_score"],
            "matching_method":r["matching_method"],
            "skill_score":r["skill_score"],
            "experience_score":r["experience_score"],
            "education_score":r["education_score"],
            "project_score":r["project_score"],
            "matched_skills":r["matched_skills"],
            "missing_skills":r["missing_skills"]
        })
    db.session.commit()
    return jsonify(output)
