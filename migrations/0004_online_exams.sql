-- 온라인 시험 테이블
CREATE TABLE IF NOT EXISTS online_exams (
  id INT AUTO_INCREMENT PRIMARY KEY COMMENT '온라인 시험 ID',
  title VARCHAR(255) NOT NULL COMMENT '시험 제목',
  exam_bank_id INT NOT NULL COMMENT '문제은행 시험 ID (exam_bank.exam_id)',
  course_code VARCHAR(10) NOT NULL COMMENT '과정 코드',
  instructor_code VARCHAR(50) NOT NULL COMMENT '출제 강사 코드',
  duration INT NOT NULL DEFAULT 60 COMMENT '시험 시간 (분)',
  status ENUM('scheduled', 'waiting', 'ongoing', 'ended', 'graded') NOT NULL DEFAULT 'scheduled' COMMENT '상태',
  scheduled_at DATETIME COMMENT '예정 시작 시간 (공지용)',
  started_at DATETIME COMMENT '실제 시작 시간',
  ended_at DATETIME COMMENT '종료 시간',
  description TEXT COMMENT '시험 안내사항',
  pass_score INT DEFAULT 60 COMMENT '합격 점수',
  shuffle_questions TINYINT(1) DEFAULT 0 COMMENT '문제 순서 섞기',
  shuffle_options TINYINT(1) DEFAULT 0 COMMENT '선택지 순서 섞기',
  show_result TINYINT(1) DEFAULT 1 COMMENT '결과 즉시 공개 여부',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_course (course_code),
  INDEX idx_instructor (instructor_code),
  INDEX idx_status (status),
  INDEX idx_exam_bank (exam_bank_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='온라인 시험 테이블';

-- 온라인 시험 응시자 테이블
CREATE TABLE IF NOT EXISTS online_exam_participants (
  id INT AUTO_INCREMENT PRIMARY KEY COMMENT '응시 ID',
  online_exam_id INT NOT NULL COMMENT '온라인 시험 ID',
  student_id INT NOT NULL COMMENT '학생 ID',
  status ENUM('waiting', 'taking', 'submitted', 'graded') NOT NULL DEFAULT 'waiting' COMMENT '응시 상태',
  entered_at DATETIME COMMENT '대기실 입장 시간',
  started_at DATETIME COMMENT '시험 시작 시간',
  submitted_at DATETIME COMMENT '제출 시간',
  answers JSON COMMENT '학생 답안 {"question_id": "answer", ...}',
  score INT COMMENT '점수',
  correct_count INT COMMENT '정답 수',
  total_questions INT COMMENT '총 문제 수',
  is_passed TINYINT(1) COMMENT '합격 여부',
  graded_at DATETIME COMMENT '채점 시간',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_exam_student (online_exam_id, student_id),
  INDEX idx_online_exam (online_exam_id),
  INDEX idx_student (student_id),
  INDEX idx_status (status),
  FOREIGN KEY (online_exam_id) REFERENCES online_exams(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='온라인 시험 응시자 테이블';
