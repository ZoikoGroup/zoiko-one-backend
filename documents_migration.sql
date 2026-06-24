-- Documents table
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id               VARCHAR(50) DEFAULT NULL,
    document_type           ENUM('contract','offer_letter','nda','employee_handbook','policy_document','certificate','report','invoice','receipt','other') NOT NULL,
    title                   VARCHAR(200) NOT NULL,
    description             TEXT DEFAULT NULL,
    file_name               VARCHAR(255) NOT NULL,
    file_path               VARCHAR(500) DEFAULT NULL,
    file_size               INT DEFAULT NULL,
    category                VARCHAR(100) DEFAULT NULL,
    tags                    JSON DEFAULT NULL,
    uploaded_by_id          INT NOT NULL,
    uploaded_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    status                  VARCHAR(20) DEFAULT 'active' NOT NULL,
    expiry_date             DATE DEFAULT NULL,
    is_public               BOOLEAN DEFAULT FALSE NOT NULL,
    is_deleted              BOOLEAN DEFAULT FALSE NOT NULL,
    created_by              VARCHAR(100) DEFAULT NULL,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_documents_type (document_type),
    INDEX idx_documents_category (category),
    INDEX idx_documents_status (status),
    INDEX idx_documents_uploaded_by (uploaded_by_id),
    INDEX idx_documents_expiry (expiry_date),
    CONSTRAINT fk_documents_uploader FOREIGN KEY (uploaded_by_id) REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;