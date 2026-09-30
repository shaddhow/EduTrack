import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk

# --- GLOBAL LIGHT THEME CONFIGURATION ---
THEME = {
    "bg": "#edf6fb",
    "sidebar": "#12324f",
    "sidebar_active": "#d9edfb",
    "sidebar_text": "#b8cde0",
    "card": "#ffffff",
    "card_border": "#d7e6ee",
    "accent": "#1688c4",
    "accent_hover": "#0c70aa",
    "success": "#21866c",
    "warning": "#c88a33",
    "danger": "#c65355",
    "text_primary": "#17364d",
    "text_secondary": "#647f90",
    "input_bg": "#f0f7fb"
}

class EduTrackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EduTrack Pro - Smart Academic Trajectory Predictor")
        self.root.geometry("1280x750")
        self.root.minsize(1100, 680)
        self.root.configure(bg=THEME["bg"])

        # User Session State
        self.authenticated_user = None
        self.nav_buttons = []
        self.active_btn_container = None
        self._transition_job = None

        # Main Container
        self.main_container = tk.Frame(self.root, bg=THEME["bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Show Auth Gate Screen First
        self.show_login_screen()

    def find_bubt_logo(self):
        logo_name = "bubt-seeklogo.png"
        candidates = (
            os.path.join(os.path.dirname(__file__), "assets", logo_name),
            os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "bubt_logo", logo_name)),
            r"D:\bubt_logo\bubt-seeklogo.png",
        )
        return next((path for path in candidates if os.path.exists(path)), None)

    def animate_transition(self):
        if self._transition_job:
            try:
                self.root.after_cancel(self._transition_job)
            except tk.TclError:
                pass
        try:
            self.root.attributes("-alpha", 0.78)
        except tk.TclError:
            return

        def reveal(frame=1):
            if not self.root.winfo_exists():
                return
            try:
                self.root.attributes("-alpha", min(1.0, 0.78 + frame * 0.044))
            except tk.TclError:
                return
            if frame < 5:
                self._transition_job = self.root.after(18, reveal, frame + 1)
            else:
                self._transition_job = None

        self._transition_job = self.root.after(0, reveal)

    # ==========================================
    # 1. LIGHT THEME LOGIN / AUTH GATEWAY
    # ==========================================
    def show_login_screen(self):
        reveal_job = getattr(self, "_login_reveal_job", None)
        if reveal_job:
            try:
                self.root.after_cancel(reveal_job)
            except tk.TclError:
                pass
            self._login_reveal_job = None
        for widget in self.main_container.winfo_children():
            widget.destroy()
        palette = {
            "ink": "#d6f1ff",
            "ink_soft": "#eff9fe",
            "mint": "#148bc8",
            "paper": "#f3faff",
            "white": "#ffffff",
            "text": "#17364d",
            "muted": "#5d7b8e",
            "line": "#d4e7f1",
            "field": "#ffffff",
            "accent": "#1688c4",
            "accent_hover": "#0c70aa",
            "error": "#c65355",
        }

        self.root.minsize(1000, 650)
        self.main_container.configure(bg=palette["paper"])
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=11, minsize=480)
        self.main_container.grid_columnconfigure(1, weight=9, minsize=440)

        showcase = tk.Frame(self.main_container, bg=palette["ink"], padx=52, pady=38)
        showcase.grid(row=0, column=0, sticky="nsew")
        showcase.grid_rowconfigure(2, weight=1)
        showcase.grid_columnconfigure(0, weight=1)

        brand = tk.Frame(showcase, bg=palette["ink"])
        brand.grid(row=0, column=0, sticky="ew")
        brand.grid_columnconfigure(1, weight=1)
        mark = tk.Canvas(brand, width=42, height=42, bg=palette["ink"], highlightthickness=0)
        mark.pack(side=tk.LEFT, padx=(0, 12))
        mark.create_rectangle(2, 2, 40, 40, fill=palette["mint"], outline="")
        mark.create_text(21, 21, text="E", fill=palette["ink"], font=("Segoe UI", 22, "bold"))
        brand_name = tk.Frame(brand, bg=palette["ink"])
        brand_name.pack(side=tk.LEFT)
        tk.Label(brand_name, text="EduTrack", font=("Segoe UI", 17, "bold"), fg=palette["text"], bg=palette["ink"]).pack(anchor="w")
        tk.Label(brand_name, text="ACADEMIC INTELLIGENCE", font=("Segoe UI", 8, "bold"), fg=palette["muted"], bg=palette["ink"]).pack(anchor="w", pady=(1, 0))
        logo_path = self.find_bubt_logo()
        if logo_path:
            try:
                logo_image = Image.open(logo_path).convert("RGBA")
                logo_image.thumbnail((132, 48), Image.Resampling.LANCZOS)
                self.login_bubt_logo = ImageTk.PhotoImage(logo_image)
                logo_badge = tk.Frame(brand, bg=palette["white"], padx=8, pady=4)
                logo_badge.pack(side=tk.RIGHT)
                tk.Label(logo_badge, image=self.login_bubt_logo, bg=palette["white"]).pack()
            except Exception:
                pass

        message = tk.Frame(showcase, bg=palette["ink"])
        message.grid(row=1, column=0, sticky="w", pady=(64, 26))
        tk.Label(message, text="YOUR NEXT CHAPTER,\nBY THE NUMBERS.", justify="left", font=("Segoe UI", 29, "bold"), fg=palette["text"], bg=palette["ink"]).pack(anchor="w")
        tk.Label(message, text="See where you stand. Plan where you’re going.\nMake every semester move you forward.", justify="left", font=("Segoe UI", 11), fg=palette["muted"], bg=palette["ink"], pady=13).pack(anchor="w")

        visual = tk.Frame(showcase, bg=palette["ink_soft"], padx=18, pady=16)
        visual.grid(row=2, column=0, sticky="nsew", pady=(0, 24))
        visual.grid_rowconfigure(1, weight=1)
        visual.grid_columnconfigure(0, weight=1)
        chart_header = tk.Frame(visual, bg=palette["ink_soft"])
        chart_header.grid(row=0, column=0, sticky="ew")
        tk.Label(chart_header, text="ACADEMIC TRAJECTORY", font=("Segoe UI", 8, "bold"), fg=palette["text"], bg=palette["ink_soft"]).pack(side=tk.LEFT)
        tk.Label(chart_header, text="ON THE RISE  ↗", font=("Segoe UI", 8, "bold"), fg=palette["mint"], bg=palette["ink_soft"]).pack(side=tk.RIGHT)

        chart = tk.Canvas(visual, height=205, bg=palette["ink_soft"], highlightthickness=0)
        chart.grid(row=1, column=0, sticky="nsew", pady=(10, 5))

        def draw_trajectory(event=None):
            chart.delete("all")
            width = max(chart.winfo_width(), 280)
            height = max(chart.winfo_height(), 170)
            left, right, top, bottom = 12, width - 12, 22, height - 24
            for job in getattr(self, "login_chart_jobs", []):
                try:
                    chart.after_cancel(job)
                except tk.TclError:
                    pass
            self.login_chart_jobs = []
            for step in range(4):
                y = top + step * (bottom - top) / 3
                chart.create_line(left, y, right, y, fill="#d7eaf4", dash=(2, 5))
            points = [(left + (right - left) * index / 5, bottom - (bottom - top) * value) for index, value in enumerate((0.18, 0.31, 0.29, 0.54, 0.68, 0.88))]
            trajectory_line = chart.create_line(*points[0], *points[1], fill=palette["mint"], width=3, smooth=True, splinesteps=24)

            def reveal_point(index):
                visible_points = points[:index + 1]
                chart.coords(trajectory_line, *[coordinate for point in visible_points for coordinate in point])
                chart.delete("trajectory-marker")
                for point_index, (x, y) in enumerate(visible_points):
                    radius = 5 if point_index == len(points) - 1 else 3
                    chart.create_oval(x - radius, y - radius, x + radius, y + radius, fill=palette["mint"], outline=palette["white"], width=2, tags="trajectory-marker")
                if index < len(points) - 1:
                    self.login_chart_jobs.append(chart.after(75, reveal_point, index + 1))

            reveal_point(1)
            chart.create_text(right - 2, top + 2, text="GOAL", fill=palette["muted"], font=("Segoe UI", 8, "bold"), anchor="ne")

        chart.bind("<Configure>", draw_trajectory)
        metrics = tk.Frame(visual, bg=palette["ink_soft"])
        metrics.grid(row=2, column=0, sticky="ew", pady=(7, 0))
        for column, (value, label) in enumerate((("4.00", "CGPA CEILING"), ("142", "CREDIT PLAN"), ("1", "CLEAR DIRECTION"))):
            metric = tk.Frame(metrics, bg=palette["ink_soft"])
            metric.grid(row=0, column=column, sticky="w", padx=(0, 20))
            tk.Label(metric, text=value, font=("Segoe UI", 14, "bold"), fg=palette["text"], bg=palette["ink_soft"]).pack(anchor="w")
            tk.Label(metric, text=label, font=("Segoe UI", 7, "bold"), fg=palette["muted"], bg=palette["ink_soft"]).pack(anchor="w")

        tk.Label(showcase, text="BUBT  ·  CSE DEPARTMENT", font=("Segoe UI", 8, "bold"), fg=palette["muted"], bg=palette["ink"]).grid(row=3, column=0, sticky="w")

        form_area = tk.Frame(self.main_container, bg=palette["paper"], padx=56, pady=40)
        form_area.grid(row=0, column=1, sticky="nsew")
        form_area.grid_columnconfigure(0, weight=1)
        form = tk.Frame(form_area, bg=palette["paper"])
        form.place(relx=0.5, rely=0.54, anchor="center", relwidth=1)

        def reveal_login_form(frame=0):
            try:
                form.place_configure(rely=0.54 - (0.04 * frame / 6))
            except tk.TclError:
                self._login_reveal_job = None
                return
            if frame < 6:
                self._login_reveal_job = self.root.after(35, reveal_login_form, frame + 1)
            else:
                self._login_reveal_job = None

        tk.Label(form, text="WELCOME BACK", font=("Segoe UI", 9, "bold"), fg=palette["accent"], bg=palette["paper"]).pack(anchor="w")
        tk.Label(form, text="Sign in to EduTrack", font=("Segoe UI", 25, "bold"), fg=palette["text"], bg=palette["paper"]).pack(anchor="w", pady=(7, 4))
        tk.Label(form, text="Your academic journey is waiting.", font=("Segoe UI", 10), fg=palette["muted"], bg=palette["paper"]).pack(anchor="w", pady=(0, 25))

        tk.Label(form, text="CONTINUE AS", font=("Segoe UI", 8, "bold"), fg=palette["muted"], bg=palette["paper"]).pack(anchor="w", pady=(0, 8))
        self.role_var = tk.StringVar(value="Student")
        role_frame = tk.Frame(form, bg="#e4f1f8", padx=4, pady=4)
        role_frame.pack(fill=tk.X, pady=(0, 21))
        role_buttons = {}

        def set_role(role):
            self.role_var.set(role)
            for option, button in role_buttons.items():
                selected = option == role
                button.configure(bg=palette["white"] if selected else "#e4f1f8", fg=palette["text"] if selected else palette["muted"], relief=tk.FLAT)

        for role, label in (("Student", "Student"), ("Faculty", "Faculty / Advisor")):
            button = tk.Button(role_frame, text=label, font=("Segoe UI", 9, "bold"), bd=0, padx=8, pady=9, cursor="hand2", command=lambda value=role: set_role(value))
            button.pack(side=tk.LEFT, fill=tk.X, expand=True)
            role_buttons[role] = button
        set_role("Student")

        def make_input(label_text, show=None):
            tk.Label(form, text=label_text, font=("Segoe UI", 9, "bold"), fg=palette["text"], bg=palette["paper"]).pack(anchor="w", pady=(0, 7))
            shell = tk.Frame(form, bg=palette["white"], highlightbackground=palette["line"], highlightthickness=1, padx=12, pady=3)
            shell.pack(fill=tk.X, pady=(0, 17))
            entry = tk.Entry(shell, font=("Segoe UI", 10), bg=palette["white"], fg=palette["text"], insertbackground=palette["accent"], bd=0, relief=tk.FLAT, show=show)
            entry.pack(fill=tk.X, ipady=9)
            entry.bind("<FocusIn>", lambda event, frame=shell: frame.configure(highlightbackground=palette["accent"]))
            entry.bind("<FocusOut>", lambda event, frame=shell: frame.configure(highlightbackground=palette["line"]))
            return entry

        self.id_entry = make_input("STUDENT ID OR INSTITUTIONAL EMAIL")
        tk.Label(form, text="PASSWORD OR ACCESS TOKEN", font=("Segoe UI", 9, "bold"), fg=palette["text"], bg=palette["paper"]).pack(anchor="w", pady=(0, 7))
        password_shell = tk.Frame(form, bg=palette["white"], highlightbackground=palette["line"], highlightthickness=1, padx=12, pady=3)
        password_shell.pack(fill=tk.X, pady=(0, 8))
        self.pass_entry = tk.Entry(password_shell, font=("Segoe UI", 10), bg=palette["white"], fg=palette["text"], insertbackground=palette["accent"], bd=0, relief=tk.FLAT, show="*")
        self.pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=9)
        self.password_visible = False

        def toggle_password():
            self.password_visible = not self.password_visible
            self.pass_entry.configure(show="" if self.password_visible else "*")
            visibility_button.configure(text="Hide" if self.password_visible else "Show")

        visibility_button = tk.Button(password_shell, text="Show", font=("Segoe UI", 8, "bold"), fg=palette["accent"], bg=palette["white"], activebackground=palette["white"], activeforeground=palette["accent"], bd=0, cursor="hand2", command=toggle_password)
        visibility_button.pack(side=tk.RIGHT, padx=(8, 0))
        self.id_entry.bind("<Return>", lambda event: self.handle_login())
        self.pass_entry.bind("<Return>", lambda event: self.handle_login())
        self.pass_entry.bind("<FocusIn>", lambda event: password_shell.configure(highlightbackground=palette["accent"]), add="+")
        self.pass_entry.bind("<FocusOut>", lambda event: password_shell.configure(highlightbackground=palette["line"]), add="+")

        self.login_status = tk.Label(form, text="", font=("Segoe UI", 9), fg=palette["error"], bg=palette["paper"], anchor="w")
        self.login_status.pack(fill=tk.X, pady=(0, 9))
        login_btn = tk.Button(form, text="Sign in to your workspace   →", font=("Segoe UI", 10, "bold"), bg=palette["accent"], fg=palette["white"], activebackground=palette["accent_hover"], activeforeground=palette["white"], bd=0, cursor="hand2", command=self.handle_login)
        login_btn.pack(fill=tk.X, ipady=12)
        login_btn.bind("<Enter>", lambda event: login_btn.configure(bg=palette["accent_hover"]))
        login_btn.bind("<Leave>", lambda event: login_btn.configure(bg=palette["accent"]))
        tk.Label(form, text="Access is reserved for BUBT CSE students and faculty.", font=("Segoe UI", 8), fg=palette["muted"], bg=palette["paper"], wraplength=360, justify="left").pack(anchor="w", pady=(17, 0))
        self.id_entry.focus_set()
        reveal_login_form()
        self.animate_transition()

    def handle_login(self):
        user_id = self.id_entry.get().strip()
        pwd = self.pass_entry.get().strip()

        if not user_id or not pwd:
            if hasattr(self, "login_status"):
                self.login_status.configure(text="Enter both your ID and password to continue.")
            else:
                messagebox.showerror("Authentication Error", "Please fill in ID and Password.")
            return

        if hasattr(self, "login_status"):
            self.login_status.configure(text="")

        role = self.role_var.get()
        self.authenticated_user = {
            "id": user_id,
            "name": "Faculty Member" if role == "Faculty" else "Student",
            "role": role,
            "dept": "CSE",
            "intake": "Intake 48"
        }

        self.build_authenticated_workspace()

    # ==========================================
    # 2. LIGHT THEME DASHBOARD & NAVIGATION
    # ==========================================
    def build_authenticated_workspace(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

        self.nav_buttons = []
        self.active_btn_container = None

        # Build Sidebar & Content Layout
        self.build_sidebar()
        
        right_wrapper = tk.Frame(self.main_container, bg=THEME["bg"])
        right_wrapper.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.build_header(right_wrapper)
        
        self.content_area = tk.Frame(right_wrapper, bg=THEME["bg"])
        self.content_area.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)

        if self.nav_buttons:
            home_view = self.show_faculty_dashboard if self.authenticated_user["role"] == "Faculty" else self.show_dashboard_view
            self.set_active_nav(home_view, self.nav_buttons[0][1], self.nav_buttons[0][2])

    def build_sidebar(self):
        sidebar = tk.Frame(self.main_container, bg=THEME["sidebar"], width=260, highlightbackground=THEME["card_border"], highlightthickness=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # Brand Header
        brand_frame = tk.Frame(sidebar, bg=THEME["sidebar"])
        brand_frame.pack(fill=tk.X, padx=15, pady=20)

        logo_path = self.find_bubt_logo()
        if logo_path:
            try:
                raw_img = Image.open(logo_path).convert("RGBA")
                raw_img.thumbnail((180, 50), Image.Resampling.LANCZOS)
                self.sidebar_logo = ImageTk.PhotoImage(raw_img)
                logo_badge = tk.Frame(brand_frame, bg="white", padx=8, pady=4)
                logo_badge.pack(anchor="w")
                tk.Label(logo_badge, image=self.sidebar_logo, bg="white").pack()
            except Exception:
                tk.Label(brand_frame, text="BUBT CSE", font=("Segoe UI", 16, "bold"), fg=THEME["accent"], bg=THEME["sidebar"]).pack(anchor="w")
        else:
            tk.Label(brand_frame, text="BUBT CSE", font=("Segoe UI", 16, "bold"), fg=THEME["accent"], bg=THEME["sidebar"]).pack(anchor="w")

        tk.Label(brand_frame, text=self.authenticated_user["role"].upper() + " WORKSPACE", font=("Segoe UI", 8, "bold"), fg=THEME["sidebar_text"], bg=THEME["sidebar"]).pack(anchor="w", pady=(10, 0))
        tk.Frame(sidebar, bg="#315054", height=1).pack(fill=tk.X, padx=15, pady=(0, 15))

        if self.authenticated_user["role"] == "Faculty":
            nav_items = [
                ("Student lookup", self.show_faculty_dashboard),
                ("Academic advisor", self.show_advisor_view),
                ("Reports & analytics", self.show_analytics_view),
            ]
        else:
            nav_items = [
                ("Overview", self.show_dashboard_view),
                ("Trajectory planner", self.show_predictor_view),
                ("AI academic advisor", self.show_advisor_view),
                ("Analytics & reports", self.show_analytics_view),
                ("Export summary", self.show_export_view),
            ]

        for text, command in nav_items:
            container = tk.Frame(sidebar, bg=THEME["sidebar"], height=42)
            container.pack(fill=tk.X, pady=2)

            indicator = tk.Frame(container, bg=THEME["sidebar"], width=4)
            indicator.pack(side=tk.LEFT, fill=tk.Y)

            btn = tk.Button(
                container,
                text=text,
                font=("Segoe UI", 9, "bold"),
                fg=THEME["sidebar_text"],
                bg=THEME["sidebar"],
                activeforeground=THEME["accent"],
                activebackground=THEME["sidebar_active"],
                bd=0,
                padx=15,
                anchor="w",
                cursor="hand2",
                command=lambda c=command, ct=container, ind=indicator: self.set_active_nav(c, ct, ind)
            )
            btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            btn.bind("<Enter>", lambda e, b=btn, ct=container: self.on_nav_hover(b, ct, True))
            btn.bind("<Leave>", lambda e, b=btn, ct=container: self.on_nav_hover(b, ct, False))

            self.nav_buttons.append((btn, container, indicator))

        # BACK TO LOGIN BUTTON AT BOTTOM OF SIDEBAR
        back_btn = tk.Button(
            sidebar,
            text="Return to sign in",
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9",
            fg=THEME["danger"],
            activebackground="#e2e8f0",
            activeforeground=THEME["danger"],
            bd=1,
            relief="solid",
            cursor="hand2",
            command=self.show_login_screen
        )
        back_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=15, ipady=5)

        tk.Label(sidebar, text="BUBT CSE  /  EDUTrack", font=("Segoe UI", 8), fg=THEME["sidebar_text"], bg=THEME["sidebar"]).pack(side=tk.BOTTOM, pady=(0, 5))

    def on_nav_hover(self, btn, container, is_hover):
        if self.active_btn_container == container:
            return
        if is_hover:
            btn.config(bg=THEME["sidebar_active"], fg=THEME["accent"])
            container.config(bg=THEME["sidebar_active"])
        else:
            btn.config(bg=THEME["sidebar"], fg=THEME["sidebar_text"])
            container.config(bg=THEME["sidebar"])

    def set_active_nav(self, command, active_container, active_indicator):
        self.active_btn_container = active_container
        for btn, container, indicator in self.nav_buttons:
            if container == active_container:
                btn.config(bg=THEME["sidebar_active"], fg=THEME["accent"])
                container.config(bg=THEME["sidebar_active"])
                indicator.config(bg=THEME["accent"])
            else:
                btn.config(bg=THEME["sidebar"], fg=THEME["sidebar_text"])
                container.config(bg=THEME["sidebar"])
                indicator.config(bg=THEME["sidebar"])
        command()
        self.animate_transition()

    # Header with Quick Back / Logout Controls
    def build_header(self, parent):
        header = tk.Frame(parent, bg=THEME["sidebar"], height=65, highlightbackground=THEME["card_border"], highlightthickness=1)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        context = "Faculty advising" if self.authenticated_user["role"] == "Faculty" else "Student workspace"
        tk.Label(header, text=context, font=("Segoe UI", 10, "bold"), fg=THEME["text_secondary"], bg=THEME["sidebar"]).pack(side=tk.LEFT, padx=25)

        # User Profile Actions
        profile_frame = tk.Frame(header, bg=THEME["sidebar"])
        profile_frame.pack(side=tk.RIGHT, padx=25)

        u_info = f"{self.authenticated_user['name']} | ID: {self.authenticated_user['id']}"
        tk.Label(profile_frame, text=u_info, font=("Segoe UI", 9, "bold"), fg=THEME["text_primary"], bg=THEME["sidebar"]).pack(side=tk.LEFT, padx=(0, 15))

        logout_btn = tk.Button(
            profile_frame,
            text="Sign out",
            font=("Segoe UI", 9, "bold"),
            bg="#fef2f2",
            fg=THEME["danger"],
            activebackground="#fee2e2",
            activeforeground=THEME["danger"],
            bd=1,
            relief="solid",
            padx=12,
            pady=3,
            cursor="hand2",
            command=self.show_login_screen
        )
        logout_btn.pack(side=tk.LEFT)

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    # ==========================================
    # 3. INTERACTIVE DASHBOARD VIEWS
    # ==========================================
    def create_stat_card(self, parent, title, value, subtitle="", border_accent="#2563eb"):
        card = tk.Frame(parent, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

        top_line = tk.Frame(card, bg=border_accent, height=3)
        top_line.pack(fill=tk.X)

        inner = tk.Frame(card, bg=THEME["card"], padx=15, pady=15)
        inner.pack(fill=tk.BOTH, expand=True)

        tk.Label(inner, text=title, font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w")
        value_label = tk.Label(inner, text=value, font=("Segoe UI", 20, "bold"), fg=THEME["text_primary"], bg=THEME["card"])
        value_label.pack(anchor="w", pady=4)
        subtitle_label = None
        if subtitle:
            subtitle_label = tk.Label(inner, text=subtitle, font=("Segoe UI", 8), fg=THEME["text_secondary"], bg=THEME["card"])
            subtitle_label.pack(anchor="w")
        return value_label, subtitle_label

    def show_dashboard_view(self):
        self.clear_content()
        try:
            from modules.crud import AcademicCRUD
            enrollments = AcademicCRUD.get_student_enrollments(self.authenticated_user["id"]) or []
        except Exception as error:
            print(f"Unable to load dashboard enrollments: {error}")
            enrollments = []

        valid_records = []
        semester_totals = {}
        total_credits = 0.0
        total_grade_points = 0.0
        for record in enrollments:
            try:
                credits = float(record["credit_hours"])
                grade_point = float(record["grade_point"])
                semester = str(record["semester_no"])
                if credits <= 0 or grade_point < 0:
                    continue
            except (KeyError, TypeError, ValueError):
                continue

            valid_records.append((record, credits, grade_point))
            total_credits += credits
            total_grade_points += credits * grade_point
            semester_total = semester_totals.setdefault(semester, [0.0, 0.0])
            semester_total[0] += credits * grade_point
            semester_total[1] += credits

        current_cgpa = total_grade_points / total_credits if total_credits else None
        program_credits = 142
        target_cgpa = 3.85
        remaining_credits = max(program_credits - total_credits, 0)

        heading = tk.Frame(self.content_area, bg=THEME["bg"])
        heading.pack(fill=tk.X, pady=(0, 14))
        tk.Label(heading, text="STUDENT OVERVIEW  /  ACADEMIC YEAR", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["bg"]).pack(anchor="w")
        tk.Label(heading, text="Your academic journey", font=("Segoe UI", 21, "bold"), fg=THEME["text_primary"], bg=THEME["bg"]).pack(anchor="w", pady=(3, 0))

        goal_banner = tk.Frame(self.content_area, bg="#164b70", height=122, padx=22, pady=15)
        goal_banner.pack(fill=tk.X, pady=(0, 14))
        goal_banner.pack_propagate(False)
        tk.Label(goal_banner, text="PLAN YOUR FINISH", font=("Segoe UI", 8, "bold"), fg="#c4e2f1", bg="#164b70").pack(anchor="w")
        tk.Label(goal_banner, text="Small, steady progress adds up.", font=("Segoe UI", 17, "bold"), fg="white", bg="#164b70").pack(anchor="w", pady=(3, 0))
        tk.Label(goal_banner, text="Adjust your graduation goal to see the pace your remaining credits require.", font=("Segoe UI", 9), fg="#c4e2f1", bg="#164b70").pack(anchor="w", pady=(2, 0))

        goal_control = tk.Frame(goal_banner, bg="#23658e", padx=14, pady=8)
        goal_control.place(relx=1.0, rely=0.5, anchor="e", relwidth=0.31, relheight=0.82)
        tk.Label(goal_control, text="GRADUATION GOAL", font=("Segoe UI", 8, "bold"), fg="#c4e2f1", bg="#23658e").pack(anchor="w")
        target_value_label = tk.Label(goal_control, text=f"{target_cgpa:.2f}", font=("Segoe UI", 17, "bold"), fg="#bcecff", bg="#23658e")
        target_value_label.pack(side=tk.RIGHT, anchor="e")
        target_slider = tk.Scale(goal_control, from_=3.0, to=4.0, resolution=0.05, orient=tk.HORIZONTAL, showvalue=False, bg="#23658e", fg="white", highlightthickness=0, troughcolor="#78a8c1", activebackground="#bcecff", bd=0, length=180)
        target_slider.set(target_cgpa)
        target_slider.pack(fill=tk.X, pady=(0, 0))

        stats_frame = tk.Frame(self.content_area, bg=THEME["bg"])
        stats_frame.pack(fill=tk.X, pady=(0, 14))
        cgpa_value, cgpa_detail = self.create_stat_card(
            stats_frame,
            "CURRENT CGPA",
            f"{current_cgpa:.2f}" if current_cgpa is not None else "--",
            "Weighted from recorded courses" if current_cgpa is not None else "No graded courses found",
            THEME["success"],
        )
        credits_value, credits_detail = self.create_stat_card(
            stats_frame,
            "CREDITS COMPLETED",
            f"{total_credits:g} / {program_credits:g}",
            f"{max(program_credits - total_credits, 0):g} credits remaining",
            THEME["accent"],
        )
        target_card_value, target_card_detail = self.create_stat_card(
            stats_frame,
            "TARGET CGPA",
            f"{target_cgpa:.2f}",
            "Graduation goal",
            THEME["warning"],
        )
        required_value, required_detail = self.create_stat_card(
            stats_frame,
            "REQUIRED FUTURE GPA",
            "--",
            "Add grades to calculate your pace",
            THEME["danger"],
        )

        def update_goal(value):
            target = float(value)
            target_value_label.configure(text=f"{target:.2f}")
            target_card_value.configure(text=f"{target:.2f}")
            if current_cgpa is None:
                required_value.configure(text="--")
                required_detail.configure(text="Add grades to calculate your pace")
            elif remaining_credits == 0:
                required_value.configure(text="Done")
                required_detail.configure(text="All program credits recorded")
            else:
                required = (target * program_credits - total_grade_points) / remaining_credits
                required_value.configure(text=f"{required:.2f}")
                required_detail.configure(text="Above 4.00; revise goal" if required > 4.0 else "Average across remaining credits")

        target_slider.configure(command=update_goal)
        update_goal(target_slider.get())

        workspace = tk.Frame(self.content_area, bg=THEME["bg"])
        workspace.pack(fill=tk.BOTH, expand=True)
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=7)
        workspace.grid_columnconfigure(1, weight=5)

        trend_panel = tk.Frame(workspace, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=18, pady=15)
        trend_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(trend_panel, text="SEMESTER PERFORMANCE", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(trend_panel, text="Your grade trend", font=("Segoe UI", 14, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(3, 0))
        trend_chart = tk.Canvas(trend_panel, height=180, bg=THEME["card"], highlightthickness=0)
        trend_chart.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        ordered_semesters = sorted(
            semester_totals.items(),
            key=lambda item: (0, int(item[0])) if item[0].isdigit() else (1, item[0]),
        )

        def draw_semester_trend(event=None):
            trend_chart.delete("all")
            width = max(trend_chart.winfo_width(), 300)
            height = max(trend_chart.winfo_height(), 150)
            left, right, top, bottom = 34, width - 12, 15, height - 28
            if not ordered_semesters:
                trend_chart.create_text(width / 2, height / 2 - 8, text="No academic records yet", fill=THEME["text_primary"], font=("Segoe UI", 11, "bold"))
                trend_chart.create_text(width / 2, height / 2 + 15, text="Semester results will appear here", fill=THEME["text_secondary"], font=("Segoe UI", 9))
                return

            for grade in (0, 1, 2, 3, 4):
                y = bottom - grade * (bottom - top) / 4
                trend_chart.create_line(left, y, right, y, fill=THEME["card_border"])
                trend_chart.create_text(left - 8, y, text=f"{grade}.0", fill=THEME["text_secondary"], font=("Segoe UI", 7), anchor="e")
            slot = (right - left) / len(ordered_semesters)
            bar_width = min(36, slot * 0.52)
            for index, (semester, totals) in enumerate(ordered_semesters):
                average = totals[0] / totals[1]
                x = left + slot * (index + 0.5)
                y = bottom - min(average, 4.0) * (bottom - top) / 4
                trend_chart.create_rectangle(x - bar_width / 2, y, x + bar_width / 2, bottom, fill=THEME["accent"], outline="")
                trend_chart.create_text(x, y - 9, text=f"{average:.2f}", fill=THEME["text_primary"], font=("Segoe UI", 8, "bold"))
                trend_chart.create_text(x, bottom + 14, text=f"Sem {semester}", fill=THEME["text_secondary"], font=("Segoe UI", 7))

        trend_chart.bind("<Configure>", draw_semester_trend)

        focus_panel = tk.Frame(workspace, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=18, pady=15)
        focus_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(focus_panel, text="ACADEMIC FOCUS", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(focus_panel, text="Your next best step", font=("Segoe UI", 14, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(3, 12))
        if valid_records:
            weakest_record, weakest_credits, weakest_grade = min(valid_records, key=lambda item: item[2])
            tk.Label(focus_panel, text="COURSE TO REVIEW", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w")
            tk.Label(focus_panel, text=weakest_record.get("course_code", "Course"), font=("Segoe UI", 19, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(4, 0))
            tk.Label(focus_panel, text=weakest_record.get("course_title", "Recorded course"), font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"], wraplength=250, justify="left").pack(anchor="w", pady=(2, 10))
            tk.Label(focus_panel, text=f"Grade point  {weakest_grade:.2f}     ·     {weakest_credits:g} credits", font=("Segoe UI", 9, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w")
            tk.Label(focus_panel, text="Give this course a little extra review time as you plan your next study week.", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"], wraplength=255, justify="left").pack(anchor="w", pady=(13, 0))
        else:
            tk.Label(focus_panel, text="Your records will power this space", font=("Segoe UI", 11, "bold"), fg=THEME["text_primary"], bg=THEME["card"], wraplength=260, justify="left").pack(anchor="w", pady=(7, 6))
            tk.Label(focus_panel, text="Once course grades are available, EduTrack will highlight where a focused review can make the biggest difference.", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"], wraplength=260, justify="left").pack(anchor="w")

    def show_faculty_dashboard(self):
        self.clear_content()

        heading = tk.Frame(self.content_area, bg=THEME["bg"])
        heading.pack(fill=tk.X, pady=(0, 18))
        tk.Label(heading, text="FACULTY WORKSPACE  /  STUDENT SUPPORT", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["bg"]).pack(anchor="w")
        tk.Label(heading, text="Student review", font=("Segoe UI", 23, "bold"), fg=THEME["text_primary"], bg=THEME["bg"]).pack(anchor="w", pady=(3, 2))
        tk.Label(heading, text="Look up a student to review their course history and plan an advising conversation.", font=("Segoe UI", 10), fg=THEME["text_secondary"], bg=THEME["bg"]).pack(anchor="w")

        lookup_panel = tk.Frame(self.content_area, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=20, pady=18)
        lookup_panel.pack(fill=tk.X, pady=(0, 16))
        tk.Label(lookup_panel, text="STUDENT ID", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", pady=(0, 7))
        search_row = tk.Frame(lookup_panel, bg=THEME["card"])
        search_row.pack(fill=tk.X)
        search_shell = tk.Frame(search_row, bg=THEME["input_bg"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=12, pady=2)
        search_shell.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.faculty_lookup_entry = tk.Entry(search_shell, font=("Segoe UI", 11), bg=THEME["input_bg"], fg=THEME["text_primary"], insertbackground=THEME["accent"], bd=0, relief=tk.FLAT)
        self.faculty_lookup_entry.pack(fill=tk.X, ipady=8)
        self.faculty_lookup_entry.bind("<Return>", lambda event: self.load_faculty_student())
        lookup_button = tk.Button(search_row, text="Review student  →", font=("Segoe UI", 9, "bold"), bg=THEME["accent"], fg="white", activebackground=THEME["accent_hover"], activeforeground="white", bd=0, padx=18, pady=11, cursor="hand2", command=self.load_faculty_student)
        lookup_button.pack(side=tk.RIGHT)
        lookup_button.bind("<Enter>", lambda event: lookup_button.configure(bg=THEME["accent_hover"]))
        lookup_button.bind("<Leave>", lambda event: lookup_button.configure(bg=THEME["accent"]))
        self.faculty_status = tk.Label(lookup_panel, text="", font=("Segoe UI", 9), fg=THEME["danger"], bg=THEME["card"], anchor="w")
        self.faculty_status.pack(fill=tk.X, pady=(7, 0))

        self.faculty_results = tk.Frame(self.content_area, bg=THEME["bg"])
        self.faculty_results.pack(fill=tk.BOTH, expand=True)
        empty_panel = tk.Frame(self.faculty_results, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=24, pady=28)
        empty_panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(empty_panel, text="READY TO REVIEW", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(empty_panel, text="A student record, in one place.", font=("Segoe UI", 17, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(6, 3))
        tk.Label(empty_panel, text="Course grades, credit progress and the student's strongest review priorities will appear here.", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"], wraplength=620, justify="left").pack(anchor="w")
        self.faculty_lookup_entry.focus_set()

    def load_faculty_student(self):
        student_id = self.faculty_lookup_entry.get().strip()
        self.faculty_status.configure(text="")
        for widget in self.faculty_results.winfo_children():
            widget.destroy()
        if not student_id:
            self.faculty_status.configure(text="Enter a student ID to search.")
            return

        try:
            from modules.crud import AcademicCRUD
            records = AcademicCRUD.get_student_enrollments(student_id) or []
        except Exception as error:
            print(f"Unable to load student record: {error}")
            records = []

        if not records:
            empty_panel = tk.Frame(self.faculty_results, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=24, pady=24)
            empty_panel.pack(fill=tk.BOTH, expand=True)
            tk.Label(empty_panel, text="No course records found", font=("Segoe UI", 15, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w")
            tk.Label(empty_panel, text=f"No enrollments are available for student ID {student_id}.", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", pady=(5, 0))
            return

        total_credits = 0.0
        graded_credits = 0.0
        grade_points = 0.0
        for record in records:
            try:
                credits = float(record["credit_hours"])
                total_credits += credits
                if record.get("grade_point") is not None:
                    grade_point = float(record["grade_point"])
                    grade_points += credits * grade_point
                    graded_credits += credits
            except (KeyError, TypeError, ValueError):
                continue

        current_cgpa = grade_points / graded_credits if graded_credits else None
        result_heading = tk.Frame(self.faculty_results, bg=THEME["bg"])
        result_heading.pack(fill=tk.X, pady=(0, 10))
        tk.Label(result_heading, text="STUDENT RECORD", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["bg"]).pack(anchor="w")
        tk.Label(result_heading, text=f"Student ID  {student_id}", font=("Segoe UI", 15, "bold"), fg=THEME["text_primary"], bg=THEME["bg"]).pack(anchor="w", pady=(3, 0))

        summary = tk.Frame(self.faculty_results, bg=THEME["bg"])
        summary.pack(fill=tk.X, pady=(0, 12))
        self.create_stat_card(summary, "SELECTED STUDENT · CGPA", f"{current_cgpa:.2f}" if current_cgpa is not None else "--", "Calculated from graded courses", THEME["success"])
        self.create_stat_card(summary, "CREDITS ON RECORD", f"{total_credits:g}", "Across listed enrollments", THEME["accent"])
        self.create_stat_card(summary, "COURSES REVIEWED", str(len(records)), "Course enrollment records", THEME["warning"])

        course_panel = tk.Frame(self.faculty_results, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=12, pady=10)
        course_panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(course_panel, text="COURSE HISTORY", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", padx=4, pady=(0, 8))
        style = ttk.Style(self.root)
        style.configure("EduTrack.Treeview", background=THEME["card"], foreground=THEME["text_primary"], fieldbackground=THEME["card"], rowheight=29, font=("Segoe UI", 9), borderwidth=0)
        style.configure("EduTrack.Treeview.Heading", background=THEME["input_bg"], foreground=THEME["text_primary"], font=("Segoe UI", 8, "bold"), relief="flat")
        style.map("EduTrack.Treeview", background=[("selected", THEME["sidebar_active"])], foreground=[("selected", THEME["text_primary"])])
        columns = ("course", "title", "semester", "credits", "grade", "points")
        course_table = ttk.Treeview(course_panel, columns=columns, show="headings", style="EduTrack.Treeview")
        for column, title, width in (("course", "COURSE", 110), ("title", "COURSE TITLE", 260), ("semester", "SEMESTER", 90), ("credits", "CREDITS", 80), ("grade", "GRADE", 75), ("points", "GP", 70)):
            course_table.heading(column, text=title)
            course_table.column(column, width=width, anchor="w" if column in ("course", "title") else "center")
        for record in records:
            course_table.insert("", tk.END, values=(
                record.get("course_code", ""),
                record.get("course_title", ""),
                record.get("semester_no", ""),
                record.get("credit_hours", ""),
                record.get("letter_grade") or "—",
                record.get("grade_point") if record.get("grade_point") is not None else "—",
            ))
        course_table.pack(fill=tk.BOTH, expand=True)

    def get_student_enrollments(self):
        try:
            from modules.crud import AcademicCRUD
            return AcademicCRUD.get_student_enrollments(self.authenticated_user["id"]) or []
        except Exception as error:
            print(f"Unable to load student enrollments: {error}")
            return []

    def summarize_enrollments(self, enrollments):
        graded_records = []
        semester_totals = {}
        completed_credits = 0.0
        total_grade_points = 0.0
        for record in enrollments:
            try:
                credits = float(record["credit_hours"])
                grade_point = float(record["grade_point"])
                semester = str(record["semester_no"])
                if credits <= 0 or not 0 <= grade_point <= 4:
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            graded_records.append((record, credits, grade_point))
            completed_credits += credits
            total_grade_points += credits * grade_point
            totals = semester_totals.setdefault(semester, [0.0, 0.0])
            totals[0] += credits * grade_point
            totals[1] += credits
        return {
            "graded_records": graded_records,
            "completed_credits": completed_credits,
            "cgpa": total_grade_points / completed_credits if completed_credits else None,
            "semester_averages": {
                semester: totals[0] / totals[1]
                for semester, totals in semester_totals.items()
                if totals[1]
            },
            "weak_courses": [record.get("course_code", "Course") for record, _, grade in graded_records if grade < 2.5],
        }

    def create_page_header(self, eyebrow, title, description):
        header = tk.Frame(self.content_area, bg=THEME["bg"])
        header.pack(fill=tk.X, pady=(0, 18))
        tk.Label(header, text=eyebrow.upper(), font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["bg"]).pack(anchor="w")
        tk.Label(header, text=title, font=("Segoe UI", 22, "bold"), fg=THEME["text_primary"], bg=THEME["bg"]).pack(anchor="w", pady=(3, 2))
        tk.Label(header, text=description, font=("Segoe UI", 10), fg=THEME["text_secondary"], bg=THEME["bg"], wraplength=780, justify="left").pack(anchor="w")

    def create_panel(self, parent, padx=18, pady=16):
        return tk.Frame(parent, bg=THEME["card"], highlightbackground=THEME["card_border"], highlightthickness=1, padx=padx, pady=pady)

    def show_predictor_view(self):
        self.clear_content()
        self.create_page_header("Trajectory planning", "Build your graduation target", "Test a CGPA goal against your completed and remaining credits.")
        summary = self.summarize_enrollments(self.get_student_enrollments())

        layout = tk.Frame(self.content_area, bg=THEME["bg"])
        layout.pack(fill=tk.BOTH, expand=True)
        layout.grid_columnconfigure(0, weight=6)
        layout.grid_columnconfigure(1, weight=5)
        input_panel = self.create_panel(layout, 20, 18)
        input_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        result_panel = self.create_panel(layout, 22, 20)
        result_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(input_panel, text="YOUR PLANNING ASSUMPTIONS", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["card"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        self.predictor_entries = {}
        current_default = f"{summary['cgpa']:.2f}" if summary["cgpa"] is not None else "0.00"
        completed_default = f"{summary['completed_credits']:g}"
        remaining_default = f"{max(142 - summary['completed_credits'], 0):g}"
        fields = (
            ("Current CGPA", current_default, "current"),
            ("Credits completed", completed_default, "completed"),
            ("Target CGPA", "3.85", "target"),
            ("Credits remaining", remaining_default, "remaining"),
        )
        for index, (label, value, key) in enumerate(fields):
            row, column = 1 + index * 2, 0
            tk.Label(input_panel, text=label, font=("Segoe UI", 9, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).grid(row=row, column=column, columnspan=2, sticky="w", pady=(0, 6))
            entry = tk.Entry(input_panel, font=("Segoe UI", 11), bg=THEME["input_bg"], fg=THEME["text_primary"], insertbackground=THEME["accent"], relief=tk.FLAT, bd=0)
            entry.insert(0, value)
            entry.grid(row=row + 1, column=column, columnspan=2, sticky="ew", padx=(0, 12), ipady=10, pady=(0, 14))
            self.predictor_entries[key] = entry
        input_panel.grid_columnconfigure(0, weight=1)
        input_panel.grid_columnconfigure(2, weight=1)
        planning_note = "No graded records yet. Enter your current CGPA and completed credits to personalize this scenario." if summary["cgpa"] is None else "Starts from your recorded grades. Adjust any value to explore a different scenario."
        tk.Label(input_panel, text=planning_note, font=("Segoe UI", 8), fg=THEME["text_secondary"], bg=THEME["card"], wraplength=400, justify="left").grid(row=9, column=0, columnspan=4, sticky="w", pady=(0, 14))
        calculate_button = tk.Button(input_panel, text="Calculate required GPA  →", font=("Segoe UI", 9, "bold"), bg=THEME["accent"], fg="white", activebackground=THEME["accent_hover"], activeforeground="white", bd=0, padx=18, pady=11, cursor="hand2", command=self.calculate_trajectory)
        calculate_button.grid(row=10, column=0, columnspan=4, sticky="ew")
        calculate_button.bind("<Enter>", lambda event: calculate_button.configure(bg=THEME["accent_hover"]))
        calculate_button.bind("<Leave>", lambda event: calculate_button.configure(bg=THEME["accent"]))
        self.predictor_status = tk.Label(input_panel, text="", font=("Segoe UI", 9), fg=THEME["danger"], bg=THEME["card"], anchor="w")
        self.predictor_status.grid(row=11, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        tk.Label(result_panel, text="PROJECTED STUDY PACE", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(result_panel, text="Required future GPA", font=("Segoe UI", 14, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(4, 12))
        self.required_gpa_label = tk.Label(result_panel, text="--", font=("Segoe UI", 38, "bold"), fg=THEME["accent"], bg=THEME["card"])
        self.required_gpa_label.pack(anchor="w")
        self.required_gpa_note = tk.Label(result_panel, text="Run a scenario to see your target pace.", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"], wraplength=300, justify="left")
        self.required_gpa_note.pack(anchor="w", pady=(3, 18))
        self.gpa_meter = tk.Canvas(result_panel, height=12, bg=THEME["card"], highlightthickness=0)
        self.gpa_meter.pack(fill=tk.X, pady=(0, 8))
        self.gpa_meter.bind("<Configure>", lambda event: self.draw_gpa_meter(0))
        tk.Label(result_panel, text="0.00", font=("Segoe UI", 8), fg=THEME["text_secondary"], bg=THEME["card"]).pack(side=tk.LEFT)
        tk.Label(result_panel, text="4.00 maximum", font=("Segoe UI", 8), fg=THEME["text_secondary"], bg=THEME["card"]).pack(side=tk.RIGHT)

    def calculate_trajectory(self):
        try:
            current = float(self.predictor_entries["current"].get())
            completed = float(self.predictor_entries["completed"].get())
            target = float(self.predictor_entries["target"].get())
            remaining = float(self.predictor_entries["remaining"].get())
            if not 0 <= current <= 4 or not 0 <= target <= 4 or completed < 0 or remaining < 0:
                raise ValueError
        except ValueError:
            self.predictor_status.configure(text="Enter CGPA values from 0 to 4 and non-negative credit values.")
            return

        self.predictor_status.configure(text="")
        if remaining == 0:
            self.required_gpa_label.configure(text="Done", fg=THEME["success"])
            self.required_gpa_note.configure(text="No remaining credits in this scenario.")
            self.draw_gpa_meter(0)
            return

        from modules.predictor import TrajectoryEngine
        required = TrajectoryEngine(current, completed, target, remaining).calculate_required_gpa()
        self.required_gpa_label.configure(text=f"{required:.2f}", fg=THEME["danger"] if required > 4 else THEME["accent"])
        if required > 4:
            note = "This goal exceeds the 4.00 grading ceiling. Try a lower target or review your credit assumptions."
        elif required <= 0:
            note = "You are already on track to meet this target based on the entered credits."
        else:
            note = f"Aim for an average of {required:.2f} across the remaining {remaining:g} credits."
        self.required_gpa_note.configure(text=note)
        self.draw_gpa_meter(required)

    def draw_gpa_meter(self, value):
        if not hasattr(self, "gpa_meter") or not self.gpa_meter.winfo_exists():
            return
        self.gpa_meter.delete("all")
        width = max(self.gpa_meter.winfo_width(), 240)
        self.gpa_meter.create_rectangle(0, 2, width, 10, fill=THEME["input_bg"], outline="")
        self.gpa_meter.create_rectangle(0, 2, width * min(max(value / 4, 0), 1), 10, fill=THEME["accent"], outline="")

    def show_advisor_view(self):
        self.clear_content()
        self.create_page_header("Personalized guidance", "Academic advisor", "Ask about your academic plan and get suggestions grounded in your recorded performance.")
        summary = self.summarize_enrollments(self.get_student_enrollments())
        layout = tk.Frame(self.content_area, bg=THEME["bg"])
        layout.pack(fill=tk.BOTH, expand=True)
        layout.grid_columnconfigure(0, weight=4)
        layout.grid_columnconfigure(1, weight=7)

        profile = self.create_panel(layout, 20, 18)
        profile.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(profile, text="YOUR ACADEMIC CONTEXT", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(profile, text=self.authenticated_user["id"], font=("Segoe UI", 15, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(8, 2))
        tk.Label(profile, text="Current CGPA", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", pady=(15, 1))
        tk.Label(profile, text=f"{summary['cgpa']:.2f}" if summary["cgpa"] is not None else "Not available", font=("Segoe UI", 23, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(profile, text=f"{summary['completed_credits']:g} graded credits", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", pady=(1, 14))
        tk.Label(profile, text="COURSES TO WATCH", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", pady=(0, 7))
        weak_courses = summary["weak_courses"]
        if weak_courses:
            for course in weak_courses[:4]:
                tk.Label(profile, text=f"•  {course}", font=("Segoe UI", 9, "bold"), fg=THEME["danger"], bg=THEME["card"]).pack(anchor="w", pady=2)
        else:
            tk.Label(profile, text="No low-grade courses flagged", font=("Segoe UI", 9), fg=THEME["success"], bg=THEME["card"], wraplength=210, justify="left").pack(anchor="w")

        conversation = tk.Frame(layout, bg=THEME["bg"])
        conversation.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        question_panel = self.create_panel(conversation, 18, 16)
        question_panel.pack(fill=tk.X, pady=(0, 12))
        tk.Label(question_panel, text="WHAT WOULD YOU LIKE TO WORK ON?", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", pady=(0, 8))
        quick_actions = tk.Frame(question_panel, bg=THEME["card"])
        quick_actions.pack(fill=tk.X, pady=(0, 10))
        self.advisor_input = tk.Text(question_panel, height=4, wrap=tk.WORD, font=("Segoe UI", 10), bg=THEME["input_bg"], fg=THEME["text_primary"], insertbackground=THEME["accent"], relief=tk.FLAT, padx=10, pady=9)
        self.advisor_input.pack(fill=tk.X, pady=(0, 10))

        def set_prompt(prompt):
            self.advisor_input.delete("1.0", tk.END)
            self.advisor_input.insert("1.0", prompt)
            self.advisor_input.focus_set()

        for prompt in ("How can I improve my CGPA?", "Help me plan my next semester"):
            action = tk.Button(quick_actions, text=prompt, font=("Segoe UI", 8, "bold"), bg=THEME["input_bg"], fg=THEME["text_primary"], activebackground=THEME["sidebar_active"], bd=0, padx=10, pady=7, cursor="hand2", command=lambda value=prompt: set_prompt(value))
            action.pack(side=tk.LEFT, padx=(0, 7))
        ask_button = tk.Button(question_panel, text="Get academic guidance  →", font=("Segoe UI", 9, "bold"), bg=THEME["accent"], fg="white", activebackground=THEME["accent_hover"], activeforeground="white", bd=0, padx=16, pady=10, cursor="hand2", command=self.request_academic_advice)
        ask_button.pack(anchor="e")

        answer_panel = self.create_panel(conversation, 18, 16)
        answer_panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(answer_panel, text="ADVISOR RESPONSE", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w", pady=(0, 9))
        self.advisor_output = tk.Text(answer_panel, height=8, wrap=tk.WORD, font=("Segoe UI", 10), bg=THEME["card"], fg=THEME["text_primary"], relief=tk.FLAT, padx=2, pady=2, state=tk.DISABLED)
        self.advisor_output.pack(fill=tk.BOTH, expand=True)
        self.advisor_output.configure(state=tk.NORMAL)
        self.advisor_output.insert("1.0", "Your academic context is ready. Choose a prompt or ask your own question to get started.")
        self.advisor_output.configure(state=tk.DISABLED)

    def request_academic_advice(self):
        question = self.advisor_input.get("1.0", tk.END).strip()
        if not question:
            self.advisor_output.configure(state=tk.NORMAL)
            self.advisor_output.delete("1.0", tk.END)
            self.advisor_output.insert("1.0", "Add a question or choose one of the suggested prompts above.")
            self.advisor_output.configure(state=tk.DISABLED)
            return

        summary = self.summarize_enrollments(self.get_student_enrollments())
        if summary["cgpa"] is None:
            advice = "There are no graded course records to analyze yet. Once your grades are available, ask again for guidance tailored to your academic performance."
        else:
            try:
                from modules.ai_advisor import AIAdvisorEngine
                advisor = AIAdvisorEngine(api_key=os.environ.get("GEMINI_API_KEY"))
                advice = advisor.get_academic_advice(
                    self.authenticated_user["name"],
                    summary["cgpa"],
                    summary["completed_credits"],
                    summary["weak_courses"],
                    question,
                )
            except Exception as error:
                advice = f"Advisor service is unavailable right now. Please try again later. ({error})"
        self.advisor_output.configure(state=tk.NORMAL)
        self.advisor_output.delete("1.0", tk.END)
        self.advisor_output.insert("1.0", advice)
        self.advisor_output.configure(state=tk.DISABLED)

    def show_analytics_view(self):
        self.clear_content()
        self.create_page_header("Academic insights", "Performance analytics", "Explore semester GPA movement and the grade profile behind your current standing.")
        records = self.get_student_enrollments()
        summary = self.summarize_enrollments(records)
        stats = tk.Frame(self.content_area, bg=THEME["bg"])
        stats.pack(fill=tk.X, pady=(0, 14))
        self.create_stat_card(stats, "CUMULATIVE GPA", f"{summary['cgpa']:.2f}" if summary["cgpa"] is not None else "--", "Weighted from graded credits", THEME["accent"])
        self.create_stat_card(stats, "GRADED CREDITS", f"{summary['completed_credits']:g}", "Credits included in GPA", THEME["success"])
        self.create_stat_card(stats, "SEMESTERS RECORDED", str(len(summary["semester_averages"])), "With graded course data", THEME["warning"])

        panels = tk.Frame(self.content_area, bg=THEME["bg"])
        panels.pack(fill=tk.BOTH, expand=True)
        panels.grid_columnconfigure(0, weight=7)
        panels.grid_columnconfigure(1, weight=4)
        trend_panel = self.create_panel(panels, 18, 15)
        trend_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(trend_panel, text="GPA BY SEMESTER", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(trend_panel, text="Performance trend", font=("Segoe UI", 14, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(3, 0))
        self.analytics_chart = tk.Canvas(trend_panel, height=260, bg=THEME["card"], highlightthickness=0)
        self.analytics_chart.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        distribution_panel = self.create_panel(panels, 18, 15)
        distribution_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(distribution_panel, text="COURSE GRADE MIX", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(distribution_panel, text="Grades on record", font=("Segoe UI", 14, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(3, 0))
        self.grade_mix_chart = tk.Canvas(distribution_panel, height=250, bg=THEME["card"], highlightthickness=0)
        self.grade_mix_chart.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        semester_averages = summary["semester_averages"]
        ordered_semesters = sorted(semester_averages.items(), key=lambda item: (0, int(item[0])) if item[0].isdigit() else (1, item[0]))
        grade_order = ("A", "A-", "B+", "B", "B-", "C+", "C", "D", "F")
        grade_counts = {grade: 0 for grade in grade_order}
        for record in records:
            grade = str(record.get("letter_grade") or "").strip().upper()
            if grade in grade_counts:
                grade_counts[grade] += 1

        def draw_analytics(event=None):
            chart = self.analytics_chart
            chart.delete("all")
            width = max(chart.winfo_width(), 320)
            height = max(chart.winfo_height(), 190)
            left, right, top, bottom = 38, width - 16, 18, height - 36
            if not ordered_semesters:
                chart.create_text(width / 2, height / 2, text="Semester data will appear here", fill=THEME["text_secondary"], font=("Segoe UI", 10))
            else:
                for grade in range(5):
                    y = bottom - grade * (bottom - top) / 4
                    chart.create_line(left, y, right, y, fill=THEME["card_border"])
                    chart.create_text(left - 7, y, text=f"{grade}.0", fill=THEME["text_secondary"], font=("Segoe UI", 7), anchor="e")
                slot = (right - left) / max(len(ordered_semesters) - 1, 1)
                points = []
                for index, (semester, average) in enumerate(ordered_semesters):
                    x = left + (right - left) * index / max(len(ordered_semesters) - 1, 1) if len(ordered_semesters) > 1 else (left + right) / 2
                    y = bottom - min(average, 4.0) * (bottom - top) / 4
                    points.append((x, y))
                    chart.create_text(x, bottom + 16, text=f"Sem {semester}", fill=THEME["text_secondary"], font=("Segoe UI", 7))
                    chart.create_text(x, y - 12, text=f"{average:.2f}", fill=THEME["text_primary"], font=("Segoe UI", 8, "bold"))
                if len(points) > 1:
                    chart.create_line(*[coordinate for point in points for coordinate in point], fill=THEME["accent"], width=3, smooth=True, splinesteps=20)
                for x, y in points:
                    chart.create_oval(x - 5, y - 5, x + 5, y + 5, fill=THEME["accent"], outline=THEME["card"], width=2)

            mix = self.grade_mix_chart
            mix.delete("all")
            mix_width = max(mix.winfo_width(), 230)
            max_count = max(grade_counts.values(), default=0)
            bar_left, bar_right = 42, mix_width - 14
            row_height = max((mix.winfo_height() - 14) / len(grade_order), 19)
            for index, grade in enumerate(grade_order):
                y = 10 + index * row_height
                mix.create_text(0, y + 7, text=grade, fill=THEME["text_secondary"], font=("Segoe UI", 8, "bold"), anchor="w")
                mix.create_rectangle(bar_left, y + 2, bar_right, y + 12, fill=THEME["input_bg"], outline="")
                bar_end = bar_left + (bar_right - bar_left) * grade_counts[grade] / max(max_count, 1)
                mix.create_rectangle(bar_left, y + 2, bar_end, y + 12, fill=THEME["accent"] if grade_counts[grade] else THEME["input_bg"], outline="")
                mix.create_text(bar_right + 5, y + 7, text=str(grade_counts[grade]), fill=THEME["text_primary"], font=("Segoe UI", 8), anchor="w")

        self.analytics_chart.bind("<Configure>", draw_analytics)
        self.grade_mix_chart.bind("<Configure>", draw_analytics)

    def show_export_view(self):
        self.clear_content()
        self.create_page_header("Official document", "Export academic summary", "Preview your current academic record, then create a shareable PDF report.")
        records = self.get_student_enrollments()
        summary = self.summarize_enrollments(records)
        layout = tk.Frame(self.content_area, bg=THEME["bg"])
        layout.pack(fill=tk.BOTH, expand=True)
        layout.grid_columnconfigure(0, weight=7)
        layout.grid_columnconfigure(1, weight=4)

        preview = self.create_panel(layout, 24, 22)
        preview.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(preview, text="BUBT  /  EDUTRACK", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(preview, text="Academic progress report", font=("Segoe UI", 19, "bold"), fg=THEME["text_primary"], bg=THEME["card"]).pack(anchor="w", pady=(5, 2))
        tk.Label(preview, text=f"Student ID   {self.authenticated_user['id']}", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w")
        tk.Frame(preview, bg=THEME["card_border"], height=1).pack(fill=tk.X, pady=17)
        preview_stats = tk.Frame(preview, bg=THEME["card"])
        preview_stats.pack(fill=tk.X)
        self.create_stat_card(preview_stats, "CURRENT CGPA", f"{summary['cgpa']:.2f}" if summary["cgpa"] is not None else "--", "Graded courses only", THEME["accent"])
        self.create_stat_card(preview_stats, "CREDITS", f"{summary['completed_credits']:g}", "Completed and graded", THEME["success"])
        tk.Label(preview, text="COURSE RECORDS INCLUDED", font=("Segoe UI", 8, "bold"), fg=THEME["text_secondary"], bg=THEME["card"]).pack(anchor="w", pady=(19, 7))
        preview_table = ttk.Treeview(preview, columns=("course", "semester", "credits", "grade"), show="headings", height=6, style="EduTrack.Treeview")
        for column, label, width in (("course", "COURSE", 150), ("semester", "SEMESTER", 110), ("credits", "CREDITS", 90), ("grade", "GRADE", 90)):
            preview_table.heading(column, text=label)
            preview_table.column(column, width=width, anchor="w" if column == "course" else "center")
        for record in records[:100]:
            preview_table.insert("", tk.END, values=(record.get("course_code", ""), record.get("semester_no", ""), record.get("credit_hours", ""), record.get("letter_grade") or "—"))
        preview_table.pack(fill=tk.BOTH, expand=True)

        action = self.create_panel(layout, 20, 18)
        action.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(action, text="PDF EXPORT", font=("Segoe UI", 8, "bold"), fg=THEME["accent"], bg=THEME["card"]).pack(anchor="w")
        tk.Label(action, text="A clean, printable report.", font=("Segoe UI", 15, "bold"), fg=THEME["text_primary"], bg=THEME["card"], wraplength=230, justify="left").pack(anchor="w", pady=(6, 8))
        tk.Label(action, text="Your report includes student ID, current CGPA, course grades, semester details and earned credits.", font=("Segoe UI", 9), fg=THEME["text_secondary"], bg=THEME["card"], wraplength=230, justify="left").pack(anchor="w", pady=(0, 18))
        export_button = tk.Button(action, text="Save report as PDF  ↓", font=("Segoe UI", 9, "bold"), bg=THEME["accent"], fg="white", activebackground=THEME["accent_hover"], activeforeground="white", bd=0, padx=14, pady=11, cursor="hand2", command=self.export_academic_report)
        export_button.pack(fill=tk.X)
        export_button.bind("<Enter>", lambda event: export_button.configure(bg=THEME["accent_hover"]))
        export_button.bind("<Leave>", lambda event: export_button.configure(bg=THEME["accent"]))
        self.export_status = tk.Label(action, text="", font=("Segoe UI", 9), fg=THEME["success"], bg=THEME["card"], wraplength=230, justify="left")
        self.export_status.pack(anchor="w", pady=(12, 0))

    def export_academic_report(self):
        filename = filedialog.asksaveasfilename(
            title="Save academic report",
            defaultextension=".pdf",
            initialfile=f"EduTrack_{self.authenticated_user['id']}.pdf",
            filetypes=(("PDF document", "*.pdf"),),
        )
        if not filename:
            return
        try:
            from modules.pdf_generator import AcademicPDFReport
            records = self.get_student_enrollments()
            summary = self.summarize_enrollments(records)
            AcademicPDFReport.generate_transcript_pdf(
                filename,
                {"student_id": self.authenticated_user["id"], "name": self.authenticated_user["name"]},
                records,
                summary["cgpa"] if summary["cgpa"] is not None else 0,
            )
        except Exception as error:
            self.export_status.configure(text=f"Could not create the report: {error}", fg=THEME["danger"])
            return
        self.export_status.configure(text=f"Report saved: {filename}", fg=THEME["success"])

if __name__ == "__main__":
    root = tk.Tk()
    app = EduTrackApp(root)
    root.mainloop()