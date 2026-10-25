CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    fhir_patient_id VARCHAR(100) NOT NULL UNIQUE,

    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    last_name VARCHAR(100),

    date_of_birth DATE,
    gender VARCHAR(30),

    phone VARCHAR(50),
    email VARCHAR(255),

    address_line VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),

    preferred_language VARCHAR(50),
    marital_status VARCHAR(50),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fhir_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL
        REFERENCES patients(id)
        ON DELETE CASCADE,

    resource_type VARCHAR(100) NOT NULL,
    fhir_resource_id VARCHAR(100) NOT NULL,

    version_id VARCHAR(100),
    last_updated TIMESTAMP,

    resource_json JSONB NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fhir_resource
        UNIQUE (resource_type, fhir_resource_id)
);

CREATE TABLE IF NOT EXISTS conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL
        REFERENCES patients(id)
        ON DELETE CASCADE,

    fhir_resource_id UUID
        REFERENCES fhir_resources(id)
        ON DELETE CASCADE,

    condition_code VARCHAR(100),
    code_system VARCHAR(255),
    condition_name VARCHAR(500),

    clinical_status VARCHAR(100),
    verification_status VARCHAR(100),

    onset_date TIMESTAMP,
    abatement_date TIMESTAMP,
    recorded_date TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS medications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL
        REFERENCES patients(id)
        ON DELETE CASCADE,

    fhir_resource_id UUID
        REFERENCES fhir_resources(id)
        ON DELETE CASCADE,

    rxnorm_code VARCHAR(100),
    medication_name VARCHAR(500),

    status VARCHAR(50),
    intent VARCHAR(50),

    dosage_text TEXT,

    authored_on TIMESTAMP,

    start_date TIMESTAMP,
    end_date TIMESTAMP,

    reason TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS care_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL
        REFERENCES patients(id)
        ON DELETE CASCADE,

    fhir_resource_id UUID
        REFERENCES fhir_resources(id)
        ON DELETE CASCADE,

    status VARCHAR(50),
    intent VARCHAR(50),

    category_code VARCHAR(100),
    category_name VARCHAR(500),

    title VARCHAR(500),
    description TEXT,

    start_date TIMESTAMP,
    end_date TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS encounters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL
        REFERENCES patients(id)
        ON DELETE CASCADE,

    fhir_resource_id UUID
        REFERENCES fhir_resources(id)
        ON DELETE CASCADE,

    status VARCHAR(50),
    encounter_class VARCHAR(100),

    encounter_type_code VARCHAR(100),
    encounter_type_name VARCHAR(500),

    start_time TIMESTAMP,
    end_time TIMESTAMP,

    reason TEXT,

    discharge_disposition VARCHAR(255),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL
        REFERENCES patients(id)
        ON DELETE CASCADE,

    fhir_resource_id UUID
        REFERENCES fhir_resources(id)
        ON DELETE CASCADE,

    observation_code VARCHAR(100),
    code_system VARCHAR(255),
    observation_name VARCHAR(500),

    status VARCHAR(50),

    value_numeric NUMERIC,
    value_text TEXT,
    unit VARCHAR(100),

    effective_time TIMESTAMP,

    interpretation VARCHAR(100),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    patient_id UUID NOT NULL
        REFERENCES patients(id)
        ON DELETE CASCADE,

    fhir_resource_id UUID
        REFERENCES fhir_resources(id)
        ON DELETE CASCADE,

    status VARCHAR(50),

    appointment_type VARCHAR(255),
    reason TEXT,

    start_time TIMESTAMP,
    end_time TIMESTAMP,

    location VARCHAR(500),
    practitioner_name VARCHAR(500),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);



CREATE INDEX IF NOT EXISTS idx_conditions_patient
ON conditions(patient_id);

CREATE INDEX IF NOT EXISTS idx_conditions_status
ON conditions(clinical_status);

CREATE INDEX IF NOT EXISTS idx_medications_patient
ON medications(patient_id);

CREATE INDEX IF NOT EXISTS idx_medications_status
ON medications(status);

CREATE INDEX IF NOT EXISTS idx_care_plans_patient
ON care_plans(patient_id);

CREATE INDEX IF NOT EXISTS idx_care_plans_status
ON care_plans(status);

CREATE INDEX IF NOT EXISTS idx_encounters_patient
ON encounters(patient_id);

CREATE INDEX IF NOT EXISTS idx_encounters_start_time
ON encounters(start_time);

CREATE INDEX IF NOT EXISTS idx_observations_patient
ON observations(patient_id);

CREATE INDEX IF NOT EXISTS idx_observations_code
ON observations(observation_code);

CREATE INDEX IF NOT EXISTS idx_observations_effective_time
ON observations(effective_time);

CREATE INDEX IF NOT EXISTS idx_appointments_patient
ON appointments(patient_id);

CREATE INDEX IF NOT EXISTS idx_appointments_start_time
ON appointments(start_time);



CREATE INDEX IF NOT EXISTS idx_fhir_resources_patient
ON fhir_resources(patient_id);

CREATE INDEX IF NOT EXISTS idx_fhir_resources_type
ON fhir_resources(resource_type);

CREATE INDEX IF NOT EXISTS idx_fhir_resources_json
ON fhir_resources
USING GIN (resource_json);