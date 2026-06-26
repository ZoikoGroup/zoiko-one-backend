-- Migration: Add Employee Master fields
-- Adds all missing fields to the employees table for the complete Employee Master System

ALTER TABLE employees
  ADD COLUMN IF NOT EXISTS work_email           VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS personal_email       VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS designation_id       INT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS reporting_manager_id INT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS confirmation_date    DATE DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS company              VARCHAR(200) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS business_unit        VARCHAR(200) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS division             VARCHAR(200) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS team                 VARCHAR(200) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS ctc                  DECIMAL(12,2) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS current_address      TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS permanent_address    TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS city                 VARCHAR(100) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS state                VARCHAR(100) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS country              VARCHAR(100) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS pincode              VARCHAR(20) DEFAULT NULL;

-- Add foreign keys
ALTER TABLE employees
  ADD CONSTRAINT fk_employees_designation
    FOREIGN KEY (designation_id) REFERENCES designations(id)
    ON DELETE SET NULL;

ALTER TABLE employees
  ADD CONSTRAINT fk_employees_reporting_manager
    FOREIGN KEY (reporting_manager_id) REFERENCES employees(id)
    ON DELETE SET NULL;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_employees_designation_id ON employees(designation_id);
CREATE INDEX IF NOT EXISTS idx_employees_reporting_manager_id ON employees(reporting_manager_id);
CREATE INDEX IF NOT EXISTS idx_employees_work_email ON employees(work_email);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
CREATE INDEX IF NOT EXISTS idx_employees_employment_type ON employees(employment_type);

-- Update employee_code to 5-digit format for existing records (optional)
-- This is informational only - existing codes are preserved
-- New codes will use ZK-XXXXX format via _generate_employee_code()
