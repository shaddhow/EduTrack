import google.genai as genai

class AIAdvisorEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    def get_academic_advice(self, student_name, current_cgpa, completed_credits, weak_courses, user_query):
        # Offline / Fallback Mode
        if not self.client:
            if current_cgpa < 2.50:
                return f"[Offline Advisor] Dear {student_name}, your current CGPA ({current_cgpa}) is below academic target. Consider prioritizing retakes for low-grade courses like {', '.join(weak_courses) if weak_courses else 'D/F grade subjects'}."
            else:
                return f"[Offline Advisor] Dear {student_name}, your performance is steady ({current_cgpa} CGPA across {completed_credits} credits). Maintain focus on core algorithm & math courses."

        # Online LLM Context Injection Pipeline
        prompt = f"""
        You are EduTrack's Academic Advisor AI for BUBT CSE students.
        Student Profile:
        - Name: {student_name}
        - Current CGPA: {current_cgpa}
        - Credits Completed: {completed_credits}
        - Weak Courses needing attention: {', '.join(weak_courses) if weak_courses else 'None'}
        
        Student Question: "{user_query}"
        
        Provide concise, constructive, professional academic guidance.
        """
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"[AI Connection Error] Unable to reach cloud LLM: {e}. Switching to local heuristics."