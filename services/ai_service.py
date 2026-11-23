import os
import json
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.0-flash"
)

client = genai.Client(
    api_key=API_KEY
) if API_KEY else None

def ask_ai(prompt):
    if not client:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Add it to your .env file."
        )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    return response.text or ""

def clean_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")

    return text.strip()

def generate_interview_question(resume_text, interview_type):
    prompt = f"""
Create ONE personalized {interview_type} interview question
based only on the resume below.

Do not invent experience.

Return valid JSON only:
{{
  "question": "...",
  "topic": "...",
  "difficulty": "easy|medium|hard"
}}

RESUME:
{resume_text[:12000]}
"""

    return json.loads(
        clean_json(ask_ai(prompt))
    )

def evaluate_interview_answer(question, answer):
    prompt = f"""
Evaluate this interview answer fairly and constructively.

Return valid JSON only:
{{
  "score": 0,
  "technical_score": 0,
  "communication_score": 0,
  "strengths": [],
  "weaknesses": [],
  "improvements": [],
  "better_approach": ""
}}

Question:
{question}

Answer:
{answer}
"""

    return json.loads(
        clean_json(ask_ai(prompt))
    )
