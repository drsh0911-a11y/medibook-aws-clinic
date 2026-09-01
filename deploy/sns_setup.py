"""
MediBook — SNS Topic Setup Script
Run this once from your EC2 instance (with LabRole attached) to create
the SNS topic used for appointment confirmation emails.

Usage:
    python3 sns_setup.py
"""
import boto3
import json

REGION = "us-east-1"
TOPIC_NAME = "clinic-notifications"

sns = boto3.client("sns", region_name=REGION)

# Create topic (idempotent — safe to re-run)
response = sns.create_topic(Name=TOPIC_NAME)
topic_arn = response["TopicArn"]
print(f"SNS Topic ARN: {topic_arn}")
print(f"Set SNS_TOPIC_ARN={topic_arn} in your .env file")
print()
print("Subscribe your email once (AWS Console or CLI):")
print(f"  aws sns subscribe --topic-arn {topic_arn} --protocol email --notification-endpoint YOUR@EMAIL.com --region {REGION}")
