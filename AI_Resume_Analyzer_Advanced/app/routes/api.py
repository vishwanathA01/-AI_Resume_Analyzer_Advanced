import os, json, uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Resume, Job, Match
from app.services.parser import extract_text
from app.services.nlp import extract_skills, resume_score
from app.services.recommender import recommend

api_bp = Blueprint("api", __name__)

def auth_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

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
    filename = f"{uuid.uuid4().hex}_{safe}"
    path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    file.save(path)

    try:
        text = extract_text(path)
        skills = extract_skills(text)
        score = resume_score(text, skills)

        resume = Resume(
            user_id=user.id,
            filename=safe,
            extracted_text=text,
            resume_score=score
        )
        db.session.add(resume)
        db.session.commit()

        return jsonify({
            "message":"Resume analyzed successfully",
            "resume_id":resume.id,
            "score":score,
            "skills":skills
        })
    except Exception as e:
        if path.exists():
            path.unlink()
        return jsonify({"error":str(e)}), 500

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
        match = Match(
            user_id=user.id, resume_id=resume.id, job_id=r["job"].id,
            similarity_score=r["semantic_score"],
            skill_score=r["skill_score"],
            final_score=r["final_score"],
            missing_skills=missing
        )
        db.session.add(match)
        output.append({
            "job_id":r["job"].id,
            "title":r["job"].title,
            "company":r["job"].company,
            "location":r["job"].location,
            "final_score":r["final_score"],
            "semantic_score":r["semantic_score"],
            "skill_score":r["skill_score"],
            "missing_skills":r["missing_skills"]
        })
    db.session.commit()
    return jsonify(output)
