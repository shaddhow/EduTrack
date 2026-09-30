import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db_config import get_connection

class AcademicCRUD:
    @staticmethod
    def add_student(student_id, name, email, intake="55", section="06"):
        conn = get_connection()
        if not conn:
            return False, "Database Connection Failed"
        try:
            cursor = conn.cursor()
            query = "INSERT INTO students (student_id, name, email, intake, section) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (student_id, name, email, intake, section))
            conn.commit()
            return True, "Student Added Successfully"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    @staticmethod
    def get_student_enrollments(student_id):
        conn = get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT e.enrollment_id, e.course_code, c.course_title, c.credit_hours, 
                       e.semester_no, e.letter_grade, e.grade_point
                FROM enrollments e
                JOIN courses c ON e.course_code = c.course_code
                WHERE e.student_id = %s
                ORDER BY e.semester_no ASC
            """
            cursor.execute(query, (student_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching enrollments: {e}")
            return []
        finally:
            conn.close()