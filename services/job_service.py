import re
from .resume_service import SKILLS

def match_job(resume_text, job_description):
    resume = resume_text.lower()
    job = job_description.lower()

    required_skills = sorted({
        skill for skill in SKILLS
        if skill in job
    })

    matched = [
        skill for skill in required_skills
        if skill in resume
    ]

    missing = [
        skill for skill in required_skills
        if skill not in resume
    ]

    if required_skills:
        score = round(
            len(matched) / len(required_skills) * 100
        )
    else:
        resume_words = set(
            re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{3,}", resume)
        )
        job_words = set(
            re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{3,}", job)
        )

        overlap = len(resume_words & job_words)
        score = round(
            overlap / max(1, len(job_words)) * 100
        )

    return {
        "match_score": min(score, 100),
        "required_skills": required_skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "recommended_actions": [
            "Prioritize genuine missing skills.",
            "Use job-description terminology when it truthfully matches your experience.",
            "Add project or experience evidence for important skills."
        ]
    }
