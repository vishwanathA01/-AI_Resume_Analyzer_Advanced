import re

from app.services.nlp import extract_skills, resume_score


SECTION_LABELS = {
    "experience": ("experience", "employment", "work history", "professional background", "work experience", "professional experience", "employment history"),
    "education": ("education", "academic", "qualification", "qualifications"),
    "projects": ("projects", "project experience", "personal projects"),
    "certifications": ("certification", "certifications", "certificates", "licenses"),
}


def extract_sections(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = {key: [] for key in SECTION_LABELS}
    active = None
    for line in lines:
        normalized = line.lower().strip(" :|#-")
        heading = next(
            (
                key
                for key, labels in SECTION_LABELS.items()
                if normalized in labels
                or any(normalized.startswith(label + " ") for label in labels)
            ),
            None,
        )
        if heading:
            active = heading
        elif active:
            result[active].append(line)
    return {key: "\n".join(lines) for key, lines in result.items()}


def analyze_resume(text):
    normalized = text.lower()
    skills = extract_skills(text)
    sections = extract_sections(text)
    email = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I)
    phone = re.search(r"(?:\+?\d[\d ().-]{7,}\d)", text)
    years = [
        int(value)
        for value in re.findall(r"\b(\d{1,2})\+?\s+years?\b", normalized)
        if 0 < int(value) < 60
    ]
    checks = [
        ("Contact details", bool(email and phone), "Add an email address and a reachable phone number."),
        ("Professional summary", any(term in normalized for term in ("summary", "profile", "objective")), "Add a concise role-focused professional summary."),
        ("Work experience", bool(sections["experience"]) or "experience" in normalized, "Add an experience section with measurable outcomes."),
        ("Education", bool(sections["education"]) or "education" in normalized, "Include your education and relevant qualifications."),
        ("Skills", bool(skills) or "skills" in normalized, "Include a clearly labeled skills section using job-relevant terms."),
        ("Projects", bool(sections["projects"]) or "projects" in normalized, "Add projects that demonstrate practical results."),
        ("Certifications", bool(sections["certifications"]) or "certification" in normalized, "List relevant certifications when applicable."),
    ]
    base_score = resume_score(text, skills)
    ats_score = round(sum(100 / len(checks) for _, passed, _ in checks if passed))
    suggestions = [advice for _, passed, advice in checks if not passed]
    return {
        "skills": skills,
        "sections": sections,
        "email": email.group(0) if email else None,
        "phone": phone.group(0).strip() if phone else None,
        "experience_years": max(years) if years else None,
        "ats_score": min(100, ats_score),
        "quality_score": base_score,
        "checks": checks,
        "suggestions": suggestions,
    }
