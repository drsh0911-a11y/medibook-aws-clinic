#!/usr/bin/env bash
set -e
cd /opt/medibook/app
python3 -m venv venv
source venv/bin/activate
pip install -q flask==3.0.3 pymysql==1.1.1 boto3==1.34.100 gunicorn==22.0.0 python-dotenv==1.0.1

cat > /opt/medibook/app/.env << 'EOF'
FLASK_SECRET_KEY=medibook-super-secret-key-2526
DB_HOST=clinic-db.cw9g7sxoafwh.us-east-1.rds.amazonaws.com
DB_USER=admin
DB_PASSWORD=MediBook2526!
DB_NAME=clinic_db
AWS_REGION=us-east-1
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:958776740470:clinic-notifications
S3_BUCKET_NAME=medibook-23100312
CLOUDFRONT_URL=https://d2p7nqtdrvomoc.cloudfront.net
EOF

sudo dnf install -y mariadb105 nginx

echo "=== MySQL schema ==="
mysql -h clinic-db.cw9g7sxoafwh.us-east-1.rds.amazonaws.com -u admin -pMediBook2526! < /opt/medibook/deploy/rds_schema.sql
mysql -h clinic-db.cw9g7sxoafwh.us-east-1.rds.amazonaws.com -u admin -pMediBook2526! clinic_db -e "SELECT COUNT(*) AS doctors FROM users WHERE role='doctor';"

sudo tee /etc/systemd/system/medibook.service > /dev/null << 'SVC'
[Unit]
Description=MediBook App
After=network.target
[Service]
User=ec2-user
WorkingDirectory=/opt/medibook/app
EnvironmentFile=/opt/medibook/app/.env
ExecStart=/opt/medibook/app/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 60 app:app
Restart=always
[Install]
WantedBy=multi-user.target
SVC

sudo tee /etc/nginx/conf.d/medibook.conf > /dev/null << 'NGINX'
server {
    listen 80;
    server_name _;
    location /health { proxy_pass http://127.0.0.1:5000/health; }
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX

if grep -q 'root.*/usr/share/nginx/html' /etc/nginx/nginx.conf 2>/dev/null; then
  sudo sed -i '/^    server {/,/^    }/d' /etc/nginx/nginx.conf
fi

sudo systemctl daemon-reload
sudo systemctl enable medibook
sudo systemctl start medibook
sleep 2

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo "=== HEALTH ==="
curl -s http://127.0.0.1:5000/health
echo
echo "=== CURL localhost ==="
curl -s http://localhost/ | head -12
