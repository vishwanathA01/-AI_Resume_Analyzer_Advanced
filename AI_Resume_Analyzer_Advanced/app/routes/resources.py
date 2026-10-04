from flask import Blueprint, abort, make_response, redirect, render_template, request, session, url_for

from app.services.matcher import calculate_match
from app.services.nlp import extract_skills

resources_bp = Blueprint("resources", __name__)

RESOURCE_PAGES = {
    "resume-templates": {
        "title": "Resume Templates",
        "kicker": "START WITH A CLEAR STRUCTURE",
        "description": "Choose a simple, readable format, then tailor every section to the role you want.",
        "sections": [
            ("ATS-friendly chronological", "Use this when your recent experience is the strongest evidence for your next role. Put contact details, summary, experience, education, and skills in a single column."),
            ("Early-career and graduate", "Lead with education, projects, internships, and relevant skills when your professional experience is still growing."),
            ("Career-change", "Open with a targeted summary and transferable skills, then use selected projects and achievements to connect your previous work to the new role."),
        ],
        "action": ("Build a resume", "resources.resume_builder"),
    },
    "resume-examples": {
        "title": "Resume Examples",
        "kicker": "EXAMPLES TO LEARN FROM",
        "description": "Use these fictional examples for structure and phrasing inspiration. Replace every detail with truthful evidence from your own experience.",
        "sections": [
            ("Data analyst · project-led", "SUMMARY\nEarly-career analyst with experience turning customer and operations data into clear reporting.\n\nPROJECT\nRetail sales analysis — Cleaned a public dataset with Python and SQL; built a dashboard to explain monthly trends and product performance.\n\nSKILLS\nSQL · Python · Excel · Data visualization"),
            ("Software developer · experience-led", "SUMMARY\nSoftware developer focused on maintainable web applications and reliable APIs.\n\nEXPERIENCE\nSoftware engineering intern — Shipped a set of documented API endpoints with automated tests in collaboration with a four-person team.\n\nSKILLS\nPython · Flask · REST APIs · Git · Testing"),
            ("Product designer · portfolio-led", "SUMMARY\nProduct designer who pairs user research with accessible, clear interface design.\n\nPROJECT\nOnboarding redesign — Interviewed five users, mapped friction points, and prototyped a shorter onboarding flow.\n\nSKILLS\nFigma · Prototyping · Accessibility · User research"),
        ],
        "action": ("Create your version", "resources.resume_builder"),
    },
    "ats-resume-score-guide": {
        "title": "ATS Resume Score Guide",
        "kicker": "UNDERSTAND THE SIGNALS",
        "description": "A practical guide to readable, relevant resumes. No resume score can guarantee that a particular employer's system will rank or accept an application.",
        "sections": [
            ("Use a readable structure", "Use standard headings, a consistent date format, and a clean layout. Keep important details in the document body rather than relying on decorative graphics or text boxes."),
            ("Show role-relevant evidence", "Use terminology from the job description when it accurately describes your experience. Support important skills with examples in experience or project bullets."),
            ("Make achievements specific", "Describe the action, context, and result. Use numbers only when you can verify them and explain what they measure."),
            ("Check the source document", "Confirm that your PDF or DOCX text can be selected and copied in the correct order. Proofread contact details, dates, and spelling before applying."),
        ],
        "action": ("Analyze a resume", "resources.resume_analyzer"),
    },
    "cover-letter-examples": {
        "title": "Cover Letter Examples",
        "kicker": "MAKE YOUR CASE CLEARLY",
        "description": "Short fictional examples show how to connect a role requirement to real evidence. Adapt the structure; do not claim experience you do not have.",
        "sections": [
            ("Experienced candidate", "Dear Hiring Team,\n\nI am applying for the [Role] position because my experience in [relevant area] aligns with your team's work on [specific priority]. In my current role, I [specific action and verifiable result].\n\nI would welcome the opportunity to discuss how this experience could support [team or goal]. Thank you for your consideration.\n\nSincerely,\n[Your name]"),
            ("Graduate or early-career candidate", "Dear Hiring Team,\n\nI am excited to apply for [Role]. Through [course, internship, or project], I developed practical experience with [relevant skill]. For example, I [specific contribution and outcome].\n\nI am interested in [company-specific reason] and would be glad to bring my [relevant strength] to your team.\n\nSincerely,\n[Your name]"),
            ("Career change", "Dear Hiring Team,\n\nI am applying for [Role] after building transferable strengths in [relevant skills] through [previous field or experience]. In particular, I [evidence that connects to the role]. I have also developed my knowledge of [new-field skill] through [project or learning].\n\nI would value a conversation about how my background could contribute to [team priority].\n\nSincerely,\n[Your name]"),
        ],
        "action": ("Generate a cover letter", "resources.cover_letter_generator"),
    },
    "resume-writing-guide": {
        "title": "Resume Writing Guide",
        "kicker": "WRITE FOR PEOPLE FIRST",
        "description": "A concise workflow for turning your experience into a focused, easy-to-review resume.",
        "sections": [
            ("1. Choose a target", "Pick a role family and identify the most important responsibilities and skills in the job description."),
            ("2. Select relevant evidence", "Prioritize experience, projects, and training that demonstrate those responsibilities. Remove detail that does not help explain your fit."),
            ("3. Write evidence-led bullets", "Start with a clear action, describe what you worked on, and state a measurable result when one is available and accurate."),
            ("4. Edit and proofread", "Use consistent tense and formatting, check links and contact details, and ask someone to review the final document."),
        ],
        "action": ("Build a resume", "resources.resume_builder"),
    },
    "resources": {
        "title": "Career Resources",
        "kicker": "TOOLS, GUIDES & EXAMPLES",
        "description": "Browse practical tools for resumes, applications, compensation planning, and interview preparation.",
        "sections": [],
    },
    "blog": {
        "title": "InterviewIQ Blog",
        "kicker": "PRACTICAL CAREER NOTES",
        "description": "Short, actionable reads for making your next application clearer and more intentional.",
        "sections": [
            ("Turn a job description into a resume checklist", "Identify the role's core responsibilities, note the skills you can genuinely evidence, and check that your most relevant examples are easy to find."),
            ("Make project bullets easier to evaluate", "Explain the problem, your contribution, and the outcome. For team projects, be precise about what you personally delivered."),
            ("Prepare for an interview with evidence", "For each important requirement, prepare one concise example that explains the situation, your actions, and what you learned."),
        ],
    },
    "help": {
        "title": "Help Center",
        "kicker": "QUICK ANSWERS",
        "description": "Get help using InterviewIQ's local-first career tools.",
        "sections": [
            ("Which resume files can I analyze?", "The signed-in resume workspace accepts PDF and DOCX files. The public job-fit checker also accepts pasted resume text and does not save it."),
            ("Are scores hiring or ATS guarantees?", "No. Resume checks and job-fit scores are guidance based on visible content and the selected listing. They do not predict a hiring decision or represent a particular employer's ATS."),
            ("Are generated documents saved?", "The resume, cover letter, and LinkedIn tools show a preview only. Copy or download the text before leaving; these public generators do not save it to your account."),
            ("Where is interview preparation?", "Sign in and open Interview Preparation in your workspace to generate role-focused practice questions."),
        ],
    },
}

TOOL_TITLES = {
    "resume-builder": "AI Resume Builder",
    "europass-cv-builder": "Europass CV Builder",
    "resume-analyzer": "Resume Analyzer",
    "job-fit-checker": "Job Fit Checker",
    "salary-insights": "Salary Insights",
    "cover-letter-generator": "Cover Letter Generator",
    "linkedin-optimizer": "LinkedIn Optimizer",
}

RESOURCES = [
    ("AI Resume Builder", "Create and copy a clean, role-focused resume draft.", "resources.resume_builder", ""),
    ("Europass CV Builder", "Organize your profile into a Europass-inspired CV structure.", "resources.europass_cv_builder", ""),
    ("Resume Analyzer", "Review your uploaded resume and ATS-style checks.", "resources.resume_analyzer", ""),
    ("Job Fit Checker", "Compare pasted resume text with a role description and inspect the score breakdown.", "resources.job_fit_checker", ""),
    ("Salary Insights", "Compare current and target compensation using your own figures.", "resources.salary_insights", ""),
    ("Resume Templates", "Explore readable formats for different career stages.", "resources.resource_page", "resume-templates"),
    ("Resume Examples", "Learn from fictional, role-focused examples.", "resources.resource_page", "resume-examples"),
    ("ATS Resume Score Guide", "Understand resume readability and relevance checks.", "resources.resource_page", "ats-resume-score-guide"),
    ("Cover Letter Examples", "Adapt concise examples for different situations.", "resources.resource_page", "cover-letter-examples"),
    ("Resume Writing Guide", "Follow a practical resume-writing workflow.", "resources.resource_page", "resume-writing-guide"),
    ("Interview Prep", "Practice questions tailored to a role.", "resources.interview_prep", ""),
    ("Cover Letter Generator", "Draft a tailored cover letter from your own details.", "resources.cover_letter_generator", ""),
    ("LinkedIn Optimizer", "Create a headline and improve the focus of your About section.", "resources.linkedin_optimizer", ""),
    ("Resources", "Browse all InterviewIQ tools and guides.", "resources.resource_hub", ""),
    ("Blog", "Read short, practical career notes.", "resources.blog", ""),
    ("Help", "Find answers to common questions.", "resources.help_center", ""),
]


def _render_tool(tool, result=None, error=None, form_data=None, match=None, resume_data=None, alignment=None):
    return render_template(
        "RESOURCES/tool.html",
        tool=tool,
        title=TOOL_TITLES[tool],
        result=result,
        error=error,
        form_data=form_data or {},
        match=match,
        resume_data=resume_data,
        alignment=alignment,
        resources=RESOURCES,
    )


@resources_bp.get("/resources")
def resource_hub():
    return render_template(
        "RESOURCES/hub.html",
        title="Career Resources",
        resources=RESOURCES,
        pages=RESOURCE_PAGES,
    )


@resources_bp.get("/blog")
def blog():
    return render_template(
        "RESOURCES/page.html",
        slug="blog",
        page=RESOURCE_PAGES["blog"],
        pages=RESOURCE_PAGES,
        resources=RESOURCES,
    )


@resources_bp.get("/help")
def help_center():
    return render_template(
        "RESOURCES/page.html",
        slug="help",
        page=RESOURCE_PAGES["help"],
        pages=RESOURCE_PAGES,
        resources=RESOURCES,
    )


@resources_bp.get("/career-guides/<slug>")
@resources_bp.get("/resume-templates", defaults={"slug": "resume-templates"})
@resources_bp.get("/resume-examples", defaults={"slug": "resume-examples"})
@resources_bp.get("/ats-resume-score-guide", defaults={"slug": "ats-resume-score-guide"})
@resources_bp.get("/cover-letter-examples", defaults={"slug": "cover-letter-examples"})
@resources_bp.get("/resume-writing-guide", defaults={"slug": "resume-writing-guide"})
def resource_page(slug):
    page = RESOURCE_PAGES.get(slug)
    if page is None:
        abort(404)
    return render_template(
        "RESOURCES/page.html",
        slug=slug,
        page=page,
        pages=RESOURCE_PAGES,
        resources=RESOURCES,
    )


@resources_bp.route("/europass-cv-builder", endpoint="europass_cv_builder", methods=["GET", "POST"])
@resources_bp.route("/resume-builder", methods=["GET", "POST"])
def resume_builder():
    tool = "europass-cv-builder" if request.path.endswith("europass-cv-builder") else "resume-builder"
    if request.method == "GET":
        return _render_tool(tool)

    if tool == "resume-builder":
        scalar_fields = ("name", "role", "email", "phone", "location", "template", "summary", "skills", "certifications", "links", "job_description")
        values = {key: request.form.get(key, "").strip() for key in scalar_fields}
        values["template"] = values["template"] if values["template"] in {"classic", "modern", "compact"} else "modern"
        repeaters = {
            "work_entries": ("work_role", "work_company", "work_dates", "work_achievements"),
            "education_entries": ("education_degree", "education_school", "education_dates", "education_details"),
            "project_entries": ("project_name", "project_technologies", "project_details"),
        }
        form_data = {**values}
        for form_key, field_names in repeaters.items():
            field_values = [request.form.getlist(field_name) for field_name in field_names]
            if len({len(items) for items in field_values}) != 1:
                return _render_tool(tool, error="Some repeated resume fields were incomplete. Please review your entries.", form_data=form_data), 400
            form_data[form_key] = [
                dict(zip(field_names, entry))
                for entry in zip(*field_values)
            ]
        all_values = list(values.values()) + [
            value
            for form_key in repeaters
            for entry in form_data[form_key]
            for value in entry.values()
        ]
        if any(len(value) > 5000 for value in all_values):
            return _render_tool(tool, error="Each resume section or entry must be 5,000 characters or fewer.", form_data=form_data), 400
        if any(len(form_data[key]) > 6 for key in repeaters):
            return _render_tool(tool, error="You can add up to six entries in each repeatable section.", form_data=form_data), 400
        if not values["name"] or not values["role"]:
            return _render_tool(tool, error="Add your name and target role to create a useful draft.", form_data=form_data), 400

        skills = [skill.strip() for skill in values["skills"].replace("\n", ",").split(",") if skill.strip()]
        sections = []
        if values["summary"]:
            sections.append({"title": "Professional summary", "text": values["summary"]})
        if skills:
            sections.append({"title": "Skills", "skills": skills})
        work_entries = [
            {
                "heading": " — ".join(filter(None, (entry["work_role"], entry["work_company"]))),
                "dates": entry["work_dates"],
                "details": entry["work_achievements"],
            }
            for entry in form_data["work_entries"]
            if any(entry.values())
        ]
        if work_entries:
            sections.append({"title": "Experience", "items": work_entries})
        education_entries = [
            {
                "heading": " — ".join(filter(None, (entry["education_degree"], entry["education_school"]))),
                "dates": entry["education_dates"],
                "details": entry["education_details"],
            }
            for entry in form_data["education_entries"]
            if any(entry.values())
        ]
        if education_entries:
            sections.append({"title": "Education", "items": education_entries})
        project_entries = [
            {
                "heading": entry["project_name"],
                "dates": entry["project_technologies"],
                "details": entry["project_details"],
            }
            for entry in form_data["project_entries"]
            if any(entry.values())
        ]
        if project_entries:
            sections.append({"title": "Selected projects", "items": project_entries})
        for title, key in (("Certifications", "certifications"), ("Additional links", "links")):
            items = [item.strip() for item in values[key].splitlines() if item.strip()]
            if items:
                sections.append({"title": title, "skills": items})

        contact = " · ".join(filter(None, (values["email"], values["phone"], values["location"])))
        lines = [values["name"], values["role"], contact]
        for section in sections:
            lines.extend(["", section["title"].upper()])
            if "text" in section:
                lines.append(section["text"])
            elif "skills" in section:
                lines.append(" · ".join(section["skills"]))
            else:
                for item in section["items"]:
                    if item["heading"]:
                        lines.append(item["heading"])
                    if item["dates"]:
                        lines.append(item["dates"])
                    if item["details"]:
                        lines.append(item["details"])
        result = "\n".join(line for line in lines if line is not None).strip()
        if len(result) > 50000:
            return _render_tool(tool, error="This draft is too long to export. Shorten some sections and try again.", form_data=form_data), 400

        resume_data = {
            "name": values["name"],
            "role": values["role"],
            "contact": contact,
            "template": values["template"],
            "sections": sections,
        }
        target_skills = extract_skills(values["job_description"]) if values["job_description"] else []
        resume_skills = set(extract_skills(" ".join((values["summary"], values["skills"], result))))
        matched_skills = sorted(resume_skills.intersection(target_skills))
        alignment = {
            "matched": matched_skills,
            "missing": sorted(set(target_skills) - set(matched_skills)),
            "checked": bool(values["job_description"]),
        }
        return _render_tool(
            tool,
            result=result,
            form_data=form_data,
            resume_data=resume_data,
            alignment=alignment,
        )

    fields = [
        ("Full name", "name"),
        ("Email", "email"),
        ("Phone", "phone"),
        ("Location", "location"),
        ("Target role", "role"),
        ("Professional summary", "summary"),
        ("Skills", "skills"),
        ("Experience", "experience"),
        ("Education", "education"),
        ("Projects", "projects"),
    ]
    if tool == "europass-cv-builder":
        fields.extend(
            [
                ("Languages", "languages"),
                ("Digital skills", "digital_skills"),
                ("Nationality (optional)", "nationality"),
                ("Date of birth (optional)", "date_of_birth"),
            ]
        )
    values = {key: request.form.get(key, "").strip() for _, key in fields}
    if any(len(value) > 10000 for value in values.values()):
        return _render_tool(tool, error="Each section must be 10,000 characters or fewer.", form_data=values), 400
    if not values["name"] or not values["role"]:
        return _render_tool(tool, error="Add your name and target role to create a useful draft.", form_data=values), 400

    lines = [values["name"], " | ".join(filter(None, (values["email"], values["phone"], values["location"]))), "", values["role"]]
    for label, key in fields[5:]:
        if values[key]:
            lines.extend(["", label.upper(), values[key]])
    output = "\n".join(lines).strip()
    return _render_tool(tool, result=output, form_data=values)


@resources_bp.route("/job-fit-checker", methods=["GET", "POST"])
def job_fit_checker():
    if request.method == "GET":
        return _render_tool("job-fit-checker")
    resume_text = request.form.get("resume_text", "").strip()
    job_description = request.form.get("job_description", "").strip()
    form_data = {"resume_text": resume_text, "job_description": job_description}
    if not resume_text or not job_description:
        return _render_tool("job-fit-checker", error="Paste both resume text and a job description.", form_data=form_data), 400
    if len(resume_text) > 20000 or len(job_description) > 20000:
        return _render_tool("job-fit-checker", error="Each text field must be 20,000 characters or fewer.", form_data=form_data), 400
    skills = ", ".join(extract_skills(job_description))
    match = calculate_match(resume_text, job_description, skills)
    return _render_tool("job-fit-checker", result=match, match=match, form_data=form_data)


@resources_bp.route("/salary-insights", methods=["GET", "POST"])
def salary_insights():
    if request.method == "GET":
        return _render_tool("salary-insights")
    currency = request.form.get("currency", "USD").strip().upper()
    if currency not in {"USD", "EUR", "GBP", "INR", "CAD", "AUD"}:
        return _render_tool("salary-insights", error="Choose a supported currency."), 400
    try:
        current = float(request.form.get("current_salary", ""))
        target = float(request.form.get("target_salary", ""))
    except ValueError:
        return _render_tool("salary-insights", error="Enter a valid current and target annual salary."), 400
    if not (0 < current <= 1_000_000_000 and 0 < target <= 1_000_000_000):
        return _render_tool("salary-insights", error="Enter annual amounts greater than zero and below one billion."), 400
    difference = target - current
    result = {
        "currency": currency,
        "current": f"{current:,.2f}",
        "target": f"{target:,.2f}",
        "difference": f"{difference:+,.2f}",
        "percentage": round(difference / current * 100, 1),
    }
    return _render_tool("salary-insights", result=result, form_data=request.form)


@resources_bp.route("/cover-letter-generator", methods=["GET", "POST"])
def cover_letter_generator():
    if request.method == "GET":
        return _render_tool("cover-letter-generator")
    values = {
        key: request.form.get(key, "").strip()
        for key in ("name", "role", "company", "evidence", "motivation")
    }
    if not values["name"] or not values["role"] or not values["company"]:
        return _render_tool("cover-letter-generator", error="Add your name, target role, and company.", form_data=values), 400
    if any(len(value) > 5000 for value in values.values()):
        return _render_tool("cover-letter-generator", error="Each field must be 5,000 characters or fewer.", form_data=values), 400
    evidence = values["evidence"] or "my experience and the skills I have developed"
    motivation = values["motivation"] or f"the opportunity to contribute to {values['company']}"
    result = (
        f"Dear Hiring Team,\n\n"
        f"I am writing to apply for the {values['role']} position at {values['company']}. "
        f"I am interested in this opportunity because of {motivation.rstrip('.')}.\n\n"
        f"In my background, {evidence.rstrip('.')}. I would welcome the opportunity to discuss "
        f"how my experience could support your team and its goals.\n\n"
        f"Thank you for your consideration. I look forward to hearing from you.\n\n"
        f"Sincerely,\n{values['name']}"
    )
    return _render_tool("cover-letter-generator", result=result, form_data=values)


@resources_bp.route("/linkedin-optimizer", methods=["GET", "POST"])
def linkedin_optimizer():
    if request.method == "GET":
        return _render_tool("linkedin-optimizer")
    values = {
        key: request.form.get(key, "").strip()
        for key in ("name", "role", "skills", "about")
    }
    if not values["role"]:
        return _render_tool("linkedin-optimizer", error="Add the role or professional direction you want to target.", form_data=values), 400
    if any(len(value) > 5000 for value in values.values()):
        return _render_tool("linkedin-optimizer", error="Each field must be 5,000 characters or fewer.", form_data=values), 400
    skills = ", ".join(part.strip() for part in values["skills"].split(",") if part.strip())
    headline_parts = [values["role"]]
    if skills:
        headline_parts.append(skills)
    if values["name"]:
        headline_parts.append(values["name"])
    about = values["about"] or "Add a short, first-person summary of your experience and strongest evidence."
    result = {
        "headline": " | ".join(headline_parts),
        "about": f"I am a {values['role']} focused on {skills or '[your key strengths]'}. {about}\n\nI am interested in opportunities where I can apply my experience, keep learning, and contribute to meaningful outcomes.",
    }
    return _render_tool("linkedin-optimizer", result=result, form_data=values)


@resources_bp.get("/resume-analyzer")
def resume_analyzer():
    if session.get("user_id"):
        return redirect(url_for("workspace.resume_tools", view="analyzer"))
    return redirect(url_for("auth.register"))


@resources_bp.get("/interview-prep")
def interview_prep():
    if session.get("user_id"):
        return redirect(url_for("workspace.interview"))
    return redirect(url_for("auth.login"))


@resources_bp.post("/download-draft")
def download_draft():
    draft = request.form.get("draft", "")
    draft_type = request.form.get("draft_type", "")
    filenames = {
        "resume": "interviewiq-resume-draft.txt",
        "europass-cv": "interviewiq-europass-cv-draft.txt",
        "cover-letter": "interviewiq-cover-letter-draft.txt",
        "linkedin-profile": "interviewiq-linkedin-profile-draft.txt",
    }
    if draft_type not in filenames or not draft.strip() or len(draft) > 50000:
        abort(400)
    response = make_response(draft)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{filenames[draft_type]}"'
    response.headers["Cache-Control"] = "no-store"
    return response
