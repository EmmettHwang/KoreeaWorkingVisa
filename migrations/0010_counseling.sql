-- =====================================================
-- Phase 6: 상담일지
-- =====================================================

CREATE TABLE IF NOT EXISTS kwv_counseling (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '상담 대상 근로자',
    counselor_id INT NOT NULL COMMENT '상담사 (관리자)',
    counseling_date DATE NOT NULL,
    counseling_type ENUM('in_person','phone','video','text') DEFAULT 'in_person',
    category ENUM('work','health','legal','housing','salary','homesick','conflict','other') DEFAULT 'other',
    title VARCHAR(255) NOT NULL,
    content TEXT,
    action_taken TEXT COMMENT '조치 사항',
    follow_up_date DATE COMMENT '후속 상담 예정일',
    follow_up_note TEXT,
    severity ENUM('low','medium','high','urgent') DEFAULT 'low',
    status ENUM('open','in_progress','resolved','closed') DEFAULT 'open',
    is_confidential TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_counselor (counselor_id),
    INDEX idx_date (counseling_date),
    INDEX idx_status (status),
    INDEX idx_severity (severity),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id),
    FOREIGN KEY (counselor_id) REFERENCES kwv_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
