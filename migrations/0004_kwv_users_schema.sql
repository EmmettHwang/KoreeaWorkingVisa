-- =====================================================
-- KoreaWorkingVisa 사용자 스키마
-- =====================================================

-- 1. 사용자 테이블
CREATE TABLE IF NOT EXISTS kwv_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),

    -- OAuth 정보
    oauth_provider ENUM('local', 'google') DEFAULT 'local',
    oauth_id VARCHAR(255),

    -- 사용자 유형
    user_type ENUM('admin', 'applicant') NOT NULL DEFAULT 'applicant',
    admin_level INT DEFAULT NULL COMMENT '1:슈퍼관리자, 2:일반관리자, 3:조회전용',

    -- 프로필
    profile_photo VARCHAR(500),
    language VARCHAR(10) DEFAULT 'en',
    organization VARCHAR(255) COMMENT '소속 기관 (관리자용)',

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT TRUE,

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,

    INDEX idx_email (email),
    INDEX idx_user_type (user_type),
    INDEX idx_admin_level (admin_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 비자 신청자 정보 테이블
CREATE TABLE IF NOT EXISTS kwv_visa_applicants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,

    -- 비자 정보
    visa_type VARCHAR(20) COMMENT 'E8, E9, H2 등',
    nationality VARCHAR(50),
    passport_number VARCHAR(50),
    birth_date DATE,
    gender ENUM('male', 'female'),

    -- 고용 정보
    employer_name VARCHAR(255),
    job_category VARCHAR(100),

    -- 상태
    application_status ENUM('pending', 'processing', 'approved', 'rejected') DEFAULT 'pending',
    rejection_reason TEXT,

    -- 메타
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES kwv_users(id) ON DELETE CASCADE,
    INDEX idx_status (application_status),
    INDEX idx_visa_type (visa_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 관리자 권한 테이블
CREATE TABLE IF NOT EXISTS kwv_admin_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_level INT NOT NULL,
    permission_name VARCHAR(100) NOT NULL,
    can_view BOOLEAN DEFAULT FALSE,
    can_edit BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,

    UNIQUE KEY unique_level_permission (admin_level, permission_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 기본 권한 설정
INSERT INTO kwv_admin_permissions (admin_level, permission_name, can_view, can_edit, can_delete) VALUES
-- Level 1: 슈퍼관리자 (모든 권한)
(1, 'applicants', TRUE, TRUE, TRUE),
(1, 'admins', TRUE, TRUE, TRUE),
(1, 'settings', TRUE, TRUE, TRUE),
(1, 'statistics', TRUE, TRUE, TRUE),
(1, 'reports', TRUE, TRUE, TRUE),

-- Level 2: 일반관리자 (신청자 관리)
(2, 'applicants', TRUE, TRUE, FALSE),
(2, 'admins', FALSE, FALSE, FALSE),
(2, 'settings', FALSE, FALSE, FALSE),
(2, 'statistics', TRUE, FALSE, FALSE),
(2, 'reports', TRUE, FALSE, FALSE),

-- Level 3: 조회전용
(3, 'applicants', TRUE, FALSE, FALSE),
(3, 'admins', FALSE, FALSE, FALSE),
(3, 'settings', FALSE, FALSE, FALSE),
(3, 'statistics', TRUE, FALSE, FALSE),
(3, 'reports', TRUE, FALSE, FALSE)
ON DUPLICATE KEY UPDATE can_view = VALUES(can_view), can_edit = VALUES(can_edit), can_delete = VALUES(can_delete);
