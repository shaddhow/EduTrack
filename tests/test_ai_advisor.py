"""Tests for the rule-based academic trainer and Gemini prompt context."""

from modules.ai_advisor import AIAdvisorEngine


def test_local_advice_uses_course_and_attendance_records() -> None:
    advisor = AIAdvisorEngine()
    profile = {
        "student_name": "Amina",
        "current_cgpa": 3.22,
        "graded_credits": 42,
        "target_cgpa": 3.8,
        "courses": [{"course_code": "CSE101"}, {"course_code": "MAT102"}],
        "weak_courses": [{"course_code": "MAT102"}],
        "attendance": [
            {"course_code": "MAT102", "attendance_percentage": 60.0}
        ],
        "schedules": [{"course_code": "CSE101", "day": "Monday"}],
    }

    response = advisor.get_academic_advice(
        "Amina",
        3.22,
        42,
        ["MAT102"],
        "How should I improve my CGPA?",
        academic_profile=profile,
    )

    assert "3.22" in response
    assert "MAT102" in response
    assert "below 75%" in response
    assert "42 graded credits" in response
    assert advisor.cloud_error is not None


def test_prompt_contains_complete_profile_and_trainer_instructions() -> None:
    profile = {
        "current_cgpa": 3.22,
        "courses": [{"course_code": "CSE101", "letter_grade": "A"}],
        "attendance": [{"course_code": "CSE101", "attendance_percentage": 90}],
        "schedules": [{"course_code": "CSE101", "day": "Monday"}],
    }
    prompt = AIAdvisorEngine._build_prompt(
        profile,
        [{"role": "user", "text": "Help me prioritize"}],
    )

    assert "strict but encouraging Academic Mentor" in prompt
    assert '"letter_grade": "A"' in prompt
    assert '"attendance_percentage": 90' in prompt
    assert '"day": "Monday"' in prompt
    assert "Help me prioritize" in prompt
    assert "latest message as the question" in prompt
