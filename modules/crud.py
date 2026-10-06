"""Academic data access operations backed by the local SQLite database."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog
from typing import Any

from database.db_config import (
    BACKUP_FORMAT,
    BACKUP_VERSION,
    get_connection,
    read_json_backup,
    verify_password,
    write_json_backup,
)
from modules.grading import (
    GRADE_POINTS,
    calculate_weighted_cgpa,
    grade_point_for_enrollment,
    grade_point_for_letter,
)
from modules.typography import ACCENT_THEMES, DEFAULT_ACCENT_THEME


class AcademicCRUD:
    WEEKDAYS = (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    )

    @staticmethod
    def export_data(file_path: str | Path | None = None) -> str | None:
        """Export all profiles, their enrollments, course details, and settings."""
        if file_path is None:
            selected_path = filedialog.asksaveasfilename(
                title="Export EduTrack data",
                defaultextension=".json",
                filetypes=(("JSON backup", "*.json"), ("All files", "*.*")),
                initialfile="edutrack-backup.json",
            )
            if not selected_path:
                return None
            file_path = selected_path

        connection = get_connection()
        try:
            connection.execute("BEGIN")
            students = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT student_id, name, email, intake, section,
                           current_semester, program_credits, target_cgpa
                    FROM students
                    ORDER BY student_id
                    """
                ).fetchall()
            ]
            courses = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT DISTINCT courses.course_code, courses.course_title,
                                    courses.credit_hours
                    FROM courses
                    JOIN enrollments
                        ON enrollments.course_code = courses.course_code
                    ORDER BY courses.course_code
                    """
                ).fetchall()
            ]
            enrollments = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT student_id, course_code, semester_no,
                           letter_grade, grade_point
                    FROM enrollments
                    ORDER BY student_id, semester_no, course_code
                    """
                ).fetchall()
            ]
            user_settings = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT user_id, display_name, current_semester,
                           program_credits, target_cgpa, current_cgpa,
                           gemini_api_key,
                           accent_theme
                    FROM user_settings
                    ORDER BY user_id
                    """
                ).fetchall()
            ]
            faculty_sections = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT faculty_user_id, section
                    FROM faculty_sections
                    ORDER BY faculty_user_id, section
                    """
                ).fetchall()
            ]
            connection.commit()
        finally:
            connection.close()

        payload = {
            "format": BACKUP_FORMAT,
            "version": BACKUP_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "students": students,
            "courses": courses,
            "enrollments": enrollments,
            "user_settings": user_settings,
            "faculty_sections": faculty_sections,
        }
        return str(write_json_backup(file_path, payload))

    @staticmethod
    def restore_data(
        file_path: str | Path | None = None, mode: str = "merge"
    ) -> dict[str, int] | None:
        """Validate and restore a backup atomically, merging or replacing imported records."""
        if mode not in {"merge", "overwrite"}:
            raise ValueError("Restore mode must be 'merge' or 'overwrite'.")
        if file_path is None:
            selected_path = filedialog.askopenfilename(
                title="Restore EduTrack data",
                filetypes=(("JSON backup", "*.json"), ("All files", "*.*")),
            )
            if not selected_path:
                return None
            file_path = selected_path

        backup = AcademicCRUD._validate_backup(read_json_backup(file_path))
        student_ids = [row["student_id"] for row in backup["students"]]
        settings_user_ids = {
            row["user_id"] for row in backup["user_settings"]
        } | set(student_ids)
        faculty_user_ids = {
            row["faculty_user_id"] for row in backup["faculty_sections"]
        }
        connection = get_connection()
        try:
            connection.execute("BEGIN")
            for faculty_user_id in faculty_user_ids:
                faculty = connection.execute(
                    "SELECT role FROM users WHERE user_id = ?",
                    (faculty_user_id,),
                ).fetchone()
                if faculty is None or faculty["role"] != "faculty":
                    raise ValueError(
                        "Faculty section assignments must reference an existing "
                        "faculty account."
                    )
            if mode == "overwrite":
                for student_id in student_ids:
                    connection.execute(
                        "DELETE FROM enrollments WHERE student_id = ?",
                        (student_id,),
                    )
                for user_id in settings_user_ids:
                    connection.execute(
                        "DELETE FROM user_settings WHERE user_id = ?",
                        (user_id,),
                    )
                for faculty_user_id in faculty_user_ids:
                    connection.execute(
                        "DELETE FROM faculty_sections WHERE faculty_user_id = ?",
                        (faculty_user_id,),
                    )

            connection.executemany(
                """
                INSERT INTO students (
                    student_id, name, email, intake, section, current_semester,
                    program_credits, target_cgpa
                )
                VALUES (
                    :student_id, :name, :email, :intake, :section,
                    :current_semester, :program_credits, :target_cgpa
                )
                ON CONFLICT(student_id) DO UPDATE SET
                    name = excluded.name,
                    email = excluded.email,
                    intake = excluded.intake,
                    section = excluded.section,
                    current_semester = excluded.current_semester,
                    program_credits = excluded.program_credits,
                    target_cgpa = excluded.target_cgpa
                """,
                backup["students"],
            )

            course_statement = """
                INSERT INTO courses (course_code, course_title, credit_hours)
                VALUES (:course_code, :course_title, :credit_hours)
                ON CONFLICT(course_code) DO UPDATE SET
                    course_title = excluded.course_title,
                    credit_hours = excluded.credit_hours
            """
            if mode == "merge":
                course_statement = """
                    INSERT INTO courses (course_code, course_title, credit_hours)
                    VALUES (:course_code, :course_title, :credit_hours)
                    ON CONFLICT(course_code) DO NOTHING
                """
            connection.executemany(course_statement, backup["courses"])

            connection.executemany(
                """
                INSERT INTO enrollments (
                    student_id, course_code, semester_no, letter_grade, grade_point
                )
                VALUES (
                    :student_id, :course_code, :semester_no,
                    :letter_grade, :grade_point
                )
                ON CONFLICT(student_id, course_code, semester_no) DO UPDATE SET
                    letter_grade = excluded.letter_grade,
                    grade_point = excluded.grade_point
                """,
                backup["enrollments"],
            )
            connection.executemany(
                """
                INSERT INTO user_settings (
                    user_id, display_name, current_semester, program_credits,
                    target_cgpa, current_cgpa, gemini_api_key, accent_theme
                )
                VALUES (
                    :user_id, :display_name, :current_semester, :program_credits,
                    :target_cgpa, :current_cgpa, :gemini_api_key, :accent_theme
                )
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    current_semester = excluded.current_semester,
                    program_credits = excluded.program_credits,
                    target_cgpa = excluded.target_cgpa,
                    current_cgpa = excluded.current_cgpa,
                    gemini_api_key = excluded.gemini_api_key,
                    accent_theme = excluded.accent_theme
                """,
                backup["user_settings"],
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO faculty_sections (faculty_user_id, section)
                VALUES (:faculty_user_id, :section)
                """,
                backup["faculty_sections"],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return {
            "students": len(backup["students"]),
            "courses": len(backup["courses"]),
            "enrollments": len(backup["enrollments"]),
            "user_settings": len(backup["user_settings"]),
            "faculty_sections": len(backup["faculty_sections"]),
        }

    @staticmethod
    def _validate_backup(payload: Any) -> dict[str, list[dict[str, Any]]]:
        """Reject unsupported, malformed, or internally inconsistent backups."""
        if not isinstance(payload, dict):
            raise ValueError("The selected file is not an EduTrack JSON backup.")
        if payload.get("format") != BACKUP_FORMAT:
            raise ValueError("The selected file is not an EduTrack JSON backup.")
        if payload.get("version") != BACKUP_VERSION:
            raise ValueError(
                f"Unsupported EduTrack backup version: {payload.get('version')!r}."
            )

        required_fields = {
            "students": (
                "student_id", "name", "email", "intake", "section",
                "current_semester", "program_credits", "target_cgpa",
            ),
            "courses": ("course_code", "course_title", "credit_hours"),
            "enrollments": (
                "student_id", "course_code", "semester_no",
                "letter_grade", "grade_point",
            ),
            "user_settings": (
                "user_id", "display_name", "current_semester", "program_credits",
                "target_cgpa", "gemini_api_key",
            ),
            "faculty_sections": ("faculty_user_id", "section"),
        }
        backup: dict[str, list[dict[str, Any]]] = {}
        for section, fields in required_fields.items():
            raw_records = payload.get(section, []) if section == "faculty_sections" else payload.get(section)
            if not isinstance(raw_records, list):
                raise ValueError(f"Backup field '{section}' must be a list.")
            records: list[dict[str, Any]] = []
            for index, raw_record in enumerate(raw_records):
                if not isinstance(raw_record, dict):
                    raise ValueError(
                        f"Backup {section} record {index + 1} must be an object."
                    )
                missing_fields = [field for field in fields if field not in raw_record]
                if missing_fields:
                    raise ValueError(
                        f"Backup {section} record {index + 1} is missing: "
                        f"{', '.join(missing_fields)}."
                    )
                record = {field: raw_record[field] for field in fields}
                if section == "user_settings":
                    record["current_cgpa"] = raw_record.get("current_cgpa")
                    record["accent_theme"] = raw_record.get(
                        "accent_theme", DEFAULT_ACCENT_THEME
                    )
                records.append(record)
            backup[section] = records

        def require_text(value: Any, field: str) -> None:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Backup field '{field}' must be non-empty text.")

        def require_number(
            value: Any, field: str, *, minimum: float, maximum: float | None = None
        ) -> None:
            try:
                finite = math.isfinite(float(value))
            except (OverflowError, TypeError, ValueError):
                finite = False
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not finite
                or value < minimum
                or (maximum is not None and value > maximum)
            ):
                bound = (
                    f"between {minimum} and {maximum}"
                    if maximum is not None
                    else f"at least {minimum}"
                )
                raise ValueError(f"Backup field '{field}' must be {bound}.")

        for record in backup["students"]:
            for field in (
                "student_id", "name", "email", "intake", "section", "current_semester"
            ):
                require_text(record[field], field)
            require_number(record["program_credits"], "program_credits", minimum=0)
            if record["program_credits"] == 0:
                raise ValueError("Backup field 'program_credits' must be greater than 0.")
            require_number(
                record["target_cgpa"], "target_cgpa", minimum=0, maximum=4
            )

        for record in backup["courses"]:
            require_text(record["course_code"], "course_code")
            require_text(record["course_title"], "course_title")
            require_number(record["credit_hours"], "credit_hours", minimum=0)
            if record["credit_hours"] == 0:
                raise ValueError("Backup field 'credit_hours' must be greater than 0.")

        for record in backup["enrollments"]:
            for field in ("student_id", "course_code", "semester_no"):
                require_text(record[field], field)
            if record["letter_grade"] is not None and not isinstance(
                record["letter_grade"], str
            ):
                raise ValueError("Backup field 'letter_grade' must be text or null.")
            grade_point = record["grade_point"]
            if grade_point is not None:
                require_number(grade_point, "grade_point", minimum=0, maximum=4)
                if grade_point not in {0, 2, 2.25, 2.5, 2.75, 3, 3.25, 3.5, 3.75, 4}:
                    raise ValueError("Backup contains an unsupported grade point.")

        for record in backup["user_settings"]:
            for field in ("user_id", "display_name", "current_semester"):
                require_text(record[field], field)
            if not isinstance(record["gemini_api_key"], str):
                raise ValueError("Backup field 'gemini_api_key' must be text.")
            if (
                not isinstance(record["accent_theme"], str)
                or record["accent_theme"] not in ACCENT_THEMES
            ):
                raise ValueError("Backup contains an unsupported accent theme.")
            require_number(record["program_credits"], "program_credits", minimum=0)
            if record["program_credits"] == 0:
                raise ValueError("Backup field 'program_credits' must be greater than 0.")
            require_number(
                record["target_cgpa"], "target_cgpa", minimum=0, maximum=4
            )
            if record["current_cgpa"] is not None:
                require_number(
                    record["current_cgpa"],
                    "current_cgpa",
                    minimum=0,
                    maximum=4,
                )

        for record in backup["faculty_sections"]:
            require_text(record["faculty_user_id"], "faculty_user_id")
            require_text(record["section"], "section")

        for section, key in (
            ("students", "student_id"),
            ("courses", "course_code"),
            ("user_settings", "user_id"),
        ):
            values = [record[key] for record in backup[section]]
            if len(values) != len(set(values)):
                raise ValueError(f"Backup contains duplicate {section} records.")
        faculty_section_keys = [
            (row["faculty_user_id"], row["section"])
            for row in backup["faculty_sections"]
        ]
        if len(faculty_section_keys) != len(set(faculty_section_keys)):
            raise ValueError("Backup contains duplicate faculty section assignments.")
        enrollment_keys = [
            (row["student_id"], row["course_code"], row["semester_no"])
            for row in backup["enrollments"]
        ]
        if len(enrollment_keys) != len(set(enrollment_keys)):
            raise ValueError("Backup contains duplicate enrollment records.")
        student_ids = {row["student_id"] for row in backup["students"]}
        sections = {row["section"] for row in backup["students"]}
        course_codes = {row["course_code"] for row in backup["courses"]}
        for record in backup["faculty_sections"]:
            if record["section"] not in sections:
                raise ValueError(
                    "Every faculty section assignment must reference a student "
                    "section in the backup."
                )
        for record in backup["enrollments"]:
            if record["student_id"] not in student_ids:
                raise ValueError(
                    "Every enrollment must reference a student in the backup."
                )
            if record["course_code"] not in course_codes:
                raise ValueError(
                    "Every enrollment must reference a course in the backup."
                )
        return backup

    @staticmethod
    def authenticate_user(
        user_id: str, password: str, role: str
    ) -> dict[str, str] | None:
        """Return the account profile on a matching role and password."""
        normalized_role = role.strip().lower()
        if normalized_role not in {"student", "faculty"}:
            return None

        connection = get_connection()
        try:
            row = connection.execute(
                """
                SELECT user_id, password_hash, role, display_name
                FROM users
                WHERE user_id = ? AND role = ?
                """,
                (user_id.strip(), normalized_role),
            ).fetchone()
            if row is None or not verify_password(password, row["password_hash"]):
                return None
            return {
                "user_id": row["user_id"],
                "role": row["role"],
                "display_name": row["display_name"],
            }
        finally:
            connection.close()

    @staticmethod
    def add_student(
        student_id: str,
        name: str,
        email: str,
        intake: str = "55",
        section: str = "06",
    ) -> tuple[bool, str]:
        connection = get_connection()
        try:
            connection.execute(
                """
                INSERT INTO students (student_id, name, email, intake, section)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, name, email, intake, section),
            )
            connection.commit()
            return True, "Student added successfully."
        except Exception as error:
            connection.rollback()
            return False, str(error)
        finally:
            connection.close()

    @staticmethod
    def get_student_profile(student_id: str) -> dict[str, Any] | None:
        connection = get_connection()
        try:
            row = connection.execute(
                """
                SELECT
                    student_id, name, email, intake, section,
                    current_semester, program_credits, target_cgpa
                FROM students
                WHERE student_id = ?
                """,
                (student_id,),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            connection.close()

    @staticmethod
    def get_user_settings(user_id: str) -> dict[str, Any]:
        """Get persisted preferences with student-profile defaults if unset."""
        connection = get_connection()
        try:
            row = connection.execute(
                """
                SELECT
                    COALESCE(settings.display_name, students.name, users.display_name,
                             students.student_id, ?) AS display_name,
                    COALESCE(settings.current_semester, students.current_semester,
                             'Fall 2026') AS current_semester,
                    COALESCE(settings.program_credits, students.program_credits,
                             142) AS program_credits,
                    COALESCE(settings.target_cgpa, students.target_cgpa, 3.85)
                        AS target_cgpa,
                    settings.current_cgpa AS current_cgpa,
                    COALESCE(settings.gemini_api_key, '') AS gemini_api_key,
                    COALESCE(settings.accent_theme, ?) AS accent_theme
                FROM (SELECT ? AS user_id) AS requested
                LEFT JOIN users ON users.user_id = requested.user_id
                LEFT JOIN students ON students.student_id = requested.user_id
                LEFT JOIN user_settings AS settings
                    ON settings.user_id = requested.user_id
                """,
                (user_id, DEFAULT_ACCENT_THEME, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeError("Could not load user settings.")
            settings = dict(row)
        finally:
            connection.close()
        if settings["current_cgpa"] is None:
            current_cgpa, _ = calculate_weighted_cgpa(
                AcademicCRUD.get_student_enrollments(user_id)
            )
            settings["current_cgpa"] = current_cgpa
        return settings

    @staticmethod
    def save_user_settings(
        user_id: str,
        display_name: str,
        current_semester: str,
        program_credits: float,
        target_cgpa: float,
        current_cgpa: float | None,
        gemini_api_key: str,
        accent_theme: str | None = None,
    ) -> None:
        """Persist workspace settings and update the matching student profile."""
        if accent_theme is not None and accent_theme not in ACCENT_THEMES:
            raise ValueError(f"Unknown accent theme: {accent_theme!r}.")
        if current_cgpa is not None and (
            not math.isfinite(current_cgpa) or not 0 <= current_cgpa <= 4
        ):
            raise ValueError("Current CGPA must be between 0 and 4.")
        connection = get_connection()
        try:
            connection.execute(
                """
                INSERT INTO user_settings (
                    user_id, display_name, current_semester, program_credits,
                    target_cgpa, current_cgpa, gemini_api_key, accent_theme
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, ?))
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    current_semester = excluded.current_semester,
                    program_credits = excluded.program_credits,
                    target_cgpa = excluded.target_cgpa,
                    current_cgpa = excluded.current_cgpa,
                    gemini_api_key = excluded.gemini_api_key,
                    accent_theme = COALESCE(?, user_settings.accent_theme)
                """,
                (
                    user_id,
                    display_name,
                    current_semester,
                    program_credits,
                    target_cgpa,
                    current_cgpa,
                    gemini_api_key,
                    accent_theme,
                    DEFAULT_ACCENT_THEME,
                    accent_theme,
                ),
            )
            connection.execute(
                """
                UPDATE students
                SET name = ?, current_semester = ?, program_credits = ?,
                    target_cgpa = ?
                WHERE student_id = ?
                """,
                (
                    display_name,
                    current_semester,
                    program_credits,
                    target_cgpa,
                    user_id,
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def save_user_theme(user_id: str, accent_theme: str) -> None:
        """Persist an accent theme without changing the rest of the user's settings."""
        if accent_theme not in ACCENT_THEMES:
            raise ValueError(f"Unknown accent theme: {accent_theme!r}.")

        connection = get_connection()
        try:
            settings = connection.execute(
                "SELECT 1 FROM user_settings WHERE user_id = ?", (user_id,)
            ).fetchone()
            if settings is None:
                profile = connection.execute(
                    """
                    SELECT COALESCE(students.name, users.display_name, ?) AS name
                    FROM (SELECT ? AS user_id) AS requested
                    LEFT JOIN students ON students.student_id = requested.user_id
                    LEFT JOIN users ON users.user_id = requested.user_id
                    """,
                    (user_id, user_id),
                ).fetchone()
                if profile is None:
                    raise RuntimeError("Could not load the user profile for settings.")
                connection.execute(
                    """
                    INSERT INTO user_settings (user_id, display_name, accent_theme)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, profile["name"], accent_theme),
                )
            else:
                connection.execute(
                    "UPDATE user_settings SET accent_theme = ? WHERE user_id = ?",
                    (accent_theme, user_id),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def update_student_profile(
        student_id: str,
        name: str,
        current_semester: str,
        program_credits: float,
        target_cgpa: float,
    ) -> bool:
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                UPDATE students
                SET name = ?, current_semester = ?, program_credits = ?, target_cgpa = ?
                WHERE student_id = ?
                """,
                (name, current_semester, program_credits, target_cgpa, student_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def get_student_enrollments(student_id: str) -> list[dict[str, Any]]:
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.student_id,
                    e.course_code,
                    c.course_title,
                    c.credit_hours,
                    e.semester_no,
                    e.letter_grade,
                    e.grade_point
                FROM enrollments AS e
                JOIN courses AS c ON c.course_code = e.course_code
                WHERE e.student_id = ?
                ORDER BY
                    CASE WHEN e.semester_no GLOB '[0-9]*' THEN 0 ELSE 1 END,
                    CAST(e.semester_no AS INTEGER),
                    e.semester_no,
                    e.course_code
                """,
                (student_id,),
            ).fetchall()
            enrollments = [dict(row) for row in rows]
            for enrollment in enrollments:
                official_points = grade_point_for_letter(enrollment["letter_grade"])
                if official_points is not None:
                    enrollment["grade_point"] = official_points
            return enrollments
        finally:
            connection.close()

    @staticmethod
    def get_faculty_section_options() -> list[str]:
        connection = get_connection()
        try:
            return [
                row["section"]
                for row in connection.execute(
                    "SELECT DISTINCT section FROM students ORDER BY section"
                ).fetchall()
            ]
        finally:
            connection.close()

    @staticmethod
    def get_faculty_sections(faculty_user_id: str) -> list[str]:
        connection = get_connection()
        try:
            faculty = connection.execute(
                "SELECT role FROM users WHERE user_id = ?",
                (faculty_user_id,),
            ).fetchone()
            if faculty is None or faculty["role"] != "faculty":
                raise ValueError("Section assignments require a faculty account.")
            return [
                row["section"]
                for row in connection.execute(
                    """
                    SELECT section
                    FROM faculty_sections
                    WHERE faculty_user_id = ?
                    ORDER BY section
                    """,
                    (faculty_user_id,),
                ).fetchall()
            ]
        finally:
            connection.close()

    @staticmethod
    def save_faculty_sections(
        faculty_user_id: str, sections: list[str]
    ) -> None:
        normalized_sections = [section.strip() for section in sections]
        if any(not section for section in normalized_sections):
            raise ValueError("Section names cannot be blank.")
        if len(normalized_sections) != len(set(normalized_sections)):
            raise ValueError("A section can only be assigned once.")

        connection = get_connection()
        try:
            connection.execute("BEGIN")
            faculty = connection.execute(
                "SELECT role FROM users WHERE user_id = ?",
                (faculty_user_id,),
            ).fetchone()
            if faculty is None or faculty["role"] != "faculty":
                raise ValueError("Section assignments require a faculty account.")
            available_sections = {
                row["section"]
                for row in connection.execute(
                    "SELECT DISTINCT section FROM students"
                ).fetchall()
            }
            unknown_sections = set(normalized_sections) - available_sections
            if unknown_sections:
                raise ValueError(
                    "Unknown student section(s): "
                    + ", ".join(sorted(unknown_sections))
                )
            connection.execute(
                "DELETE FROM faculty_sections WHERE faculty_user_id = ?",
                (faculty_user_id,),
            )
            connection.executemany(
                """
                INSERT INTO faculty_sections (faculty_user_id, section)
                VALUES (?, ?)
                """,
                [(faculty_user_id, section) for section in normalized_sections],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def get_faculty_students(faculty_user_id: str) -> list[dict[str, Any]]:
        connection = get_connection()
        try:
            faculty = connection.execute(
                "SELECT role FROM users WHERE user_id = ?",
                (faculty_user_id,),
            ).fetchone()
            if faculty is None or faculty["role"] != "faculty":
                raise ValueError("Student rosters are only available to faculty.")
            rows = connection.execute(
                """
                SELECT
                    s.student_id, s.name, s.section,
                    e.enrollment_id, e.letter_grade, e.grade_point,
                    c.credit_hours
                FROM faculty_sections AS fs
                JOIN students AS s ON s.section = fs.section
                LEFT JOIN enrollments AS e ON e.student_id = s.student_id
                LEFT JOIN courses AS c ON c.course_code = e.course_code
                WHERE fs.faculty_user_id = ?
                ORDER BY s.student_id, e.semester_no, e.course_code
                """,
                (faculty_user_id,),
            ).fetchall()
            students: dict[str, dict[str, Any]] = {}
            for row in rows:
                student = students.setdefault(
                    row["student_id"],
                    {
                        "student_id": row["student_id"],
                        "name": row["name"],
                        "section": row["section"],
                        "enrollments": [],
                    },
                )
                if row["enrollment_id"] is not None:
                    student["enrollments"].append(
                        {
                            "letter_grade": row["letter_grade"],
                            "grade_point": row["grade_point"],
                            "credit_hours": row["credit_hours"],
                        }
                    )
        finally:
            connection.close()

        roster: list[dict[str, Any]] = []
        for student in students.values():
            cgpa, _ = calculate_weighted_cgpa(student["enrollments"])
            needs_attention = False
            for enrollment in student["enrollments"]:
                grade_point = grade_point_for_enrollment(enrollment)
                try:
                    credit_hours = float(enrollment["credit_hours"])
                except (KeyError, TypeError, ValueError):
                    continue
                if (
                    grade_point is not None
                    and grade_point < 2.5
                    and math.isfinite(credit_hours)
                    and credit_hours > 0
                ):
                    needs_attention = True
                    break
            student["current_cgpa"] = cgpa
            student["status"] = (
                "No grades"
                if cgpa is None
                else "Needs attention"
                if needs_attention
                else "On track"
            )
            del student["enrollments"]
            roster.append(student)
        return roster

    @staticmethod
    def get_faculty_student_enrollments(
        faculty_user_id: str, student_id: str
    ) -> list[dict[str, Any]]:
        connection = get_connection()
        try:
            assignment = connection.execute(
                """
                SELECT 1
                FROM users AS u
                JOIN faculty_sections AS fs ON fs.faculty_user_id = u.user_id
                JOIN students AS s ON s.section = fs.section
                WHERE u.user_id = ? AND u.role = 'faculty' AND s.student_id = ?
                """,
                (faculty_user_id, student_id),
            ).fetchone()
            if assignment is None:
                raise ValueError(
                    "This student is not in one of your assigned sections."
                )
        finally:
            connection.close()
        return AcademicCRUD.get_student_enrollments(student_id)

    @staticmethod
    def update_faculty_student_grade(
        faculty_user_id: str,
        student_id: str,
        course_code: str,
        semester_no: str,
        letter_grade: str | None,
    ) -> None:
        normalized_grade = letter_grade.strip().upper() if letter_grade else None
        if normalized_grade == "":
            normalized_grade = None
        if normalized_grade is not None and normalized_grade not in GRADE_POINTS:
            raise ValueError("Select a valid BUBT letter grade.")
        grade_point = (
            GRADE_POINTS[normalized_grade] if normalized_grade is not None else None
        )

        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                UPDATE enrollments
                SET letter_grade = ?, grade_point = ?
                WHERE student_id = ? AND course_code = ? AND semester_no = ?
                    AND EXISTS (
                        SELECT 1
                        FROM users AS u
                        JOIN faculty_sections AS fs
                            ON fs.faculty_user_id = u.user_id
                        JOIN students AS s ON s.section = fs.section
                        WHERE u.user_id = ? AND u.role = 'faculty'
                            AND s.student_id = enrollments.student_id
                    )
                """,
                (
                    normalized_grade,
                    grade_point,
                    student_id,
                    course_code,
                    semester_no,
                    faculty_user_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(
                    "The academic record was not found in your assigned sections."
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def get_attendance(student_id: str) -> list[dict[str, Any]]:
        """Return a student's attendance totals with course titles and percentages."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT
                    attendance.student_id,
                    attendance.course_code,
                    courses.course_title,
                    attendance.total_classes,
                    attendance.attended_classes
                FROM attendance
                JOIN courses ON courses.course_code = attendance.course_code
                WHERE attendance.student_id = ?
                ORDER BY attendance.course_code
                """,
                (student_id,),
            ).fetchall()
            records = [dict(row) for row in rows]
            for record in records:
                total_classes = record["total_classes"]
                record["attendance_percentage"] = (
                    record["attended_classes"] / total_classes * 100
                    if total_classes
                    else None
                )
            return records
        finally:
            connection.close()

    @staticmethod
    def save_attendance(
        student_id: str,
        course_code: str,
        total_classes: int,
        attended_classes: int,
    ) -> None:
        """Insert or update one student's attendance record for a course."""
        if (
            isinstance(total_classes, bool)
            or not isinstance(total_classes, int)
            or isinstance(attended_classes, bool)
            or not isinstance(attended_classes, int)
            or total_classes < 0
            or attended_classes < 0
            or attended_classes > total_classes
        ):
            raise ValueError(
                "Class totals must be non-negative integers, and attended classes "
                "cannot exceed total classes."
            )

        connection = get_connection()
        try:
            connection.execute(
                """
                INSERT INTO attendance
                    (student_id, course_code, total_classes, attended_classes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(student_id, course_code) DO UPDATE SET
                    total_classes = excluded.total_classes,
                    attended_classes = excluded.attended_classes
                """,
                (student_id, course_code, total_classes, attended_classes),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def delete_attendance(student_id: str, course_code: str) -> bool:
        """Delete one student's attendance record for a course."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                DELETE FROM attendance
                WHERE student_id = ? AND course_code = ?
                """,
                (student_id, course_code),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def get_routines() -> list[dict[str, Any]]:
        """Return the weekly course routine in weekday and time order."""
        connection = get_connection()
        try:
            rows = connection.execute(
                """
                SELECT
                    routines.routine_id,
                    routines.day,
                    routines.time,
                    routines.course_code,
                    courses.course_title,
                    routines.room
                FROM routines
                JOIN courses ON courses.course_code = routines.course_code
                ORDER BY
                    CASE routines.day
                        WHEN 'Monday' THEN 1
                        WHEN 'Tuesday' THEN 2
                        WHEN 'Wednesday' THEN 3
                        WHEN 'Thursday' THEN 4
                        WHEN 'Friday' THEN 5
                        WHEN 'Saturday' THEN 6
                        WHEN 'Sunday' THEN 7
                    END,
                    routines.time,
                    routines.course_code
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    @staticmethod
    def _validate_routine(
        day: str, time: str, course_code: str, room: str
    ) -> tuple[str, str, str, str]:
        normalized_day = day.strip().title()
        normalized_time = time.strip()
        normalized_course = course_code.strip()
        normalized_room = room.strip()
        if normalized_day not in AcademicCRUD.WEEKDAYS:
            raise ValueError("Choose a valid weekday.")
        if not normalized_time or not normalized_course or not normalized_room:
            raise ValueError("Time, course code, and room are required.")
        return normalized_day, normalized_time, normalized_course, normalized_room

    @staticmethod
    def add_routine(day: str, time: str, course_code: str, room: str) -> int:
        """Add a class to the shared weekly routine and return its identifier."""
        day, time, course_code, room = AcademicCRUD._validate_routine(
            day, time, course_code, room
        )
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                INSERT INTO routines (day, time, course_code, room)
                VALUES (?, ?, ?, ?)
                """,
                (day, time, course_code, room),
            )
            connection.commit()
            return int(cursor.lastrowid)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def update_routine(
        routine_id: int, day: str, time: str, course_code: str, room: str
    ) -> bool:
        """Update an existing weekly class entry."""
        day, time, course_code, room = AcademicCRUD._validate_routine(
            day, time, course_code, room
        )
        connection = get_connection()
        try:
            cursor = connection.execute(
                """
                UPDATE routines
                SET day = ?, time = ?, course_code = ?, room = ?
                WHERE routine_id = ?
                """,
                (day, time, course_code, room, routine_id),
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def delete_routine(routine_id: int) -> bool:
        """Delete a class from the weekly routine."""
        connection = get_connection()
        try:
            cursor = connection.execute(
                "DELETE FROM routines WHERE routine_id = ?", (routine_id,)
            )
            connection.commit()
            return cursor.rowcount == 1
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
