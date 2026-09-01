#!/usr/bin/env bash
# ============================================================
# MediBook — EC2 User-Data / Setup Script
# Installs Flask app + Gunicorn + Nginx on Amazon Linux 2023
# Region: us-east-1  |  AMI: Amazon Linux 2023
# IAM: LabInstanceProfile required
# ============================================================
set -euo pipefail
LOG=/var/log/medibook-setup.log
exec > >(tee -a $LOG) 2>&1
echo "=== MediBook setup started: $(date) ==="

dnf update -y
dnf install -y python3 python3-pip nginx git

APP_ROOT=/opt/medibook
APP_DIR=$APP_ROOT/app
mkdir -p $APP_DIR

# Copy project files to $APP_ROOT before running (git clone, scp, or S3 zip).
# Example: aws s3 cp s3://YOUR-BUCKET/medibook.zip $APP_ROOT/ && unzip -o medibook.zip -d $APP_ROOT

cd $APP_DIR
python3 -m venv $APP_ROOT/venv
source $APP_ROOT/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

cat > $APP_DIR/.env << 'ENV'
FLASK_SECRET_KEY=CHANGE_THIS_TO_RANDOM_64_CHAR_STRING
DB_HOST=YOUR_RDS_ENDPOINT.rds.amazonaws.com
DB_USER=admin
DB_PASSWORD=YourRDSPassword123!
DB_NAME=clinic_db
AWS_REGION=us-east-1
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:ACCOUNT_ID:clinic-notifications
S3_BUCKET_NAME=medibook-assets-ACCOUNT_ID
CLOUDFRONT_URL=https://XXXXXXXXXX.cloudfront.net
ENV
chmod 600 $APP_DIR/.env

cat > /etc/systemd/system/medibook.service << SVC
[Unit]
Description=MediBook Gunicorn App Server
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/opt/medibook/app
EnvironmentFile=/opt/medibook/app/.env
ExecStart=/opt/medibook/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:5000 \
    --timeout 60 \
    --access-logfile /var/log/medibook-access.log \
    --error-logfile  /var/log/medibook-error.log \
    app:app
Restart=always

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable medibook
systemctl start medibook

cat > /etc/nginx/conf.d/medibook.conf << 'NGINX'
server {
    listen 80;
    server_name _;

    location /health {
        proxy_pass http://127.0.0.1:5000/health;
    }

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINX

nginx -t && systemctl enable nginx && systemctl restart nginx

dnf install -y amazon-cloudwatch-agent || true
mkdir -p /opt/aws/amazon-cloudwatch-agent/etc
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWA'
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {"file_path": "/var/log/medibook-access.log", "log_group_name": "/medibook/access"},
          {"file_path": "/var/log/medibook-error.log",  "log_group_name": "/medibook/error"}
        ]
      }
    }
  }
}
CWA
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s || true

echo "=== MediBook setup complete: $(date) ==="
echo "Edit /opt/medibook/app/.env then: sudo systemctl restart medibook"
