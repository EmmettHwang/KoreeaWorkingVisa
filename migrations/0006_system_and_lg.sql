-- Migration 0006: 시스템 설정 + 지자체 등록
-- KWV 외국인 계절근로자 관리 플랫폼

-- ==================== 시스템 설정 테이블 ====================
CREATE TABLE IF NOT EXISTS kwv_system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type ENUM('string','number','boolean','json') DEFAULT 'string',
    description VARCHAR(500),
    updated_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기본 설정 삽입
INSERT INTO kwv_system_settings (setting_key, setting_value, setting_type, description) VALUES
('system_title', 'Korea Working Visa', 'string', '플랫폼 제목'),
('system_subtitle', '외국인 계절근로자 관리 포털', 'string', '플랫폼 부제'),
('logo_url', '', 'string', '로고 이미지 URL'),
('favicon_url', '', 'string', '파비콘 URL'),
('approval_mode', 'manual', 'string', '가입 승인 모드: auto 또는 manual'),
('maintenance_mode', 'false', 'boolean', '시스템 점검 모드'),
('default_language', 'ko', 'string', '기본 언어'),
('max_upload_size_mb', '10', 'number', '최대 파일 업로드 크기 (MB)'),
('google_maps_api_key', '', 'string', 'Google Maps API 키'),
('ai_anomaly_enabled', 'false', 'boolean', 'AI 이상감지 활성화'),
('ai_api_key', '', 'string', 'AI 서비스 API 키 (Groq/Gemini)'),
('point_check_in', '10', 'number', '출근 포인트'),
('point_check_out', '5', 'number', '퇴근 포인트'),
('point_activity_log', '3', 'number', '활동일지 포인트'),
('attendance_deadline_hours', '10', 'number', '출근 마감 시간 (24h)'),
('gps_radius_meters', '500', 'number', '허용 GPS 반경 (m)'),
('qr_expiry_minutes', '5', 'number', 'QR 코드 만료 시간 (분)'),
('login_show_register', 'true', 'boolean', '로그인 페이지 회원가입 버튼 표시'),
('login_show_mou', 'true', 'boolean', '로그인 페이지 MOU 쇼케이스 링크 표시'),
('login_show_google', 'true', 'boolean', '로그인 페이지 Google 로그인 버튼 표시')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);

-- ==================== 지자체 테이블 ====================
CREATE TABLE IF NOT EXISTS kwv_local_governments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL COMMENT '지자체명 (예: 해남군)',
    name_en VARCHAR(255) COMMENT 'English name',
    region VARCHAR(100) NOT NULL COMMENT '광역 지역 (예: 전라남도)',
    address TEXT,
    phone VARCHAR(30),
    email VARCHAR(255),
    website_url VARCHAR(500) COMMENT '지자체 홈페이지',
    representative_name VARCHAR(100) COMMENT '담당자 이름',
    representative_phone VARCHAR(30),
    representative_email VARCHAR(255),

    -- TO(쿼터) 관리
    allocated_quota INT DEFAULT 0 COMMENT '배정된 TO (근로자 수)',
    used_quota INT DEFAULT 0 COMMENT '사용된 TO',
    quota_year INT COMMENT '배정 연도',

    -- 프로필
    logo_url VARCHAR(500),
    description TEXT,
    description_en TEXT,
    latitude DECIMAL(10, 7) COMMENT 'GPS 위도',
    longitude DECIMAL(10, 7) COMMENT 'GPS 경도',

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_region (region),
    INDEX idx_active (is_active),
    INDEX idx_quota_year (quota_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== kwv_users 확장 ====================
ALTER TABLE kwv_users ADD COLUMN IF NOT EXISTS local_government_id INT COMMENT '배정된 지자체' AFTER region;
ALTER TABLE kwv_users ADD COLUMN IF NOT EXISTS target_local_government_id INT COMMENT '신청 대상 지자체' AFTER local_government_id;
ALTER TABLE kwv_users ADD COLUMN IF NOT EXISTS points_balance INT DEFAULT 0 COMMENT '포인트 잔액' AFTER target_local_government_id;
ALTER TABLE kwv_users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE COMMENT '가입 승인 여부' AFTER is_active;
ALTER TABLE kwv_users ADD COLUMN IF NOT EXISTS approved_at DATETIME COMMENT '승인 일시' AFTER is_approved;
ALTER TABLE kwv_users ADD COLUMN IF NOT EXISTS approved_by INT COMMENT '승인자 ID' AFTER approved_at;
ALTER TABLE kwv_users ADD COLUMN IF NOT EXISTS rejection_reason TEXT COMMENT '반려 사유' AFTER approved_by;
