-- =====================================================
-- Phase 8: 이상감지 + 알림
-- =====================================================

-- 이상감지 기록 테이블
CREATE TABLE IF NOT EXISTS kwv_anomalies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '대상 근로자',
    anomaly_type ENUM('absent_streak','gps_violation','pattern_change','no_checkout','manual_flag') NOT NULL,
    score INT DEFAULT 0 COMMENT '위험 점수 (0~100)',
    description TEXT,
    details JSON COMMENT '상세 데이터',
    status ENUM('detected','reviewing','resolved','dismissed') DEFAULT 'detected',
    resolved_by INT,
    resolved_at TIMESTAMP NULL,
    resolve_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_type (anomaly_type),
    INDEX idx_score (score),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 알림 테이블
CREATE TABLE IF NOT EXISTS kwv_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '알림 수신자',
    title VARCHAR(255) NOT NULL,
    message TEXT,
    notification_type ENUM('info','warning','urgent','success','system') DEFAULT 'info',
    reference_type VARCHAR(50) COMMENT 'anomaly, counseling, attendance 등',
    reference_id INT,
    is_read TINYINT(1) DEFAULT 0,
    read_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_read (is_read),
    INDEX idx_type (notification_type),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 이상감지 규칙 설정
CREATE TABLE IF NOT EXISTS kwv_anomaly_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_key VARCHAR(50) UNIQUE NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    score INT NOT NULL DEFAULT 0 COMMENT '기본 점수',
    threshold INT DEFAULT 0 COMMENT '임계값',
    description VARCHAR(255),
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 기본 이상감지 규칙
INSERT INTO kwv_anomaly_rules (rule_key, rule_name, score, threshold, description) VALUES
('absent_3days', '3일 연속 결근', 30, 3, '3일 이상 연속 결근 시 이탈 의심'),
('gps_violation', 'GPS 이탈', 20, 500, 'GPS 검증 실패 (500m 이상 이탈)'),
('pattern_change', '출근 패턴 급변', 15, 0, '평소와 다른 출근 패턴 감지'),
('no_checkout_3', '미퇴근 3회 이상', 10, 3, '퇴근 미기록 3회 이상'),
('late_streak', '연속 지각', 15, 3, '3일 이상 연속 지각');
