-- =====================================================
-- Migration 0014: 구인 공고 + 테마 설정
-- v2.0: 구인구직, 관리자 관리, 테마 프리셋
-- =====================================================

-- ==================== 구인 공고 테이블 ====================
CREATE TABLE IF NOT EXISTS kwv_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL COMMENT '공고 제목',
    description TEXT COMMENT '상세 설명',
    local_government_id INT COMMENT '지자체 ID',
    visa_types VARCHAR(255) COMMENT '비자 유형 (콤마 구분: E-8,E-9)',
    positions INT DEFAULT 1 COMMENT '모집 인원',
    salary VARCHAR(255) COMMENT '급여 정보',
    period VARCHAR(255) COMMENT '근무 기간',
    location VARCHAR(500) COMMENT '근무 위치',
    requirements TEXT COMMENT '자격 요건',
    benefits TEXT COMMENT '복리 후생',
    contact_name VARCHAR(100) COMMENT '담당자 이름',
    contact_phone VARCHAR(30) COMMENT '담당자 연락처',
    contact_email VARCHAR(255) COMMENT '담당자 이메일',
    status ENUM('draft','active','closed') DEFAULT 'draft' COMMENT '상태',
    image_url VARCHAR(500) COMMENT '대표 이미지',
    created_by INT NOT NULL COMMENT '작성자 ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_lg (local_government_id),
    INDEX idx_created (created_at),
    FOREIGN KEY (local_government_id) REFERENCES kwv_local_governments(id),
    FOREIGN KEY (created_by) REFERENCES kwv_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 테마 시스템 설정 추가 ====================
INSERT INTO kwv_system_settings (setting_key, setting_value, setting_type, description) VALUES
('theme_preset', 'blue', 'string', '테마 프리셋 (blue, green, purple, orange, teal, rose, slate)'),
('theme_header_bg_start', '#007AFF', 'string', '헤더 그라데이션 시작 색상'),
('theme_header_bg_end', '#5856D6', 'string', '헤더 그라데이션 끝 색상'),
('theme_menu_active_color', '#2563eb', 'string', '메뉴 활성 색상')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);
