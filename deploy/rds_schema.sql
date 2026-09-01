-- ============================================================
-- MediBook — RDS MySQL Schema
-- Medical Clinic Appointment Booking System
-- AWS Cloud Computing Project, Spring 25/26
-- Run this against your RDS MySQL instance after creation.
-- ============================================================

CREATE DATABASE IF NOT EXISTS clinic_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE clinic_db;

-- ─── Users table (patients + doctors) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id            INT           NOT NULL AUTO_INCREMENT,
  name          VARCHAR(120)  NOT NULL,
  email         VARCHAR(200)  NOT NULL UNIQUE,
  password_hash VARCHAR(64)   NOT NULL,          -- SHA-256 hex
  role          ENUM('patient','doctor') NOT NULL DEFAULT 'patient',
  specialty     VARCHAR(100)  DEFAULT NULL,       -- doctors only
  bio           TEXT          DEFAULT NULL,
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_email (email),
  INDEX idx_role  (role)
) ENGINE=InnoDB;

-- ─── Appointments table ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appointments (
  id               INT          NOT NULL AUTO_INCREMENT,
  patient_id       INT          NOT NULL,
  doctor_id        INT          NOT NULL,
  appointment_date DATE         NOT NULL,
  time_slot        VARCHAR(5)   NOT NULL,   -- e.g. "09:30"
  status           ENUM('scheduled','completed','cancelled','no-show')
                               NOT NULL DEFAULT 'scheduled',
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  -- Prevent double-booking: one patient per doctor per slot (excluding cancelled)
  UNIQUE KEY uq_slot (doctor_id, appointment_date, time_slot),
  FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (doctor_id)  REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_doctor_date (doctor_id, appointment_date),
  INDEX idx_patient     (patient_id)
) ENGINE=InnoDB;

-- ─── Seed data — sample doctors ───────────────────────────────────────────
-- Password for all seed accounts: "password123"
-- SHA-256("password123") = ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f

INSERT IGNORE INTO users (name, email, password_hash, role, specialty, bio) VALUES
  ('Sara Ahmed',    'sara@clinic.com',   'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'doctor', 'Cardiology',          'Board-certified cardiologist with 10+ years of experience in interventional cardiology.'),
  ('Omar Khalil',   'omar@clinic.com',   'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'doctor', 'Neurology',           'Specialist in neurological disorders including migraine, epilepsy, and stroke management.'),
  ('Nada Hassan',   'nada@clinic.com',   'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'doctor', 'Dermatology',         'Experienced dermatologist specializing in skin conditions, acne, and cosmetic procedures.'),
  ('Youssef Taha',  'youssef@clinic.com','ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'doctor', 'Orthopedics',         'Orthopedic surgeon focused on sports injuries, joint replacements, and spinal disorders.'),
  ('Hana Mostafa',  'hana@clinic.com',   'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'doctor', 'Pediatrics',          'Dedicated pediatrician with a gentle approach to children\'s healthcare from birth to age 18.'),
  ('Karim Saber',   'karim@clinic.com',  'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'doctor', 'General Practitioner', 'Family medicine physician providing comprehensive primary care for all ages.');
