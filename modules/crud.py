"""Academic data access operations backed by the local SQLite database."""

from __future__ import annotations

from typing import Any

from database.db_config import get_connection, verify_password
from modules.grading import grade_point_for_letter


class AcademicCRUD:
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
                    COALESCE(settings.gemini_api_key, '') AS gemini_api_key
                FROM (SELECT ? AS user_id) AS requested
                LEFT JOIN users ON users.user_id = requested.user_id
                LEFT JOIN students ON students.student_id = requested.user_id
                LEFT JOIN user_settings AS settings
                    ON settings.user_id = requested.user_id
                """,
                (user_id, user_id),
            ).fetchone()
            if row is None:
                raise RuntimeError("Could not load user settings.")
            return dict(row)
        finally:
            connection.close()

    @staticmethod
    def save_user_settings(
        user_id: str,
        display_name: str,
        current_semester: str,
        program_credits: float,
        target_cgpa: float,
        gemini_api_key: str,
    ) -> None:
        """Persist workspace settings and update the matching student profile."""
        connection = get_connection()
        try:
            connection.execute(
                """
                INSERT INTO user_settings (
                    user_id, display_name, current_semester, program_credits,
                    target_cgpa, gemini_api_key
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    current_semester = excluded.current_semester,
                    program_credits = excluded.program_credits,
                    target_cgpa = excluded.target_cgpa,
                    gemini_api_key = excluded.gemini_api_key
                """,
                (
                    user_id,
                    display_name,
                    current_semester,
                    program_credits,
                    target_cgpa,
                    gemini_api_key,
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
