# ResumeChecker

ResumeChecker is a purple-grey AI resume analysis website with a Flask REST API backend.

## Backend features

- PDF/DOCX resume parsing
- Resume scoring
- Resume section detection
- Skill extraction
- ATS-oriented suggestions
- Job description matching
- Missing skill detection
- Gemini interview question generation
- Gemini interview answer evaluation
- SQLite persistence
- Upload validation
- 10 MB upload limit
- Temporary upload cleanup
- REST API

## Installation

Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put your Gemini API key inside `.env`. The default model is `gemini-2.0-flash`, which is valid for the `google-genai` SDK.

Then run:

```bash
python app.py
```

Open:

http://127.0.0.1:5000

## API endpoints

### Health

GET `/api/health`

### Resume analysis

POST `/api/resume/analyze`

Form-data:

`resume = resume.pdf`

### Job matching

POST `/api/job/match`

Form-data:

`resume = resume.pdf`

`job_description = Python developer with SQL...`

### Generate interview question

POST `/api/interview/question`

JSON:

```json
{
  "resume_text": "Resume text...",
  "type": "Technical"
}
```

### Evaluate answer

POST `/api/interview/evaluate`

JSON:

```json
{
  "question": "Explain your project.",
  "answer": "I built..."
}
```

### History

GET `/api/history`

## Production upgrades

For deployment, add authentication, PostgreSQL, Redis/background jobs, rate limiting, cloud file storage, OCR for scanned resumes, monitoring, and a production WSGI server.

## OTP sign-up + accounts (new)
Run `pip install -r requirements.txt`, copy `.env.example` to `.env`, then `python app.py`
and open http://127.0.0.1:5000/workspace

- `POST /api/otp/send` `{channel:"email"|"phone", destination}` – sends a 6-digit code
- `POST /api/otp/verify` `{channel, destination, code}` – returns a signed token
- `POST /api/auth/register` `{name,email,phone,password,token}` – needs a valid token
- `POST /api/auth/login` `{email,password}`

Security: codes are stored hashed, expire in 5 min, 5 wrong tries, 30 s resend gap, 5 sends/hour,
single use. Passwords are hashed with Werkzeug. Set a strong `SECRET_KEY`, and never use
`OTP_DEV_MODE=1` in production (it prints codes to the console instead of sending them).
Email uses any SMTP server; SMS uses Twilio (your own account and sender number).

## Folder guide
- app.py, services/, templates/, static/ — Flask backend (resume analysis, job match, AI interview, OTP, accounts)
- templates/workspace.html — the full app (lamp login, OTP sign-up, projects, artifacts, 22 AI tools, owner console)
- standalone/index.html — the same app as a single file (for Claude's page; AI, Claude sign-in and downloads need the Claude runtime)
