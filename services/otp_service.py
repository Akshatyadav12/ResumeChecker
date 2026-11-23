"""OTP (one-time code) verification for email and phone, plus account storage.

Codes are random 6-digit numbers, stored only as salted SHA-256 hashes, valid for
5 minutes, limited to 5 wrong tries, 30 s between sends and 5 sends per hour.
"""
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage

import requests

from services.db import connect

OTP_TTL = 300
COOLDOWN = 30
MAX_TRIES = 5
MAX_PER_HOUR = 5


def init_otp():
    con = connect()
    con.execute("""CREATE TABLE IF NOT EXISTS otp_codes(
        dest TEXT PRIMARY KEY, channel TEXT, code_hash TEXT, salt TEXT,
        expires REAL, tries INTEGER DEFAULT 0, last_sent REAL,
        hour_start REAL, sent_count INTEGER DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE,
        phone TEXT, password_hash TEXT, verified TEXT, created_at TEXT)""")
    con.commit()
    con.close()


def _hash(code, salt):
    return hashlib.sha256((salt + code).encode()).hexdigest()


def normalize(channel, dest):
    dest = (dest or "").strip()
    if channel == "email":
        dest = dest.lower()
        return dest if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", dest) else None
    if channel == "phone":
        dest = re.sub(r"[\s\-().]", "", dest)
        return dest if re.fullmatch(r"\+?\d{10,14}", dest) else None
    return None


def _send_email(to, code):
    host = os.getenv("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP is not configured (set SMTP_HOST, SMTP_USER, SMTP_PASS).")
    msg = EmailMessage()
    msg["Subject"] = "Your ResumeChecker verification code"
    msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", ""))
    msg["To"] = to
    msg.set_content(f"Your verification code is {code}. It expires in 5 minutes.\n"
                    "If you did not request it, ignore this email.")
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
        s.starttls()
        s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
        s.send_message(msg)


def _send_sms(to, code):
    sid, token, sender = (os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"),
                          os.getenv("TWILIO_FROM"))
    if not (sid and token and sender):
        raise RuntimeError("Twilio is not configured (set TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM).")
    r = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        auth=(sid, token), timeout=15,
        data={"To": to, "From": sender,
              "Body": f"Your ResumeChecker code is {code}. Valid for 5 minutes."})
    r.raise_for_status()


def send_code(channel, dest):
    dest = normalize(channel, dest)
    if not dest:
        return False, "Enter a valid email address or phone number."
    now = time.time()
    con = connect()
    row = con.execute("SELECT last_sent, hour_start, sent_count FROM otp_codes WHERE dest=?",
                      (dest,)).fetchone()
    hour_start, count = now, 0
    if row:
        last, hs, cnt = row
        if now - last < COOLDOWN:
            con.close()
            return False, f"Please wait {int(COOLDOWN - (now - last))}s before requesting another code."
        if now - hs < 3600:
            hour_start, count = hs, cnt
            if cnt >= MAX_PER_HOUR:
                con.close()
                return False, "Too many codes requested. Try again in an hour."
    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    try:
        if os.getenv("OTP_DEV_MODE") == "1":
            print(f"[OTP DEV MODE] code for {dest}: {code}")   # never enable in production
        elif channel == "email":
            _send_email(dest, code)
        else:
            _send_sms(dest, code)
    except Exception as exc:
        con.close()
        return False, f"Could not send the code: {exc}"
    con.execute("""INSERT OR REPLACE INTO otp_codes
        (dest, channel, code_hash, salt, expires, tries, last_sent, hour_start, sent_count)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (dest, channel, _hash(code, salt), salt, now + OTP_TTL, 0, now, hour_start, count + 1))
    con.commit()
    con.close()
    return True, "Code sent."


def verify_code(channel, dest, code):
    dest = normalize(channel, dest)
    if not dest:
        return False, "Invalid destination."
    con = connect()
    row = con.execute("SELECT code_hash, salt, expires, tries FROM otp_codes WHERE dest=?",
                      (dest,)).fetchone()
    if not row:
        con.close()
        return False, "No code was requested for this address."
    code_hash, salt, expires, tries = row
    if time.time() > expires:
        con.execute("DELETE FROM otp_codes WHERE dest=?", (dest,))
        con.commit(); con.close()
        return False, "That code has expired. Request a new one."
    if tries >= MAX_TRIES:
        con.close()
        return False, "Too many wrong attempts. Request a new code."
    if not hmac.compare_digest(code_hash, _hash(str(code).strip(), salt)):
        con.execute("UPDATE otp_codes SET tries=tries+1 WHERE dest=?", (dest,))
        con.commit(); con.close()
        return False, "Incorrect code."
    con.execute("DELETE FROM otp_codes WHERE dest=?", (dest,))   # single use
    con.commit(); con.close()
    return True, "Verified."


def create_user(name, email, phone, password_hash, verified):
    con = connect()
    try:
        con.execute("INSERT INTO users (name,email,phone,password_hash,verified,created_at) VALUES (?,?,?,?,?,?)",
                    (name, email, phone, password_hash, verified, datetime.now().isoformat()))
        con.commit()
        return True, "Account created."
    except Exception:
        return False, "An account with this email already exists."
    finally:
        con.close()


def get_user(email):
    con = connect()
    row = con.execute("SELECT id,name,email,phone,password_hash,verified FROM users WHERE email=?",
                      (email,)).fetchone()
    con.close()
    return row
