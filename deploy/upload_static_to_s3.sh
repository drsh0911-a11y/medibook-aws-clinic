#!/usr/bin/env bash
# Upload app/static/ to your S3 bucket (run from project root on EC2 or CloudShell)
set -euo pipefail
BUCKET="${1:?Usage: ./deploy/upload_static_to_s3.sh medibook-assets-YOURACCOUNTID}"
aws s3 sync app/static/ "s3://${BUCKET}/static/" --region us-east-1 --delete
echo "Uploaded to s3://${BUCKET}/static/"
echo "Point CloudFront origin at this bucket, then set CLOUDFRONT_URL in .env"
