-- 퀴즈 타입 추가
ALTER TABLE online_exams
ADD COLUMN exam_type ENUM('exam', 'quiz') DEFAULT 'exam' AFTER title;
