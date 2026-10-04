import logging
import os

from app.services.nlp import similarity, skill_score
from app.services.resume_analysis import analyze_resume

logger = logging.getLogger(__name__)
_semantic_model = None
_matching_method = "TF-IDF"


def semantic_similarity(resume_text, job_text):
    global _matching_method
    if os.getenv("SEMANTIC_MATCHING", "false").lower() != "true":
        _matching_method = "TF-IDF"
        return similarity(resume_text, job_text)

    global _semantic_model
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        logger.warning("Sentence-Transformers is unavailable; using TF-IDF matching.")
        _matching_method = "TF-IDF (transformer package unavailable)"
        return similarity(resume_text, job_text)
    if _semantic_model is None:
        _semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
    a = _semantic_model.encode(resume_text, convert_to_tensor=True)
    b = _semantic_model.encode(job_text, convert_to_tensor=True)
    _matching_method = "Sentence-Transformers · all-MiniLM-L6-v2"
    return float(util.cos_sim(a, b).item() * 100)


def calculate_match(resume_text, job_description, required_skills, min_experience=0):
    analysis = analyze_resume(resume_text)
    skills = analysis["skills"]
    semantic = semantic_similarity(resume_text, job_description)
    required_skills = required_skills or ""
    skill, missing = skill_score(skills, required_skills)
    requested = {item.strip().lower() for item in required_skills.split(",") if item.strip()}
    matched = sorted(
        (item for item in requested if item in {value.lower() for value in skills}),
        key=str.lower,
    )
    required_years = max(float(min_experience or 0), 0)
    candidate_years = analysis["experience_years"]
    experience = (
        100.0 if required_years == 0
        else 60.0 if candidate_years is None
        else min(100.0, candidate_years / required_years * 100)
    )
    education_terms = ("bachelor", "master", "degree", "phd", "diploma", "university")
    education_requested = any(term in job_description.lower() for term in education_terms)
    education_found = bool(analysis["sections"]["education"]) or any(
        term in resume_text.lower() for term in education_terms
    )
    education = 100.0 if not education_requested else (85.0 if education_found else 35.0)
    project_terms = {word for word in matched if word in analysis["sections"]["projects"].lower()}
    projects = 100.0 if not matched else min(100.0, len(project_terms) / len(matched) * 100)
    final = semantic * 0.40 + skill * 0.30 + experience * 0.15 + education * 0.10 + projects * 0.05
    return {
        "semantic_score": round(semantic, 2),
        "skill_score": round(skill, 2),
        "experience_score": round(experience, 2),
        "education_score": round(education, 2),
        "project_score": round(projects, 2),
        "final_score": round(final, 2),
        "matched_skills": matched,
        "matching_method": _matching_method,
        "resume_skills": skills,
        "missing_skills": missing
    }
