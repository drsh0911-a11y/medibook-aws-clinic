# AWS Medical Clinic Appointment Booking System (MediBook)

## Solution Architecture Diagram
![AWS Solution Architecture](./app/templates/architecture.html)

## Project Overview
MediBook is a cloud-native web application built on AWS (us-east-1) that enables patients to browse doctors and book appointment slots while providing doctors with daily schedule management tools.

## Key AWS Services Used
- **Amazon EC2 & ELB**: Scalable web application backend using Flask/Gunicorn fronted by an Elastic Load Balancer.
- **Amazon RDS (MySQL)**: Relational database storing user credentials, doctor profiles, and appointment records.
- **Amazon S3 & CloudFront**: Static file storage and global edge content delivery.
- **Amazon SNS**: Event-driven email notifications for booking confirmations.
- **Amazon CloudWatch & SSM**: Infrastructure monitoring, performance metrics, and secure instance management.

## ?? Video Demonstration
Watch the live application walkthrough and AWS infrastructure tour:
[?? Click here to watch the MediBook Demo Video](https://drive.google.com/file/d/1qF-yD0O72CrG_5KZM5a48yiJNo004hb3/view?usp=drive_link)

## Repository Structure
- /app: Flask application source code, HTML templates, and static assets.
- /deploy: Database DDL scripts, shell setup scripts, and deployment configurations.
- DEPLOYMENT_GUIDE.md: Step-by-step AWS provisioning and configuration instructions.
