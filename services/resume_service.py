import re
from pypdf import PdfReader
from docx import Document

SKILLS = [
    "python", "java", "c++", "c#", "javascript", "typescript",
    "react", "node.js", "html", "css", "sql", "mongodb",
    "postgresql", "mysql", "machine learning", "deep learning",
    "generative ai", "llm", "nlp", "git", "github", "docker",
    "aws", "azure", "gcp", "fastapi", "flask", "django",
    "streamlit", "tensorflow", "pytorch", "pandas", "numpy",
    "scikit-learn", "langchain", "rag"
]

def extract_resume_text(path, filename):
    extension = filename.lower().rsplit(".", 1)[-1]

    if extension == "pdf":
        reader = PdfReader(path)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    if extension == "docx":
        document = Document(path)
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

    raise ValueError("Unsupported file format.")

def analyze_resume(text):
    lower = text.lower()

    sections = {
        "Contact": bool(
            re.search(r"@", lower)
            and re.search(r"\+?\d[\d\s().-]{8,}", lower)
        ),
        "Summary": bool(
            re.search(r"\b(summary|objective|profile)\b", lower)
        ),
        "Education": "education" in lower,
        "Experience": bool(
            re.search(
                r"\b(experience|employment|work history)\b",
                lower
            )
        ),
        "Projects": bool(
            re.search(r"\bprojects?\b", lower)
        ),
        "Skills": bool(
            re.search(r"\bskills?\b", lower)
        )
    }

    skills = sorted({
        skill for skill in SKILLS
        if skill in lower
    })

    quantified = len(re.findall(
        r"\b\d+(?:\.\d+)?\s*%|\b\d+\+?\s*"
        r"(?:users|projects|months|years|students)\b",
        lower
    ))

    action_verbs = len(re.findall(
        r"\b(built|developed|created|designed|implemented|"
        r"optimized|automated|led|deployed|improved|engineered)\b",
        lower
    ))

    score = 35
    score += min(len(skills) * 2, 22)
    score += sum(5 for value in sections.values() if value)
    score += min(quantified * 3, 12)
    score += min(action_verbs, 8)
    score = min(score, 100)

    suggestions = [
        "Use consistent headings and a simple ATS-friendly layout.",
        "Tailor your resume keywords to the target job.",
        "Add measurable results to important experience and project bullets."
    ]

    if not sections["Summary"]:
        suggestions.append(
            "Add a concise 2–3 line professional summary."
        )

    if not sections["Projects"]:
        suggestions.append(
            "Add relevant projects with technologies and outcomes."
        )

    if quantified == 0:
        suggestions.append(
            "Add numbers such as percentage improvement, users, "
            "accuracy, scale, or time saved."
        )

    return {
        "score": score,
        "skills": skills,
        "sections": sections,
        "word_count": len(text.split()),
        "quantified_bullets": quantified,
        "action_verbs": action_verbs,
        "suggestions": suggestions
    }
