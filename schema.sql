-- ============================================================
-- 🔁 FULL RESET (SAFE RERUN)
-- ============================================================

DROP DATABASE IF EXISTS adaptive_learning;

CREATE DATABASE adaptive_learning 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE adaptive_learning;

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120)        NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255)        NOT NULL,
    role          ENUM('student','instructor','admin') DEFAULT 'student',
    avatar_url    VARCHAR(500),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================================
-- COURSES
-- ============================================================

CREATE TABLE courses (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    title         VARCHAR(255)  NOT NULL,
    description   TEXT,
    thumbnail_url VARCHAR(500),
    difficulty    ENUM('beginner','intermediate','advanced') DEFAULT 'beginner',
    instructor_id INT NOT NULL,
    is_published  BOOLEAN DEFAULT FALSE,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- MODULES
-- ============================================================

CREATE TABLE modules (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    course_id  INT NOT NULL,
    title      VARCHAR(255) NOT NULL,
    order_num  INT DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- ============================================================
-- LESSONS
-- ============================================================

CREATE TABLE lessons (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    module_id    INT NOT NULL,
    title        VARCHAR(255) NOT NULL,
    content      LONGTEXT,
    video_url    VARCHAR(500),
    order_num    INT DEFAULT 0,
    xp_reward    INT DEFAULT 10,
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
);

-- ============================================================
-- ENROLLMENTS
-- ============================================================

CREATE TABLE enrollments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    course_id   INT NOT NULL,
    enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_enroll (user_id, course_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- ============================================================
-- LESSON PROGRESS
-- ============================================================

CREATE TABLE lesson_progress (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    lesson_id     INT NOT NULL,
    completed     BOOLEAN DEFAULT FALSE,
    time_spent_s  INT DEFAULT 0,
    completed_at  DATETIME,
    UNIQUE KEY uq_lp (user_id, lesson_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- ============================================================
-- QUESTIONS
-- ============================================================

CREATE TABLE questions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    lesson_id    INT NOT NULL,
    question     TEXT NOT NULL,
    type         ENUM('mcq','true_false','fill') DEFAULT 'mcq',
    options      JSON,
    correct      VARCHAR(255) NOT NULL,
    explanation  TEXT,
    difficulty   TINYINT DEFAULT 1,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- ============================================================
-- QUIZ ATTEMPTS
-- ============================================================

CREATE TABLE quiz_attempts (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    lesson_id     INT NOT NULL,
    score         FLOAT DEFAULT 0,
    total_q       INT DEFAULT 0,
    correct_q     INT DEFAULT 0,
    answers       JSON,
    attempted_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
);

-- ============================================================
-- LEARNER PROFILE
-- ============================================================

CREATE TABLE learner_profiles (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNIQUE NOT NULL,
    skill_level     FLOAT DEFAULT 0.5,
    learning_speed  FLOAT DEFAULT 1.0,
    weak_topics     JSON,
    strong_topics   JSON,
    preferred_type  ENUM('visual','reading','practice') DEFAULT 'reading',
    total_xp        INT DEFAULT 0,
    streak_days     INT DEFAULT 0,
    last_active     DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- BADGES (FIXED)
-- ============================================================

CREATE TABLE badges (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    description     TEXT,
    icon            VARCHAR(10),
    condition_text  VARCHAR(255)
);

-- ============================================================
-- USER BADGES
-- ============================================================

CREATE TABLE user_badges (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    badge_id    INT NOT NULL,
    earned_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ub (user_id, badge_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badges(id) ON DELETE CASCADE
);

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO badges (name, description, icon, condition_text) VALUES
('First Step',    'Completed your first lesson',         '🎯', 'lessons_completed=1'),
('Quiz Master',   'Scored 100% on a quiz',               '🏆', 'perfect_quiz=1'),
('Speed Learner', 'Completed 5 lessons in one day',      '⚡', 'daily_lessons=5'),
('Consistent',    '7-day learning streak',               '🔥', 'streak=7'),
('Scholar',       'Earned 500 XP',                       '📚', 'xp=500');

INSERT INTO users (name, email, password_hash, role) VALUES
('Admin', 'admin@learn.io',
'$2b$12$KIX5UXq3JvC0eGRKv8e0t.ZZRWdIcFULqGLGIUjWlWMJGkP3NTNHG',
'admin');