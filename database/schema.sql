CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'faculty')),
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    current_semester TEXT NOT NULL DEFAULT 'Fall 2026',
    program_credits REAL NOT NULL DEFAULT 142 CHECK (program_credits > 0),
    target_cgpa REAL NOT NULL DEFAULT 3.85 CHECK (target_cgpa BETWEEN 0 AND 4),
    gemini_api_key TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    intake TEXT NOT NULL,
    section TEXT NOT NULL,
    current_semester TEXT NOT NULL DEFAULT 'Fall 2026',
    program_credits REAL NOT NULL DEFAULT 142 CHECK (program_credits > 0),
    target_cgpa REAL NOT NULL DEFAULT 3.85 CHECK (target_cgpa BETWEEN 0 AND 4)
);

CREATE TABLE IF NOT EXISTS courses (
    course_code TEXT PRIMARY KEY,
    course_title TEXT NOT NULL,
    credit_hours REAL NOT NULL CHECK (credit_hours > 0)
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    course_code TEXT NOT NULL,
    semester_no TEXT NOT NULL,
    letter_grade TEXT,
    grade_point REAL CHECK (
        grade_point IS NULL OR grade_point IN
            (0, 2, 2.25, 2.5, 2.75, 3, 3.25, 3.5, 3.75, 4)
    ),
    UNIQUE (student_id, course_code, semester_no),
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_code) REFERENCES courses (course_code)
);

CREATE INDEX IF NOT EXISTS idx_enrollments_student
    ON enrollments (student_id, semester_no);
