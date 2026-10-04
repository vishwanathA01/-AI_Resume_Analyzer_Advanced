import re
from flask import has_app_context
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILLS = {
    "python","java","c++","javascript","typescript","html","css","react",
    "node.js","flask","fastapi","django","php","mysql","sql","mongodb",
    "pandas","numpy","scikit-learn","tensorflow","pytorch","keras",
    "machine learning","deep learning","nlp","natural language processing",
    "computer vision","data analysis","data analytics","power bi","tableau",
    "excel","git","github","docker","aws","azure","gcp","rest api",
    "spring boot","android","flutter","figma","communication","leadership"
}

def clean(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_skills(text):
    t = clean(text)
    found = []
    skill_names = set(SKILLS)
    if has_app_context():
        from app.models import SkillDefinition

        skill_names.update(
            item.name.lower()
            for item in SkillDefinition.query.filter_by(is_active=True).all()
        )
    for skill in sorted(skill_names, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"
        if re.search(pattern, t):
            found.append(skill)
    return sorted(set(found))

def similarity(resume_text, job_text):
    docs = [clean(resume_text), clean(job_text)]
    if not all(docs):
        return 0.0
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
    try:
        matrix = vectorizer.fit_transform(docs)
    except ValueError as error:
        if "empty vocabulary" not in str(error).lower():
            raise
        return 0.0
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0] * 100)

def skill_score(resume_skills, required_skills):
    required = {x.strip().lower() for x in required_skills.split(",") if x.strip()}
    if not required:
        return 100.0, []
    matched = required.intersection(set(resume_skills))
    missing = sorted(required - matched)
    return len(matched) / len(required) * 100, missing

def resume_score(text, skills):
    score = 0
    if len(text) > 500: score += 20
    if len(text) > 1200: score += 10
    sections = ["education", "experience", "skills", "projects"]
    score += sum(10 for s in sections if s in clean(text))
    score += min(20, len(skills) * 2)
    return min(100, float(score))
