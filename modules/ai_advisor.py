"""Academic coaching backed by Gemini with a local rule-based fallback."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from modules.grading import calculate_weighted_cgpa, grade_point_for_enrollment


def build_student_academic_profile(
    student_id: str,
    student_name: str,
    target_cgpa: float,
    program_credits: float,
) -> dict[str, Any]:
    """Load the student's latest academic, attendance, and schedule records."""
    from modules.crud import AcademicCRUD

    courses = AcademicCRUD.get_student_enrollments(student_id)
    attendance = AcademicCRUD.get_attendance(student_id)
    course_codes = {str(course["course_code"]) for course in courses}
    schedules = [
        routine
        for routine in AcademicCRUD.get_routines()
        if str(routine["course_code"]) in course_codes
    ]
    cgpa, graded_credits = calculate_weighted_cgpa(courses)
    weak_courses = [
        course
        for course in courses
        if (grade_point := grade_point_for_enrollment(course)) is not None
        and grade_point < 2.5
    ]
    return {
        "student_name": student_name,
        "student_id": student_id,
        "current_cgpa": cgpa,
        "graded_credits": graded_credits,
        "target_cgpa": target_cgpa,
        "program_credits": program_credits,
        "courses": courses,
        "weak_courses": weak_courses,
        "attendance": attendance,
        "schedules": schedules,
    }


class AIAdvisorEngine:
    """Generate personalized coaching, using Gemini when a key is available."""

    def __init__(self, api_key: str | None = None) -> None:
        self.client: Any | None = None
        self.cloud_error: str | None = (
            "Using personalized local coaching; no Gemini API key is configured."
            if not api_key or not api_key.strip()
            else None
        )
        if api_key and api_key.strip():
            try:
                from google import genai

                self.client = genai.Client(api_key=api_key.strip())
            except Exception as exc:
                self.cloud_error = f"Gemini could not be initialized ({type(exc).__name__})."

    def get_academic_advice(
        self,
        student_name: str,
        current_cgpa: float | None,
        completed_credits: float,
        weak_courses: Sequence[str] | Sequence[Mapping[str, Any]] | None,
        user_query: str,
        academic_profile: Mapping[str, Any] | None = None,
        conversation: Sequence[Mapping[str, str]] | None = None,
    ) -> str:
        """Answer a coaching question from academic history and recent chat."""
        profile = dict(academic_profile or {})
        profile.setdefault("student_name", student_name)
        profile.setdefault("current_cgpa", current_cgpa)
        profile.setdefault("graded_credits", completed_credits)
        profile.setdefault("weak_courses", list(weak_courses or []))

        if self.client is not None:
            try:
                from google.genai import types

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_query,
                    config=types.GenerateContentConfig(
                        system_instruction=self._build_prompt(
                            profile, conversation
                        )
                    ),
                )
                answer = getattr(response, "text", None)
                if answer and answer.strip():
                    return answer.strip()
                self.cloud_error = "Gemini returned an empty response."
            except Exception as exc:
                self.cloud_error = (
                    f"Gemini request failed ({type(exc).__name__}); "
                    "using personalized local coaching."
                )

        return self._local_advice(profile, user_query)

    @staticmethod
    def _build_prompt(
        profile: Mapping[str, Any],
        conversation: Sequence[Mapping[str, str]] | None,
    ) -> str:
        system_instructions = (
            "You are EduTrack's strict but encouraging Academic Mentor and "
            "Trainer. Be direct, constructive, and specific; never shame the "
            "student or invent facts. Diagnose patterns using only the supplied "
            "records, state assumptions, and distinguish recommendations from "
            "known data. For study plans, give a realistic weekly schedule with "
            "priorities and measurable checkpoints. For exam strategy, give a "
            "course-aware revision sequence, active-recall practice, and an "
            "exam-day approach. For performance diagnostics, explain strengths, "
            "risks, and the highest-impact next actions. Address the student's "
            "latest question, keep the response readable, and ask one focused "
            "follow-up only when essential."
        )
        history = [
            {"role": item.get("role", ""), "text": item.get("text", "")}
            for item in (conversation or [])[-8:]
        ]
        context = json.dumps(
            {"academic_profile": profile, "recent_conversation": history},
            ensure_ascii=False,
            default=str,
            indent=2,
        )
        return (
            f"{system_instructions}\n\n"
            f"Complete student context from EduTrack SQLite:\n{context}\n\n"
            "Use the student's latest message as the question to answer."
        )

    @staticmethod
    def _local_advice(profile: Mapping[str, Any], question: str) -> str:
        name = str(profile.get("student_name") or "Student")
        cgpa = profile.get("current_cgpa")
        credits = float(profile.get("graded_credits") or 0)
        target = profile.get("target_cgpa")
        courses = list(profile.get("courses") or [])
        weak_courses = list(profile.get("weak_courses") or [])
        attendance = list(profile.get("attendance") or [])
        schedules = list(profile.get("schedules") or [])

        if isinstance(cgpa, (int, float)):
            if cgpa < 2.5:
                headline = f"{name}, your CGPA is {cgpa:.2f}; recovery needs a focused plan."
                priority = (
                    "Meet your academic adviser about retake eligibility, then "
                    "prioritize the courses with the lowest grades."
                )
            elif cgpa < 3.0:
                headline = f"{name}, your {cgpa:.2f} CGPA has room to improve steadily."
                priority = (
                    "Protect study time for difficult courses and aim to raise "
                    "one course result at a time."
                )
            elif cgpa < 3.5:
                headline = f"{name}, a {cgpa:.2f} CGPA is a solid base to build on."
                priority = (
                    "Keep your strongest routines and target the courses just "
                    "below your desired grade band."
                )
            else:
                headline = f"{name}, your {cgpa:.2f} CGPA shows strong performance."
                priority = (
                    "Maintain consistency while giving extra practice to advanced "
                    "or high-credit courses."
                )
        else:
            headline = f"{name}, there are not enough graded records to calculate a CGPA yet."
            priority = (
                "Start by recording your course grades and credits; until then, "
                "use weekly practice goals and attendance as leading indicators."
            )

        weak_names = [
            str(course.get("course_code") or course.get("course_title") or "Course")
            if isinstance(course, Mapping)
            else str(course)
            for course in weak_courses
        ]
        low_attendance = [
            item
            for item in attendance
            if isinstance(item.get("attendance_percentage"), (int, float))
            and item["attendance_percentage"] < 75
        ]
        question_lower = question.casefold()
        if any(word in question_lower for word in ("exam", "test", "final", "midterm")):
            response = [
                "### Exam preparation",
                "1. List the examinable topics and mark each as strong, uncertain, or weak.",
                "2. Spend most practice time on weak topics using worked problems and closed-book recall.",
                "3. Do timed questions, review every error, then repeat the missed concept the next day.",
            ]
        elif any(word in question_lower for word in ("plan", "schedule", "study", "semester")):
            response = [
                "### Your weekly training plan",
                "1. Schedule five focused 45-minute study blocks across the week; use a 10-minute break between blocks.",
                "2. Begin each block with retrieval practice, then solve problems or explain a concept without notes.",
                "3. End the week with a 30-minute self-test and adjust next week's priorities from the mistakes.",
            ]
        elif any(word in question_lower for word in ("diagnos", "performance", "improve", "cgpa", "grade")):
            response = ["### Performance check", priority]
        else:
            response = ["### Coaching", priority]

        response.extend(["", "### Based on your records", headline])
        if isinstance(target, (int, float)):
            response.append(f"Your saved target is {target:.2f} CGPA.")
        response.append(
            f"You have {credits:g} graded credits across {len(courses)} recorded course(s)."
        )
        if weak_names:
            response.append(
                "First courses to review: " + ", ".join(weak_names[:5]) + "."
            )
        if low_attendance:
            course_names = [
                str(item.get("course_code") or item.get("course_title") or "Course")
                for item in low_attendance[:5]
            ]
            response.append(
                "Attendance below 75% needs attention in: "
                + ", ".join(course_names)
                + "."
            )
        elif attendance:
            response.append("No recorded course has attendance below 75%.")
        if schedules:
            response.append(
                f"{len(schedules)} scheduled class session(s) are available; "
                "anchor study blocks around those classes."
            )
        response.extend(
            [
                "",
                "### Next checkpoint",
                "Choose one priority above, complete two focused practice sessions "
                "before your next class, and track what you can solve without notes.",
            ]
        )
        return "\n".join(response)
