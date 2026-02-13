-- Migration 0007: MOU 협정 관리
-- KWV 외국인 계절근로자 관리 플랫폼

-- ==================== MOU 협정 테이블 ====================
CREATE TABLE IF NOT EXISTS kwv_mou_agreements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(500) NOT NULL COMMENT '협정 제목',
    title_en VARCHAR(500) COMMENT '영문 제목',

    -- 상대측 정보
    partner_country VARCHAR(100) NOT NULL COMMENT '상대국 코드 (VN, TH, PH 등)',
    partner_country_name VARCHAR(200) COMMENT '상대국 이름 (한글)',
    partner_type ENUM('government','local_government','agency','other') DEFAULT 'government' COMMENT '상대 기관 유형',
    partner_organization VARCHAR(500) NOT NULL COMMENT '상대 기관명',
    partner_organization_en VARCHAR(500) COMMENT '상대 기관 영문명',
    partner_representative VARCHAR(200) COMMENT '상대측 대표자',
    partner_contact VARCHAR(500) COMMENT '상대측 연락처',

    -- 한국측 정보
    korean_organization VARCHAR(500) COMMENT '한국측 기관명',
    korean_representative VARCHAR(200) COMMENT '한국측 대표자',

    -- 협정 상세
    description TEXT COMMENT '협정 내용 요약',
    description_en TEXT COMMENT '영문 요약',
    signed_date DATE COMMENT '체결일',
    effective_date DATE COMMENT '발효일',
    expiry_date DATE COMMENT '만료일',
    worker_quota INT DEFAULT 0 COMMENT '협정 배정 인원',

    -- 파일/미디어
    document_url VARCHAR(500) COMMENT '협정 문서 파일',
    photo_url VARCHAR(500) COMMENT '체결식 사진',
    photo_url_2 VARCHAR(500) COMMENT '추가 사진',
    photo_url_3 VARCHAR(500) COMMENT '추가 사진',

    -- 상태
    status ENUM('draft','active','expired','terminated') DEFAULT 'draft' COMMENT '협정 상태',
    is_public BOOLEAN DEFAULT FALSE COMMENT '공개 여부 (MOU 쇼케이스)',
    display_order INT DEFAULT 0 COMMENT '표시 순서',

    created_by INT COMMENT '등록자',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_country (partner_country),
    INDEX idx_status (status),
    INDEX idx_public (is_public),
    INDEX idx_signed (signed_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
