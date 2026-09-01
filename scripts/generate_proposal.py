"""
Generate Medical_Clinic_Proposal.pptx for the AWS Cloud Computing project.
Run: pip install python-pptx && python scripts/generate_proposal.py
"""
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
except ImportError:
    raise SystemExit("Install: pip install python-pptx")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Medical_Clinic_Proposal.pptx"

SLIDES = [
    ("MediBook — Medical Clinic Appointment System", [
        "AASTMT · Computer Engineering · Cloud Computing Project",
        "Spring 25/26 · Group project (3–4 students)",
        "Region: us-east-1 (N. Virginia) only",
    ]),
    ("Project overview & core goal", [
        "Build a web app where patients browse doctors, book time slots, and get email confirmations.",
        "Doctors log in to view daily schedules and update appointment status.",
        "Prove AWS skills by connecting compute, database, storage, messaging, load balancing, CDN, and monitoring.",
    ]),
    ("User perspective", [
        "Patient: Register → Login → Filter doctors by specialty → Pick date/time → Book → SNS email confirmation.",
        "Doctor: Login (seed accounts) → Open daily schedule → Mark completed / no-show / cancelled.",
        "Public: Browse doctors without login; booking requires a patient account.",
    ]),
    ("Architecture & AWS integration", [
        "EC2 (t2.micro) + LabInstanceProfile: Flask app (Gunicorn + Nginx).",
        "RDS MySQL (db.t3.micro): users, appointments; UNIQUE(doctor, date, slot) prevents double-booking.",
        "S3 + CloudFront: static CSS/images; ELB: public HTTP entry; health check /health.",
        "SNS: booking confirmation emails · CloudWatch: logs & CPU/storage alarms.",
        "IAM: LabRole (read-only) + LabInstanceProfile on EC2.",
    ]),
    ("How the system scales", [
        "ELB adds EC2 instances (up to 9 t2/t3 in sandbox) behind one DNS name.",
        "RDS holds shared state so all instances see the same appointments.",
        "CloudFront caches static assets at the edge; app servers stay lightweight.",
        "SNS decouples notifications from the web request path.",
    ]),
    ("Eligible services used (≥4 required)", [
        "Compute: EC2 · Storage/DB: RDS + S3 · Networking: ELB + CloudFront",
        "Messaging: SNS · Monitoring: CloudWatch · IAM: LabRole/LabInstanceProfile",
    ]),
    ("Hardest problem & solution", [
        "Problem: Prevent double-booking the same doctor slot under concurrent requests.",
        "Solution: Application checks + MySQL UNIQUE KEY on (doctor_id, appointment_date, time_slot).",
        "Local demo mode uses the same rules in memory for testing without RDS.",
    ]),
    ("Demo checklist (2–3 min video)", [
        "Show architecture diagram · Patient books appointment · Show SNS email",
        "Doctor dashboard · Mention us-east-1 and sandbox constraints",
    ]),
]


def add_bullets(slide, lines):
    body = slide.placeholders[1]
    tf = body.text_frame
    tf.clear()
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.level = 0
        p.font.size = Pt(18)


def main():
    prs = Presentation()
    title_layout = prs.slide_layouts[0]
    bullet_layout = prs.slide_layouts[1]

    for i, (title, bullets) in enumerate(SLIDES):
        layout = title_layout if i == 0 else bullet_layout
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = title
        if bullets:
            if i == 0:
                sub = slide.placeholders[1]
                sub.text = bullets[0]
            else:
                add_bullets(slide, bullets)

    prs.save(OUT)
    print(f"Created: {OUT}")


if __name__ == "__main__":
    main()
