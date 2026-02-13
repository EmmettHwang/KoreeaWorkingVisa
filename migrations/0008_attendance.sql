-- =====================================================
-- Phase 4: 출퇴근 시스템 + QR 체크인
-- =====================================================

-- 사업장(작업장) 테이블
CREATE TABLE IF NOT EXISTS kwv_workplaces (
    id INT AUTO_INCREMENT PRIMARY KEY,
    local_government_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    address TEXT,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    geofence_radius INT DEFAULT 200 COMMENT '허용 반경(미터)',
    qr_code VARCHAR(100) UNIQUE COMMENT 'QR 체크인용 고유코드',
    manager_name VARCHAR(100),
    manager_phone VARCHAR(30),
    worker_capacity INT DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_lg (local_government_id),
    INDEX idx_qr (qr_code),
    FOREIGN KEY (local_government_id) REFERENCES kwv_local_governments(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 출퇴근 기록 테이블
CREATE TABLE IF NOT EXISTS kwv_attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    workplace_id INT NOT NULL,
    check_type ENUM('check_in', 'check_out') NOT NULL,
    check_method ENUM('qr', 'gps', 'manual', 'admin') DEFAULT 'qr',
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    distance_from_workplace INT COMMENT '사업장과의 거리(미터)',
    is_valid TINYINT(1) DEFAULT 1 COMMENT '유효한 체크인 여부',
    invalid_reason VARCHAR(255),
    photo_url VARCHAR(500) COMMENT '출퇴근 인증 사진',
    device_info VARCHAR(255),
    ip_address VARCHAR(45),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_workplace (workplace_id),
    INDEX idx_check_time (check_time),
    INDEX idx_user_date (user_id, check_time),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id),
    FOREIGN KEY (workplace_id) REFERENCES kwv_workplaces(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 근로자-사업장 배정 테이블
CREATE TABLE IF NOT EXISTS kwv_worker_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    workplace_id INT NOT NULL,
    assigned_date DATE NOT NULL,
    end_date DATE,
    status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_workplace (workplace_id),
    UNIQUE KEY uk_user_workplace (user_id, workplace_id, assigned_date),
    FOREIGN KEY (user_id) REFERENCES kwv_users(id),
    FOREIGN KEY (workplace_id) REFERENCES kwv_workplaces(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
