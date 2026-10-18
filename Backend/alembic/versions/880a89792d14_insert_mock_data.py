"""Insert mock data

Revision ID: 880a89792d14
Revises: ba266a56e651
Create Date: 2026-10-13 22:52:39.034112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '880a89792d14'
down_revision: Union[str, None] = 'ba266a56e651'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert Organizations
    op.execute("""
        INSERT INTO organizations (organization_name, organization_type, address, phone, status) VALUES
        ('City General Hospital', 'HOSPITAL', '123 Main St, Springfield, IL 62701', '555-0100', 'ACTIVE'),
        ('Community Health Clinic', 'CLINIC', '456 Oak Ave, Springfield, IL 62702', '555-0200', 'ACTIVE'),
        ('Midwest Healthcare Group', 'HEALTHCARE_GROUP', '789 Elm St, Springfield, IL 62703', '555-0300', 'ACTIVE'),
        ('HealthCare Pharmacy', 'PHARMACY', '321 Maple Dr, Springfield, IL 62704', '555-0400', 'ACTIVE')
    """)
    
    # Insert Roles
    op.execute("""
        INSERT INTO roles (role_name, description) VALUES
        ('PATIENT', 'Patient receiving care through the navigation system'),
        ('CARE_MANAGER', 'Care manager coordinating patient care'),
        ('TRANSITIONAL_CARE_NURSE', 'Nurse managing post-discharge transitions'),
        ('PHARMACIST', 'Pharmacist handling medication-related escalations'),
        ('SCHEDULER', 'Scheduler managing appointments and follow-ups'),
        ('SOCIAL_WORKER', 'Social worker handling support and social needs'),
        ('POPULATION_HEALTH_MANAGER', 'Manager overseeing population health metrics'),
        ('CLINICAL_GOVERNANCE', 'Clinical governance and safety oversight'),
        ('SYSTEM_ADMIN', 'System administrator managing configuration')
    """)
    
    # Insert Users - Password for all: "Test@1234" (bcrypt hashed)
    op.execute("""
        INSERT INTO users (organization_id, role_id, first_name, last_name, email, password_hash, phone, status, is_verified) VALUES
        (1, 1, 'John', 'Doe', 'john.doe@example.com', '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS', '555-1001', 'ACTIVE', TRUE),
        (1, 2, 'Sarah', 'Johnson', 'sarah.johnson@cityhospital.com', '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS', '555-1002', 'ACTIVE', TRUE),
        (2, 3, 'Michael', 'Chen', 'michael.chen@communityclinic.com', '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS', '555-1003', 'ACTIVE', TRUE),
        (3, 9, 'Emma', 'Williams', 'emma.williams@midwesthealthcare.com', '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS', '555-1004', 'ACTIVE', TRUE)
    """)
    
    # Insert Patient Profile
    op.execute("""
        INSERT INTO patient_profiles (user_id, date_of_birth, gender, preferred_language, preferred_contact_method, emergency_contact_name, emergency_contact_phone) VALUES
        (1, '1965-03-15', 'MALE', 'en', 'SMS', 'Jane Doe', '555-9001')
    """)
    
    # Insert Staff Profiles
    op.execute("""
        INSERT INTO staff_profiles (user_id, employee_id, license_number, license_type, department, specialization) VALUES
        (2, 'EMP001', 'RN123456', 'Registered Nurse', 'Care Management', 'Transitional Care'),
        (3, 'EMP002', 'RN789012', 'Registered Nurse', 'Transitional Care', 'Post-Discharge Care'),
        (4, 'EMP003', 'ADM001', 'System Administrator', 'IT Administration', 'Healthcare IT')
    """)
    
    # Insert Audit Logs
    op.execute("""
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address) VALUES
        (2, 'LOGIN', 'USER', 2, 'User logged in successfully', '127.0.0.1'),
        (1, 'LOGIN', 'USER', 1, 'Patient logged in successfully', '127.0.0.1'),
        (2, 'VIEW_PATIENT', 'PATIENT', 1, 'Care manager viewed patient profile', '127.0.0.1'),
        (4, 'CREATE_USER', 'USER', 3, 'System admin created new user', '127.0.0.1')
    """)


def downgrade() -> None:
    # Delete in reverse order due to foreign key constraints
    op.execute("DELETE FROM audit_logs")
    op.execute("DELETE FROM staff_profiles")
    op.execute("DELETE FROM patient_profiles")
    op.execute("DELETE FROM users")
    op.execute("DELETE FROM roles")
    op.execute("DELETE FROM organizations")
