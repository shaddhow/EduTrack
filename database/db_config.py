"""SQLite database setup and credential helpers for EduTrack."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Any

from modules.grading import grade_point_for_letter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "edutrack.db"
DATABASE_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
BACKUP_FORMAT = "edutrack-data"
BACKUP_VERSION = 1
DEMO_STUDENT_ID = "20255103311"
DEMO_PASSWORD = "EduTrack2026!"
PASSWORD_HASH_ITERATIONS = 310_000

_initialization_lock = threading.Lock()
_initialized_paths: set[Path] = set()


def get_database_path() -> Path:
    """Return the configured SQLite file, defaulting to project-root edutrack.db."""
    configured_path = os.environ.get("EDUTRACK_DB_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DATABASE_PATH


def write_json_backup(file_path: str | Path, payload: dict[str, Any]) -> Path:
    """Write a JSON backup atomically so a failed export cannot truncate a file."""
    path = Path(file_path).expanduser()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as backup_file:
            temporary_path = Path(backup_file.name)
            json.dump(payload, backup_file, ensure_ascii=False, indent=2)
            backup_file.write("\n")
        os.replace(temporary_path, path)
        return path
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def read_json_backup(file_path: str | Path) -> Any:
    """Read a UTF-8 JSON backup and report malformed JSON to the caller."""
    with Path(file_path).expanduser().open("r", encoding="utf-8") as backup_file:
        return json.load(backup_file)


def hash_password(password: str) -> str:
    """Hash a password with a unique salt using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time verify a password against its encoded PBKDF2 hash."""
    try:
        algorithm, iteration_text, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iteration_text)
        if not 100_000 <= iterations <= 2_000_000:
            return False
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (AttributeError, TypeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _seed_demo_data(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO students
            (student_id, name, email, intake, section, current_semester,
             program_credits, target_cgpa)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            DEMO_STUDENT_ID,
            "CSE Student",
            "student@edutrack.local",
            "55",
            "06",
            "Fall 2026",
            142,
            3.85,
        ),
    )

    demo_users = (
        (DEMO_STUDENT_ID, "student", "CSE Student"),
        ("FACULTY001", "faculty", "Faculty Member"),
    )
    demo_password_hash = hash_password(DEMO_PASSWORD)
    for user_id, role, display_name in demo_users:
        connection.execute(
            """
            INSERT OR IGNORE INTO users (user_id, password_hash, role, display_name)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, demo_password_hash, role, display_name),
        )

    courses = (
        ("CSE101", "Introduction to Computer Science", 3.0),
        ("MAT101", "Differential and Integral Calculus", 3.0),
        ("CSE103", "Structured Programming Language", 3.0),
        ("CSE201", "Data Structures", 3.0),
        ("EEE101", "Basic Electrical Engineering", 3.0),
        ("CSE203", "Discrete Mathematics", 3.0),
        ("ENG101", "English Language", 3.0),
        ("CSE205", "Object Oriented Programming", 3.0),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO courses (course_code, course_title, credit_hours)
        VALUES (?, ?, ?)
        """,
        courses,
    )

    enrollments = (
        (DEMO_STUDENT_ID, "CSE101", "1", "A-", 3.5),
        (DEMO_STUDENT_ID, "MAT101", "1", "B+", 3.25),
        (DEMO_STUDENT_ID, "CSE103", "1", "B", 3.0),
        (DEMO_STUDENT_ID, "CSE201", "2", "A-", 3.5),
        (DEMO_STUDENT_ID, "EEE101", "2", "C+", 2.5),
        (DEMO_STUDENT_ID, "CSE203", "2", "B+", 3.25),
        (DEMO_STUDENT_ID, "ENG101", "3", "A", 3.75),
        (DEMO_STUDENT_ID, "CSE205", "3", "B", 3.0),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO enrollments
            (student_id, course_code, semester_no, letter_grade, grade_point)
        VALUES (?, ?, ?, ?, ?)
        """,
        enrollments,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO attendance
            (student_id, course_code, total_classes, attended_classes)
        VALUES (?, ?, ?, ?)
        """,
        (
            (DEMO_STUDENT_ID, "CSE101", 15, 12),
            (DEMO_STUDENT_ID, "MAT101", 15, 10),
            (DEMO_STUDENT_ID, "CSE103", 16, 14),
        ),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO routines (day, time, course_code, room)
        VALUES (?, ?, ?, ?)
        """,
        (
            ("Monday", "09:00 - 10:30", "CSE101", "Room 501"),
            ("Monday", "11:00 - 12:30", "MAT101", "Room 402"),
            ("Tuesday", "10:00 - 11:30", "CSE103", "Lab 2"),
            ("Wednesday", "09:00 - 10:30", "CSE101", "Room 501"),
            ("Thursday", "11:00 - 12:30", "MAT101", "Room 402"),
        ),
    )


def initialize_database(database_path: str | Path | None = None) -> Path:
    """Create the database schema and seed an idempotent demo profile."""
    path = Path(database_path).expanduser().resolve() if database_path else get_database_path()
    with _initialization_lock:
        if path in _initialized_paths and path.exists():
            return path

        path.parent.mkdir(parents=True, exist_ok=True)
        connection = _connect(path)
        try:
            faculty_sections_table_existed = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'faculty_sections'
                """
            ).fetchone() is not None
            schema = DATABASE_SCHEMA_PATH.read_text(encoding="utf-8")
            connection.executescript(schema)
            _migrate_student_profile(connection)
            _migrate_user_settings(connection)
            _seed_demo_data(connection)
            if not faculty_sections_table_existed:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO faculty_sections
                        (faculty_user_id, section)
                    VALUES (?, ?)
                    """,
                    ("FACULTY001", "06"),
                )
            _normalize_grade_points(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        _initialized_paths.add(path)
    return path


def _normalize_grade_points(connection: sqlite3.Connection) -> None:
    """Migrate all recognized stored letter grades to official BUBT points."""
    rows = connection.execute(
        "SELECT enrollment_id, letter_grade FROM enrollments"
    ).fetchall()
    normalized = [
        (grade_point, row["enrollment_id"])
        for row in rows
        if (
            grade_point := grade_point_for_letter(row["letter_grade"])
        ) is not None
    ]
    connection.executemany(
        "UPDATE enrollments SET grade_point = ? WHERE enrollment_id = ?",
        normalized,
    )


def _migrate_student_profile(connection: sqlite3.Connection) -> None:
    """Add profile fields to databases created by earlier EduTrack versions."""
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(students)").fetchall()
    }
    migrations = (
        (
            "current_semester",
            "ALTER TABLE students ADD COLUMN current_semester "
            "TEXT NOT NULL DEFAULT 'Fall 2026'",
        ),
        (
            "program_credits",
            "ALTER TABLE students ADD COLUMN program_credits "
            "REAL NOT NULL DEFAULT 142",
        ),
        (
            "target_cgpa",
            "ALTER TABLE students ADD COLUMN target_cgpa "
            "REAL NOT NULL DEFAULT 3.85",
        ),
    )
    for column, statement in migrations:
        if column not in existing_columns:
            connection.execute(statement)


def _migrate_user_settings(connection: sqlite3.Connection) -> None:
    """Add newer preferences to databases created by earlier versions."""
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(user_settings)").fetchall()
    }
    if "accent_theme" not in existing_columns:
        connection.execute(
            "ALTER TABLE user_settings ADD COLUMN accent_theme "
            "TEXT NOT NULL DEFAULT 'Default Blue'"
        )
    if "current_cgpa" not in existing_columns:
        connection.execute(
            "ALTER TABLE user_settings ADD COLUMN current_cgpa "
            "REAL CHECK (current_cgpa BETWEEN 0 AND 4)"
        )


def get_connection() -> sqlite3.Connection:
    """Return a ready-to-use SQLite connection with dictionary-like rows."""
    database_path = initialize_database()
    return _connect(database_path)
