# InterviewIQ — AI Resume Analyzer & Job Matcher

InterviewIQ is a full-stack academic project for analyzing resumes, extracting skills, matching candidates with jobs, identifying skill gaps, scoring resumes, and preparing for interviews.

## Template organization
The Flask template tree keeps public pages at the root and separates candidate and administrator screens:

```text
app/templates/
├── base.html, home.html, login.html, register.html, how_it_works.html
├── USER/
│   ├── dashboard.html, profile.html, workspace.html
│   ├── resume.html, resume_analysis.html, ats_score.html, skills.html
│   ├── skill_gap.html, jobs.html, job_details.html, matches.html
│   ├── recommendations.html, learning.html, resume_improvement.html
│   ├── interview.html, interview_result.html, saved_jobs.html
│   ├── applications.html, notifications.html, settings.html
├── RESOURCES/
│   ├── hub.html, page.html, tool.html
└── ADMIN/
    ├── admin.html, admin_tools.html, users.html, resumes.html
    ├── jobs_manage.html, skills_manage.html, categories.html
    ├── analytics.html, ai_analytics.html, match_analytics.html
    ├── learning_resources.html, interview_questions.html, reports.html
    ├── notifications.html, settings.html, admin_profile.html, activity_logs.html
```

## Architecture
Browser → Flask Web/API → NLP/ML Services → SQLite or MySQL
                         ├→ Resume Parser
                         ├→ Skill Extractor
                         ├→ TF-IDF + Cosine Similarity
                         ├→ Semantic Embeddings (optional)
                         └→ Recommendation Engine

## Main Features
- User registration/login
- Candidate profile and password management
- Private profile photo uploads with image validation, resizing, and member-only display
- Member-only community feed with text posts, replies, likes, and owner-controlled post removal
- Resume upload: PDF/DOCX
- Resume text extraction
- Skill extraction from a configurable skill dictionary
- Resume completeness/quality score
- ATS-style structure checklist and resume improvement guidance
- Extraction of contact details, stated years of experience, and labeled experience, education, project, and certification sections
- Candidate dashboard with profile-completion checklist and resume-score history
- Skill-gap roadmap summarized from recent job matches
- Personalized next-step cards and recent career activity timeline
- Dashboard section navigation for quick access to resume, skills, and activity
- Readability-focused user dashboard with larger typography, improved contrast, a career snapshot, and responsive workspace navigation
- Admin overview with platform metrics, a seven-day candidate registration chart, recent audit activity, and direct management shortcuts
- Shared, responsive admin workspace navigation with active-page indicators across all management, analytics, reporting, settings, and profile screens
- Grouped Career Tools and candidate Workspace menus, with a compact, scrollable navigation layout on smaller screens
- Job catalog
- Searchable public job catalog and matching-method guide
- Resume-to-job matching
- Skill-gap analysis
- Job recommendations
- Explainable match breakdown across text similarity, skills, experience, education, and projects
- Saved-job shortlist and application status tracker
- Role-based interview practice questions and admin-curated question bank
- Skill-gap-based learning recommendations and curated resource management
- In-app notifications and candidate preferences
- Resume version history
- Saved match history with score breakdowns
- User dashboard
- Admin dashboard
- Admin job publishing and listing controls
- Admin candidate overview
- Admin user, resume, category, skills, learning-resource, and interview-question management
- Admin analytics for user, resume, job, match, resume-score, and skill demand/gap metrics
- CSV report export, platform notifications, runtime settings, and admin audit log
- REST API endpoints
- MySQL schema and seed data
- Responsive UI
- Secure password hashing
- File validation and size limits
- Optional Sentence-Transformers semantic matching
- Local-first analysis; no paid AI API is required
- InterviewIQ logo and favicon
- Public Career Resources hub with resume templates and examples, ATS and writing guides, cover-letter examples, blog notes, and help pages
- Guided public resume builder with a live preview, three print-ready layouts, repeatable experience/education/project sections, and an optional recognized-skill keyword check against a pasted job description
- Europass-inspired CV draft builder with copyable previews; it is an independent draft tool, not an official Europass service
- Job-fit checker with explainable text, skill, experience, education, and project signals
- Salary comparison calculator based on candidate-entered figures (no fabricated market benchmarks)
- Cover-letter and LinkedIn profile draft generators
- Responsive navigation and homepage entry points for career tools
- Homepage career illustrations, private visitor feedback form, and administrator-only feedback review
- Original SVG career illustrations for job discovery, community conversations, learning plans, resume tools, interview preparation, and sign-in experiences across public pages, candidate workspaces, and the admin dashboard
- External job-board search references for relevant LinkedIn Jobs and Upwork queries from the homepage, job list, and job detail pages

## Run on Windows

1. Install Python 3.11+.
2. Open a terminal in this folder and install dependencies:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

3. Start the app:
   python run.py
4. Open http://127.0.0.1:5000

By default, the app uses a local SQLite database at `instance/resume_ai.sqlite3`
and creates its tables automatically, so registration and login work without
installing a separate database server.

To use MySQL instead, install MySQL/XAMPP, create the `resume_ai` database,
copy `.env.example` to `.env`, set `DATABASE_URL` and `SECRET_KEY`, and start
the app. The MySQL tables are created automatically; optionally import
`database/seed.sql` to add the sample jobs.

For the default SQLite setup, create an administrator from a terminal in the
project folder with `python -m flask --app run.py create-admin`. The command
prompts for the administrator name, email, and password. Use this account to
publish and manage job listings in `/admin/`.

The optional MySQL seed file includes this admin account:
- Email: admin@resumeai.local
- Password: Admin@12345

Change the password before real deployment.

## Optional semantic model
The project works without a transformer model using TF-IDF text similarity. For stronger semantic similarity, install the optional local model package:

python -m pip install sentence-transformers

Then set:
SEMANTIC_MATCHING=true

The first semantic match downloads `all-MiniLM-L6-v2` if it is not cached. This model runs locally; its package and model are intentionally not installed by the base requirements because they are large optional dependencies. The UI reports which similarity method was used.

## Explainable analysis notes
Resume parsing reads PDF/DOCX text locally. Profile fields and labeled sections are extracted with deterministic patterns, and the ATS checklist is a transparent structure/completeness heuristic rather than a third-party ATS certification. Interview practice questions are assembled locally from job requirements and the admin-managed question bank; no hosted generative AI is called.

The displayed job-fit score is weighted as follows: text similarity 40%, required skills 30%, experience 15%, education 10%, and project evidence 5%. Each component is displayed so candidates can inspect the match rather than relying on a single unexplained number.

The public resume and letter tools generate drafts in the response and do not save submitted text. The resume builder's keyword check uses only recognized skill terms and is not an ATS score or hiring prediction; the builder does not call a hosted generative-AI service or invent candidate details. Use the browser print dialog to save a generated resume as PDF. The Europass-inspired builder is not an official Europass document service. Salary Insights compares user-entered compensation only; it does not provide live market salary data. Review generated material and all automated scores before relying on them.

New feature tables are created automatically by SQLAlchemy when the application starts. The expanded MySQL reference schema is in `database/schema.sql`.
#   i n t e r v i e w I Q  
 