from app.services.matcher import calculate_match

def recommend(resume_text, jobs, limit=10):
    results = []
    for job in jobs:
        m = calculate_match(resume_text, job.description, job.required_skills)
        results.append({
            "job": job,
            **m
        })
    return sorted(results, key=lambda x: x["final_score"], reverse=True)[:limit]
