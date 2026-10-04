# AI Resume Analyzer & Job Matcher — Advanced Edition

A full-stack academic project for analyzing resumes, extracting skills, matching candidates with jobs, identifying skill gaps, scoring resumes, and generating recommendations.

## Architecture
Browser → Flask Web/API → NLP/ML Services → MySQL
                         ├→ Resume Parser
                         ├→ Skill Extractor
                         ├→ TF-IDF + Cosine Similarity
                         ├→ Semantic Embeddings (optional)
                         └→ Recommendation Engine

## Main Features
- User registration/login
- Resume upload: PDF/DOCX
- Resume text extraction
- Skill extraction from a configurable skill dictionary
- Resume completeness/quality score
- Job catalog
- Searchable public job catalog and matching-method guide
- Resume-to-job matching
- Skill-gap analysis
- Job recommendations
- Saved match history with score breakdowns
- User dashboard
- Admin dashboard
- REST API endpoints
- MySQL schema and seed data
- Responsive UI
- Secure password hashing
- File validation and size limits
- Optional Sentence-Transformers semantic matching

## Run on Windows

1. Install Python 3.11+.
2. Install MySQL/XAMPP and create a database.
3. Copy `.env.example` to `.env` and edit credentials.
4. Open terminal in this folder:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

5. Create database and import `database/schema.sql` and `database/seed.sql`.
6. Start:
   python run.py
7. Open http://127.0.0.1:5000

Default seeded admin:
- Email: admin@resumeai.local
- Password: Admin@12345

Change the password before real deployment.

## Optional semantic model
The project works without a transformer model using TF-IDF. For stronger semantic matching:

pip install sentence-transformers

Then set:
SEMANTIC_MATCHING=true

The first run may download the model.
