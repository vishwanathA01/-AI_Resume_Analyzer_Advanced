import os
from app.services.nlp import similarity, extract_skills, skill_score

def semantic_similarity(resume_text, job_text):
    if os.getenv("SEMANTIC_MATCHING", "false").lower() != "true":
        return similarity(resume_text, job_text)

    try:
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer("all-MiniLM-L6-v2")
        a = model.encode(resume_text, convert_to_tensor=True)
        b = model.encode(job_text, convert_to_tensor=True)
        return float(util.cos_sim(a, b).item() * 100)
    except Exception:
        return similarity(resume_text, job_text)

def calculate_match(resume_text, job_description, required_skills):
    skills = extract_skills(resume_text)
    semantic = semantic_similarity(resume_text, job_description)
    skill, missing = skill_score(skills, required_skills)
    final = semantic * 0.60 + skill * 0.40
    return {
        "semantic_score": round(semantic, 2),
        "skill_score": round(skill, 2),
        "final_score": round(final, 2),
        "resume_skills": skills,
        "missing_skills": missing
    }
