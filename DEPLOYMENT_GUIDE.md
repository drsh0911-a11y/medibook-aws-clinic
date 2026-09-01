# MediBook — Deployment Guide
## Medical Clinic Appointment Booking System
**AWS Cloud Computing Project | Spring 25/26 | AASTMT**

---

## AWS Services Used

| Service | Purpose |
|---------|---------|
| Amazon EC2 (t2.micro) | Hosts the Flask web application |
| Amazon RDS (MySQL) | Stores users, doctors, appointments |
| Amazon S3 | Hosts static assets (CSS, JS, images) |
| Amazon SNS | Sends email booking confirmations |
| Elastic Load Balancer | Distributes traffic across EC2 instances |
| Amazon CloudFront | CDN for static assets from S3 |
| Amazon CloudWatch | Monitoring, logs, and alarms |

All resources must be in **us-east-1 (N. Virginia)**.

---

## Step-by-Step Deployment

### Step 1 — RDS (MySQL Database)

1. Go to **RDS → Create Database**
2. Choose **MySQL**, Standard Create
3. Template: **Free tier** (or Dev/Test)
4. DB Instance: `db.t3.micro`, Storage: 20 GB gp2
5. DB name: `clinic_db`, Master username: `admin`
6. VPC security group: allow port 3306 from your EC2 security group only
7. After creation, copy the **Endpoint URL**
8. Connect with a MySQL client and run:
   ```bash
   mysql -h YOUR_ENDPOINT -u admin -p clinic_db < deploy/rds_schema.sql
   ```

### Step 2 — S3 Bucket (Static Assets)

1. Go to **S3 → Create Bucket**
2. Name: `medibook-assets-YOURACCOUNTID`
3. Region: `us-east-1`, unblock public access (for CloudFront origin)
4. Upload `app/static/` contents to the bucket
5. Note the bucket name for the `.env` file

### Step 3 — CloudFront Distribution

1. Go to **CloudFront → Create Distribution**
2. Origin: your S3 bucket
3. Default cache behavior: redirect HTTP to HTTPS
4. Copy the **Distribution domain name** (e.g. `d1abc.cloudfront.net`)

### Step 4 — SNS Topic

```bash
# On your EC2 instance (LabRole attached):
python3 deploy/sns_setup.py
```

Copy the printed `SNS_TOPIC_ARN` into your `.env` file.

### Step 5 — EC2 Instance

1. Go to **EC2 → Launch Instance**
2. AMI: **Amazon Linux 2023**
3. Instance type: `t2.micro`
4. IAM Instance Profile: **LabInstanceProfile**
5. Security Group: allow HTTP (80) from the Load Balancer, SSH (22) from your IP
6. User Data: paste the contents of `deploy/setup_ec2.sh`
7. Edit `/opt/medibook/.env` with your actual RDS endpoint, SNS ARN, etc.

### Step 6 — Elastic Load Balancer

1. Go to **EC2 → Load Balancers → Create**
2. Type: **Application Load Balancer**
3. Listeners: HTTP port 80
4. Target Group: your EC2 instance(s), health check path `/health`
5. Copy the **DNS name** — this is your app's public URL

### Step 7 — CloudWatch Alarms

1. Go to **CloudWatch → Alarms → Create Alarm**
2. Suggested alarms:
   - EC2 CPUUtilization > 70% for 5 minutes → SNS alert
   - RDS FreeStorageSpace < 5 GB → SNS alert
   - ELB UnHealthyHostCount > 0 → SNS alert

---

## Local Development

```bash
cd app/
pip install -r requirements.txt
cp ../env.example .env      # Fill in your values (or copy env.example to app/.env)
python app.py               # Runs on http://localhost:5000
```

---

## Seed Doctor Accounts

After running `rds_schema.sql`, these doctor logins are available:

| Name | Email | Password | Specialty |
|------|-------|----------|-----------|
| Dr. Sara Ahmed | sara@clinic.com | password123 | Cardiology |
| Dr. Omar Khalil | omar@clinic.com | password123 | Neurology |
| Dr. Nada Hassan | nada@clinic.com | password123 | Dermatology |
| Dr. Youssef Taha | youssef@clinic.com | password123 | Orthopedics |
| Dr. Hana Mostafa | hana@clinic.com | password123 | Pediatrics |
| Dr. Karim Saber | karim@clinic.com | password123 | General Practitioner |

---

## Project Structure

```
clinic-project/
├── app/
│   ├── app.py                    # Flask application (all routes + AWS integrations)
│   ├── requirements.txt          # Python dependencies
│   └── templates/
│       ├── base.html             # Navbar, footer, Bootstrap layout
│       ├── index.html            # Home - browse doctors
│       ├── register.html         # Patient/Doctor registration
│       ├── login.html            # Login page
│       ├── book.html             # Appointment booking with slot picker
│       ├── patient_dashboard.html# Patient's appointment history
│       └── doctor_dashboard.html # Doctor's daily schedule
├── deploy/
│   ├── rds_schema.sql            # MySQL schema + seed data
│   ├── setup_ec2.sh              # EC2 user-data / install script
│   └── sns_setup.py              # One-time SNS topic creation
├── Medical_Clinic_Proposal.pptx  # PowerPoint proposal
└── DEPLOYMENT_GUIDE.md           # This file
```

---

## Video Demo Outline (2-3 min)

1. **Intro** (20s) — Show the architecture diagram from the PPTX, name all AWS services
2. **Patient flow** (60s) — Register → Browse doctors → Book slot → Show SNS email confirmation
3. **Doctor flow** (30s) — Login as doctor → View today's schedule → Mark appointment completed
4. **Architecture walkthrough** (30s) — Explain EC2 + RDS + SNS + ELB + S3 + CloudWatch
5. **Hardest problem** (20s) — Double-booking prevention: unique DB constraint on (doctor_id, date, slot)
