from collections.abc import Mapping
from typing import Any

from modules.grading import calculate_weighted_cgpa

class TrajectoryEngine:
    def __init__(self, current_cgpa, completed_credits, target_cgpa, remaining_credits):
        self.current_cgpa = current_cgpa
        self.completed_credits = completed_credits
        self.target_cgpa = target_cgpa
        self.remaining_credits = remaining_credits

    def calculate_required_gpa(self):
        total_credits = self.completed_credits + self.remaining_credits
        required_points = (self.target_cgpa * total_credits) - (self.current_cgpa * self.completed_credits)
        
        if self.remaining_credits == 0:
            return 0.0
            
        req_gpa = required_points / self.remaining_credits
        return round(req_gpa, 2)

    @staticmethod
    def calculate_current_cgpa(
        enrollments: list[Mapping[str, Any]],
    ) -> tuple[float | None, float]:
        """Calculate current CGPA and credits using official BUBT grade points."""
        return calculate_weighted_cgpa(enrollments)

    @staticmethod
    def calculate_target_required_gpa(
        current_cgpa: float,
        completed_credits: float,
        target_cgpa: float,
        remaining_credits: float,
    ) -> tuple[float, str]:
        """Compatibility helper returning the required GPA and feasibility note."""
        required_gpa = TrajectoryEngine(
            current_cgpa,
            completed_credits,
            target_cgpa,
            remaining_credits,
        ).calculate_required_gpa()
        if remaining_credits == 0:
            status = "No remaining credits."
        elif required_gpa > 4.0:
            status = "Target exceeds the maximum GPA of 4.00."
        elif required_gpa <= 0:
            status = "You are already on track to meet this target."
        else:
            status = "Target is achievable within the grading scale."
        return required_gpa, status