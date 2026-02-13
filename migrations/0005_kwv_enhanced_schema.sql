-- =====================================================
-- KWV 스키마 확장: 파일 업로드, 주소, 지역
-- =====================================================

-- 1. kwv_users 테이블 컬럼 추가
ALTER TABLE kwv_users
    ADD COLUMN IF NOT EXISTS address TEXT AFTER phone,
    ADD COLUMN IF NOT EXISTS region VARCHAR(100) COMMENT '관리자: 소속 지역' AFTER organization;

-- 2. password_hash NULL 허용 (기본 비밀번호 서버측 설정)
ALTER TABLE kwv_users MODIFY password_hash VARCHAR(255) NULL;

-- 3. password_salt 컬럼 추가
ALTER TABLE kwv_users
    ADD COLUMN IF NOT EXISTS password_salt VARCHAR(64) AFTER password_hash;

-- 4. 파일 업로드 테이블
CREATE TABLE IF NOT EXISTS kwv_file_uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    file_category VARCHAR(50) NOT NULL COMMENT 'passport_copy, visa_copy, id_card, insurance_cert, profile_photo',
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT,
    mime_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES kwv_users(id) ON DELETE CASCADE,
    INDEX idx_user_category (user_id, file_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. organization 컬럼 코멘트 변경 (소속 기관 → 소속 지역 지원)
ALTER TABLE kwv_users MODIFY organization VARCHAR(255) COMMENT '관리자: 소속 기관 또는 소속 지역';
