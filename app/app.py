"""
Medical Clinic Appointment Booking System
AWS Cloud Computing Project — Spring 25/26
AASTMT – Computer Engineering Department

LOCAL MODE: Works without RDS — uses in-memory fallback data.
PRODUCTION: Set DB_HOST env variable to your RDS endpoint.
"""

import os
import hashlib
from datetime import datetime, date, timedelta
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "medibook-local-secret-key-2526")

# ─── AWS / DB configuration ──────────────────────────────────────────────────
DB_HOST     = os.environ.get("DB_HOST", "")          # empty = local/demo mode
DB_USER     = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME", "clinic_db")

AWS_REGION    = os.environ.get("AWS_REGION", "us-east-1")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
S3_BUCKET       = os.environ.get("S3_BUCKET_NAME", "")
CLOUDFRONT_URL  = os.environ.get("CLOUDFRONT_URL", "").rstrip("/")

# ─── Fallback in-memory data (used when no RDS is configured) ─────────────────
FALLBACK_DOCTORS = [
    {"id": 1, "name": "Sara Ahmed",   "specialty": "Cardiology",           "bio": "Board-certified cardiologist with 10+ years experience."},
    {"id": 2, "name": "Omar Khalil",  "specialty": "Neurology",            "bio": "Specialist in neurological disorders and stroke management."},
    {"id": 3, "name": "Nada Hassan",  "specialty": "Dermatology",          "bio": "Expert in skin conditions, acne, and cosmetic procedures."},
    {"id": 4, "name": "Youssef Taha", "specialty": "Orthopedics",          "bio": "Orthopedic surgeon focused on sports injuries and joint care."},
    {"id": 5, "name": "Hana Mostafa", "specialty": "Pediatrics",           "bio": "Dedicated pediatrician providing care from birth to age 18."},
    {"id": 6, "name": "Karim Saber",  "specialty": "General Practitioner", "bio": "Family medicine physician for comprehensive primary care."},
]

# In-memory stores for local demo mode
_local_users = {
    "sara@clinic.com":    {"id": 1, "name": "Sara Ahmed",   "role": "doctor",   "password_hash": hashlib.sha256(b"password123").hexdigest(), "specialty": "Cardiology"},
    "omar@clinic.com":    {"id": 2, "name": "Omar Khalil",  "role": "doctor",   "password_hash": hashlib.sha256(b"password123").hexdigest(), "specialty": "Neurology"},
    "nada@clinic.com":    {"id": 3, "name": "Nada Hassan",  "role": "doctor",   "password_hash": hashlib.sha256(b"password123").hexdigest(), "specialty": "Dermatology"},
    "youssef@clinic.com": {"id": 4, "name": "Youssef Taha", "role": "doctor",   "password_hash": hashlib.sha256(b"password123").hexdigest(), "specialty": "Orthopedics"},
    "hana@clinic.com":    {"id": 5, "name": "Hana Mostafa", "role": "doctor",   "password_hash": hashlib.sha256(b"password123").hexdigest(), "specialty": "Pediatrics"},
    "karim@clinic.com":   {"id": 6, "name": "Karim Saber",  "role": "doctor",   "password_hash": hashlib.sha256(b"password123").hexdigest(), "specialty": "General Practitioner"},
}
_next_user_id   = 100
_local_appointments = []   # {"id", "patient_id", "doctor_id", "appointment_date", "time_slot", "status"}
_next_appt_id   = 1

SLOT_TIMES = ["09:00","09:30","10:00","10:30","11:00","11:30",
              "13:00","13:30","14:00","14:30","15:00","15:30","16:00","16:30"]

def is_local_mode():
    return not DB_HOST


@app.context_processor
def inject_globals():
    """CloudFront base URL for S3-hosted static assets (production)."""
    def static_url(path: str) -> str:
        path = path.lstrip("/")
        if CLOUDFRONT_URL:
            return f"{CLOUDFRONT_URL}/static/{path}"
        return url_for("static", filename=path)

    return {
        "static_url": static_url,
        "cloudfront_enabled": bool(CLOUDFRONT_URL),
        "deployment_mode": "local" if is_local_mode() else "aws",
    }

# ─── Database helpers ─────────────────────────────────────────────────────────
def get_db():
    import pymysql
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5
    )

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ─── AWS helpers ──────────────────────────────────────────────────────────────
def send_sns_notification(email: str, subject: str, message: str):
    if not SNS_TOPIC_ARN:
        app.logger.info(f"[LOCAL] SNS skipped — would send to {email}: {subject}")
        return True
    try:
        import boto3
        sns = boto3.client("sns", region_name=AWS_REGION)
        body = f"To: {email}\n\n{message}"
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=body)
        return True
    except Exception as e:
        app.logger.error(f"SNS error: {e}")
        return False

# ─── Auth decorators ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def doctor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "doctor":
            flash("Access denied — doctors only.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES — Public
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    specialty = request.args.get("specialty", "")   # FIX: always defined first

    if is_local_mode():
        doctors = [d for d in FALLBACK_DOCTORS if not specialty or d["specialty"] == specialty]
        specialties = sorted({d["specialty"] for d in FALLBACK_DOCTORS})
    else:
        try:
            db = get_db()
            with db.cursor() as cur:
                if specialty:
                    cur.execute("SELECT id, name, specialty, bio FROM users "
                                "WHERE role='doctor' AND specialty=%s ORDER BY name", (specialty,))
                else:
                    cur.execute("SELECT id, name, specialty, bio FROM users "
                                "WHERE role='doctor' ORDER BY name")
                doctors = cur.fetchall()
                cur.execute("SELECT DISTINCT specialty FROM users WHERE role='doctor' ORDER BY specialty")
                specialties = [r["specialty"] for r in cur.fetchall()]
            db.close()
        except Exception as e:
            app.logger.error(f"DB error on index: {e}")
            doctors = FALLBACK_DOCTORS
            specialties = sorted({d["specialty"] for d in FALLBACK_DOCTORS})

    return render_template("index.html", doctors=doctors,
                           specialties=specialties, selected=specialty)


@app.route("/register", methods=["GET", "POST"])
def register():
    global _next_user_id
    if request.method == "POST":
        name      = request.form["name"].strip()
        email     = request.form["email"].strip().lower()
        password  = request.form["password"]
        role      = request.form.get("role", "patient")
        specialty = request.form.get("specialty", "").strip()

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if is_local_mode():
            if email in _local_users:
                flash("Email already registered.", "warning")
                return render_template("register.html")
            _local_users[email] = {
                "id": _next_user_id, "name": name, "role": role,
                "password_hash": hash_password(password), "specialty": specialty
            }
            _next_user_id += 1
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))

        try:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                if cur.fetchone():
                    flash("Email already registered.", "warning")
                    db.close()
                    return render_template("register.html")
                cur.execute("INSERT INTO users (name, email, password_hash, role, specialty) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (name, email, hash_password(password), role, specialty))
                db.commit()
            db.close()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            app.logger.error(f"Register error: {e}")
            flash("Registration failed. Try again.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"].strip().lower()
        password = request.form["password"]

        if is_local_mode():
            u = _local_users.get(email)
            if u and u["password_hash"] == hash_password(password):
                session["user_id"] = u["id"]
                session["name"]    = u["name"]
                session["role"]    = u["role"]
                session["email"]   = email
                flash(f"Welcome back, {u['name']}!", "success")
                return redirect(url_for("doctor_dashboard") if u["role"] == "doctor" else url_for("index"))
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        try:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT id, name, role FROM users WHERE email=%s AND password_hash=%s",
                            (email, hash_password(password)))
                user = cur.fetchone()
            db.close()
            if user:
                session["user_id"] = user["id"]
                session["name"]    = user["name"]
                session["role"]    = user["role"]
                session["email"]   = email
                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for("doctor_dashboard") if user["role"] == "doctor" else url_for("index"))
            flash("Invalid email or password.", "danger")
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash("Login failed. Try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES — Patient
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/patient/dashboard")
@login_required
def patient_dashboard():
    if is_local_mode():
        uid = session["user_id"]
        appts = []
        for a in _local_appointments:
            if a["patient_id"] == uid:
                doc = next((d for d in FALLBACK_DOCTORS if d["id"] == a["doctor_id"]), {})
                appts.append({**a, "doctor_name": doc.get("name",""), "specialty": doc.get("specialty","")})
        return render_template("patient_dashboard.html", appointments=appts)

    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""SELECT a.id, a.appointment_date, a.time_slot, a.status,
                                  u.name AS doctor_name, u.specialty
                           FROM appointments a JOIN users u ON a.doctor_id=u.id
                           WHERE a.patient_id=%s ORDER BY a.appointment_date DESC""",
                        (session["user_id"],))
            appointments = cur.fetchall()
        db.close()
    except Exception as e:
        app.logger.error(f"Patient dashboard error: {e}")
        appointments = []
    return render_template("patient_dashboard.html", appointments=appointments)


@app.route("/book/<int:doctor_id>", methods=["GET", "POST"])
@login_required
def book(doctor_id):
    global _next_appt_id
    if session.get("role") == "doctor":
        flash("Doctors cannot book appointments.", "warning")
        return redirect(url_for("index"))

    if is_local_mode():
        doctor = next((d for d in FALLBACK_DOCTORS if d["id"] == doctor_id), None)
        if not doctor:
            flash("Doctor not found.", "danger")
            return redirect(url_for("index"))

        if request.method == "POST":
            appt_date = request.form["appointment_date"]
            time_slot = request.form["time_slot"]
            # Check double-booking
            conflict = any(a["doctor_id"] == doctor_id and
                           a["appointment_date"] == appt_date and
                           a["time_slot"] == time_slot and
                           a["status"] != "cancelled"
                           for a in _local_appointments)
            if conflict:
                flash("That slot is already taken. Please choose another.", "warning")
            else:
                _local_appointments.append({
                    "id": _next_appt_id, "patient_id": session["user_id"],
                    "doctor_id": doctor_id, "appointment_date": appt_date,
                    "time_slot": time_slot, "status": "scheduled"
                })
                _next_appt_id += 1
                patient_email = session.get("email", "")
                if patient_email:
                    send_sns_notification(
                        patient_email,
                        "Appointment Confirmed — MediBook",
                        f"Dear {session['name']},\n\nYour appointment with Dr. {doctor['name']} "
                        f"({doctor['specialty']}) is confirmed for {appt_date} at {time_slot}.\n\nMediBook"
                    )
                flash("Appointment booked! Check your email for confirmation.", "success")
                return redirect(url_for("patient_dashboard"))

        # Build available slots
        today = date.today()
        available_slots = {}
        for i in range(1, 8):
            d = (today + timedelta(days=i)).isoformat()
            taken = {a["time_slot"] for a in _local_appointments
                     if a["doctor_id"] == doctor_id and a["appointment_date"] == d and a["status"] != "cancelled"}
            available_slots[d] = [t for t in SLOT_TIMES if t not in taken]
        return render_template("book.html", doctor=doctor, available_slots=available_slots)

    # ── RDS mode ──
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT id, name, specialty FROM users WHERE id=%s AND role='doctor'", (doctor_id,))
            doctor = cur.fetchone()
        if not doctor:
            flash("Doctor not found.", "danger")
            db.close()
            return redirect(url_for("index"))

        if request.method == "POST":
            appt_date = request.form["appointment_date"]
            time_slot = request.form["time_slot"]
            with db.cursor() as cur:
                cur.execute("SELECT id FROM appointments WHERE doctor_id=%s AND appointment_date=%s "
                            "AND time_slot=%s AND status!='cancelled'", (doctor_id, appt_date, time_slot))
                if cur.fetchone():
                    flash("That slot is already taken.", "warning")
                else:
                    cur.execute("INSERT INTO appointments (patient_id,doctor_id,appointment_date,time_slot,status) "
                                "VALUES (%s,%s,%s,%s,'scheduled')",
                                (session["user_id"], doctor_id, appt_date, time_slot))
                    db.commit()
                    cur.execute("SELECT email FROM users WHERE id=%s", (session["user_id"],))
                    row = cur.fetchone()
                    if row:
                        send_sns_notification(row["email"], "Appointment Confirmed",
                            f"Dear {session['name']},\nAppointment with Dr. {doctor['name']} "
                            f"confirmed for {appt_date} at {time_slot}.\n\nMediBook")
                    flash("Appointment booked! Check your email.", "success")
                    db.close()
                    return redirect(url_for("patient_dashboard"))

        today = date.today()
        available_slots = {}
        with db.cursor() as cur:
            for i in range(1, 8):
                d = (today + timedelta(days=i)).isoformat()
                cur.execute("SELECT time_slot FROM appointments WHERE doctor_id=%s "
                            "AND appointment_date=%s AND status!='cancelled'", (doctor_id, d))
                taken = {r["time_slot"] for r in cur.fetchall()}
                available_slots[d] = [t for t in SLOT_TIMES if t not in taken]
        db.close()
        return render_template("book.html", doctor=doctor, available_slots=available_slots)
    except Exception as e:
        app.logger.error(f"Book error: {e}")
        flash("Booking error. Try again.", "danger")
        return redirect(url_for("index"))


@app.route("/appointment/cancel/<int:appt_id>", methods=["POST"])
@login_required
def cancel_appointment(appt_id):
    if is_local_mode():
        for a in _local_appointments:
            if a["id"] == appt_id and a["patient_id"] == session["user_id"]:
                a["status"] = "cancelled"
                break
        flash("Appointment cancelled.", "info")
        return redirect(url_for("patient_dashboard"))

    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("UPDATE appointments SET status='cancelled' WHERE id=%s AND patient_id=%s",
                        (appt_id, session["user_id"]))
            db.commit()
        db.close()
        flash("Appointment cancelled.", "info")
    except Exception as e:
        app.logger.error(f"Cancel error: {e}")
        flash("Could not cancel. Try again.", "danger")
    return redirect(url_for("patient_dashboard"))


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES — Doctor
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/doctor/dashboard")
@login_required
@doctor_required
def doctor_dashboard():
    view_date = request.args.get("date", date.today().isoformat())

    if is_local_mode():
        uid = session["user_id"]
        appts = []
        for a in _local_appointments:
            if a["doctor_id"] == uid and a["appointment_date"] == view_date:
                # find patient name
                patient = next((u for u in _local_users.values() if u["id"] == a["patient_id"]), {})
                appts.append({**a, "patient_name": patient.get("name","Unknown"),
                              "patient_email": next((e for e,u in _local_users.items() if u["id"]==a["patient_id"]),"")})
        return render_template("doctor_dashboard.html", appointments=appts, view_date=view_date)

    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""SELECT a.id, a.appointment_date, a.time_slot, a.status,
                                  u.name AS patient_name, u.email AS patient_email
                           FROM appointments a JOIN users u ON a.patient_id=u.id
                           WHERE a.doctor_id=%s AND a.appointment_date=%s ORDER BY a.time_slot""",
                        (session["user_id"], view_date))
            appointments = cur.fetchall()
        db.close()
    except Exception as e:
        app.logger.error(f"Doctor dashboard error: {e}")
        appointments = []
    return render_template("doctor_dashboard.html", appointments=appointments, view_date=view_date)


@app.route("/doctor/appointment/<int:appt_id>/status", methods=["POST"])
@login_required
@doctor_required
def update_appointment_status(appt_id):
    new_status = request.form.get("status")
    if new_status not in {"scheduled","completed","cancelled","no-show"}:
        flash("Invalid status.", "danger")
        return redirect(url_for("doctor_dashboard"))

    if is_local_mode():
        for a in _local_appointments:
            if a["id"] == appt_id:
                a["status"] = new_status
                break
        flash(f"Appointment marked as {new_status}.", "success")
        return redirect(url_for("doctor_dashboard"))

    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("UPDATE appointments SET status=%s WHERE id=%s AND doctor_id=%s",
                        (new_status, appt_id, session["user_id"]))
            db.commit()
        db.close()
        flash(f"Appointment marked as {new_status}.", "success")
    except Exception as e:
        app.logger.error(f"Status update error: {e}")
        flash("Update failed.", "danger")
    return redirect(url_for("doctor_dashboard"))


# ─── API ─────────────────────────────────────────────────────────────────────
@app.route("/api/slots/<int:doctor_id>")
def api_slots(doctor_id):
    appt_date = request.args.get("date")
    if not appt_date:
        return jsonify({"error": "date required"}), 400
    if is_local_mode():
        taken = {a["time_slot"] for a in _local_appointments
                 if a["doctor_id"] == doctor_id and a["appointment_date"] == appt_date
                 and a["status"] != "cancelled"}
        return jsonify({"date": appt_date, "available": [t for t in SLOT_TIMES if t not in taken], "taken": list(taken)})
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT time_slot FROM appointments WHERE doctor_id=%s "
                        "AND appointment_date=%s AND status!='cancelled'", (doctor_id, appt_date))
            taken = {r["time_slot"] for r in cur.fetchall()}
        db.close()
        return jsonify({"date": appt_date, "available": [t for t in SLOT_TIMES if t not in taken], "taken": list(taken)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/architecture")
def architecture():
    services = [
        ("EC2", "Flask app (Gunicorn + Nginx), LabInstanceProfile"),
        ("RDS MySQL", "Users & appointments; double-booking prevention"),
        ("S3 + CloudFront", "Static CSS/assets via CDN"),
        ("Elastic Load Balancer", "Public URL, health checks on /health"),
        ("SNS", "Email booking confirmations"),
        ("CloudWatch", "Logs and alarms (CPU, storage, unhealthy hosts)"),
    ]
    return render_template("architecture.html", services=services)


@app.route("/health")
def health():
    mode = "local" if is_local_mode() else "rds"
    return jsonify({
        "status": "ok",
        "mode": mode,
        "region": AWS_REGION,
        "cloudfront": bool(CLOUDFRONT_URL),
        "sns": bool(SNS_TOPIC_ARN),
        "timestamp": datetime.utcnow().isoformat(),
    })


if __name__ == "__main__":
    if is_local_mode():
        print("=" * 55)
        print("  MediBook running in LOCAL MODE (no RDS needed)")
        print("  Demo logins:")
        print("    Patient : register any account")
        print("    Doctor  : sara@clinic.com / password123")
        print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=True)
