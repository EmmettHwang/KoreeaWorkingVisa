-- =====================================================
-- Phase 9: 보험 관리
-- =====================================================

CREATE TABLE IF NOT EXISTS kwv_insurance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '근로자',
    insurance_type ENUM('health','accident','liability','pension','other') NOT NULL,
    provider VARCHAR(255) COMMENT '보험사',
    policy_number VARCHAR(100) COMMENT '증권번호',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    premium DECIMAL(12,0) DEFAULT 0 COMMENT '보험료(원)',
    coverage TEXT COMMENT '보장 내용',
    status ENUM('active','expired','cancelled','pending') DEFAULT 'active',
    document_url VARCHAR(500),
    note TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_type (insurance_type),
    INDEX idx_status (status),
    INDEX idx_end (end_date),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
