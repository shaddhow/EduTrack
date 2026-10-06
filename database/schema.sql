CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'faculty')),
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS faculty_sections (
    faculty_user_id TEXT NOT NULL,
    section TEXT NOT NULL,
    PRIMARY KEY (faculty_user_id, section),
    FOREIGN KEY (faculty_user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    current_semester TEXT NOT NULL DEFAULT 'Fall 2026',
    program_credits REAL NOT NULL DEFAULT 142 CHECK (program_credits > 0),
    target_cgpa REAL NOT NULL DEFAULT 3.85 CHECK (target_cgpa BETWEEN 0 AND 4),
    current_cgpa REAL CHECK (current_cgpa BETWEEN 0 AND 4),
    gemini_api_key TEXT NOT NULL DEFAULT '',
    accent_theme TEXT NOT NULL DEFAULT 'Default Blue'
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

CREATE TABLE IF NOT EXISTS attendance (
    student_id TEXT NOT NULL,
    course_code TEXT NOT NULL,
    total_classes INTEGER NOT NULL DEFAULT 0 CHECK (total_classes >= 0),
    attended_classes INTEGER NOT NULL DEFAULT 0 CHECK (
        attended_classes >= 0 AND attended_classes <= total_classes
    ),
    PRIMARY KEY (student_id, course_code),
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_code) REFERENCES courses (course_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS routines (
    routine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL CHECK (
        day IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
    ),
    time TEXT NOT NULL,
    course_code TEXT NOT NULL,
    room TEXT NOT NULL,
    UNIQUE (day, time, course_code),
    FOREIGN KEY (course_code) REFERENCES courses (course_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_routines_day_time
    ON routines (day, time);
