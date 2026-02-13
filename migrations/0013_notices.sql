-- =====================================================
-- 공지사항 (전체 + 지자체별)
-- =====================================================

CREATE TABLE IF NOT EXISTS kwv_notices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    target_type ENUM('all','lg') DEFAULT 'all' COMMENT '전체 또는 특정 지자체',
    local_government_id INT COMMENT '특정 지자체 (target_type=lg일 때)',
    is_important TINYINT(1) DEFAULT 0 COMMENT '중요 공지',
    is_active TINYINT(1) DEFAULT 1,
    view_count INT DEFAULT 0,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_target (target_type, local_government_id),
    INDEX idx_active (is_active),
    INDEX idx_important (is_important),
    INDEX idx_created (created_at),
    FOREIGN KEY (created_by) REFERENCES kwv_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
