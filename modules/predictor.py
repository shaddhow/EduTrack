import numpy as np

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