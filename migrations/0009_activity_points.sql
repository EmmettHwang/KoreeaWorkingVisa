-- =====================================================
-- Phase 5: 활동일지 + 포인트 시스템
-- =====================================================

-- 활동일지 테이블
CREATE TABLE IF NOT EXISTS kwv_activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    workplace_id INT,
    activity_date DATE NOT NULL,
    activity_type ENUM('work','training','community','other') DEFAULT 'work',
    title VARCHAR(255) NOT NULL,
    content TEXT,
    hours DECIMAL(4,1) DEFAULT 0 COMMENT '활동 시간',
    photo_url VARCHAR(500),
    photo_url_2 VARCHAR(500),
    photo_url_3 VARCHAR(500),
    status ENUM('draft','submitted','approved','rejected') DEFAULT 'submitted',
    approved_by INT,
    approved_at TIMESTAMP NULL,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_date (activity_date),
    INDEX idx_status (status),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id),
    FOREIGN KEY (workplace_id) REFERENCES kwv_workplaces(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 포인트 테이블
CREATE TABLE IF NOT EXISTS kwv_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    points INT NOT NULL COMMENT '양수=적립, 음수=차감',
    point_type ENUM('attendance','activity','training','community','bonus','penalty','admin') NOT NULL,
    reference_type VARCHAR(50) COMMENT 'attendance, activity_log 등',
    reference_id INT COMMENT '참조 테이블의 ID',
    description VARCHAR(255),
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_type (point_type),
    INDEX idx_ref (reference_type, reference_id),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 포인트 설정 (자동 적립 규칙)
CREATE TABLE IF NOT EXISTS kwv_point_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_key VARCHAR(50) UNIQUE NOT NULL COMMENT 'attendance_checkin, activity_approved 등',
    rule_name VARCHAR(100) NOT NULL,
    points INT NOT NULL DEFAULT 0,
    description VARCHAR(255),
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 기본 포인트 규칙 삽입
INSERT INTO kwv_point_rules (rule_key, rule_name, points, description) VALUES
('attendance_checkin', '출근 체크인', 10, '정상 출근 시 자동 적립'),
('attendance_checkout', '퇴근 체크아웃', 5, '정상 퇴근 시 자동 적립'),
('attendance_perfect_week', '주간 개근', 50, '주 5일 개근 시 보너스'),
('activity_submitted', '활동일지 작성', 5, '활동일지 제출 시'),
('activity_approved', '활동일지 승인', 10, '관리자 승인 시 추가 적립'),
('training_complete', '교육 이수', 20, '교육 과정 완료 시'),
('community_activity', '커뮤니티 활동', 15, '지역사회 봉사활동'),
('penalty_late', '지각 패널티', -10, '지각 시 차감'),
('penalty_absent', '무단 결근', -30, '무단 결근 시 차감'),
('penalty_invalid_gps', 'GPS 이탈', -5, 'GPS 검증 실패 시');
