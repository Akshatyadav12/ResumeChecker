import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from services.resume_service import extract_resume_text, analyze_resume
from services.job_service import match_job
from services.ai_service import generate_interview_question, evaluate_interview_answer
from services.db import init_db, save_analysis, save_interview, get_history
from services.otp_service import init_otp, send_code, verify_code, normalize, create_user, get_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = "uploads"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs("data", exist_ok=True)
init_db()
init_otp()
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
_signer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

ALLOWED_EXTENSIONS = {"pdf", "docx"}

def validate_resume(file):
    if not file or not file.filename:
        return False, "Resume file is required."
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Only PDF and DOCX files are supported."
    return True, ""

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({
        "success": True,
        "service": "ResumeChecker API",
        "status": "healthy"
    })

@app.post("/api/resume/analyze")
def api_analyze_resume():
    file = request.files.get("resume")
    ok, error = validate_resume(file)
    if not ok:
        return jsonify({"success": False, "error": error}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        file.save(path)
        text = extract_resume_text(path, filename)

        if not text.strip():
            return jsonify({
                "success": False,
                "error": "No readable text was found in the resume."
            }), 422

        result = analyze_resume(text)
        analysis_id = save_analysis(filename, result["score"], result)

        return jsonify({
            "success": True,
            "analysis_id": analysis_id,
            "filename": filename,
            **result
        })

    except Exception as exc:
        app.logger.exception("Resume analysis failed")
        return jsonify({"success": False, "error": str(exc)}), 500

    finally:
        try:
            os.remove(path)
        except OSError:
            pass

@app.post("/api/job/match")
def api_job_match():
    file = request.files.get("resume")
    job_description = request.form.get("job_description", "").strip()

    ok, error = validate_resume(file)
    if not ok:
        return jsonify({"success": False, "error": error}), 400

    if not job_description:
        return jsonify({
            "success": False,
            "error": "job_description is required."
        }), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        file.save(path)
        resume_text = extract_resume_text(path, filename)

        if not resume_text.strip():
            return jsonify({
                "success": False,
                "error": "No readable resume text found."
            }), 422

        result = match_job(resume_text, job_description)

        return jsonify({
            "success": True,
            **result
        })

    except Exception as exc:
        app.logger.exception("Job matching failed")
        return jsonify({"success": False, "error": str(exc)}), 500

    finally:
        try:
            os.remove(path)
        except OSError:
            pass

@app.post("/api/interview/question")
def api_interview_question():
    data = request.get_json(silent=True) or {}

    resume_text = data.get("resume_text", "").strip()
    interview_type = data.get("type", "Technical")

    if not resume_text:
        return jsonify({
            "success": False,
            "error": "resume_text is required."
        }), 400

    try:
        result = generate_interview_question(
            resume_text,
            interview_type
        )
        return jsonify({
            "success": True,
            **result
        })
    except Exception as exc:
        app.logger.exception("Interview question generation failed")
        return jsonify({"success": False, "error": str(exc)}), 500

@app.post("/api/interview/evaluate")
def api_interview_evaluate():
    data = request.get_json(silent=True) or {}

    question = data.get("question", "").strip()
    answer = data.get("answer", "").strip()

    if not question or not answer:
        return jsonify({
            "success": False,
            "error": "question and answer are required."
        }), 400

    try:
        result = evaluate_interview_answer(question, answer)

        save_interview(
            question,
            answer,
            result.get("score", 0)
        )

        return jsonify({
            "success": True,
            **result
        })

    except Exception as exc:
        app.logger.exception("Interview evaluation failed")
        return jsonify({"success": False, "error": str(exc)}), 500

@app.get("/api/history")
def api_history():
    return jsonify({
        "success": True,
        "items": get_history()
    })


# ---------- OTP verification + accounts ----------
@app.post("/api/otp/send")
def api_otp_send():
    d = request.get_json(silent=True) or {}
    ok, msg = send_code(d.get("channel"), d.get("destination"))
    return jsonify({"success": ok, "message": msg}), (200 if ok else 400)

@app.post("/api/otp/verify")
def api_otp_verify():
    d = request.get_json(silent=True) or {}
    ok, msg = verify_code(d.get("channel"), d.get("destination"), d.get("code"))
    if not ok:
        return jsonify({"success": False, "error": msg}), 400
    dest = normalize(d.get("channel"), d.get("destination"))
    token = _signer.dumps({"channel": d.get("channel"), "dest": dest})
    return jsonify({"success": True, "token": token})

@app.post("/api/auth/register")
def api_register():
    d = request.get_json(silent=True) or {}
    try:
        proof = _signer.loads(d.get("token", ""), max_age=600)
    except (BadSignature, SignatureExpired):
        return jsonify({"success": False, "error": "Verification expired. Verify again."}), 400
    email, phone = normalize("email", d.get("email")), normalize("phone", d.get("phone"))
    if not email or not phone or len(d.get("password", "")) < 6 or not d.get("name"):
        return jsonify({"success": False, "error": "Name, email, phone and a 6+ character password are required."}), 400
    # the verified channel must match what is being registered
    if proof["dest"] not in (email, phone):
        return jsonify({"success": False, "error": "Verified contact does not match."}), 400
    ok, msg = create_user(d["name"].strip(), email, phone, generate_password_hash(d["password"]), proof["channel"])
    return jsonify({"success": ok, "message" if ok else "error": msg}), (200 if ok else 400)

@app.post("/api/auth/login")
def api_login():
    d = request.get_json(silent=True) or {}
    row = get_user((d.get("email") or "").strip().lower())
    if not row or not check_password_hash(row[4], d.get("password", "")):
        return jsonify({"success": False, "error": "Wrong email or password."}), 401
    return jsonify({"success": True, "user": {"name": row[1], "email": row[2], "phone": row[3], "verified": row[5]}})

@app.get("/workspace")
def workspace():
    return render_template("workspace.html")

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
