-- Recruitment tables
-- ============================================================

CREATE TABLE IF NOT EXISTS recruitment_requisitions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    department  VARCHAR(100) NOT NULL,
    location    VARCHAR(150) DEFAULT NULL,
    openings    INT DEFAULT 1,
    filled      INT DEFAULT 0,
    priority    VARCHAR(20) DEFAULT 'medium',
    status      ENUM('draft','pending','open','closed','on_hold') NOT NULL DEFAULT 'draft',
    description TEXT DEFAULT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rec_req_status (status),
    INDEX idx_rec_req_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recruitment_candidates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    phone       VARCHAR(50) DEFAULT NULL,
    position    VARCHAR(150) NOT NULL,
    source      VARCHAR(100) DEFAULT NULL,
    status      ENUM('applied','screening','interview','offer','hired','rejected') NOT NULL DEFAULT 'applied',
    location    VARCHAR(150) DEFAULT NULL,
    experience  INT DEFAULT NULL,
    resume_link VARCHAR(500) DEFAULT NULL,
    applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes       TEXT DEFAULT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rec_cand_status (status),
    INDEX idx_rec_cand_position (position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recruitment_interviews (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id    INT NOT NULL,
    candidate_name  VARCHAR(150) NOT NULL,
    position        VARCHAR(150) NOT NULL,
    interview_type  VARCHAR(50) DEFAULT 'in_person',
    interview_date  DATE NOT NULL,
    start_time      VARCHAR(10) DEFAULT NULL,
    end_time        VARCHAR(10) DEFAULT NULL,
    interviewer     VARCHAR(150) DEFAULT NULL,
    interviewer_id  INT DEFAULT NULL,
    status          ENUM('scheduled','in_progress','completed','cancelled') NOT NULL DEFAULT 'scheduled',
    feedback        TEXT DEFAULT NULL,
    rating          INT DEFAULT NULL,
    notes           TEXT DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rec_int_candidate (candidate_id),
    INDEX idx_rec_int_status (status),
    INDEX idx_rec_int_date (interview_date),
    CONSTRAINT fk_rec_int_candidate FOREIGN KEY (candidate_id) REFERENCES recruitment_candidates(id) ON DELETE CASCADE,
    CONSTRAINT fk_rec_int_interviewer FOREIGN KEY (interviewer_id) REFERENCES employees(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recruitment_offers (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id    INT NOT NULL,
    candidate_name  VARCHAR(150) NOT NULL,
    position        VARCHAR(150) NOT NULL,
    salary          DECIMAL(12,2) DEFAULT NULL,
    equity          VARCHAR(50) DEFAULT NULL,
    joining_date    DATE DEFAULT NULL,
    status          ENUM('draft','pending','approved','rejected','accepted','withdrawn','countered') NOT NULL DEFAULT 'draft',
    notes           TEXT DEFAULT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rec_off_candidate (candidate_id),
    INDEX idx_rec_off_status (status),
    CONSTRAINT fk_rec_off_candidate FOREIGN KEY (candidate_id) REFERENCES recruitment_candidates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
