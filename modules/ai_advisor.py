"""Academic coaching backed by local on-device Llama 3.2, local Ollama LLMs, and an advanced offline expert inference engine."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from modules.grading import calculate_weighted_cgpa, grade_point_for_enrollment
from modules.academic_brain import BUBTAcademicBrain


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
    """Generate personalized coaching with local on-device Llama 3.2, local Ollama, and offline expert reasoning."""

    def __init__(self, api_key: str | None = None) -> None:
        self.client: Any | None = None
        self.cloud_error: str | None = "Using 100% offline local academic coaching."

    def get_academic_advice(
        self,
        student_name: str,
        current_cgpa: float | None,
        completed_credits: float,
        weak_courses: Sequence[str] | Sequence[Mapping[str, Any]] | None,
        user_query: str,
        academic_profile: Mapping[str, Any] | None = None,
        conversation: Sequence[Mapping[str, str]] | None = None,
        language: str = "en",
    ) -> str:
        """Answer a coaching question from academic history, recent chat, or offline expert reasoning."""
        profile = dict(academic_profile or {})
        profile.setdefault("student_name", student_name)
        profile.setdefault("current_cgpa", current_cgpa)
        profile.setdefault("graded_credits", completed_credits)
        profile.setdefault("weak_courses", list(weak_courses or []))

        # 0. Quick casual greetings & core trajectory calculations (instant 0ms response)
        q_trim = user_query.strip().lower()
        if any(w in q_trim for w in (
            "kmn aso", "kmn acho", "kemon aso", "kemon acho", "kmn", "ki obostha", "ki khobor",
            "valo aso", "bhalo aso", "hi", "hello", "hey", "salam", "assalamu", "how are you",
            "improve my cgpa", "raise my cgpa", "target cgpa", "reach my target"
        )):
            return self._local_advice(profile, user_query, language=language)

        # 1. Try In-App Embedded Generative LLM (Llama 3.2 1B in models/ folder - 100% Offline)
        try:
            from modules.offline_llm import EmbeddedOfflineLLM
            embedded = EmbeddedOfflineLLM.get_instance()
            if embedded.is_available():
                system_instr = (
                    f"You are EduTrack AI, an autonomous academic intelligence advisor for B.Sc. in CSE at BUBT (Bangladesh University of Business and Technology). "
                    f"Student Name: {student_name}, Current CGPA: {current_cgpa}, Completed Credits: {completed_credits}/142. "
                    "Be friendly, helpful, and precise. Answer any coding question, programming logic, theory, math, or study advice fluently in English, Bengali, or Banglish as requested."
                )
                gen_text = embedded.generate(
                    prompt=user_query,
                    system_instruction=system_instr,
                    max_tokens=350,
                    threads=8
                )
                if gen_text and len(gen_text.strip()) > 8:
                    return gen_text.strip()
        except Exception:
            pass

        # 2. Try Local Ollama LLM if available on localhost:11434 (100% offline)
        ollama_response = self._try_query_ollama(profile, user_query, conversation, language=language)
        if ollama_response:
            return ollama_response

        # 3. Fallback to Deep Academic Inference Engine (offline rule-based reasoning)
        return self._local_advice(profile, user_query, language=language)

    @classmethod
    def _try_query_ollama(
        cls,
        profile: Mapping[str, Any],
        query: str,
        conversation: Sequence[Mapping[str, str]] | None,
        language: str = "en",
    ) -> str | None:
        """Query local Ollama server if running on localhost:11434 without internet."""
        import urllib.error
        import urllib.request

        try:
            prompt = cls._build_prompt(profile, conversation, language=language)
            payload = json.dumps({
                "model": "llama3.2:1b",
                "prompt": f"{prompt}\n\nStudent question: {query}",
                "stream": False,
            }).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode())
                response_text = data.get("response", "").strip()
                if response_text:
                    return response_text
        except Exception:
            return None
        return None

    @staticmethod
    def _build_prompt(
        profile: Mapping[str, Any],
        conversation: Sequence[Mapping[str, str]] | None,
        language: str = "en",
    ) -> str:
        lang_instruction = (
            "You MUST respond in professional Academic English."
            if language == "en"
            else "Respond in natural, encouraging Bengali (বাংলা)."
        )
        system_instructions = (
            "You are EduTrack's strict but encouraging Academic Mentor and "
            "Trainer for B.Sc. in CSE at BUBT. Be direct, constructive, and specific; never shame the "
            "student or invent facts. Diagnose patterns using only the supplied "
            "records, state assumptions, and distinguish recommendations from "
            "known data. For study plans, give a realistic weekly schedule with "
            "priorities and measurable checkpoints. For exam strategy, give a "
            "course-aware revision sequence, active-recall practice, and an "
            "exam-day approach. For performance diagnostics, explain strengths, "
            "risks, and the highest-impact next actions. Address the student's "
            f"latest question, keep the response readable. {lang_instruction}"
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
    def _local_advice(profile: Mapping[str, Any], question: str, language: str = "en") -> str:
        """Deep Academic Inference Engine: Generates smart, mathematically rigorous offline coaching."""
        import re

        name = str(profile.get("student_name") or "Student")
        cgpa = profile.get("current_cgpa")
        credits = float(profile.get("graded_credits") or profile.get("completed_credits") or 0)
        target = profile.get("target_cgpa") or 3.85
        prog_credits = float(profile.get("program_credits") or 142.0)
        courses = list(profile.get("courses") or [])
        weak_courses = list(profile.get("weak_courses") or [])
        attendance = list(profile.get("attendance") or [])
        schedules = list(profile.get("schedules") or [])

        cgpa_display = f"{cgpa:.2f}" if isinstance(cgpa, (int, float)) else "N/A"
        rem_credits = max(prog_credits - credits, 0.0)

        # Determine language mode: default is English unless explicitly bn, Bengali unicode, or Banglish words
        banglish_indicators = {
            "kmn", "aso", "acho", "asen", "achen", "kemon", "obostha", "khobor",
            "valo", "bhalo", "ki", "kivabe", "korbo", "korte", "parbo", "lagbe",
            "pora", "porbo", "shomoy", "mon", "boshe", "na", "amar", "tumi",
            "apni", "bhai", "vai", "dost", "bro", "voy", "lagtese", "hobe",
            "kichu", "bolen", "dao", "dhonnobad", "thik", "ase", "ache", "acha"
        }
        words = set(re.findall(r"[a-zA-Z]+", question.lower()))
        is_banglish = bool(words.intersection(banglish_indicators))
        has_bengali_unicode = bool(re.search(r"[\u0980-\u09FF]", question))
        is_bn = (str(language).lower() == "bn") or has_bengali_unicode or is_banglish

        # 1. Trajectory calculation
        req_gpa: float | None = None
        if isinstance(cgpa, (int, float)) and rem_credits > 0:
            total_credits = credits + rem_credits
            req_gpa = ((target * total_credits) - (cgpa * credits)) / rem_credits

        # 2. Extract weak courses and low attendance
        weak_names = [
            str(c.get("course_code") or c.get("course_title") or "Course")
            if isinstance(c, Mapping)
            else str(c)
            for c in weak_courses
        ]
        low_attendance = [
            item
            for item in attendance
            if isinstance(item.get("attendance_percentage"), (int, float))
            and item["attendance_percentage"] < 75
        ]

        q_lower = question.casefold()

        # --- 1. GREETINGS & CASUAL CONVERSATION (ENG / BANGLISH / BANGLA) ---
        if any(w in q_lower for w in (
            "how are you", "how r u", "kemon acho", "kemon aso", "kemon achen", "kemon asen",
            "kmn aso", "kmn acho", "kmn asen", "kmn achen", "kmn", "ki obostha", "ki khobor",
            "valo aso", "bhalo aso", "valo acho", "bhalo acho", "valo asen", "bhalo asen",
            "kire", "bro", "dost",
            "কেমন আছো", "কেমন আছেন", "কি অবস্থা", "কী খবর"
        )):
            if is_bn:
                return (
                    f"Hello {name}! আমি EduTrack AI (EduTrackAi), আলহামদুলিল্লাহ ভালো আছি। আপনি কেমন আছেন?\n\n"
                    f"আজকে আপনার BUBT CSE পড়াশোনা, কোর্স প্ল্যান বা অন্য কোনো বিষয়ে কোনো সহায়তা লাগবে কি? নির্দ্বিধায় বলুন!"
                )
            return (
                f"Hello {name}! I am EduTrack AI (EduTrackAi), doing great and ready to assist you!\n\n"
                f"How are you doing today? How can I assist with your BUBT CSE coursework, study routine, or degree planning?"
            )

        if any(q_lower.startswith(w) or q_lower == w for w in (
            "hi", "hello", "hey", "salam", "assalamu", "good morning", "good evening",
            "suprobhat", "হাই", "হ্যালো", "সালাম", "আসসালামু আলাইকুম"
        )):
            if is_bn:
                return (
                    f"Hello {name}! Welcome to EduTrackAi.\n\n"
                    f"আমি আপনার B.Sc. in CSE প্রোগ্রামের একাডেমিক ট্র্যাক পর্যবেক্ষণ করছি "
                    f"(বর্তমান CGPA: {cgpa_display}, লক্ষ্যমাত্রা: {target:.2f}, সম্পন্ন ক্রেডিট: {credits:g})।\n\n"
                    "পড়াশোনা, রুটিন, পরীক্ষার প্রস্তুতি, রিটেক অ্যানালাইসিস বা যেকোনো পরামর্শের জন্য আপনার প্রশ্নটি লিখুন!"
                )
            return (
                f"Hello {name}! Welcome to EduTrackAi.\n\n"
                f"I am actively monitoring your B.Sc. in CSE academic trajectory at BUBT "
                f"(Current CGPA: {cgpa_display}, Target: {target:.2f}, Completed Credits: {credits:g}/{prog_credits:g}).\n\n"
                "How may I guide your study planning, course sequencing, or exam preparation today?"
            )

        # --- 2. FAREWELL & CONVERSATIONAL ACKNOWLEDGEMENTS ---
        if any(w in q_lower for w in (
            "bye", "tata", "allah hafez", "see you", "good night", "shuvo ratri",
            "pore kotha hobe", "thik ache", "thik ase", "accha", "acha", "bujhlam",
            "ok", "okay", "alhamdulillah", "বিদায়", "আচ্ছা", "ঠিক আছে"
        )):
            if is_bn:
                return (
                    f"You're always welcome, {name}! \n\n"
                    "নিয়মিত পড়াশোনার অভ্যাস বজায় রাখুন এবং ক্লাসের প্রতি মনোযোগী থাকুন। "
                    "যেকোনো পড়াশোনার পরিকল্পনা বা সহায়তায় EduTrackAi সবসময় সম্পূর্ণ অফলাইনে আপনার পাশে আছে!"
                )
            return (
                f"You're very welcome, {name}! \n\n"
                "Maintain your structured study habits, focus on core engineering subjects, and ensure high lecture attendance. "
                "EduTrackAi is always running 100% offline whenever you need strategic degree guidance!"
            )

        # --- 3. GRATITUDE ---
        if any(w in q_lower for w in ("thank you", "thanks", "dhonnobad", "thx", "onek help hoilo", "অনেক ধন্যবাদ", "ধন্যবাদ")):
            if is_bn:
                return (
                    f"You're very welcome, {name}! \n\n"
                    "আপনার লক্ষ্যমাত্রা অর্জনে নিয়মিত অধ্যবসায় রাখুন। কোনো বিষয়ে সন্দেহ থাকলে নির্দ্বিধায় আমাকে জিজ্ঞেস করুন!"
                )
            return (
                f"You're very welcome, {name}! \n\n"
                "Stay consistent in your academic routine. Feel free to consult EduTrackAi anytime for semester forecasting or grade optimization!"
            )

        # --- 4. IDENTITY & CAPABILITIES ---
        if any(w in q_lower for w in (
            "who are you", "what are you", "what can you do", "tumi ke", "ki korte paro",
            "tumar kaj ki", "introduce yourself", "about yourself", "তুমি কে", "কী করতে পারো", "তোমার কাজ কি"
        )):
            if is_bn:
                return (
                    f"আমি EduTrack AI (EduTrackAi) — BUBT CSE শিক্ষার্থীদের জন্য তৈরি স্বায়ত্তশাসিত অফলাইন একাডেমিক ইন্টেলিজেন্স সিস্টেম!\n\n"
                    f"আমি আপনার এনরোল করা কোর্স, CGPA রেকর্ড, ক্লাসের শিডিউল ও অ্যাটেনডেন্সের উপর ভিত্তি করে রিয়েল-টাইম অফলাইন বিশ্লেষণ প্রদান করি (কোনো ইন্টারনেট প্রয়োজন নেই)।\n\n"
                    "আমার মূল সক্ষমতাসমূহ:\n"
                    f"1. Trajectory Planner: আপনার {target:.2f} CGPA লক্ষ্যে পৌঁছাতে সামনের ক্রেডিটগুলোতে গড়ে কত GPA পেতে হবে তা হিসাব করা।\n"
                    "2. 7-Day Timetable: ক্লাসের সময়ের সাথে সামঞ্জস্য রেখে সাপ্তাহিক পড়ার ভারসাম্যপূর্ণ রুটিন তৈরি করা।\n"
                    "3. Retake Simulator: কম গ্রেড পাওয়া কোর্সগুলো রিটেক দিলে কীভাবে দ্রুত CGPA বুস্ট হবে তার সঠিক পূর্বাভাস।\n"
                    "4. Attendance Watchdog: কোনো কোর্সে উপস্থিতি ৭৫% এর নিচে নামলে পরীক্ষার আগেই সতর্কবার্তা প্রদান।\n"
                    "5. Offline ML Lab: ১০০টি ডিসিশন ট্রি সমৃদ্ধ র‍্যান্ডম ফরেস্ট এনসেম্বল দিয়ে পারফরম্যান্স প্রেডিকশন।\n\n"
                    "যেকোনো প্রশ্ন লিখে এন্টার (Enter) প্রেস করুন!"
                )
            return (
                f"I am EduTrack AI (EduTrackAi) — an autonomous offline Academic Intelligence Advisor engineered specifically for B.Sc. in CSE students at BUBT!\n\n"
                "System Architecture & Capabilities:\n"
                "• 100% Offline & Zero Network Latency: Runs completely on-device without cloud dependency, guaranteeing full privacy and instantaneous feedback.\n"
                f"• Trajectory Planner: Dynamically evaluates your required GPA pacing to hit your {target:.2f} CGPA goal across your remaining {rem_credits:g} credits.\n"
                "• 7-Day Study Timetable: Generates a balanced engineering routine combining lecture review, active recall, and programming sprints.\n"
                "• Course Retake Simulator: Accurately projects how repeating low-grade courses replaces previous grade points and accelerates CGPA recovery.\n"
                "• BUBT Attendance Watchdog: Monitors class attendance against the university's mandatory 75% exam clearance policy.\n"
                "• Machine Learning Simulation Lab: Employs a 100-estimator Random Forest ensemble with Explainable AI (XAI) feature attribution and Pareto optimization.\n\n"
                "Feel free to ask any academic question or explore the simulation tools!"
            )

        # --- 4.5. BUBT CSE DOMAIN BRAIN: PREREQUISITES, WAIVERS & FINE-TUNED DATASET ---
        brain = BUBTAcademicBrain.get_instance()
        prereq_match = brain.evaluate_prerequisite(question)
        if prereq_match:
            return prereq_match

        for item in brain.training_qa:
            inst = item.get("instruction", "").lower()
            inst_words = set(re.findall(r"\w+", inst))
            query_words = set(re.findall(r"\w+", q_lower))
            overlap = inst_words.intersection(query_words)
            if len(overlap) >= 3 or (len(query_words) <= 3 and len(overlap) >= 2):
                return item.get("response", "")

        if any(w in q_lower for w in ("waiver", "scholarship", "ওয়েভার", "ওয়েভারের শর্ত", "টাকা ছাড়")):
            return (
                "**BUBT টিউশন ফি ওয়েভার ও স্কলারশিপ নীতিমালা**\n\n"
                "BUBT-তে সেমিস্টার ফাইনাল ফলাফলের ওপর ভিত্তি করে নিম্নোক্ত হারে ওয়েভার প্রদান করা হয়:\n"
                "• **SGPA 4.00:** ৫০% থেকে ১০০% টিউশন ফি ওয়েভার (Chairman's / Dean's Honor Roll)\n"
                "• **SGPA 3.80 - 3.99:** ২৫% থেকে ৫০% মেরিট ওয়েভার\n\n"
                "**বাধ্যতামূলক ৩টি শর্ত:**\n"
                "১. সংশ্লিষ্ট সেমিস্টারে ন্যূনতম ১২ ক্রেডিট এনরোল থাকতে হবে।\n"
                "২. কোনো কোর্সে F বা Incomplete (I) গ্রেড থাকা যাবে না।\n"
                "৩. ক্লাসে ন্যূনতম ৭৫% উপস্থিতি সন্তোষজনক হতে হবে।"
            )

        # --- 5. MOTIVATION, STRESS, PROCRASTINATION & FOCUS ---
        if any(w in q_lower for w in (
            "stress", "tension", "tensed", "depressed", "voy", "fear", "fail",
            "mon boshe na", "alashemi", "procrastinat", "motivat", "motivation",
            "tired", "bhalo lagena", "panic", "parbo na", "কষ্ট", "মন বসে না", "টেনশন", "ভয়"
        )):
            if is_bn:
                return (
                    f"ACADEMIC MOTIVATION & FOCUS COACHING ({name})\n\n"
                    "সিএসই এবং ইঞ্জিনিয়ারিং পড়াশোনায় মানসিক চাপ বা মনোযোগের ঘাটতি অনুভব করা খুব স্বাভাবিক। তবে মনে রাখবেন:\n\n"
                    f"• আপনার বর্তমান ভিত্তি: আপনি ইতিমধ্যে {credits:g} ক্রেডিট সফলভাবে সম্পন্ন করেছেন (CGPA: {cgpa_display})। আপনি অবশ্যই সামনে আরও ভালো করতে সক্ষম।\n\n"
                    "মনোযোগ ফিরিয়ে আনার ৩টি গোল্ডেন রুল:\n"
                    "1. দ্য ৫-মিনিট রুল: বড় সিলেবাস দেখে ভয় না পেয়ে ভাবুন 'আমি শুধু মাত্র ৫ মিনিট পড়ব/কোড করব'। শুরু করার পরেই পড়ার মোমেন্টাম চলে আসে।\n"
                    "2. পোমোডোরো টেকনিক (Pomodoro): ২৫ মিনিট মোবাইল দূরে রেখে সম্পূর্ণ ফোকাস দিয়ে পড়ুন, এরপর ৫ মিনিটের রিফ্রেশিং ব্রেক নিন।\n"
                    "3. একটি করে কাজ: একসাথে ৩টি বিষয়ের চিন্তা না করে আজকের সবচেয়ে গুরুত্বপূর্ণ ১টি টপিক শেষ করুন।\n\n"
                    "ধারাবাহিকতাই সেরা সাফল্য এনে দেয়। আজ থেকেই শুরু করুন!"
                )
            return (
                f"ACADEMIC MOMENTUM & MOTIVATION FOCUS COACHING ({name})\n\n"
                "Computer Science and Engineering curricula are cognitively demanding. Experiencing stress, exam anxiety, or study fatigue is natural, but systematic execution always overcomes doubt:\n\n"
                f"• Verified Academic Baseline: You have already completed {credits:g} graded credits with a current CGPA of {cgpa_display}. You have the proven capacity to handle advanced engineering coursework.\n\n"
                "3 Cognitive Execution Rules:\n"
                "1. The 5-Minute Kickstart Rule: Never stare at an intimidating textbook or problem set. Tell yourself: \"I will only code or read for 5 minutes.\" Action creates motivation, not the other way around.\n"
                "2. Structured Pomodoro (25 + 5): Work with 100% uninterrupted focus for 25 minutes with devices silenced, followed by a 5-minute mental reset.\n"
                "3. Single-Task Priority: Never attempt to balance 3 demanding subjects in one sitting. Finish one high-impact module before switching context.\n\n"
                "Consistency will always outperform sporadic intensity. Start with just 20 minutes today!"
            )

        # --- 6. PROGRAMMING, PROJECTS & LAB GUIDANCE ---
        if any(w in q_lower for w in (
            "programming", "code", "coding", "python", "java", "c++", "dsa",
            "project", "thesis", "lab", "assignment", "problem solve", "leet code",
            "software", "development", "প্রজেক্ট", "প্রোগ্রামিং", "কোডিং", "অ্যাসাইনমেন্ট"
        )):
            if is_bn:
                return (
                    f"CSE PROGRAMMING & PROJECT STRATEGY ({name})\n\n"
                    "সিএসইতে ভালো রেজাল্ট এবং ইন্ডাস্ট্রি স্কিল অর্জনের জন্য থিওরি ও ল্যাবের সমন্বয় অত্যন্ত জরুরি:\n\n"
                    "1. ল্যাব রিপোর্ট ও অ্যাসাইনমেন্ট:\n"
                    "   - ল্যাব পারফরম্যান্স এবং সময়মত অ্যাসাইনমেন্ট সাবমিশন আপনার সেমিস্টার GPA-এর একটি বড় অংশ নির্ধারণ করে।\n"
                    "   - কোড লেখার সময় সবসময় ক্লিন কমেন্ট এবং গিট (Git) দিয়ে ভার্সন কন্ট্রোল বজায় রাখুন।\n\n"
                    "2. প্রোগ্রামিং লজিক ডেভেলপমেন্ট:\n"
                    "   - মুখস্থ না করে প্রতিদিন কমপক্ষে ১টি করে বেসিক প্রবলেম সলভ করুন (LeetCode/Codeforces/HackerRank)।\n"
                    "   - Data Structures & Algorithms (DSA) এবং অবজেক্ট ওরিয়েন্টেড কনসেপ্টে বিশেষ জোর দিন।\n\n"
                    "3. ফাইনাল ইয়ার প্রজেক্ট / থিসিস প্রস্তুতি:\n"
                    "   - নিজের আগ্রহের ফিল্ড (AI/ML, Web, App, Cyber Security) অনুযায়ী একটি রিয়েল-ওয়ার্ল্ড প্রজেক্ট বেছে নিন।\n\n"
                    "আজকের স্টাডি ব্লকে আপনার ল্যাব প্রবলেমগুলো প্র্যাকটিস করার জন্য ১ ঘণ্টা সময় বরাদ্দ রাখুন!"
                )
            return (
                f"CSE TECHNICAL MASTERY & LAB STRATEGY ({name})\n\n"
                "To build elite engineering competency and protect your GPA in B.Sc. in CSE:\n\n"
                "1. Laboratory Excellence & Continuous Assessment:\n"
                "   • Lab deliverables and weekly evaluations significantly impact semester GPA. Never treat lab reports as secondary.\n"
                "   • Maintain version control for all your coursework using Git/GitHub with clear commit logs.\n\n"
                "2. Algorithmic Problem Solving (DSA):\n"
                "   • Dedicate 45 minutes daily to solve at least 1-2 algorithmic problems (LeetCode, HackerRank, Codeforces).\n"
                "   • Focus deeply on Trees, Graphs, Dynamic Programming, and Object-Oriented System Design.\n\n"
                "3. Project Portfolio & Capstone Readiness:\n"
                "   • Develop end-to-end applications solving authentic problems (e.g., machine learning pipelines, desktop/web systems).\n\n"
                "Reserve a daily 60-minute distraction-free block strictly for hands-on coding and lab implementation!"
            )

        # --- 7. ATTENDANCE & CLASS TIMINGS ---
        if any(w in q_lower for w in (
            "attendance", "shortage", "presence", "class skip", "percentage",
            "75%", "clearence", "hazira", "kalke ki class", "class routine", "উপস্থিতি", "হাজিরা", "ক্লাস"
        )):
            if is_bn:
                lines_att: list[str] = [f"ATTENDANCE STATUS & ACADEMIC CLEARANCE ({name})"]
                if low_attendance:
                    lines_att.append("ATTENDANCE WARNING (Below 75% Clearance Threshold):")
                    for att in low_attendance:
                        pct = att.get('attendance_percentage', 0)
                        lines_att.append(f"• {att.get('course_code', 'Course')}: {pct:.1f}% উপস্থিতি — জরুরি ভিত্তিতে পরবর্তী ক্লাসগুলোতে উপস্থিত থাকতে হবে!")
                    lines_att.append("\nবি.দ্র.: বিশ্ববিদ্যালয়ের নীতিমালা অনুযায়ী পরীক্ষায় বসার জন্য ন্যূনতম ৭৫% উপস্থিতি আবশ্যক। অনুপস্থিতির কারণ থাকলে দ্রুত কোর্স শিক্ষকের সাথে যোগাযোগ করুন।")
                else:
                    lines_att.append("চমৎকার রেকর্ড! আপনার কোনো কোর্সেই উপস্থিতি ৭৫%-এর নিচে নেই।")
                    lines_att.append("ক্লাসে নিয়মিত উপস্থিত থাকলে কন্টিনিউয়াস অ্যাসেসমেন্টে ফুল মার্কস নিশ্চিত করা অনেক সহজ হয়।")
                return "\n".join(lines_att)
            lines_att_en: list[str] = [f"ATTENDANCE AUDIT & BUBT CLEARANCE STATUS ({name})"]
            if low_attendance:
                lines_att_en.append("ACADEMIC CLEARANCE ALERT (Courses Below 75% Requirement):")
                for att in low_attendance:
                    pct = att.get("attendance_percentage", 0)
                    lines_att_en.append(f"• {att.get('course_code', 'Course')}: {pct:.1f}% Attendance — Immediate attendance recovery required!")
                lines_att_en.append("\nNote: BUBT academic regulations mandate a minimum 75% attendance for final examination clearance. Please consult your course instructor promptly if legitimate medical or personal grounds exist.")
            else:
                lines_att_en.append("Exemplary Attendance Record: All enrolled courses meet or exceed the 75% university examination clearance threshold.")
                lines_att_en.append("High attendance strongly correlates with maximum marks in Continuous Assessment and Midterm evaluations.")
            return "\n".join(lines_att_en)

        lines: list[str] = []

        # --- SCENARIO 7.5: OFFLINE MACHINE LEARNING & SIMULATION ENGINE ---
        if any(w in q_lower for w in (
            "ml", "machine learning", "algorithm", "simulate", "model", "random forest",
            "prediction", "predict my grade", "how ai works", "offline ai", "xai", "explainable",
            "মেশিন লার্নিং", "অ্যালগরিদম", "প্রেডিকশন"
        )):
            try:
                from modules.offline_ml import AcademicMLPipeline
                pipeline = AcademicMLPipeline.get_instance()
                avg_att = sum(item.get("attendance_percentage", 85.0) for item in attendance) / max(len(attendance), 1)
                pred = pipeline.predict(
                    attendance_pct=avg_att,
                    midterm_pct=80.0,
                    continuous_pct=82.0,
                    credit_weight=3.0,
                    prior_cgpa=float(cgpa or 3.22),
                )
                opt = pipeline.solve_pareto_grade_plan(
                    current_cgpa=float(cgpa or 3.22),
                    completed_credits=credits,
                    target_cgpa=target,
                    remaining_credits=rem_credits,
                )
                imp_str = "\n".join([f"  • {k}: {v}% weight" for k, v in pred['feature_importances'].items()])
                plan_str = "\n".join([f"  • {p['grade']} ({p['grade_point']:.2f} GP): {p['courses_needed']} course(s) — {p['description']}" for p in opt.get('plan', [])])

                if is_bn:
                    return (
                        f"EDUTRACK অফলাইন মেশিন লার্নিং ডায়াগনস্টিক ({name})\n\n"
                        f"মেশিন লার্নিং মডেল স্পেসিফিকেশন:\n"
                        f"• অ্যালগরিদম: {pred['meta']['algorithm']}\n"
                        f"• এক্সিকিউশন: {pred['meta']['framework']} (লেটেন্সি: {pred['meta']['latency_ms']}ms, ১০০% অফলাইন)\n"
                        f"• পারফরম্যান্স প্রেডিকশন: {pred['predicted_marks']}% মার্কস → গ্রেড: {pred['predicted_grade']} ({pred['predicted_grade_point']:.2f} GP)\n"
                        f"• ঝুঁকি ক্যাটাগরি: {pred['risk_category']} (ঝুঁকির সম্ভাবনা: {pred['critical_risk_pct']}%)\n\n"
                        f"Explainable AI (XAI) ফিচার গুরুত্ব:\n{imp_str}\n\n"
                        f"প্যারেটো অপটিমাল গ্রেড প্ল্যান ({target:.2f} CGPA লক্ষ্য):\n"
                        f"• প্রয়োজনীয় ভবিষ্যৎ গড় GPA: {opt['required_avg']:.2f}\n"
                        f"{plan_str}\n\n"
                        "EduTrack-এর AI Simulation Lab ট্যাবে গিয়ে আপনি নিজে প্যারামিটার পরিবর্তন করে রিয়েল-টাইম টেস্ট করতে পারেন!"
                    )

                return (
                    f"EDUTRACK ENTERPRISE OFFLINE ML DIAGNOSTIC ({name})\n\n"
                    f"Core Machine Learning Specifications:\n"
                    f"• Algorithm: {pred['meta']['algorithm']}\n"
                    f"• Execution: {pred['meta']['framework']} (Latency: {pred['meta']['latency_ms']}ms, 100% On-Device ML)\n"
                    f"• Predicted Course Performance: {pred['predicted_marks']}% Marks → {pred['predicted_grade']} ({pred['predicted_grade_point']:.2f} Grade Point)\n"
                    f"• Risk Classification: {pred['risk_category']} (Critical Risk Probability: {pred['critical_risk_pct']}%)\n\n"
                    f"Explainable AI (XAI) Feature Importance Attribution:\n{imp_str}\n\n"
                    f"Pareto-Optimal Course Plan for {target:.2f} CGPA Target:\n"
                    f"• Required Future Average GPA: {opt['required_avg']:.2f}\n"
                    f"{plan_str}\n\n"
                    "You can simulate dynamic what-if scenarios in real-time inside the interactive AI Simulation Lab!"
                )
            except Exception:
                pass

        # --- SCENARIO 8: CGPA TARGET & HOW TO REACH GOAL ---
        if any(w in q_lower for w in (
            "cgpa", "goal", "target", "reach", "achieve", "improve", "diagnos",
            "barabo", "bhalo korbo", "barate", "jump", "point", "kivabe cgpa",
            "grade boost", "amar cgpa", "current standing", "সিজিপিএ", "গ্রেড", "টার্গেট"
        )):
            if is_bn:
                lines.append(f"ACADEMIC TRAJECTORY DIAGNOSTIC ({name})")
                lines.append(
                    f"আপনি এ পর্যন্ত {credits:g} ক্রেডিট সম্পন্ন করেছেন এবং আপনার বর্তমান CGPA {cgpa_display} (রেকর্ডকৃত কোর্স: {len(courses)}টি)। "
                    f"আপনার লক্ষ্যমাত্রা হলো {prog_credits:g} ক্রেডিটের ডিগ্রিতে {target:.2f} CGPA অর্জন করা।"
                )
                lines.append("")
                if req_gpa is not None:
                    if req_gpa <= 0:
                        lines.append(f"আপনি ইতোমধ্যে আপনার লক্ষ্যমাত্রার উপরে আছেন! বর্তমান ধারাবাহিকতা বজায় রাখুন।")
                    elif req_gpa <= 3.85:
                        lines.append(f"অবশিষ্ট {rem_credits:g} ক্রেডিটে আপনার গড়ে {req_gpa:.2f} GPA প্রয়োজন। নিয়মিত পরিশ্রমে এটি সম্পূর্ণ অর্জনযোগ্য।")
                    elif req_gpa <= 4.00:
                        lines.append(f"উচ্চ লক্ষ্যমাত্রা: অবশিষ্ট {rem_credits:g} ক্রেডিটে গড়ে {req_gpa:.2f} GPA প্রয়োজন। নতুন কোর্সের পাশাপাশি আগের কম গ্রেড পাওয়া কোর্স রিটেক দিলে লক্ষ্যমাত্রা সহজ হবে।")
                    else:
                        lines.append(f"শুধু নতুন কোর্স দিয়ে {target:.2f} অর্জন করতে {req_gpa:.2f} প্রয়োজন (যা ৪.০০ এর বেশি)। তবে রিটেক সিমুলেটর ব্যবহার করে আগের C/D গ্রেড রিপ্লেস করলে অনায়াসে টার্গেট স্পর্শ করা সম্ভব!")
                lines.append("")
                lines.append("কৌশলগত অগ্রাধিকার:")
                if weak_names:
                    lines.append(f"• প্রায়োরিটি রিভিউ: {', '.join(weak_names[:4])} কোর্সগুলোতে প্রতি সপ্তাহে ৪+ ঘণ্টা সময় দিন।")
                else:
                    lines.append("• কোর মাস্টারি: ৩-ক্রেডিট থিওরি কোর্সগুলোতে নিয়মিত রিভিশন বজায় রাখুন।")
                if low_attendance:
                    low_att_names = [str(i.get("course_code", "Course")) for i in low_attendance[:3]]
                    lines.append(f"• উপস্থিতি সতর্কতা: {', '.join(low_att_names)} কোর্সে দ্রুত উপস্থিতি বৃদ্ধি করুন।")
                lines.append("• রিটেক সুবিধা: EduTrack-এর Trajectory Planner রিটেক সিমুলেটরে টেস্ট করে দেখুন কোন কোর্সে দ্রুততম সময়ে CGPA বাড়ে।")
                return "\n".join(lines)

            # English version
            lines.append(f"ACADEMIC TRAJECTORY DIAGNOSTIC ({name})")
            lines.append(
                f"You have {credits:g} graded credits completed with a current CGPA of {cgpa_display} across {len(courses)} recorded course(s). "
                f"Your saved target is {target:.2f} CGPA across a {prog_credits:g}-credit B.Sc. in CSE degree."
            )
            lines.append("")

            if req_gpa is not None:
                if req_gpa <= 0:
                    lines.append(
                        f"Status: You are already on track! Your current pace exceeds your {target:.2f} target. "
                        "Focus on maintaining your grade stability without burning out."
                    )
                elif req_gpa <= 3.85:
                    lines.append(
                        f"Required Future GPA: You need an average GPA of {req_gpa:.2f} across your remaining {rem_credits:g} credits. "
                        "This goal is realistic and achievable with consistent study routines."
                    )
                elif req_gpa <= 4.00:
                    lines.append(
                        f"High-Pace Milestone: You need an average GPA of {req_gpa:.2f} across your remaining {rem_credits:g} credits. "
                        "Because this requires near-perfect grades, you should combine strong semester performance with course retakes to reduce the pressure."
                    )
                else:
                    lines.append(
                        f"Ceiling Notice: Mathematically reaching {target:.2f} purely from new courses requires {req_gpa:.2f} (above 4.00). "
                        "However, you can still easily achieve this target by retaking earlier lower-grade courses to gain bonus grade points!"
                    )
            lines.append("")
            lines.append("RECOMMENDED STRATEGIC PRIORITIES:")
            if weak_names:
                lines.append(f"• Priority Review: First courses to review: {', '.join(weak_names[:4])}. Allocate 4+ hours weekly to work through problem sets.")
            else:
                lines.append("• Core Mastery: Continue consistent preparation and prioritize your 3-credit lecture courses.")

            if low_attendance:
                low_att_names = [str(i.get("course_code", "Course")) for i in low_attendance[:3]]
                lines.append(f"• Attendance Alert: Attendance below 75% needs attention in: {', '.join(low_att_names)}. Regular attendance directly protects your continuous assessment marks.")
            else:
                lines.append("• Attendance Record: No recorded course has attendance below 75%. Keep this high standard.")

            lines.append("• Retake Advantage: Use the Trajectory Planner Retake Simulator to calculate the exact jump you can achieve by repeating low-grade courses.")
            return "\n".join(lines)

        # --- SCENARIO 9: 7-DAY STUDY TIMETABLE & ROUTINE ---
        elif any(w in q_lower for w in (
            "routine", "schedule", "timetable", "weekly", "plan", "time table",
            "porar", "study time", "kivabe porbo", "shomoy paina", "time management",
            "daily plan", "study schedule", "routine dao", "রুটিন", "পড়ার সময়", "পড়াশোনা"
        )):
            if is_bn:
                lines.append(f"পার্সোনালাইজড ৭ দিনের স্টাডি রুটিন / WEEKLY TIMETABLE ({name})")
                lines.append(
                    f"আপনার বর্তমান প্রোফাইল ({credits:g} ক্রেডিট, CGPA {cgpa_display})-এর ভিত্তিতে ইঞ্জিনিয়ারিং থিওরি ও ল্যাবের ভারসাম্যপূর্ণ সাপ্তাহিক রুটিন:"
                )
                lines.append("")
                lines.append("• সোমবার – বৃহস্পতিবার (লেকচার ও প্রবলেম সলভিং ব্লক):")
                lines.append("  - বিকেল ০৫:০০ – সন্ধ্যা ০৬:৩০: ডিপ ফোকাস — আজকের ক্লাসের স্লাইড রিভিশন ও ২-৩টি এক্সারসাইজ সলভ।")
                lines.append("  - সন্ধ্যা ০৭:৩০ – রাত ০৮:৪৫: অ্যাক্টিভ রিকল — নোট না দেখে মূল কনসেপ্ট নিজে লিখে প্র্যাকটিস।")
                lines.append("")
                lines.append("• শুক্রবার (প্রোগ্রামিং ল্যাব ও প্রজেক্ট স্প্রিন্ট):")
                lines.append("  - বিকেল ০৩:০০ – বিকেল ০৫:৩০: ল্যাব রিপোর্ট প্রস্তুত, কোডিং অ্যাসাইনমেন্ট ও গিটহাবে পুশ।")
                lines.append("")
                lines.append("• শনিবার (কঠিন বিষয়ের কনসেপ্ট রিভিউ):")
                lines.append("  - সকাল ১০:০০ – দুপুর ১২:৩০: ৩-ক্রেডিটের গুরুত্বপূর্ণ কোর্স বা কম গ্রেড পাওয়া বিষয়ের স্পেশাল রিভিউ।")
                lines.append("")
                lines.append("• রবিবার (সেলফ-টেস্ট ও পরবর্তী সপ্তাহের প্ল্যানিং):")
                lines.append("  - বিকেল ০৪:০০ – বিকেল ০৫:৩০: ৩০ মিনিটের মক টেস্ট এবং সামনের সপ্তাহের লক্ষ্য নির্ধারণ।")
                return "\n".join(lines)

            lines.append(f"PERSONALIZED 7-DAY STUDY TIMETABLE ({name})")
            lines.append(
                f"Based on your profile ({credits:g} graded credits, current CGPA {cgpa_display}), "
                "here is a structured weekly training plan designed to balance lectures, active recall, and rest:"
            )
            lines.append("")
            lines.append("• Monday – Thursday (Lecture Alignment & Problem Solving):")
            lines.append("  - 05:00 PM – 06:30 PM: Deep Focus Block — Review today's lecture slides and solve 2-3 worked exercises.")
            lines.append("  - 07:30 PM – 08:45 PM: Active Recall — Summarize core concepts without looking at lecture notes.")
            lines.append("")
            lines.append("• Friday (Lab & Project Sprint):")
            lines.append("  - 03:00 PM – 05:30 PM: Programming assignments, lab reports, and coursework implementation.")
            lines.append("")
            lines.append("• Saturday (Concept Consolidation):")
            lines.append("  - 10:00 AM – 12:30 PM: Dedicated review for challenging subjects (focusing on low-grade or high-credit courses).")
            lines.append("")
            lines.append("• Sunday (Assessment & Weekly Reset):")
            lines.append("  - 04:00 PM – 05:30 PM: 30-minute self-test and organizing goals for the upcoming week.")
            lines.append("")
            if low_attendance:
                lines.append("ATTENDANCE NOTE:")
                low_att_names = [str(i.get("course_code", "Course")) for i in low_attendance[:3]]
                lines.append(f"Attendance below 75% needs attention in: {', '.join(low_att_names)}. Never skip upcoming sessions.")
            return "\n".join(lines)

        # --- SCENARIO 10: RETAKE STRATEGY ---
        elif any(w in q_lower for w in (
            "retake", "repeat", "improve", "replacement", "c grade", "d grade",
            "f grade", "course repeat", "retake strategy", "retake ki", "retake korbo",
            "retake dibo", "আগের কোর্স", "রিটেক"
        )):
            if is_bn:
                lines.append(f"কোর্স রিটেক স্ট্র্যাটেজি ও CGPA বুস্ট অ্যানালাইসিস ({name})")
                lines.append(
                    f"আপনার বর্তমানে {credits:g} ক্রেডিট সম্পন্ন হয়েছে। একটি কম গ্রেড পাওয়া কোর্স রিটেক দিলে নতুন গ্রেডটি আগের গ্রেড পয়েন্টকে প্রতিস্থাপন করে, "
                    "ফলে কোনো অতিরিক্ত ক্রেডিট লোড ছাড়াই CGPA দ্রুত বৃদ্ধি পায়।"
                )
                lines.append("")
                lines.append("রিটেক কোর্স নির্বাচনের ৩টি নিয়ম:")
                lines.append("1. ৩-ক্রেডিট কোর্স অগ্রাধিকার: ল্যাবের চেয়ে ৩-ক্রেডিট থিওরি কোর্সের প্রভাব তিনগুণ বেশি।")
                lines.append("2. C/D গ্রেড রিপ্লেস: C (2.25) গ্রেডের কোর্সে A (3.75) পেলে সোজা +4.5 গ্রেড পয়েন্ট কিউমুলেটিভ টোটালে যোগ হয়।")
                if weak_names:
                    lines.append(f"3. চিহ্নিত সম্ভাব্য কোর্স: {', '.join(weak_names[:4])}।")
                lines.append("")
                lines.append("অ্যাকশন স্টেপ: Trajectory Planner-এর Retake Simulator ট্যাবে গিয়ে বিভিন্ন টার্গেট গ্রেড পরিবর্তন করে লাইভ সিজিপিএ জাম্প পরীক্ষা করুন!")
                return "\n".join(lines)

            lines.append(f"COURSE RETAKE STRATEGY & IMPACT ANALYSIS ({name})")
            lines.append(
                f"You currently have {credits:g} graded credits. Retaking an earlier course with a low grade allows you to replace "
                "the previous grade point with a higher one, boosting your CGPA without adding extra credit burden."
            )
            lines.append("")
            lines.append("RETAKE SELECTION RULES:")
            lines.append("1. Target 3-Credit Courses First: A 3-credit course has three times the weight of a 1-credit lab.")
            lines.append("2. Replace C/D Grades: Improving a course from C (2.25) to A (3.75) adds +4.5 grade points directly to your cumulative total.")
            if weak_names:
                lines.append(f"3. Identified Courses: First courses to review for retake: {', '.join(weak_names[:4])}.")
            lines.append("")
            lines.append("ACTION STEP:")
            lines.append("Open the Trajectory Planner in EduTrack and test different target grades in the Retake Simulator to see your exact CGPA jump.")
            return "\n".join(lines)

        # --- SCENARIO 11: EXAM PREPARATION ---
        elif any(w in q_lower for w in (
            "exam", "test", "final", "midterm", "prep", "preparation", "porashuna",
            "study tips", "active recall", "pomodoro", "quiz", "fail", "shob bhule jai",
            "পরীক্ষা", "প্রস্তুতি"
        )):
            if is_bn:
                lines.append(f"হাই-ইমপ্যাক্ট পরীক্ষা প্রস্তুতি ফ্রেমওয়ার্ক ({name})")
                lines.append("পরীক্ষায় সর্বোচ্চ গ্রেড নিশ্চিত করতে এই ৩-ধাপের বৈজ্ঞানিক পদ্ধতি অনুসরণ করুন:")
                lines.append("")
                lines.append("১. ধাপ ১ — সিলেবাস ট্রায়াজ (পরীক্ষার ২ সপ্তাহ পূর্বে):")
                lines.append("   - টপিকগুলোকে ৩ ভাগে ভাগ করুন: সবুজ (আত্মবিশ্বাসী), হলুদ (অনুশীলন দরকার), লাল (কঠিন)।")
                lines.append("   - মোট পড়ার ৭০% সময় ব্যয় করুন লাল টপিকগুলোকে হলুদে রূপান্তর করতে।")
                lines.append("")
                lines.append("২. ধাপ ২ — অ্যাক্টিভ রিকল ও পূর্ববর্তী প্রশ্ন সমাধান (১ সপ্তাহ পূর্বে):")
                lines.append("   - আগের সেমিস্টারের টার্ম ফাইনাল প্রশ্ন টাইম সেট করে সলভ করুন।")
                lines.append("   - বই বন্ধ রেখে খাতায় সূত্র ও ডায়াগ্রাম নিজে আঁকার অভ্যাস করুন।")
                lines.append("")
                lines.append("৩. ধাপ ৩ — প্রি-এক্সাম কনসলিডেশন (৪৮ ঘণ্টা পূর্বে):")
                lines.append("   - শুধুমাত্র ফর্মুলা শীট এবং ভুল হওয়া প্রশ্নগুলোর ওপর ফোকাস রাখুন।")
                lines.append("   - পরীক্ষার আগের রাতে ন্যূনতম ৭ ঘণ্টা পর্যাপ্ত ঘুম নিশ্চিত করুন।")
                return "\n".join(lines)

            lines.append(f"HIGH-YIELD EXAM PREPARATION FRAMEWORK ({name})")
            lines.append("Follow this structured 3-phase preparation sequence to maximize your grade band:")
            lines.append("")
            lines.append("1. Phase 1 — Topic Triage (2 Weeks Before Exam):")
            lines.append("   - Classify syllabus topics into Green (Confident), Yellow (Needs Practice), and Red (Challenging).")
            lines.append("   - Spend 70% of your initial study blocks converting Red topics to Yellow.")
            lines.append("")
            lines.append("2. Phase 2 — Active Recall & Mock Tests (1 Week Before):")
            lines.append("   - Practice timed questions from previous term papers.")
            lines.append("   - Never re-read passively: close the textbook and write out formulas or definitions from memory.")
            lines.append("")
            lines.append("3. Phase 3 — Pre-Exam Consolidation (48 Hours Before):")
            lines.append("   - Focus strictly on formula sheets, high-frequency concepts, and error logs.")
            lines.append("   - Prioritize 7+ hours of sleep to ensure cognitive peak on exam day.")
            if low_attendance:
                low_att_names = [str(i.get("course_code", "Course")) for i in low_attendance[:3]]
                lines.append(f"\nExam Clearance Alert: Attendance below 75% needs attention in: {', '.join(low_att_names)}. Ensure clearance with your department controller.")
            return "\n".join(lines)

        # --- SCENARIO 12: INTELLIGENT DYNAMIC FALLBACK FOR ALL OTHER QUERIES ---
        else:
            if is_bn:
                lines.append(f"EDUTRACK AI ACADEMIC ADVISOR ({name})")
                lines.append(f"আপনার প্রশ্ন: \"{question.strip()}\"")
                lines.append("")
                lines.append(
                    f"আপনার একাডেমিক রেকর্ড অনুসারে বর্তমানে CGPA {cgpa_display} এবং {credits:g} ক্রেডিট সম্পন্ন হয়েছে (টার্গেট: {target:.2f})।"
                )
                lines.append("")
                lines.append("একাডেমিক নির্দেশনা ও কার্যপদ্ধতি:")
                if weak_names:
                    lines.append(f"1. প্রায়োরিটি সাবজেক্ট: আপনার পূর্ববর্তী কোর্সগুলোর মধ্যে {', '.join(weak_names[:3])}-এর মতো বিষয়ে বিশেষ নজর দিন।")
                else:
                    lines.append("1. ধারাবাহিক অধ্যয়ন: প্রতিদিনের ক্লাসের পড়া সেদিনই রিভিশন দেওয়ার অভ্যাস বজায় রাখুন।")
                
                if low_attendance:
                    low_att_names = [str(i.get("course_code", "Course")) for i in low_attendance[:2]]
                    lines.append(f"2. অ্যাটেনডেন্স সতর্কতা: {', '.join(low_att_names)} কোর্সে উপস্থিতি ৭৫%-এর নিচে, তাই সামনের কোনো ক্লাস মিস করবেন না।")
                else:
                    lines.append("2. অ্যাটেনডেন্স স্ট্যান্ডার্ড: আপনার উপস্থিতি সন্তোষজনক, এই ধারাবাহিকতা ধরে রাখুন।")

                lines.append("3. নিয়মিত প্র্যাকটিস: প্রতিদিন ৪৫ মিনিটের ফোকাসড সেশনে অ্যাক্টিভ রিকল বা কোডিং প্র্যাকটিস করুন।")
                lines.append("")
                lines.append("আপনি চাইলে নির্দিষ্টভাবে জিজ্ঞেস করতে পারেন:")
                lines.append("• \"How to reach my target CGPA?\" (টার্গেট অর্জনের সুনির্দিষ্ট ক্যালকুলেশন)")
                lines.append("• \"7-Day Study Timetable\" (সাপ্তাহিক রুটিন)")
                lines.append("• \"Retake Strategy\" (রিটেক কোর্সের হিসাব ও সিমুলেশন)")
                lines.append("• \"Exam Preparation Tips\" (পরীক্ষার সেরা রিভিশন কৌশল)")
                return "\n".join(lines)

            # English Default
            lines.append(f"EDUTRACK AI ACADEMIC ADVISOR ({name})")
            lines.append(f"Inquiry: \"{question.strip()}\"")
            lines.append("")
            lines.append(
                f"Academic Profile Diagnostic: Current CGPA {cgpa_display} across {credits:g} completed credits "
                f"(Degree Target: {target:.2f} CGPA, Remaining: {rem_credits:g} credits in B.Sc. CSE)."
            )
            lines.append("")
            lines.append("STRATEGIC ACADEMIC DIRECTIVES:")
            if weak_names:
                lines.append(f"1. Priority Subject Focus: Allocate dedicated weekly problem-solving blocks for {', '.join(weak_names[:3])} to reinforce foundational engineering concepts.")
            else:
                lines.append("1. Core Lecture Mastery: Maintain steady same-day revision of technical lectures and slide decks.")

            if low_attendance:
                low_att_names = [str(i.get("course_code", "Course")) for i in low_attendance[:2]]
                lines.append(f"2. Attendance Clearance Alert: Attendance in {', '.join(low_att_names)} is currently under the 75% BUBT exam threshold. Ensure full attendance in upcoming lectures.")
            else:
                lines.append("2. High Attendance Stability: All course attendances satisfy the minimum 75% benchmark, protecting your continuous assessment marks.")

            lines.append("3. Active Engineering Practice: Dedicate at least 45 minutes daily to programming logic or applied problem sets.")
            lines.append("")
            lines.append("QUICK STRATEGIC QUERIES YOU CAN ASK:")
            lines.append(f"• \"How to reach my target CGPA?\" (Pacing analysis for {target:.2f})")
            lines.append("• \"7-Day Study Timetable\" (Structured weekly engineering routine)")
            lines.append("• \"Retake Strategy\" (Grade replacement simulator)")
            lines.append("• \"High-Yield Exam Preparation Framework\" (Active recall protocol)")

        return "\n".join(lines)
