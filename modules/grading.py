"""BUBT CSE percentage-to-letter-grade and grade-point mapping."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


GRADE_POINTS: dict[str, float] = {
    "A+": 4.00,
    "A": 3.75,
    "A-": 3.50,
    "B+": 3.25,
    "B": 3.00,
    "B-": 2.75,
    "C+": 2.50,
    "C": 2.25,
    "D": 2.00,
    "F": 0.00,
}

PERCENTAGE_BANDS = (
    (80.0, "A+"),
    (75.0, "A"),
    (70.0, "A-"),
    (65.0, "B+"),
    (60.0, "B"),
    (55.0, "B-"),
    (50.0, "C+"),
    (45.0, "C"),
    (40.0, "D"),
)


def grade_point_for_letter(letter_grade: str | None) -> float | None:
    """Return the official BUBT grade point for a letter grade, if recognized."""
    if letter_grade is None:
        return None
    return GRADE_POINTS.get(letter_grade.strip().upper())


def grade_point_for_enrollment(enrollment: Mapping[str, Any]) -> float | None:
    """Resolve an enrollment to a valid BUBT point, rejecting legacy non-BUBT values."""
    grade_point = grade_point_for_letter(enrollment.get("letter_grade"))
    if grade_point is not None:
        return grade_point

    try:
        stored_point = float(enrollment["grade_point"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(stored_point) or stored_point not in GRADE_POINTS.values():
        return None
    return stored_point


def grade_from_percentage(percentage: float) -> tuple[str, float]:
    """Convert a percentage in [0, 100] to its BUBT letter grade and points."""
    if isinstance(percentage, bool) or not isinstance(percentage, (int, float)):
        raise TypeError("Percentage must be a number.")
    score = float(percentage)
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("Percentage must be between 0 and 100.")

    for threshold, letter_grade in PERCENTAGE_BANDS:
        if score >= threshold:
            return letter_grade, GRADE_POINTS[letter_grade]
    return "F", GRADE_POINTS["F"]


def calculate_weighted_cgpa(
    enrollments: Iterable[Mapping[str, Any]],
) -> tuple[float | None, float]:
    """Return CGPA and graded credits using BUBT points for recognized letters."""
    total_credits = 0.0
    total_grade_points = 0.0
    for enrollment in enrollments:
        try:
            credits = float(enrollment["credit_hours"])
            grade_point = grade_point_for_enrollment(enrollment)
            if (
                not math.isfinite(credits)
                or credits <= 0
                or grade_point is None
            ):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        total_credits += credits
        total_grade_points += credits * grade_point

    cgpa = total_grade_points / total_credits if total_credits else None
    return cgpa, total_credits
