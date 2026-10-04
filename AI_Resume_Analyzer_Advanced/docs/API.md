# API Endpoints

POST /api/resume/upload
- multipart/form-data
- field: resume
- returns resume id, score and extracted skills

GET /api/jobs
- returns active jobs

GET /api/recommendations/<resume_id>
- returns ranked job recommendations, semantic score, skill score and missing skills
