from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class AcademicPDFReport:
    @staticmethod
    def generate_transcript_pdf(filename, student_info, enrollments, current_cgpa):
        c = canvas.Canvas(filename, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "BANGLADESH UNIVERSITY OF BUSINESS & TECHNOLOGY")
        c.setFont("Helvetica", 12)
        c.drawString(100, 730, "EduTrack - Academic Trajectory Summary Report")
        c.line(100, 720, 500, 720)

        # Student Details
        c.setFont("Helvetica-Bold", 11)
        c.drawString(100, 690, f"Student ID: {student_info.get('student_id', 'N/A')}")
        c.drawString(100, 675, f"Name: {student_info.get('name', 'N/A')}")
        c.drawString(100, 660, f"Current Cumulative GPA: {current_cgpa}")

        # Table Header
        c.setFont("Helvetica-Bold", 10)
        c.drawString(100, 620, "Course Code")
        c.drawString(200, 620, "Semester")
        c.drawString(300, 620, "Credits")
        c.drawString(400, 620, "Grade")
        c.line(100, 610, 500, 610)

        y = 590
        c.setFont("Helvetica", 10)
        for row in enrollments:
            c.drawString(100, y, str(row['course_code']))
            c.drawString(200, y, str(row['semester_no']))
            c.drawString(300, y, str(row['credit_hours']))
            c.drawString(400, y, f"{row['letter_grade']} ({row['grade_point']})")
            y -= 20

        c.save()
        return filename