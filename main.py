"""EduTrack desktop dashboard.

Run with ``python main.py`` after installing CustomTkinter and the optional
database/AI dependencies used by the existing modules.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import tkinter as tk
from collections import Counter, defaultdict
from tkinter import messagebox, ttk
from typing import Any

import customtkinter as ctk

from modules.app_icon import set_app_icon
from modules.grading import GRADE_POINTS
from modules.typography import (
    ACCENT_THEMES,
    DEFAULT_ACCENT_THEME,
    accent_theme_colors,
    app_font,
    maximize_window,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def calculate_calculator_gpa(
    subjects: list[dict[str, str]],
) -> tuple[float | None, float, int]:
    """Return credit-weighted GPA, graded credits, and invalid credit-entry count."""
    total_credits = 0.0
    total_grade_points = 0.0
    invalid_entries = 0

    for subject in subjects:
        credits_text = subject.get("credits", "").strip()
        if not credits_text:
            continue
        try:
            credits = float(credits_text)
        except ValueError:
            invalid_entries += 1
            continue
        if not math.isfinite(credits) or credits <= 0:
            invalid_entries += 1
            continue

        grade_point = GRADE_POINTS.get(subject.get("grade", ""))
        if grade_point is None:
            invalid_entries += 1
            continue
        total_credits += credits
        total_grade_points += credits * grade_point

    gpa = total_grade_points / total_credits if total_credits else None
    return gpa, total_credits, invalid_entries


def calculate_projected_graduation_cgpa(
    current_cgpa: float,
    completed_credits: float,
    projected_gpa: float,
    remaining_credits: float,
) -> float | None:
    """Estimate final CGPA from completed work and a projected future GPA."""
    values = (current_cgpa, completed_credits, projected_gpa, remaining_credits)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("All GPA and credit values must be finite numbers.")
    if not 0 <= current_cgpa <= 4 or not 0 <= projected_gpa <= 4:
        raise ValueError("GPA values must be between 0 and 4.")
    if completed_credits < 0 or remaining_credits < 0:
        raise ValueError("Credit values cannot be negative.")

    total_credits = completed_credits + remaining_credits
    if total_credits == 0:
        return None
    return (
        current_cgpa * completed_credits + projected_gpa * remaining_credits
    ) / total_credits


class EduTrackApp(ctk.CTk):
    """Main application window and page router."""

    PROGRAM_CREDITS = 142
    GRADE_SCALE = 4.0
    GRADE_ORDER = ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F")
    NAV_ITEMS = (
        ("Dashboard", "01"),
        ("Trajectory Planner", "02"),
        ("CGPA Calculator", "03"),
        ("AI Advisor", "04"),
        ("Analytics", "05"),
        ("Attendance & Schedule", "06"),
        ("Settings", "07"),
    )
    FACULTY_NAV_ITEMS = (
        ("Dashboard", "01"),
        ("Section Assignments", "02"),
    )

    COLORS = {
        "window": "#0B1220",
        "sidebar": "#0E1728",
        "surface": "#111D30",
        "surface_alt": "#16243A",
        "border": "#23334A",
        "text": "#F2F6FC",
        "muted": "#91A2B9",
        "blue": "#3B82F6",
        "blue_hover": "#2563EB",
        "cyan": "#38BDF8",
        "green": "#34D399",
        "amber": "#FBBF24",
        "red": "#FB7185",
    }

    def __init__(self) -> None:
        super().__init__()
        set_app_icon(self)
        self.title("EduTrack | Academic dashboard")
        self.geometry("1440x900")
        self.minsize(1100, 720)
        maximize_window(self)
        self.accent_theme = DEFAULT_ACCENT_THEME
        self.COLORS = {
            **type(self).COLORS,
            **accent_theme_colors(self.accent_theme),
        }
        self.configure(fg_color=self.COLORS["window"])

        # The sign-in launcher passes the current profile through the process
        # environment; direct dashboard launches retain the development defaults.
        self.student = {
            "name": os.environ.get("EDUTRACK_USER_NAME", "CSE Student"),
            "student_id": os.environ.get("EDUTRACK_USER_ID", "20255103311"),
            "semester": "Fall 2026",
            "role": os.environ.get("EDUTRACK_USER_ROLE", "Student"),
        }
        self.is_faculty = self.student["role"].strip().casefold() == "faculty"
        self.nav_items = self.FACULTY_NAV_ITEMS if self.is_faculty else self.NAV_ITEMS
        self.program_credits = self.PROGRAM_CREDITS
        self.target_cgpa = 3.85
        self.current_cgpa: float | None = None
        self.gemini_api_key = ""
        self.enrollments: list[dict[str, Any]] = []
        self.data_error: str | None = None
        self.current_page: str | None = None
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.nav_indicators: dict[str, ctk.CTkFrame] = {}
        self._button_color_jobs: dict[ctk.CTkButton, str] = {}
        self._button_hover_states: dict[ctk.CTkButton, tuple[str, str]] = {}
        self._status_reset_job: str | None = None
        self._scrollable_frames: list[ctk.CTkScrollableFrame] = []
        self._pending_scroll_pixels: dict[ctk.CTkScrollableFrame, float] = {}
        self._scroll_jobs: dict[ctk.CTkScrollableFrame, str] = {}
        self._chart_redraw_jobs: dict[ctk.CTkCanvas, str] = {}
        self._page_frames: dict[str, ctk.CTkScrollableFrame] = {}
        self._built_pages: set[str] = set()
        self._page_render_job: str | None = None
        self._pending_page: str | None = None
        self.calculator_semesters: list[list[dict[str, str]]] = [[]]
        self.bind_all("<MouseWheel>", self._on_smooth_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_smooth_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_smooth_mousewheel, add="+")

        self._load_student_data()
        self._build_shell()
        self.show_page("Dashboard")

    def _build_shell(self) -> None:
        """Create the persistent sidebar and page-content area."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=278,
            corner_radius=0,
            fg_color=self.COLORS["sidebar"],
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=22, pady=(26, 30))
        mark = ctk.CTkFrame(
            brand,
            width=42,
            height=42,
            corner_radius=13,
            fg_color=self.COLORS["blue"],
        )
        mark.pack(side="left", padx=(0, 12))
        mark.pack_propagate(False)
        ctk.CTkLabel(
            mark,
            text="E",
            font=app_font(family="Segoe UI", size=23, weight="bold"),
            text_color="white",
        ).place(relx=0.5, rely=0.5, anchor="center")
        brand_name = ctk.CTkFrame(brand, fg_color="transparent")
        brand_name.pack(side="left", fill="y")
        ctk.CTkLabel(
            brand_name,
            text="EduTrack",
            font=app_font(family="Segoe UI", size=21, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(anchor="w", pady=(1, 0))
        ctk.CTkLabel(
            brand_name,
            text="ACADEMIC INTELLIGENCE",
            font=app_font(family="Segoe UI", size=8, weight="bold"),
            text_color=self.COLORS["muted"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            self.sidebar,
            text="FACULTY WORKSPACE" if self.is_faculty else "STUDENT WORKSPACE",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 10))

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.grid(row=2, column=0, sticky="new", padx=12)
        for title, number in self.nav_items:
            item = ctk.CTkFrame(nav_frame, fg_color="transparent", corner_radius=10)
            item.pack(fill="x", pady=3)
            indicator = ctk.CTkFrame(
                item,
                width=3,
                height=22,
                corner_radius=2,
                fg_color="transparent",
            )
            indicator.pack(side="left", padx=(0, 5))
            button = ctk.CTkButton(
                item,
                text=f"{number}    {title}",
                anchor="w",
                height=44,
                corner_radius=10,
                border_spacing=12,
                font=app_font(family="Segoe UI", size=13, weight="bold"),
                fg_color=self.COLORS["sidebar"],
                hover_color=self.COLORS["surface_alt"],
                text_color=self.COLORS["muted"],
                border_width=1,
                border_color=self.COLORS["sidebar"],
                command=lambda page=title: self.show_page(page),
            )
            button.pack(side="left", fill="x", expand=True)
            self.nav_buttons[title] = button
            self.nav_indicators[title] = indicator
            self._enable_button_transition(
                button, self.COLORS["sidebar"], self.COLORS["surface_alt"]
            )

        self.sidebar.grid_rowconfigure(3, weight=1)
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=self.COLORS["border"]
        ).grid(row=4, column=0, sticky="ew", padx=20, pady=(10, 14))

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)
        self.profile_badge = ctk.CTkFrame(
            footer,
            fg_color=self.COLORS["surface"],
            corner_radius=13,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        self.profile_badge.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._update_profile_badge()
        self.sign_out_button = ctk.CTkButton(
            footer,
            text="Sign out  /  Switch user",
            height=38,
            corner_radius=12,
            border_width=1,
            border_color=self.COLORS["border"],
            fg_color=self.COLORS["surface"],
            hover_color="#392535",
            text_color=self.COLORS["red"],
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            command=self.sign_out,
        )
        self.sign_out_button.grid(row=1, column=0, sticky="ew")
        self.sign_out_button.bind(
            "<Enter>",
            lambda _event: self.sign_out_button.configure(
                border_color=self.COLORS["red"]
            ),
        )
        self.sign_out_button.bind(
            "<Leave>",
            lambda _event: self.sign_out_button.configure(
                border_color=self.COLORS["border"]
            ),
        )
        self._enable_button_transition(
            self.sign_out_button, self.COLORS["surface"], "#392535"
        )

        self.main = ctk.CTkFrame(self, fg_color=self.COLORS["window"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=26, pady=22)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkFrame(self.main, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        self.header.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(
            self.header,
            text="",
            font=app_font(family="Segoe UI", size=25, weight="bold"),
            text_color=self.COLORS["text"],
            anchor="w",
        )
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_subtitle = ctk.CTkLabel(
            self.header,
            text="",
            font=app_font(family="Segoe UI", size=12),
            text_color=self.COLORS["muted"],
            anchor="w",
        )
        self.page_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.header_status = ctk.CTkLabel(
            self.header,
            text="●  LIVE WORKSPACE",
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLORS["green"],
            fg_color="transparent",
            padx=8,
            pady=5,
        )
        self.header_status.grid(row=0, column=1, rowspan=2, sticky="e")
        self.help_button = ctk.CTkButton(
            self.header,
            text="Help / Guide",
            width=112,
            height=36,
            corner_radius=10,
            border_width=1,
            border_color=self.COLORS["border"],
            fg_color=self.COLORS["surface"],
            hover_color=self.COLORS["surface_alt"],
            text_color=self.COLORS["text"],
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            command=self.open_help_guide,
        )
        self.help_button.grid(row=0, column=2, rowspan=2, sticky="e", padx=(12, 0))
        self._enable_button_transition(
            self.help_button, self.COLORS["surface"], self.COLORS["surface_alt"]
        )
        self.help_window: ctk.CTkToplevel | None = None

        self.page_host = ctk.CTkFrame(self.main, fg_color="transparent")
        self.page_host.grid(row=1, column=0, sticky="nsew")
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)

    def open_help_guide(self) -> None:
        """Open a focused, scrollable guide to the main EduTrack workflows."""
        if self.help_window is not None and self.help_window.winfo_exists():
            self.help_window.deiconify()
            self.help_window.lift()
            self.help_window.focus_force()
            return

        guide = ctk.CTkToplevel(self)
        self.help_window = guide
        guide.title("EduTrack | Quick guide")
        guide_width, guide_height = 650, 740
        guide.geometry(f"{guide_width}x{guide_height}")
        guide.minsize(540, 560)
        guide.configure(fg_color=self.COLORS["window"])
        guide.transient(self)
        guide.grid_columnconfigure(0, weight=1)
        guide.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(
            guide,
            fg_color="#142D50",
            corner_radius=0,
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Your EduTrack quick guide",
            font=app_font(family="Segoe UI", size=22, weight="bold"),
            text_color=self.COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            header,
            text="A short tour of your academic workspace and its main tools.",
            font=app_font(family="Segoe UI", size=11),
            text_color="#C3D5EB",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 20))

        content = ctk.CTkScrollableFrame(
            guide,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=self.COLORS["border"],
        )
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=16)
        content.grid_columnconfigure(0, weight=1)
        self._register_smooth_scroll(content)

        if self.is_faculty:
            self._guide_section(
                content,
                "01",
                "Review your student roster",
                (
                    "The Faculty Control Panel lists students in your assigned "
                    "sections. Search by student ID, name, CGPA, or status, then "
                    "select a student to view course records or update an existing "
                    "course grade."
                ),
            )
            self._guide_section(
                content,
                "02",
                "Manage section access",
                (
                    "Open Section Assignments to choose which student sections are "
                    "included in your roster. Student records outside those sections "
                    "cannot be opened or updated from the faculty workspace."
                ),
            )
            self._guide_section(
                content,
                "03",
                "Switch users",
                (
                    "Select Sign out at the bottom of the sidebar to return to the "
                    "sign-in screen. Your section assignments remain saved locally."
                ),
            )
        else:
            self._guide_section(
                content,
                "01",
                "Start at Dashboard",
                (
                    "Your Dashboard is the academic snapshot. Current CGPA is calculated "
                    "from your graded courses using their credit hours. Completed Credits "
                    "counts credits with valid grades; the goal card shows your saved "
                    "graduation target. Semester Trend compares your weighted GPA by term, "
                    "and Quick Insights highlights courses that may need extra attention."
                ),
            )
            self._guide_section(
                content,
                "02",
                "Plan your trajectory",
                (
                    "Choose Trajectory Planner in the sidebar. The fields start with values "
                    "from your academic record and saved goal. Enter a current CGPA and "
                    "target from 0.00 to 4.00, plus completed and remaining credits, then "
                    "select Calculate required GPA. The result is the average GPA needed "
                    "across the remaining credits; a result over 4.00 is above the grading "
                    "scale. Use What-if Scenario below to drag between 2.00 and 4.00 and "
                    "instantly estimate the resulting graduation CGPA."
                ),
            )
            self._guide_section(
                content,
                "03",
                "Calculate semester and cumulative GPA",
                (
                    "Open CGPA Calculator, add subjects to each semester, and choose "
                    "a BUBT letter grade with the subject's credit value. Semester GPA "
                    "and overall CGPA update as you edit. Subject names are optional; "
                    "blank credits are ignored, and credits must be positive numbers."
                ),
            )
            self._guide_section(
                content,
                "04",
                "Ask the AI Advisor",
                (
                    "Open AI Advisor, type a question in the prompt box, and select Get "
                    "academic guidance. The response uses your available CGPA and courses "
                    "to watch. Add a Gemini API key in Settings for cloud responses; without "
                    "one, EduTrack uses its local guidance fallback."
                ),
            )
            self._guide_section(
                content,
                "05",
                "Review Analytics",
                (
                    "Analytics shows your overall graded-credit summary, semester GPA "
                    "trend, and letter-grade distribution. If a chart has no data, check "
                    "that graded course records are available for your student ID."
                ),
            )
            self._guide_section(
                content,
                "06",
                "Check attendance and your routine",
                (
                    "Open Attendance & Schedule to review the weekly class routine and "
                    "attendance percentages for your enrolled courses. Enter total and "
                    "attended class counts to save or update attendance. Percentages below "
                    "75% are highlighted as warnings."
                ),
            )
            self._guide_section(
                content,
                "07",
                "Update Settings",
                (
                    "Open Settings to change your display name, current semester, total "
                    "program credits, target CGPA, or optional Gemini API key. Select Save "
                    "settings to store changes locally. The dashboard refreshes with your "
                    "new target and credit total. Your account's Student ID is read-only."
                ),
            )
            self._guide_section(
                content,
                "08",
                "Switch users",
                (
                    "Select Sign out at the bottom of the sidebar to return to the sign-in "
                    "screen. Your saved profile settings remain in the local database."
                ),
            )

        footer = ctk.CTkFrame(
            guide,
            fg_color=self.COLORS["surface"],
            corner_radius=0,
        )
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        close_button = ctk.CTkButton(
            footer,
            text="Close guide",
            width=130,
            height=40,
            corner_radius=10,
            font=app_font(family="Segoe UI", size=11, weight="bold"),
            command=guide.destroy,
        )
        self._enable_button_transition(
            close_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )
        close_button.grid(row=0, column=0, sticky="e", padx=20, pady=14)
        guide.protocol("WM_DELETE_WINDOW", guide.destroy)
        guide.bind("<Escape>", lambda _event: guide.destroy())
        guide.update_idletasks()
        guide_width = guide.winfo_width()
        guide_height = guide.winfo_height()
        app_x = self.winfo_rootx()
        app_y = self.winfo_rooty()
        app_width = self.winfo_width()
        app_height = self.winfo_height()
        guide_frame_x = guide.winfo_rootx() - guide.winfo_x()
        guide_frame_y = guide.winfo_rooty() - guide.winfo_y()
        x = app_x + (app_width - guide_width) // 2 - guide_frame_x
        y = app_y + (app_height - guide_height) // 2 - guide_frame_y
        screen_width = guide.winfo_screenwidth()
        screen_height = guide.winfo_screenheight()
        x = max(0, min(x, screen_width - guide_width))
        y = max(0, min(y, screen_height - guide_height))
        guide.geometry(f"{guide_width}x{guide_height}+{x}+{y}")
        guide.after(80, guide.focus_force)

    def _guide_section(
        self,
        parent: ctk.CTkFrame,
        number: str,
        title: str,
        description: str,
    ) -> None:
        """Render one numbered section of the quick-start guide."""
        section = self._card(parent)
        section.pack(fill="x", pady=(0, 10))
        section.grid_columnconfigure(1, weight=1)
        number_badge = ctk.CTkLabel(
            section,
            text=number,
            width=36,
            height=36,
            corner_radius=11,
            fg_color="#1D3B67",
            text_color=self.COLORS["cyan"],
            font=app_font(family="Segoe UI", size=11, weight="bold"),
        )
        number_badge.grid(row=0, column=0, sticky="nw", padx=(15, 12), pady=15)
        ctk.CTkLabel(
            section,
            text=title,
            font=app_font(family="Segoe UI", size=13, weight="bold"),
            text_color=self.COLORS["text"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 15), pady=(15, 5))
        ctk.CTkLabel(
            section,
            text=description,
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
            wraplength=510,
            justify="left",
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", padx=(0, 15), pady=(0, 16))

    def _enable_button_transition(
        self,
        button: ctk.CTkButton,
        base_color: str,
        hover_color: str,
    ) -> None:
        """Replace abrupt widget hover with a short foreground color transition."""
        button.configure(hover=False, fg_color=base_color)
        self._button_hover_states[button] = (base_color, hover_color)
        button.bind(
            "<Enter>",
            lambda _event, target=button: self._animate_button_color(
                target, self._button_hover_states[target][1]
            ),
            add="+",
        )
        button.bind(
            "<Leave>",
            lambda _event, target=button: self._animate_button_color(
                target, self._button_hover_states[target][0]
            ),
            add="+",
        )

    def _animate_button_color(self, button: ctk.CTkButton, target_color: str) -> None:
        """Interpolate button foreground colors without queuing stale animations."""
        previous_job = self._button_color_jobs.pop(button, None)
        if previous_job is not None:
            try:
                button.after_cancel(previous_job)
            except tk.TclError:
                pass

        current_color = button.cget("fg_color")
        if isinstance(current_color, tuple):
            current_color = current_color[1]
        if not isinstance(current_color, str) or not current_color.startswith("#"):
            current_color = self._button_hover_states[button][0]

        try:
            start = tuple(int(current_color[index : index + 2], 16) for index in (1, 3, 5))
            end = tuple(int(target_color[index : index + 2], 16) for index in (1, 3, 5))
        except (ValueError, IndexError):
            button.configure(fg_color=target_color)
            return

        def step(frame: int = 1) -> None:
            if not button.winfo_exists():
                self._button_color_jobs.pop(button, None)
                return
            progress = min(frame / 8, 1)
            progress = progress * progress * (3 - 2 * progress)
            color = "#" + "".join(
                f"{round(begin + (finish - begin) * progress):02X}"
                for begin, finish in zip(start, end)
            )
            button.configure(fg_color=color)
            if frame < 8:
                self._button_color_jobs[button] = button.after(12, step, frame + 1)
            else:
                self._button_color_jobs.pop(button, None)

        step()

    def _set_button_hover_base(self, button: ctk.CTkButton, color: str) -> None:
        """Keep the selected navigation item consistent when it is hovered."""
        _, hover_color = self._button_hover_states[button]
        self._button_hover_states[button] = (color, hover_color)

    def _show_header_status(self, text: str, color: str, reset_after: int = 0) -> None:
        if self._status_reset_job is not None:
            try:
                self.after_cancel(self._status_reset_job)
            except tk.TclError:
                pass
            self._status_reset_job = None
        self.header_status.configure(text=text, text_color=color)
        if reset_after:
            self._status_reset_job = self.after(
                reset_after, self._restore_header_status
            )

    def _restore_header_status(self) -> None:
        self._status_reset_job = None
        if not self.winfo_exists():
            return
        self.header_status.configure(
            text="●  DATA CONNECTION ISSUE" if self.data_error else "●  LIVE WORKSPACE",
            text_color=self.COLORS["amber"] if self.data_error else self.COLORS["green"],
        )

    def _update_profile_badge(self) -> None:
        for child in self.profile_badge.winfo_children():
            child.destroy()
        initials = "".join(
            part[0] for part in self.student["name"].split()[:2] if part
        ).upper() or "S"
        avatar = ctk.CTkFrame(
            self.profile_badge,
            width=38,
            height=38,
            corner_radius=12,
            fg_color="#1D3B67",
        )
        avatar.grid(row=0, column=0, rowspan=2, padx=(12, 10), pady=12)
        avatar.grid_propagate(False)
        ctk.CTkLabel(
            avatar,
            text=initials,
            font=app_font(family="Segoe UI", size=13, weight="bold"),
            text_color=self.COLORS["cyan"],
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(
            self.profile_badge,
            text=self.student["name"],
            font=app_font(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLORS["text"],
            anchor="w",
            width=164,
            wraplength=164,
            justify="left",
        ).grid(row=0, column=1, sticky="sw", padx=(0, 10), pady=(12, 0))
        ctk.CTkLabel(
            self.profile_badge,
            text=f"{self.student['role'].upper()}  /  {self.student['student_id']}",
            font=app_font(family="Segoe UI", size=8, weight="bold"),
            text_color=self.COLORS["muted"],
            anchor="w",
            width=164,
            wraplength=164,
        ).grid(row=1, column=1, sticky="nw", padx=(0, 10), pady=(2, 12))
        self.profile_badge.grid_columnconfigure(1, weight=1)

    def sign_out(self) -> None:
        """Return to the login window in a fresh process."""
        login_path = os.path.join(os.path.dirname(__file__), "auth_ui.py")
        try:
            subprocess.Popen(
                [sys.executable, login_path],
                cwd=os.path.dirname(login_path),
                env=os.environ.copy(),
            )
        except OSError as exc:
            self.header_status.configure(
                text=f"COULD NOT OPEN SIGN IN: {exc}",
                text_color=self.COLORS["red"],
            )
            return
        self.destroy()

    def _load_student_data(self) -> None:
        """Load the signed-in profile and grades from the initialized database."""
        try:
            from modules.crud import AcademicCRUD

            profile = AcademicCRUD.get_student_profile(self.student["student_id"])
            if profile is not None:
                self.student["name"] = profile["name"]
                self.student["semester"] = profile["current_semester"]
                self.program_credits = float(profile["program_credits"])
                self.target_cgpa = float(profile["target_cgpa"])
            settings = AcademicCRUD.get_user_settings(self.student["student_id"])
            self.accent_theme = settings["accent_theme"]
            self.COLORS.update(accent_theme_colors(self.accent_theme))
            self.student["name"] = settings["display_name"]
            self.student["semester"] = settings["current_semester"]
            self.program_credits = float(settings["program_credits"])
            self.target_cgpa = float(settings["target_cgpa"])
            self.current_cgpa = settings["current_cgpa"]
            self.gemini_api_key = settings["gemini_api_key"]
            self.enrollments = AcademicCRUD.get_student_enrollments(
                self.student["student_id"]
            )
            self.data_error = None
        except Exception as exc:
            self.enrollments = []
            self.data_error = str(exc)

    def _summary(self) -> dict[str, Any]:
        """Compute weighted GPA, credit totals, and course/semester insights."""
        from modules.grading import grade_point_for_enrollment

        graded: list[tuple[dict[str, Any], float, float]] = []
        semesters: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
        grade_counts: Counter[str] = Counter()
        for record in self.enrollments:
            try:
                credits = float(record["credit_hours"])
                grade_point = grade_point_for_enrollment(record)
                if (
                    not math.isfinite(credits)
                    or credits <= 0
                    or grade_point is None
                ):
                    continue
            except (KeyError, TypeError, ValueError):
                continue
            graded.append((record, credits, grade_point))
            semester = str(record.get("semester_no", "Unknown"))
            semesters[semester][0] += credits * grade_point
            semesters[semester][1] += credits
            letter_grade = str(record.get("letter_grade") or "").strip().upper()
            if letter_grade:
                grade_counts[letter_grade] += 1

        completed = sum(credits for _, credits, _ in graded)
        grade_points = sum(credits * grade for _, credits, grade in graded)
        cgpa = grade_points / completed if completed else None
        weak_courses = [
            record
            for record, _, grade in graded
            if grade < 2.5
        ]
        semester_averages = {
            semester: totals[0] / totals[1]
            for semester, totals in semesters.items()
            if totals[1]
        }
        return {
            "cgpa": cgpa,
            "completed_credits": completed,
            "remaining_credits": max(self.program_credits - completed, 0.0),
            "grade_points": grade_points,
            "graded_courses": graded,
            "weak_courses": weak_courses,
            "semester_averages": semester_averages,
            "grade_counts": grade_counts,
        }

    def show_page(self, page: str) -> None:
        """Switch pages immediately and defer first-time page construction until idle."""
        if page not in {title for title, _ in self.nav_items}:
            raise ValueError(f"Page {page!r} is not available in this workspace.")
        if page == self.current_page and (
            page in self._built_pages or self._pending_page == page
        ):
            return
        if self._page_render_job is not None:
            try:
                self.after_cancel(self._page_render_job)
            except tk.TclError:
                pass
            self._page_render_job = None
            self._pending_page = None

        previous_frame = self._page_frames.get(self.current_page or "")
        if previous_frame is not None:
            previous_frame.grid_remove()
        for title, button in self.nav_buttons.items():
            selected = title == page
            base_color = (
                self.COLORS["surface_alt"] if selected else self.COLORS["sidebar"]
            )
            button.configure(
                fg_color=base_color,
                text_color=self.COLORS["text"] if selected else self.COLORS["muted"],
                border_color=(
                    self.COLORS["border"] if selected else self.COLORS["sidebar"]
                ),
            )
            self._set_button_hover_base(button, base_color)
            self.nav_indicators[title].configure(
                fg_color=self.COLORS["cyan"] if selected else "transparent"
            )

        self._show_header_status(
            "●  DATA CONNECTION ISSUE" if self.data_error else "●  LIVE WORKSPACE",
            self.COLORS["amber"] if self.data_error else self.COLORS["green"],
        )
        page_titles = {
            "Dashboard": (
                "Your academic journey",
                "A clear view of your progress, goals, and next steps.",
            ),
            "Trajectory Planner": (
                "Trajectory planner",
                "Explore the GPA pace needed to reach your graduation goal.",
            ),
            "CGPA Calculator": (
                "CGPA Calculator",
                "Build semesters and calculate credit-weighted GPA as you enter grades.",
            ),
            "AI Advisor": (
                "AI academic advisor",
                "Get guidance informed by your academic record.",
            ),
            "Analytics": (
                "Performance analytics",
                "Review semester performance and the grades behind your CGPA.",
            ),
            "Attendance & Schedule": (
                "Attendance & schedule",
                "Review your weekly class routine and track course attendance.",
            ),
            "Settings": (
                "Workspace settings",
                "Manage the student profile and planning assumptions shown here.",
            ),
        }
        if self.is_faculty:
            page_titles.update(
                {
                    "Dashboard": (
                        "Faculty control panel",
                        "Review students and manage academic records in your assigned sections.",
                    ),
                    "Section Assignments": (
                        "Section assignments",
                        "Choose which student sections are included in your faculty roster.",
                    ),
                }
            )
        title, subtitle = page_titles[page]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)

        builders = {
            "Dashboard": self._build_dashboard,
            "Section Assignments": self._build_faculty_section_assignments,
            "Trajectory Planner": self._build_planner,
            "CGPA Calculator": self._build_semester_calculator,
            "AI Advisor": self._build_advisor,
            "Analytics": self._build_analytics,
            "Attendance & Schedule": self._build_attendance_schedule,
            "Settings": self._build_settings,
        }
        page_frame = self._page_frames.get(page)
        if page_frame is None:
            page_frame = ctk.CTkScrollableFrame(
                self.page_host,
                fg_color="transparent",
                corner_radius=0,
                scrollbar_button_color=self.COLORS["border"],
            )
            page_frame.grid_columnconfigure(0, weight=1)
            self._page_frames[page] = page_frame
            self._register_smooth_scroll(page_frame)
        if page in self._built_pages:
            page_frame.grid()
        else:
            def render_page() -> None:
                self._page_render_job = None
                self._pending_page = None
                if not self.winfo_exists() or self.current_page != page:
                    return
                builders[page](page_frame)
                self._built_pages.add(page)
                page_frame.grid(row=0, column=0, sticky="nsew")

            self._pending_page = page
            self._page_render_job = self.after_idle(render_page)
        self.current_page = page

    def _register_smooth_scroll(self, frame: ctk.CTkScrollableFrame) -> None:
        if frame not in self._scrollable_frames:
            self._scrollable_frames.append(frame)

    def _on_smooth_mousewheel(self, event: tk.Event) -> str | None:
        try:
            pointer_widget = self.winfo_containing(event.x_root, event.y_root)
        except tk.TclError:
            return None
        if pointer_widget is None:
            return None
        pointer_path = str(pointer_widget)

        active_frame: ctk.CTkScrollableFrame | None = None
        active_path_length = -1
        for frame in self._scrollable_frames[:]:
            try:
                if not frame.winfo_exists():
                    self._scrollable_frames.remove(frame)
                    continue
                frame_path = str(frame)
                if (
                    (pointer_path == frame_path or pointer_path.startswith(f"{frame_path}."))
                    and len(frame_path) > active_path_length
                ):
                    active_frame = frame
                    active_path_length = len(frame_path)
            except tk.TclError:
                self._scrollable_frames.remove(frame)

        if active_frame is None:
            return None

        canvas = active_frame._parent_canvas
        scroll_region = canvas.bbox("all")
        if scroll_region is None:
            return "break"
        content_height = scroll_region[3] - scroll_region[1]
        viewport_height = canvas.winfo_height()
        max_offset = max(content_height - viewport_height, 0)
        if max_offset <= 0:
            return "break"

        if event.num == 4:
            pixel_delta = -48.0
        elif event.num == 5:
            pixel_delta = 48.0
        elif sys.platform == "darwin":
            pixel_delta = -float(event.delta) * 2.4
        else:
            pixel_delta = -float(event.delta) * (48.0 / 120.0)

        self._pending_scroll_pixels[active_frame] = (
            self._pending_scroll_pixels.get(active_frame, 0.0) + pixel_delta
        )
        if active_frame not in self._scroll_jobs:
            self._scroll_jobs[active_frame] = active_frame.after(
                8, lambda frame=active_frame: self._apply_smooth_scroll(frame)
            )
        return "break"

    def _apply_smooth_scroll(self, frame: ctk.CTkScrollableFrame) -> None:
        self._scroll_jobs.pop(frame, None)
        pixel_delta = self._pending_scroll_pixels.pop(frame, 0.0)
        try:
            if not frame.winfo_exists() or not frame.winfo_ismapped():
                return
            canvas = frame._parent_canvas
            scroll_region = canvas.bbox("all")
            if scroll_region is None:
                return
            content_height = scroll_region[3] - scroll_region[1]
            viewport_height = canvas.winfo_height()
            max_offset = max(content_height - viewport_height, 0)
            if max_offset <= 0:
                return
            current_offset = canvas.yview()[0] * content_height
            next_offset = min(max(current_offset + pixel_delta, 0.0), max_offset)
            canvas.yview_moveto(next_offset / content_height)
        except tk.TclError:
            self._pending_scroll_pixels.pop(frame, None)

    def _discard_cached_pages(self) -> None:
        if self._page_render_job is not None:
            try:
                self.after_cancel(self._page_render_job)
            except tk.TclError:
                pass
            self._page_render_job = None
            self._pending_page = None
        for frame in self._page_frames.values():
            try:
                frame.destroy()
            except tk.TclError:
                continue
        for frame, job in self._scroll_jobs.items():
            try:
                frame.after_cancel(job)
            except tk.TclError:
                pass
        self._scroll_jobs.clear()
        self._pending_scroll_pixels.clear()
        for chart, job in self._chart_redraw_jobs.items():
            try:
                chart.after_cancel(job)
            except tk.TclError:
                pass
        self._chart_redraw_jobs.clear()
        self._page_frames.clear()
        self._built_pages.clear()
        live_frames: list[ctk.CTkScrollableFrame] = []
        for frame in self._scrollable_frames:
            try:
                if frame.winfo_exists():
                    live_frames.append(frame)
            except tk.TclError:
                continue
        self._scrollable_frames = live_frames
        self.current_page = None

    def _schedule_chart_redraw(
        self, chart: ctk.CTkCanvas, draw: Any
    ) -> None:
        previous_job = self._chart_redraw_jobs.pop(chart, None)
        if previous_job is not None:
            try:
                chart.after_cancel(previous_job)
            except tk.TclError:
                pass

        def redraw() -> None:
            self._chart_redraw_jobs.pop(chart, None)
            try:
                if chart.winfo_exists():
                    draw()
            except tk.TclError:
                return

        self._chart_redraw_jobs[chart] = chart.after(28, redraw)

    def _card(self, parent: ctk.CTkFrame, **kwargs: Any) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            parent,
            fg_color=self.COLORS["surface"],
            corner_radius=18,
            border_width=1,
            border_color=self.COLORS["border"],
            **kwargs,
        )

    def _section_heading(
        self, parent: ctk.CTkFrame, title: str, detail: str | None = None
    ) -> None:
        heading = ctk.CTkFrame(parent, fg_color="transparent")
        heading.pack(fill="x", padx=20, pady=(18, 14))
        ctk.CTkLabel(
            heading,
            text=title,
            font=app_font(family="Segoe UI", size=15, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(side="left")
        if detail:
            ctk.CTkLabel(
                heading,
                text=detail,
                font=app_font(family="Segoe UI", size=10),
                text_color=self.COLORS["muted"],
            ).pack(side="right")

    def _helper_text(self, parent: ctk.CTkFrame, text: str) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
            wraplength=850,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 16))

    def _style_faculty_treeview(self) -> None:
        style = ttk.Style(self)
        style.configure(
            "EduTrack.Treeview",
            background=self.COLORS["surface"],
            fieldbackground=self.COLORS["surface"],
            foreground=self.COLORS["text"],
            rowheight=32,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.map(
            "EduTrack.Treeview",
            background=[("selected", self.COLORS["blue"])],
            foreground=[("selected", self.COLORS["text"])],
        )
        style.configure(
            "EduTrack.Treeview.Heading",
            background=self.COLORS["surface_alt"],
            foreground=self.COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        )
        style.map(
            "EduTrack.Treeview.Heading",
            background=[("active", self.COLORS["surface_alt"])],
        )

    def _build_faculty_dashboard(self, parent: ctk.CTkFrame) -> None:
        banner = ctk.CTkFrame(
            parent,
            fg_color="#142D50",
            corner_radius=18,
            border_width=1,
            border_color="#24456D",
        )
        banner.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            banner,
            text=f"WELCOME, {self.student['name'].upper()}",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color="#AFCDF2",
        ).pack(anchor="w", padx=24, pady=(20, 6))
        ctk.CTkLabel(
            banner,
            text="Faculty Control Panel",
            font=app_font(family="Segoe UI", size=23, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(anchor="w", padx=24)
        ctk.CTkLabel(
            banner,
            text="Search your assigned sections and review student academic records.",
            font=app_font(family="Segoe UI", size=11),
            text_color="#C3D5EB",
        ).pack(anchor="w", padx=24, pady=(7, 20))

        try:
            from modules.crud import AcademicCRUD

            self.faculty_roster = AcademicCRUD.get_faculty_students(
                self.student["student_id"]
            )
            roster_error = None
        except Exception as exc:
            self.faculty_roster = []
            roster_error = str(exc)

        summary = ctk.CTkFrame(parent, fg_color="transparent")
        summary.pack(fill="x", pady=(0, 18))
        summary.grid_columnconfigure(0, weight=1)
        self._metric_card(
            summary,
            0,
            "TOTAL ENROLLED STUDENTS",
            str(len(self.faculty_roster)),
            "Students in your assigned sections",
            None,
            self.COLORS["cyan"],
            "Section-scoped roster",
        )

        roster_card = self._card(parent)
        roster_card.pack(fill="both", expand=True)
        self._section_heading(
            roster_card,
            "Student roster",
            "SEARCHABLE · ASSIGNED SECTIONS ONLY",
        )
        toolbar = ctk.CTkFrame(roster_card, fg_color="transparent")
        toolbar.pack(fill="x", padx=18, pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        search = ctk.CTkEntry(
            toolbar,
            height=38,
            corner_radius=9,
            placeholder_text="Search student ID, name, CGPA, or status",
        )
        search.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.faculty_roster_count = ctk.CTkLabel(
            toolbar,
            text="",
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
        )
        self.faculty_roster_count.grid(row=0, column=1, sticky="e")

        table_frame = ctk.CTkFrame(roster_card, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self._style_faculty_treeview()
        self.faculty_roster_tree = ttk.Treeview(
            table_frame,
            columns=("student_id", "name", "cgpa", "status"),
            show="headings",
            height=12,
            style="EduTrack.Treeview",
            selectmode="browse",
        )
        for column, heading, width in (
            ("student_id", "Student ID", 150),
            ("name", "Name", 280),
            ("cgpa", "Current CGPA", 140),
            ("status", "Status", 180),
        ):
            self.faculty_roster_tree.heading(column, text=heading)
            self.faculty_roster_tree.column(
                column, width=width, anchor="w", stretch=column == "name"
            )
        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.faculty_roster_tree.yview,
        )
        self.faculty_roster_tree.configure(yscrollcommand=scrollbar.set)
        self.faculty_roster_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        search.bind(
            "<KeyRelease>",
            lambda _event: self._filter_faculty_roster(search.get()),
        )
        self.faculty_roster_tree.bind(
            "<Double-1>", lambda _event: self._open_selected_faculty_student()
        )

        actions = ctk.CTkFrame(roster_card, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 18))
        manage_button = ctk.CTkButton(
            actions,
            text="View / manage academic records",
            height=38,
            corner_radius=9,
            command=self._open_selected_faculty_student,
        )
        manage_button.pack(side="left")
        self._enable_button_transition(
            manage_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )
        if roster_error:
            self._notice(
                roster_card,
                f"Could not load the faculty roster: {roster_error}",
                self.COLORS["red"],
            )
        elif not self.faculty_roster:
            self._notice(
                roster_card,
                "No students are assigned to your sections. Choose sections in "
                "Section Assignments to populate this roster.",
                self.COLORS["muted"],
            )
        self._filter_faculty_roster("")

    def _filter_faculty_roster(self, query: str) -> None:
        tree = self.faculty_roster_tree
        for item in tree.get_children():
            tree.delete(item)
        normalized_query = query.strip().casefold()
        visible_count = 0
        for student in self.faculty_roster:
            cgpa = student["current_cgpa"]
            values = (
                student["student_id"],
                student["name"],
                f"{cgpa:.2f}" if cgpa is not None else "No grades",
                student["status"],
            )
            if normalized_query and not any(
                normalized_query in str(value).casefold() for value in values
            ):
                continue
            tree.insert("", "end", iid=student["student_id"], values=values)
            visible_count += 1
        self.faculty_roster_count.configure(
            text=f"Showing {visible_count} of {len(self.faculty_roster)} students"
        )

    def _open_selected_faculty_student(self) -> None:
        selection = self.faculty_roster_tree.selection()
        if not selection:
            self._show_header_status(
                "SELECT A STUDENT FIRST",
                self.COLORS["amber"],
                reset_after=2500,
            )
            return
        self._open_faculty_student_records(selection[0])

    def _populate_faculty_records(
        self,
        tree: ttk.Treeview,
        enrollments: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        for item in tree.get_children():
            tree.delete(item)
        records: dict[str, dict[str, Any]] = {}
        for enrollment in enrollments:
            record_id = str(enrollment["enrollment_id"])
            records[record_id] = enrollment
            tree.insert(
                "",
                "end",
                iid=record_id,
                values=(
                    enrollment["course_code"],
                    enrollment["course_title"],
                    f"{float(enrollment['credit_hours']):g}",
                    enrollment["semester_no"],
                    enrollment["letter_grade"] or "Not graded",
                ),
            )
        return records

    def _open_faculty_student_records(self, student_id: str) -> None:
        from modules.crud import AcademicCRUD

        try:
            enrollments = AcademicCRUD.get_faculty_student_enrollments(
                self.student["student_id"], student_id
            )
        except Exception as exc:
            messagebox.showerror(
                "Could not open student records",
                str(exc),
                parent=self,
            )
            return

        student_name = next(
            (
                student["name"]
                for student in self.faculty_roster
                if student["student_id"] == student_id
            ),
            student_id,
        )
        window = ctk.CTkToplevel(self)
        window.title(f"Academic records | {student_name}")
        window.geometry("900x590")
        window.minsize(760, 480)
        window.configure(fg_color=self.COLORS["window"])
        window.transient(self)
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            window,
            text=f"{student_name}  ·  {student_id}",
            font=app_font(family="Segoe UI", size=19, weight="bold"),
            text_color=self.COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 5))
        ctk.CTkLabel(
            window,
            text="Select an existing course record to review or update its letter grade.",
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))

        table_frame = ctk.CTkFrame(window, fg_color="transparent")
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 12))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        self._style_faculty_treeview()
        records_tree = ttk.Treeview(
            table_frame,
            columns=("course", "title", "credits", "semester", "grade"),
            show="headings",
            height=12,
            style="EduTrack.Treeview",
            selectmode="browse",
        )
        for column, heading, width in (
            ("course", "Course", 110),
            ("title", "Course title", 290),
            ("credits", "Credits", 80),
            ("semester", "Semester", 100),
            ("grade", "Grade", 110),
        ):
            records_tree.heading(column, text=heading)
            records_tree.column(
                column, width=width, anchor="w", stretch=column == "title"
            )
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=records_tree.yview
        )
        records_tree.configure(yscrollcommand=scrollbar.set)
        records_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        records_by_id = self._populate_faculty_records(records_tree, enrollments)

        edit_frame = ctk.CTkFrame(window, fg_color="transparent")
        edit_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 18))
        edit_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            edit_frame,
            text="Selected record grade",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLORS["muted"],
        ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        grade_selector = ctk.CTkComboBox(
            edit_frame,
            values=["Not graded", *self.GRADE_ORDER],
            width=150,
            height=36,
            corner_radius=9,
            state="readonly",
        )
        grade_selector.set("Not graded")
        grade_selector.grid(row=0, column=1, sticky="w")
        status = ctk.CTkLabel(
            edit_frame,
            text="",
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
        )
        status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def select_record(_event: tk.Event | None = None) -> None:
            selection = records_tree.selection()
            if selection:
                grade_selector.set(
                    records_by_id[selection[0]]["letter_grade"] or "Not graded"
                )

        records_tree.bind("<<TreeviewSelect>>", select_record)

        def save_grade() -> None:
            selection = records_tree.selection()
            if not selection:
                status.configure(
                    text="Select a course record before saving.",
                    text_color=self.COLORS["amber"],
                )
                return
            record = records_by_id[selection[0]]
            selected_grade = grade_selector.get()
            try:
                AcademicCRUD.update_faculty_student_grade(
                    self.student["student_id"],
                    student_id,
                    record["course_code"],
                    record["semester_no"],
                    None if selected_grade == "Not graded" else selected_grade,
                )
                updated_enrollments = AcademicCRUD.get_faculty_student_enrollments(
                    self.student["student_id"], student_id
                )
                records_by_id.clear()
                records_by_id.update(
                    self._populate_faculty_records(records_tree, updated_enrollments)
                )
                self.faculty_roster = AcademicCRUD.get_faculty_students(
                    self.student["student_id"]
                )
                self._filter_faculty_roster("")
            except Exception as exc:
                status.configure(
                    text=f"Could not save grade: {exc}",
                    text_color=self.COLORS["red"],
                )
                return
            records_tree.selection_set(selection[0])
            status.configure(
                text="Grade saved successfully.",
                text_color=self.COLORS["green"],
            )

        save_button = ctk.CTkButton(
            edit_frame,
            text="Save grade",
            height=36,
            corner_radius=9,
            command=save_grade,
        )
        save_button.grid(row=0, column=2, sticky="e", padx=(12, 0))
        self._enable_button_transition(
            save_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )

    def _build_faculty_section_assignments(self, parent: ctk.CTkFrame) -> None:
        card = self._card(parent)
        card.pack(fill="x")
        self._section_heading(card, "Assigned sections", "FACULTY ROSTER ACCESS")
        self._helper_text(
            card,
            "Choose the student sections that should appear in your roster. "
            "Access is restricted to students in the selected sections.",
        )
        try:
            from modules.crud import AcademicCRUD

            available_sections = AcademicCRUD.get_faculty_section_options()
            assigned_sections = set(
                AcademicCRUD.get_faculty_sections(self.student["student_id"])
            )
        except Exception as exc:
            self._notice(
                card,
                f"Could not load section assignments: {exc}",
                self.COLORS["red"],
            )
            return

        if not available_sections:
            self._notice(
                card,
                "No student sections are available yet. Add student profiles before "
                "assigning section access.",
                self.COLORS["amber"],
            )
            return

        self.faculty_section_vars: dict[str, tk.BooleanVar] = {}
        for section in available_sections:
            selected = tk.BooleanVar(value=section in assigned_sections)
            self.faculty_section_vars[section] = selected
            checkbox = ctk.CTkCheckBox(
                card,
                text=f"Section {section}",
                variable=selected,
                height=34,
                font=app_font(family="Segoe UI", size=11),
                text_color=self.COLORS["text"],
                fg_color=self.COLORS["blue"],
                hover_color=self.COLORS["blue_hover"],
            )
            checkbox.pack(anchor="w", padx=20, pady=4)

        status = ctk.CTkLabel(
            card,
            text="",
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
        )
        status.pack(anchor="w", padx=20, pady=(10, 0))

        def save_assignments() -> None:
            sections = [
                section
                for section, variable in self.faculty_section_vars.items()
                if variable.get()
            ]
            try:
                AcademicCRUD.save_faculty_sections(
                    self.student["student_id"], sections
                )
            except Exception as exc:
                status.configure(
                    text=f"Could not save section assignments: {exc}",
                    text_color=self.COLORS["red"],
                )
                return
            self._discard_cached_pages()
            self.show_page("Section Assignments")
            self._show_header_status(
                "✓  SECTION ASSIGNMENTS SAVED",
                self.COLORS["green"],
                reset_after=3500,
            )

        save_button = ctk.CTkButton(
            card,
            text="Save section assignments",
            height=40,
            corner_radius=9,
            command=save_assignments,
        )
        save_button.pack(anchor="w", padx=20, pady=(14, 20))
        self._enable_button_transition(
            save_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )

    def _build_dashboard(self, parent: ctk.CTkFrame) -> None:
        if self.is_faculty:
            self._build_faculty_dashboard(parent)
            return
        summary = self._summary()
        banner = ctk.CTkFrame(
            parent,
            fg_color="#142D50",
            corner_radius=18,
            border_width=1,
            border_color="#24456D",
        )
        banner.pack(fill="x", pady=(0, 22))
        banner.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            banner,
            text=f"GOOD TO SEE YOU, {self.student['name'].upper()}",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color="#AFCDF2",
        ).grid(row=0, column=0, sticky="w", padx=26, pady=(23, 8))
        ctk.CTkLabel(
            banner,
            text="Make your next semester count.",
            font=app_font(family="Segoe UI", size=23, weight="bold"),
            text_color=self.COLORS["text"],
        ).grid(row=1, column=0, sticky="w", padx=26)
        ctk.CTkLabel(
            banner,
            text=f"{self.student['semester']}  |  {self.student['role'].upper()} WORKSPACE",
            font=app_font(family="Segoe UI", size=11),
            text_color="#C3D5EB",
        ).grid(row=2, column=0, sticky="w", padx=26, pady=(8, 23))
        ctk.CTkLabel(
            banner,
            text=f"{self.program_credits:g}\nCREDIT DEGREE",
            font=app_font(family="Segoe UI", size=13, weight="bold"),
            text_color=self.COLORS["cyan"],
            justify="center",
            fg_color="#1B3B63",
            corner_radius=13,
            padx=26,
            pady=18,
        ).grid(row=0, column=1, rowspan=3, padx=(16, 24), pady=22)

        self._section_heading(parent, "At a glance", "YOUR ACADEMIC SNAPSHOT")
        self._helper_text(
            parent,
            "Your cards summarize recorded grades and your saved graduation goal. "
            "Use Trajectory Planner to explore a different GPA target.",
        )
        cards = ctk.CTkFrame(parent, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 24))
        for column in range(4):
            cards.grid_columnconfigure(column, weight=1, uniform="metric")
        cgpa = summary["cgpa"]
        completed = summary["completed_credits"]
        metrics = (
            (
                "CURRENT CGPA",
                f"{cgpa:.2f}" if cgpa is not None else "No grades",
                "Weighted across graded courses",
                cgpa / self.GRADE_SCALE if cgpa is not None else 0,
                self.COLORS["blue"],
                f"{cgpa:.2f} / 4.00" if cgpa is not None else "No graded records yet",
            ),
            (
                "COMPLETED CREDITS",
                f"{completed:g}",
                f"of {self.program_credits:g} program credits",
                min(completed / self.program_credits, 1) if self.program_credits else 0,
                self.COLORS["cyan"],
                f"{summary['remaining_credits']:g} credits remaining",
            ),
            (
                "GRADUATION GOAL",
                f"{self.target_cgpa:.2f}",
                "Your target cumulative GPA",
                self.target_cgpa / self.GRADE_SCALE,
                self.COLORS["green"],
                "Adjustable in Settings",
            ),
            (
                "COURSES TO WATCH",
                str(len(summary["weak_courses"])),
                "Recorded below 2.50 grade points",
                None,
                self.COLORS["amber"] if summary["weak_courses"] else self.COLORS["green"],
                "Review your focus list" if summary["weak_courses"] else "No alerts on record",
            ),
        )
        for column, metric in enumerate(metrics):
            self._metric_card(cards, column, *metric)

        lower = ctk.CTkFrame(parent, fg_color="transparent")
        lower.pack(fill="both", expand=True)
        lower.grid_columnconfigure(0, weight=7, uniform="lower")
        lower.grid_columnconfigure(1, weight=5, uniform="lower")
        lower.grid_rowconfigure(0, weight=1)

        trend_card = self._card(lower)
        trend_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._section_heading(trend_card, "Semester trend", "WEIGHTED GPA")
        self._draw_semester_trend(trend_card, summary["semester_averages"])

        insights = self._card(lower)
        insights.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._section_heading(insights, "Quick insights", "YOUR NEXT STEP")
        if summary["weak_courses"]:
            for record in summary["weak_courses"][:3]:
                course = record.get("course_code", "Course")
                grade = record.get("letter_grade") or record.get("grade_point", "")
                self._insight_row(
                    insights,
                    "FOCUS",
                    f"{course}  |  {grade}",
                    "Consider giving this course extra review time.",
                    self.COLORS["amber"],
                )
        elif summary["cgpa"] is not None:
            self._insight_row(
                insights,
                "ON TRACK",
                "Keep your semester pace steady",
                "No low-grade courses are currently flagged in your record.",
                self.COLORS["green"],
            )
        else:
            self._insight_row(
                insights,
                "READY WHEN YOU ARE",
                "Your insights will appear here",
                "Connect academic records to see semester trends and course focus areas.",
                self.COLORS["cyan"],
            )
        if self.data_error:
            self._notice(
                insights,
                f"Records could not be loaded: {self.data_error}",
                self.COLORS["amber"],
            )
        elif not self.enrollments:
            self._notice(
                insights,
                "No enrollment records found for this student ID.",
                self.COLORS["muted"],
            )

    def _metric_card(
        self,
        parent: ctk.CTkFrame,
        column: int,
        title: str,
        value: str,
        subtitle: str,
        progress: float | None,
        accent: str,
        footer: str,
    ) -> None:
        card = self._card(parent)
        card.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 7, 7),
            pady=3,
        )
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLORS["muted"],
        ).pack(anchor="w", padx=20, pady=(19, 11))
        ctk.CTkLabel(
            card,
            text=value,
            font=app_font(family="Segoe UI", size=28, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(anchor="w", padx=20)
        ctk.CTkLabel(
            card,
            text=subtitle,
            font=app_font(family="Segoe UI", size=9),
            text_color=self.COLORS["muted"],
            wraplength=210,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(5, 14))
        if progress is not None:
            bar = ctk.CTkProgressBar(
                card,
                height=8,
                corner_radius=4,
                progress_color=accent,
                fg_color=self.COLORS["surface_alt"],
            )
            bar.pack(fill="x", padx=20, pady=(0, 12))
            bar.set(max(0, min(progress, 1)))
        ctk.CTkLabel(
            card,
            text=footer,
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=accent,
            wraplength=210,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 19))

    def _draw_semester_trend(
        self, parent: ctk.CTkFrame, semester_averages: dict[str, float]
    ) -> None:
        if not semester_averages:
            ctk.CTkLabel(
                parent,
                text=(
                    "No semester results yet. Add graded course records to your "
                    "academic data to see each semester's credit-weighted GPA here."
                ),
                font=app_font(family="Segoe UI", size=11),
                text_color=self.COLORS["muted"],
                wraplength=500,
                justify="left",
            ).pack(anchor="w", padx=16, pady=(5, 22))
            return
        ordered = sorted(
            semester_averages.items(),
            key=lambda item: (
                (0, int(item[0])) if item[0].isdigit() else (1, item[0])
            ),
        )
        chart = ctk.CTkCanvas(
            parent,
            height=260,
            background=self.COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        chart.pack(fill="x", padx=20, pady=(0, 20))
        chart.bind(
            "<Configure>",
            lambda _event, target=chart, data=ordered[-6:]:
            self._schedule_chart_redraw(
                target,
                lambda: self._paint_semester_chart(target, data),
            ),
        )
        self._paint_semester_chart(chart, ordered[-6:])

    def _paint_semester_chart(
        self, chart: ctk.CTkCanvas, semester_data: list[tuple[str, float]]
    ) -> None:
        chart.delete("all")
        width = max(chart.winfo_width(), 360)
        height = max(chart.winfo_height(), 230)
        left, right = 52, width - 24
        top, bottom = 26, height - 42

        for tick in range(5):
            value = float(tick)
            y = bottom - (value / self.GRADE_SCALE) * (bottom - top)
            chart.create_line(
                left, y, right, y, fill=self.COLORS["border"], width=1
            )
            chart.create_text(
                left - 12,
                y,
                text=f"{tick}.0",
                fill=self.COLORS["muted"],
                font=("Segoe UI", 10),
                anchor="e",
            )

        chart.create_line(left, top, left, bottom, fill=self.COLORS["border"], width=1)
        chart.create_line(
            left, bottom, right, bottom, fill=self.COLORS["border"], width=1
        )
        chart.create_text(
            14,
            (top + bottom) / 2,
            text="GPA",
            fill=self.COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
            angle=90,
        )

        count = len(semester_data)
        if not count:
            return
        spacing = (right - left) / max(count, 1)
        points: list[tuple[float, float]] = []
        for index, (semester, average) in enumerate(semester_data):
            x = left + spacing * (index + 0.5)
            y = bottom - (min(max(average, 0), self.GRADE_SCALE) / self.GRADE_SCALE) * (
                bottom - top
            )
            points.append((x, y))
            chart.create_text(
                x,
                bottom + 19,
                text=str(semester)[:12],
                fill=self.COLORS["muted"],
                font=("Segoe UI", 10),
                anchor="n",
            )

        line_coordinates = [coordinate for point in points for coordinate in point]
        if len(points) > 1:
            for color, line_width in (
                ("#12384A", 11),
                ("#15516A", 7),
                ("#16718C", 5),
                (self.COLORS["cyan"], 3),
            ):
                chart.create_line(
                    *line_coordinates,
                    fill=color,
                    width=line_width,
                    smooth=True,
                    splinesteps=24,
                    capstyle=tk.ROUND,
                    joinstyle=tk.ROUND,
                )
        for x, y in points:
            chart.create_oval(
                x - 5, y - 5, x + 5, y + 5,
                fill=self.COLORS["cyan"],
                outline=self.COLORS["surface"],
                width=2,
            )
        for (semester, average), (x, y) in zip(semester_data, points):
            label_y = max(top + 8, y - 15)
            chart.create_text(
                x,
                label_y,
                text=f"{average:.2f}",
                fill=self.COLORS["text"],
                font=("Segoe UI", 10, "bold"),
                anchor="s",
            )

    def _insight_row(
        self,
        parent: ctk.CTkFrame,
        eyebrow: str,
        title: str,
        detail: str,
        accent: str,
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(
            row,
            text=eyebrow,
            font=app_font(family="Segoe UI", size=8, weight="bold"),
            text_color=accent,
        ).pack(anchor="w")
        ctk.CTkLabel(
            row,
            text=title,
            font=app_font(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLORS["text"],
            wraplength=290,
            justify="left",
        ).pack(anchor="w", pady=(4, 2))
        ctk.CTkLabel(
            row,
            text=detail,
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
            wraplength=290,
            justify="left",
        ).pack(anchor="w")

    def _notice(self, parent: ctk.CTkFrame, text: str, color: str) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=app_font(family="Segoe UI", size=9),
            text_color=color,
            wraplength=290,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 14))

    def _build_planner(self, parent: ctk.CTkFrame) -> None:
        summary = self._summary()
        card = self._card(parent)
        card.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            card,
            text="PLAN YOUR GRADUATION GPA",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLORS["cyan"],
        ).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(
            card,
            text=(
                "Edit the prefilled values if needed, then calculate the average "
                "GPA you need across your remaining credits."
            ),
            font=app_font(family="Segoe UI", size=11),
            text_color=self.COLORS["muted"],
        ).pack(anchor="w", padx=20, pady=(0, 18))

        fields = ctk.CTkFrame(card, fg_color="transparent")
        fields.pack(fill="x", padx=20)
        for column in range(4):
            fields.grid_columnconfigure(column, weight=1, uniform="planner")
        values = (
            ("Current CGPA", f"{summary['cgpa']:.2f}" if summary["cgpa"] is not None else "0.00"),
            ("Credits completed", f"{summary['completed_credits']:g}"),
            ("Target CGPA", f"{self.target_cgpa:.2f}"),
            ("Credits remaining", f"{summary['remaining_credits']:g}"),
        )
        self.planner_entries: list[ctk.CTkEntry] = []
        for column, (label, value) in enumerate(values):
            item = ctk.CTkFrame(fields, fg_color="transparent")
            item.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
            ctk.CTkLabel(
                item,
                text=label,
                font=app_font(family="Segoe UI", size=10, weight="bold"),
                text_color=self.COLORS["muted"],
            ).pack(anchor="w", pady=(0, 7))
            helper_by_field = {
                "Current CGPA": "0.00–4.00",
                "Credits completed": "Graded credits",
                "Target CGPA": "Goal: 0.00–4.00",
                "Credits remaining": "Credits left in program",
            }
            ctk.CTkLabel(
                item,
                text=helper_by_field[label],
                font=app_font(family="Segoe UI", size=8),
                text_color=self.COLORS["muted"],
            ).pack(anchor="w", pady=(0, 5))
            entry = ctk.CTkEntry(
                item,
                height=40,
                corner_radius=9,
                border_color=self.COLORS["border"],
                placeholder_text=helper_by_field[label],
            )
            entry.insert(0, value)
            entry.pack(fill="x")
            self.planner_entries.append(entry)
            entry.bind(
                "<KeyRelease>",
                lambda _event: self._update_what_if_projection(),
            )

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(18, 20))
        calculate_button = ctk.CTkButton(
            actions,
            text="Calculate required GPA",
            height=40,
            corner_radius=10,
            font=app_font(family="Segoe UI", size=11, weight="bold"),
            command=self._calculate_trajectory,
        )
        self._enable_button_transition(
            calculate_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )
        calculate_button.pack(side="left")
        self.planner_result = ctk.CTkLabel(
            actions,
            text="Enter your planning assumptions.",
            font=app_font(family="Segoe UI", size=11),
            text_color=self.COLORS["muted"],
            wraplength=540,
            justify="left",
        )
        self.planner_result.pack(side="left", padx=18)

        scenario = self._card(parent)
        scenario.pack(fill="x")
        ctk.CTkLabel(
            scenario,
            text="WHAT-IF SCENARIO",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLORS["cyan"],
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            scenario,
            text=(
                "Drag to explore the GPA you might average across remaining credits. "
                "Your estimated graduation CGPA updates instantly."
            ),
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
            wraplength=800,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 14))
        scenario_body = ctk.CTkFrame(scenario, fg_color="transparent")
        scenario_body.pack(fill="x", padx=20, pady=(0, 18))
        scenario_body.grid_columnconfigure(0, weight=1)
        scenario_body.grid_columnconfigure(1, weight=0)

        slider_area = ctk.CTkFrame(scenario_body, fg_color="transparent")
        slider_area.grid(row=0, column=0, sticky="ew", padx=(0, 24))
        slider_area.grid_columnconfigure(0, weight=1)
        self.what_if_gpa_value = ctk.CTkLabel(
            slider_area,
            text="Projected GPA: 3.00",
            font=app_font(family="Segoe UI", size=14, weight="bold"),
            text_color=self.COLORS["text"],
        )
        self.what_if_gpa_value.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.what_if_slider = ctk.CTkSlider(
            slider_area,
            from_=2.0,
            to=4.0,
            number_of_steps=20,
            height=18,
            progress_color=self.COLORS["blue"],
            button_color=self.COLORS["cyan"],
            button_hover_color="#0EA5E9",
            command=self._update_what_if_projection,
        )
        self.what_if_slider.grid(row=1, column=0, sticky="ew")
        self.what_if_slider.set(3.0)
        bounds = ctk.CTkFrame(slider_area, fg_color="transparent")
        bounds.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        bounds.grid_columnconfigure(0, weight=1)
        bounds.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            bounds,
            text="2.00",
            font=app_font(family="Segoe UI", size=9),
            text_color=self.COLORS["muted"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            bounds,
            text="4.00",
            font=app_font(family="Segoe UI", size=9),
            text_color=self.COLORS["muted"],
        ).grid(row=0, column=1, sticky="e")

        projection = ctk.CTkFrame(
            scenario_body,
            fg_color=self.COLORS["surface_alt"],
            corner_radius=12,
        )
        projection.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(
            projection,
            text="ESTIMATED GRADUATION CGPA",
            font=app_font(family="Segoe UI", size=8, weight="bold"),
            text_color=self.COLORS["muted"],
        ).pack(anchor="w", padx=14, pady=(12, 2))
        self.what_if_projection = ctk.CTkLabel(
            projection,
            text="—",
            font=app_font(family="Segoe UI", size=25, weight="bold"),
            text_color=self.COLORS["green"],
        )
        self.what_if_projection.pack(anchor="w", padx=14)
        self.what_if_detail = ctk.CTkLabel(
            projection,
            text="Based on remaining credits",
            font=app_font(family="Segoe UI", size=8),
            text_color=self.COLORS["muted"],
        )
        self.what_if_detail.pack(anchor="w", padx=14, pady=(0, 11))
        self._update_what_if_projection(3.0)

    def _update_what_if_projection(self, projected_gpa: float | None = None) -> None:
        """Refresh the simulated graduation CGPA as the slider or inputs change."""
        if not hasattr(self, "what_if_projection") or not hasattr(
            self, "planner_entries"
        ):
            return
        selected_gpa = (
            float(projected_gpa)
            if projected_gpa is not None
            else float(self.what_if_slider.get())
        )
        self.what_if_gpa_value.configure(
            text=f"Projected GPA: {selected_gpa:.2f}"
        )
        try:
            current_cgpa, completed_credits, _, remaining_credits = (
                float(entry.get()) for entry in self.planner_entries
            )
            projected_cgpa = calculate_projected_graduation_cgpa(
                current_cgpa,
                completed_credits,
                selected_gpa,
                remaining_credits,
            )
        except ValueError:
            self.what_if_projection.configure(text="—")
            self.what_if_detail.configure(
                text="Check GPA and credit values",
                text_color=self.COLORS["amber"],
            )
            return

        if projected_cgpa is None:
            self.what_if_projection.configure(text="—")
            self.what_if_detail.configure(
                text="Add completed or remaining credits",
                text_color=self.COLORS["muted"],
            )
            return
        self.what_if_projection.configure(text=f"{projected_cgpa:.2f}")
        self.what_if_detail.configure(
            text=f"Based on {completed_credits:g} completed + "
            f"{remaining_credits:g} remaining credits",
            text_color=self.COLORS["muted"],
        )

    def _calculate_trajectory(self) -> None:
        try:
            current, completed, target, remaining = (
                float(entry.get()) for entry in self.planner_entries
            )
            if (
                not all(math.isfinite(v) for v in (current, completed, target, remaining))
                or not 0 <= current <= self.GRADE_SCALE
                or not 0 <= target <= self.GRADE_SCALE
                or completed < 0
                or remaining < 0
            ):
                raise ValueError
        except ValueError:
            self.planner_result.configure(
                text="Use GPA values from 0 to 4 and non-negative credit values.",
                text_color=self.COLORS["red"],
            )
            return

        if remaining == 0:
            self.planner_result.configure(
                text="No credits remain in this scenario.",
                text_color=self.COLORS["green"],
            )
            return
        try:
            from modules.predictor import TrajectoryEngine

            required = TrajectoryEngine(
                current, completed, target, remaining
            ).calculate_required_gpa()
        except Exception as exc:
            self.planner_result.configure(
                text=f"Could not calculate the projection: {exc}",
                text_color=self.COLORS["red"],
            )
            return

        if required > self.GRADE_SCALE:
            note = f"{required:.2f} required. This is above the 4.00 grading ceiling."
            color = self.COLORS["red"]
        elif required <= 0:
            note = f"{required:.2f} required. You are already on pace for this goal."
            color = self.COLORS["green"]
        else:
            note = f"Aim for {required:.2f} across the remaining {remaining:g} credits."
            color = self.COLORS["cyan"]
        self.planner_result.configure(text=note, text_color=color)

    def _build_semester_calculator(self, parent: ctk.CTkFrame) -> None:
        intro = self._card(parent)
        intro.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            intro,
            text="BUILD YOUR SEMESTER-BY-SEMESTER GPA",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLORS["cyan"],
        ).pack(anchor="w", padx=18, pady=(16, 5))
        ctk.CTkLabel(
            intro,
            text=(
                "Add subjects and their credit values. Semester GPA and cumulative "
                "CGPA recalculate automatically using the official BUBT grade points."
            ),
            font=app_font(family="Segoe UI", size=11),
            text_color=self.COLORS["muted"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 16))

        totals = self._card(parent)
        totals.pack(fill="x", pady=(0, 14))
        totals.grid_columnconfigure(0, weight=1)
        totals.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            totals,
            text="OVERALL CUMULATIVE CGPA",
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLORS["muted"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(15, 2))
        self.calculator_overall_gpa = ctk.CTkLabel(
            totals,
            text="—",
            font=app_font(family="Segoe UI", size=25, weight="bold"),
            text_color=self.COLORS["text"],
        )
        self.calculator_overall_gpa.grid(
            row=1, column=0, sticky="w", padx=18, pady=(0, 3)
        )
        self.calculator_overall_credits = ctk.CTkLabel(
            totals,
            text="0 graded credits",
            font=app_font(family="Segoe UI", size=9),
            text_color=self.COLORS["muted"],
        )
        self.calculator_overall_credits.grid(
            row=2, column=0, sticky="w", padx=18, pady=(0, 14)
        )
        self.calculator_status = ctk.CTkLabel(
            totals,
            text="Enter positive credit values to calculate GPA.",
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
            wraplength=350,
            justify="right",
        )
        self.calculator_status.grid(
            row=0, column=1, rowspan=3, sticky="e", padx=18, pady=14
        )

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 12))
        add_semester_button = ctk.CTkButton(
            actions,
            text="＋  Add Next Semester",
            height=38,
            corner_radius=10,
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            command=self._add_calculator_semester,
        )
        add_semester_button.pack(side="left")
        self._enable_button_transition(
            add_semester_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )
        self.calculator_semester_container = ctk.CTkFrame(
            parent, fg_color="transparent"
        )
        self.calculator_semester_container.pack(fill="x")
        self._render_calculator_semesters()

    def _render_calculator_semesters(self) -> None:
        for child in self.calculator_semester_container.winfo_children():
            child.destroy()
        self.calculator_semester_gpas: list[ctk.CTkLabel] = []

        for semester_index, subjects in enumerate(self.calculator_semesters):
            card = self._card(self.calculator_semester_container)
            card.pack(fill="x", pady=(0, 12))
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=16, pady=(14, 10))
            ctk.CTkLabel(
                header,
                text=f"Semester {semester_index + 1}",
                font=app_font(family="Segoe UI", size=14, weight="bold"),
                text_color=self.COLORS["text"],
            ).pack(side="left")
            gpa_label = ctk.CTkLabel(
                header,
                text="GPA  —",
                font=app_font(family="Segoe UI", size=11, weight="bold"),
                text_color=self.COLORS["cyan"],
            )
            gpa_label.pack(side="right")
            self.calculator_semester_gpas.append(gpa_label)

            subject_grid = ctk.CTkFrame(card, fg_color="transparent")
            subject_grid.pack(fill="x", padx=16)
            subject_grid.grid_columnconfigure(0, weight=3, uniform="subject")
            subject_grid.grid_columnconfigure(1, weight=1, uniform="subject")
            subject_grid.grid_columnconfigure(2, weight=1, uniform="subject")
            for column, heading in enumerate(("Subject name (optional)", "Grade", "Credits")):
                ctk.CTkLabel(
                    subject_grid,
                    text=heading,
                    font=app_font(family="Segoe UI", size=9, weight="bold"),
                    text_color=self.COLORS["muted"],
                    anchor="w",
                ).grid(row=0, column=column, sticky="ew", padx=(0, 9), pady=(0, 6))

            for row_index, subject in enumerate(subjects, start=1):
                subject_name = ctk.CTkEntry(
                    subject_grid,
                    height=36,
                    corner_radius=8,
                    border_color=self.COLORS["border"],
                    placeholder_text="e.g. Data Structures",
                )
                subject_name.insert(0, subject["name"])
                subject_name.grid(
                    row=row_index, column=0, sticky="ew", padx=(0, 9), pady=4
                )
                subject_name.bind(
                    "<KeyRelease>",
                    lambda _event, s=semester_index, r=row_index - 1, widget=subject_name:
                    self._update_calculator_subject(s, r, "name", widget.get()),
                )

                grade_menu = ctk.CTkOptionMenu(
                    subject_grid,
                    values=list(GRADE_POINTS),
                    variable=ctk.StringVar(value=subject["grade"]),
                    height=36,
                    corner_radius=8,
                    fg_color=self.COLORS["surface_alt"],
                    button_color=self.COLORS["blue"],
                    button_hover_color=self.COLORS["blue_hover"],
                    command=lambda grade, s=semester_index, r=row_index - 1:
                    self._update_calculator_subject(s, r, "grade", grade),
                )
                grade_menu.grid(
                    row=row_index, column=1, sticky="ew", padx=(0, 9), pady=4
                )

                credits_entry = ctk.CTkEntry(
                    subject_grid,
                    height=36,
                    corner_radius=8,
                    border_color=self.COLORS["border"],
                    placeholder_text="e.g. 3",
                )
                credits_entry.insert(0, subject["credits"])
                credits_entry.grid(
                    row=row_index, column=2, sticky="ew", padx=(0, 9), pady=4
                )
                credits_entry.bind(
                    "<KeyRelease>",
                    lambda _event, s=semester_index, r=row_index - 1, widget=credits_entry:
                    self._update_calculator_subject(s, r, "credits", widget.get()),
                )

                remove_button = ctk.CTkButton(
                    subject_grid,
                    text="×",
                    width=32,
                    height=32,
                    corner_radius=8,
                    fg_color="transparent",
                    hover_color="#392535",
                    text_color=self.COLORS["red"],
                    command=lambda s=semester_index, r=row_index - 1:
                    self._remove_calculator_subject(s, r),
                )
                remove_button.grid(row=row_index, column=3, padx=(0, 0), pady=4)

            add_subject_button = ctk.CTkButton(
                card,
                text="＋  Add Subject",
                width=130,
                height=34,
                corner_radius=9,
                fg_color=self.COLORS["surface_alt"],
                hover_color="#203552",
                text_color=self.COLORS["text"],
                font=app_font(family="Segoe UI", size=9, weight="bold"),
                command=lambda s=semester_index: self._add_calculator_subject(s),
            )
            add_subject_button.pack(anchor="w", padx=16, pady=(10, 14))
            self._enable_button_transition(
                add_subject_button, self.COLORS["surface_alt"], "#203552"
            )

        self._refresh_calculator_results()

    def _add_calculator_semester(self) -> None:
        self.calculator_semesters.append([])
        self._render_calculator_semesters()

    def _add_calculator_subject(self, semester_index: int) -> None:
        self.calculator_semesters[semester_index].append(
            {"name": "", "grade": "A+", "credits": ""}
        )
        self._render_calculator_semesters()

    def _remove_calculator_subject(
        self, semester_index: int, subject_index: int
    ) -> None:
        self.calculator_semesters[semester_index].pop(subject_index)
        self._render_calculator_semesters()

    def _update_calculator_subject(
        self, semester_index: int, subject_index: int, field: str, value: str
    ) -> None:
        self.calculator_semesters[semester_index][subject_index][field] = value
        self._refresh_calculator_results()

    def _refresh_calculator_results(self) -> None:
        overall_subjects: list[dict[str, str]] = []
        invalid_entries = 0
        total_credits = 0.0

        for semester_index, subjects in enumerate(self.calculator_semesters):
            overall_subjects.extend(subjects)
            gpa, credits, invalid = calculate_calculator_gpa(subjects)
            total_credits += credits
            invalid_entries += invalid
            gpa_label = self.calculator_semester_gpas[semester_index]
            gpa_label.configure(
                text=f"GPA  {gpa:.2f}" if gpa is not None else "GPA  —"
            )

        overall_gpa, overall_credits, overall_invalid = calculate_calculator_gpa(
            overall_subjects
        )
        invalid_entries = max(invalid_entries, overall_invalid)
        self.calculator_overall_gpa.configure(
            text=f"{overall_gpa:.2f}" if overall_gpa is not None else "—"
        )
        self.calculator_overall_credits.configure(
            text=f"{overall_credits:g} graded credits"
        )
        if invalid_entries:
            self.calculator_status.configure(
                text="Credits must be positive numbers. Invalid rows are excluded.",
                text_color=self.COLORS["amber"],
            )
        elif total_credits:
            self.calculator_status.configure(
                text="Semester and overall GPAs are credit-weighted.",
                text_color=self.COLORS["green"],
            )
        else:
            self.calculator_status.configure(
                text="Enter positive credit values to calculate GPA.",
                text_color=self.COLORS["muted"],
            )

    def _build_advisor(self, parent: ctk.CTkFrame) -> None:
        summary = self._summary()
        context = self._card(parent)
        context.pack(fill="x", pady=(0, 14))
        weak = ", ".join(
            str(record.get("course_code", "Course"))
            for record in summary["weak_courses"][:5]
        ) or "None identified"
        cgpa_text = (
            f"{summary['cgpa']:.2f}"
            if summary["cgpa"] is not None
            else "No grades"
        )
        ctk.CTkLabel(
            context,
            text="STUDENT CONTEXT",
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLORS["cyan"],
        ).pack(anchor="w", padx=18, pady=(16, 7))
        ctk.CTkLabel(
            context,
            text=(
                f"CGPA: {cgpa_text}  |  "
                f"Graded credits: {summary['completed_credits']:g}  |  "
                f"Courses to watch: {weak}"
            ),
            font=app_font(family="Segoe UI", size=11),
            text_color=self.COLORS["muted"],
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 16))

        card = self._card(parent)
        card.pack(fill="both", expand=True)
        ctk.CTkLabel(
            card,
            text="What would you like help with?",
            font=app_font(family="Segoe UI", size=14, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(anchor="w", padx=18, pady=(18, 10))
        ctk.CTkLabel(
            card,
            text=(
                "Type a question or edit the example below, then select "
                "Get academic guidance. Your grades help personalize the answer."
            ),
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["muted"],
            wraplength=800,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 10))
        self.advisor_input = ctk.CTkTextbox(
            card,
            height=100,
            corner_radius=10,
            border_width=1,
            border_color=self.COLORS["border"],
            font=app_font(family="Segoe UI", size=11),
            wrap="word",
        )
        self.advisor_input.pack(fill="x", padx=18)
        self.advisor_input.insert(
            "1.0", "How can I improve my CGPA next semester?"
        )
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=12)
        self.advisor_button = ctk.CTkButton(
            actions,
            text="Get academic guidance",
            height=38,
            corner_radius=9,
            command=self._request_advice,
        )
        self._enable_button_transition(
            self.advisor_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )
        self.advisor_button.pack(side="left")
        self.advisor_status = ctk.CTkLabel(
            actions,
            text="Uses your saved Gemini key, if configured; otherwise uses local guidance.",
            font=app_font(family="Segoe UI", size=9),
            text_color=self.COLORS["muted"],
            wraplength=500,
        )
        self.advisor_status.pack(side="left", padx=12)
        ctk.CTkLabel(
            card,
            text="ADVISOR RESPONSE",
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLORS["cyan"],
        ).pack(anchor="w", padx=18, pady=(5, 8))
        self.advisor_output = ctk.CTkTextbox(
            card,
            height=180,
            corner_radius=10,
            font=app_font(family="Segoe UI", size=11),
            wrap="word",
        )
        self.advisor_output.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.advisor_output.insert(
            "1.0",
            "Your academic profile is ready. Ask a question to receive guidance.",
        )
        self.advisor_output.configure(state="disabled")

    def _request_advice(self) -> None:
        question = self.advisor_input.get("1.0", "end").strip()
        if not question:
            self.advisor_status.configure(
                text="Enter a question before requesting advice.",
                text_color=self.COLORS["amber"],
            )
            return
        summary = self._summary()
        if summary["cgpa"] is None:
            self.advisor_status.configure(
                text="No graded records are available to personalize guidance.",
                text_color=self.COLORS["amber"],
            )
            return

        self.advisor_button.configure(state="disabled", text="Thinking...")
        self.advisor_status.configure(
            text="Preparing academic guidance...",
            text_color=self.COLORS["muted"],
        )
        context = (
            self.student["name"],
            summary["cgpa"],
            summary["completed_credits"],
            [
                str(record.get("course_code", "Course"))
                for record in summary["weak_courses"]
            ],
            question,
        )

        def generate() -> None:
            try:
                from modules.ai_advisor import AIAdvisorEngine

                advisor = AIAdvisorEngine(
                    api_key=self.gemini_api_key or os.environ.get("GEMINI_API_KEY")
                )
                response = advisor.get_academic_advice(*context)
                error = None
            except Exception as exc:
                response = f"Advisor could not be reached: {exc}"
                error = str(exc)
            self.after(0, lambda: self._finish_advice(response, error))

        threading.Thread(target=generate, name="edutrack-ai-advisor", daemon=True).start()

    def _finish_advice(self, response: str, error: str | None) -> None:
        if not self.winfo_exists():
            return
        self.advisor_output.configure(state="normal")
        self.advisor_output.delete("1.0", "end")
        self.advisor_output.insert("1.0", response or "The advisor returned an empty response.")
        self.advisor_output.configure(state="disabled")
        self.advisor_button.configure(state="normal", text="Get academic guidance")
        self.advisor_status.configure(
            text="Advisor service unavailable." if error else "Guidance is ready.",
            text_color=self.COLORS["red"] if error else self.COLORS["green"],
        )

    def _build_analytics(self, parent: ctk.CTkFrame) -> None:
        summary = self._summary()
        overview = self._card(parent)
        overview.pack(fill="x", pady=(0, 14))
        self._section_heading(overview, "Academic overview")
        cgpa_text = (
            f"{summary['cgpa']:.2f}"
            if summary["cgpa"] is not None
            else "No grades"
        )
        overview_metrics = (
            ("CURRENT CGPA", cgpa_text),
            ("GRADED CREDITS", f"{summary['completed_credits']:g}"),
            ("SEMESTERS", str(len(summary["semester_averages"]))),
            ("GRADED COURSES", str(len(summary["graded_courses"]))),
        )
        metric_row = ctk.CTkFrame(overview, fg_color="transparent")
        metric_row.pack(fill="x", padx=20, pady=(0, 20))
        for column, (label, value) in enumerate(overview_metrics):
            metric_row.grid_columnconfigure(column, weight=1, uniform="analytics")
            metric = ctk.CTkFrame(
                metric_row,
                fg_color=self.COLORS["surface_alt"],
                corner_radius=12,
            )
            metric.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 8, 8),
            )
            ctk.CTkLabel(
                metric,
                text=label,
                font=app_font(family="Segoe UI", size=8, weight="bold"),
                text_color=self.COLORS["muted"],
                wraplength=160,
                justify="left",
            ).pack(anchor="w", padx=14, pady=(13, 5))
            ctk.CTkLabel(
                metric,
                text=value,
                font=app_font(family="Segoe UI", size=18, weight="bold"),
                text_color=self.COLORS["text"],
            ).pack(anchor="w", padx=14, pady=(0, 13))

        trend = self._card(parent)
        trend.pack(fill="x", pady=(0, 14))
        self._section_heading(trend, "Semester GPA")
        self._helper_text(
            trend,
            "Each point shows the credit-weighted average for one semester. "
            "Higher values indicate stronger semester performance.",
        )
        self._draw_semester_trend(trend, summary["semester_averages"])

        grades = self._card(parent)
        grades.pack(fill="x")
        self._section_heading(grades, "Grade distribution")
        self._helper_text(
            grades,
            "Bars compare how many recorded courses received each letter grade.",
        )
        counts: Counter[str] = summary["grade_counts"]
        ordered_counts = [(grade, counts.get(grade, 0)) for grade in self.GRADE_ORDER]
        if not any(count for _, count in ordered_counts):
            self._helper_text(
                grades,
                "No graded courses are recorded yet. The full BUBT scale is shown "
                "with zero counts and will update when course results are available.",
            )
        chart = ctk.CTkCanvas(
            grades,
            height=max(390, len(ordered_counts) * 42 + 76),
            background=self.COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        chart.pack(fill="x", padx=24, pady=(0, 24))
        chart.bind(
            "<Configure>",
            lambda _event, target=chart, data=ordered_counts:
            self._schedule_chart_redraw(
                target,
                lambda: self._paint_grade_distribution(target, data),
            ),
        )
        self._paint_grade_distribution(chart, ordered_counts)

    def _paint_grade_distribution(
        self, chart: ctk.CTkCanvas, grade_counts: list[tuple[str, int]]
    ) -> None:
        chart.delete("all")
        width = max(chart.winfo_width(), 360)
        height = max(chart.winfo_height(), len(grade_counts) * 42 + 76)
        left, right = 62, width - 48
        top, bottom = 22, height - 48
        max_count = max((count for _, count in grade_counts), default=1)
        axis_max = max(1, math.ceil(max_count / 2) * 2)

        ticks = sorted(
            {
                round(axis_max * fraction)
                for fraction in (0, 0.25, 0.5, 0.75, 1)
            }
        )
        for tick in ticks:
            x = left + (tick / axis_max) * (right - left)
            chart.create_line(
                x,
                top,
                x,
                bottom,
                fill="#1B2A3E" if tick else self.COLORS["border"],
                width=1,
            )
            chart.create_text(
                x,
                bottom + 18,
                text=str(tick),
                fill=self.COLORS["muted"],
                font=("Segoe UI", 11),
                anchor="n",
            )

        chart.create_text(
            (left + right) / 2,
            height - 8,
            text="NUMBER OF COURSES",
            fill=self.COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
            anchor="s",
        )
        chart.create_line(
            left, bottom, right, bottom, fill=self.COLORS["border"], width=1
        )
        row_height = (bottom - top) / max(len(grade_counts), 1)
        palette = (
            self.COLORS["cyan"],
            self.COLORS["blue"],
            self.COLORS["green"],
            "#818CF8",
            "#A78BFA",
            "#FBBF24",
            "#FB923C",
            "#FB7185",
            "#F472B6",
            self.COLORS["red"],
        )
        for index, (grade, count) in enumerate(grade_counts):
            center_y = top + row_height * (index + 0.5)
            chart.create_line(
                left,
                center_y + row_height / 2,
                right,
                center_y + row_height / 2,
                fill="#17263A",
                width=1,
            )
            chart.create_text(
                left - 14,
                center_y,
                text=grade,
                fill=self.COLORS["text"],
                font=("Segoe UI", 12, "bold"),
                anchor="e",
            )
            bar_end = left + (count / axis_max) * (right - left)
            color = palette[index % len(palette)]
            if count:
                chart.create_rectangle(
                    left + 1,
                    center_y - 8,
                    max(left + 2, bar_end),
                    center_y + 8,
                    fill=color,
                    outline="",
                )
                count_x = min(bar_end - 8, right - 8)
                count_anchor = "e"
                count_color = self.COLORS["window"]
            else:
                count_x = left + 9
                count_anchor = "w"
                count_color = self.COLORS["muted"]
            chart.create_text(
                count_x,
                center_y,
                text=str(count),
                fill=count_color,
                font=("Segoe UI", 11, "bold"),
                anchor=count_anchor,
            )

    def _build_attendance_schedule(self, parent: ctk.CTkFrame) -> None:
        from modules.crud import AcademicCRUD

        try:
            routines = AcademicCRUD.get_routines()
            attendance_records = AcademicCRUD.get_attendance(
                self.student["student_id"]
            )
        except Exception as exc:
            self._notice(
                parent,
                f"Could not load attendance and schedule: {exc}",
                self.COLORS["red"],
            )
            return

        routine_card = self._card(parent)
        routine_card.pack(fill="x", pady=(0, 16))
        self._section_heading(routine_card, "Weekly class routine")
        if not routines:
            self._helper_text(
                routine_card,
                "No classes have been added to the weekly routine yet.",
            )
        else:
            by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for routine in routines:
                by_day[routine["day"]].append(routine)
            for day in AcademicCRUD.WEEKDAYS:
                day_routines = by_day.get(day)
                if not day_routines:
                    continue
                ctk.CTkLabel(
                    routine_card,
                    text=day.upper(),
                    font=app_font(family="Segoe UI", size=9, weight="bold"),
                    text_color=self.COLORS["cyan"],
                ).pack(anchor="w", padx=20, pady=(4, 7))
                for routine in day_routines:
                    row = ctk.CTkFrame(
                        routine_card,
                        fg_color=self.COLORS["surface_alt"],
                        corner_radius=10,
                    )
                    row.pack(fill="x", padx=18, pady=(0, 7))
                    row.grid_columnconfigure(1, weight=1)
                    ctk.CTkLabel(
                        row,
                        text=routine["time"],
                        width=150,
                        anchor="w",
                        font=app_font(family="Segoe UI", size=10, weight="bold"),
                        text_color=self.COLORS["text"],
                    ).grid(row=0, column=0, sticky="w", padx=12, pady=11)
                    ctk.CTkLabel(
                        row,
                        text=f"{routine['course_code']}  ·  {routine['course_title']}",
                        anchor="w",
                        font=app_font(family="Segoe UI", size=10),
                        text_color=self.COLORS["text"],
                    ).grid(row=0, column=1, sticky="ew", padx=8, pady=11)
                    ctk.CTkLabel(
                        row,
                        text=routine["room"],
                        width=100,
                        anchor="e",
                        font=app_font(family="Segoe UI", size=10),
                        text_color=self.COLORS["muted"],
                    ).grid(row=0, column=2, sticky="e", padx=12, pady=11)
            ctk.CTkFrame(
                routine_card, height=8, fg_color="transparent"
            ).pack(fill="x")

        attendance_card = self._card(parent)
        attendance_card.pack(fill="x")
        self._section_heading(
            attendance_card,
            "Course attendance",
            "Warnings appear below 75%",
        )
        self._helper_text(
            attendance_card,
            "Update the number of classes held and attended for each course, then save. "
            "Only courses with recorded classes have a percentage.",
        )
        attendance_by_course = {
            record["course_code"]: record for record in attendance_records
        }
        course_records: dict[str, dict[str, Any]] = {}
        for enrollment in self.enrollments:
            course_records.setdefault(
                enrollment["course_code"],
                {
                    "course_code": enrollment["course_code"],
                    "course_title": enrollment["course_title"],
                    "total_classes": 0,
                    "attended_classes": 0,
                },
            )
        for course_code, record in attendance_by_course.items():
            course_records[course_code] = record

        if not course_records:
            self._helper_text(
                attendance_card,
                "No enrolled courses are available to track yet.",
            )
            return

        self._attendance_inputs: dict[
            str,
            tuple[
                ctk.CTkEntry,
                ctk.CTkEntry,
                ctk.CTkLabel,
                ctk.CTkLabel,
            ],
        ] = {}
        for course_code, record in sorted(course_records.items()):
            row = ctk.CTkFrame(
                attendance_card,
                fg_color=self.COLORS["surface_alt"],
                corner_radius=11,
            )
            row.pack(fill="x", padx=18, pady=(0, 9))
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                row,
                text=f"{course_code}  ·  {record['course_title']}",
                anchor="w",
                font=app_font(family="Segoe UI", size=11, weight="bold"),
                text_color=self.COLORS["text"],
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

            count_fields = ctk.CTkFrame(row, fg_color="transparent")
            count_fields.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 11))
            ctk.CTkLabel(
                count_fields,
                text="Total",
                font=app_font(family="Segoe UI", size=9),
                text_color=self.COLORS["muted"],
            ).pack(side="left", padx=(0, 5))
            total_entry = ctk.CTkEntry(count_fields, width=68, height=32)
            total_entry.insert(0, str(record["total_classes"]))
            total_entry.pack(side="left", padx=(0, 14))
            ctk.CTkLabel(
                count_fields,
                text="Attended",
                font=app_font(family="Segoe UI", size=9),
                text_color=self.COLORS["muted"],
            ).pack(side="left", padx=(0, 5))
            attended_entry = ctk.CTkEntry(count_fields, width=68, height=32)
            attended_entry.insert(0, str(record["attended_classes"]))
            attended_entry.pack(side="left", padx=(0, 12))
            save_button = ctk.CTkButton(
                count_fields,
                text="Save",
                width=76,
                height=32,
                corner_radius=8,
                command=lambda code=course_code: self._save_attendance_record(code),
            )
            self._enable_button_transition(
                save_button, self.COLORS["blue"], self.COLORS["blue_hover"]
            )
            save_button.pack(side="left")

            percentage = record.get("attendance_percentage")
            if percentage is None:
                percentage_text = "—"
                percentage_color = self.COLORS["amber"]
                status_text = "No classes recorded"
                status_color = self.COLORS["muted"]
            elif percentage < 75:
                percentage_text = f"{percentage:.1f}%"
                percentage_color = self.COLORS["red"]
                status_text = "Below 75% — attendance warning"
                status_color = self.COLORS["red"]
            else:
                percentage_text = f"{percentage:.1f}%"
                percentage_color = self.COLORS["green"]
                status_text = "Meets the 75% attendance minimum"
                status_color = self.COLORS["green"]
            percentage_label = ctk.CTkLabel(
                row,
                text=percentage_text,
                font=app_font(family="Segoe UI", size=18, weight="bold"),
                text_color=percentage_color,
            )
            percentage_label.grid(row=0, column=1, sticky="e", padx=14, pady=(10, 0))
            status_label = ctk.CTkLabel(
                row,
                text=status_text,
                font=app_font(family="Segoe UI", size=9, weight="bold"),
                text_color=status_color,
            )
            status_label.grid(row=1, column=1, sticky="e", padx=14, pady=(0, 11))
            self._attendance_inputs[course_code] = (
                total_entry,
                attended_entry,
                percentage_label,
                status_label,
            )

    def _save_attendance_record(self, course_code: str) -> None:
        total_entry, attended_entry, percentage_label, status_label = (
            self._attendance_inputs[course_code]
        )
        try:
            total_classes = int(total_entry.get().strip())
            attended_classes = int(attended_entry.get().strip())
            from modules.crud import AcademicCRUD

            AcademicCRUD.save_attendance(
                self.student["student_id"],
                course_code,
                total_classes,
                attended_classes,
            )
        except ValueError as exc:
            status_label.configure(
                text=(
                    str(exc)
                    if "cannot exceed" in str(exc)
                    else "Enter whole-number counts; attended classes cannot exceed total."
                ),
                text_color=self.COLORS["red"],
            )
            return
        except Exception as exc:
            status_label.configure(
                text=f"Could not save attendance: {exc}",
                text_color=self.COLORS["red"],
            )
            return

        if total_classes == 0:
            percentage_label.configure(
                text="—", text_color=self.COLORS["amber"]
            )
            status_label.configure(
                text="No classes recorded",
                text_color=self.COLORS["muted"],
            )
            return

        percentage = attended_classes / total_classes * 100
        if percentage < 75:
            percentage_label.configure(
                text=f"{percentage:.1f}%", text_color=self.COLORS["red"]
            )
            status_label.configure(
                text="Below 75% — attendance warning",
                text_color=self.COLORS["red"],
            )
        else:
            percentage_label.configure(
                text=f"{percentage:.1f}%", text_color=self.COLORS["green"]
            )
            status_label.configure(
                text="Attendance saved · meets the 75% minimum",
                text_color=self.COLORS["green"],
            )

    def _build_settings(self, parent: ctk.CTkFrame) -> None:
        def create_section(title: str, detail: str) -> ctk.CTkFrame:
            card = self._card(parent)
            card.pack(fill="x", pady=(0, 14))
            heading = ctk.CTkFrame(card, fg_color="transparent")
            heading.pack(fill="x", padx=18, pady=(16, 12))
            ctk.CTkLabel(
                heading,
                text=title,
                font=app_font(family="Segoe UI", size=15, weight="bold"),
                text_color=self.COLORS["text"],
            ).pack(anchor="w", pady=(0, 4))
            ctk.CTkLabel(
                heading,
                text=detail,
                font=app_font(family="Segoe UI", size=10),
                text_color=self.COLORS["muted"],
            ).pack(anchor="w")
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x")
            return content

        def add_entry(
            section: ctk.CTkFrame,
            label: str,
            key: str,
            value: str,
            row: int,
            column: int,
            *,
            columnspan: int = 1,
        ) -> None:
            field = ctk.CTkFrame(section, fg_color="transparent")
            field.grid(
                row=row,
                column=column,
                columnspan=columnspan,
                sticky="ew",
                padx=18,
                pady=(0, 12),
            )
            ctk.CTkLabel(
                field,
                text=label,
                font=app_font(family="Segoe UI", size=10, weight="bold"),
                text_color=self.COLORS["muted"],
            ).pack(anchor="w", pady=(0, 5))
            entry = ctk.CTkEntry(
                field,
                height=38,
                corner_radius=9,
                show="•" if key == "gemini_api_key" else None,
                placeholder_text=(
                    "Optional — paste a Gemini API key to enable cloud advice"
                    if key == "gemini_api_key"
                    else None
                ),
            )
            entry.insert(0, value)
            entry.pack(fill="x")
            if key == "student_id":
                entry.configure(state="disabled")
            self.settings_entries[key] = entry

        self.settings_entries: dict[str, ctk.CTkEntry] = {}

        profile = create_section(
            "Profile Settings",
            "Personalize your student profile.",
        )
        profile.grid_columnconfigure((0, 1), weight=1, uniform="profile")
        add_entry(profile, "Display name", "name", self.student["name"], 2, 0)
        add_entry(
            profile,
            "Student ID",
            "student_id",
            self.student["student_id"],
            2,
            1,
        )
        add_entry(
            profile,
            "Current semester",
            "semester",
            self.student["semester"],
            3,
            0,
            columnspan=2,
        )

        academic = create_section(
            "Academic Goals",
            "Set your program requirements and academic target.",
        )
        academic.grid_columnconfigure((0, 1), weight=1, uniform="academic")
        add_entry(
            academic,
            "Program credits",
            "program_credits",
            str(self.program_credits),
            2,
            0,
        )
        add_entry(
            academic,
            "Target CGPA",
            "target_cgpa",
            f"{self.target_cgpa:.2f}",
            2,
            1,
        )
        add_entry(
            academic,
            "Current CGPA",
            "current_cgpa",
            f"{self.current_cgpa:.2f}" if self.current_cgpa is not None else "",
            3,
            0,
        )
        theme_field = ctk.CTkFrame(academic, fg_color="transparent")
        theme_field.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )
        ctk.CTkLabel(
            theme_field,
            text="Accent theme",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLORS["muted"],
        ).pack(anchor="w", pady=(0, 5))
        self.theme_selector = ctk.CTkOptionMenu(
            theme_field,
            values=list(ACCENT_THEMES),
            command=self._change_accent_theme,
            height=38,
            corner_radius=9,
            fg_color=self.COLORS["blue"],
            button_color=self.COLORS["blue"],
            button_hover_color=self.COLORS["blue_hover"],
            dropdown_fg_color=self.COLORS["surface_alt"],
            dropdown_hover_color=self.COLORS["blue"],
            text_color=self.COLORS["text"],
        )
        self.theme_selector.set(self.accent_theme)
        self.theme_selector.pack(anchor="w")

        ai = create_section(
            "AI Configuration",
            "Configure optional cloud-powered academic advice.",
        )
        ai.grid_columnconfigure(0, weight=1)
        add_entry(
            ai,
            "Gemini API key",
            "gemini_api_key",
            self.gemini_api_key,
            2,
            0,
        )
        ctk.CTkLabel(
            ai,
            text=(
                "Gemini API key (optional): saved locally in SQLite and used for "
                "cloud AI advice. Leave blank to use the local advisor."
            ),
            font=app_font(family="Segoe UI", size=9),
            text_color=self.COLORS["amber"],
            wraplength=760,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=18, pady=(0, 16))

        management = create_section(
            "Data Management",
            "Export a backup or restore your data from a previous backup.",
        )
        self.settings_status = ctk.CTkLabel(
            management,
            text="",
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["green"],
        )
        self.settings_status.pack(anchor="w", padx=18, pady=(0, 8))
        settings_actions = ctk.CTkFrame(management, fg_color="transparent")
        settings_actions.pack(fill="x", padx=18, pady=(0, 18))
        save_button = ctk.CTkButton(
            settings_actions,
            text="Save settings",
            height=40,
            corner_radius=9,
            command=self._save_settings,
        )
        self._enable_button_transition(
            save_button, self.COLORS["blue"], self.COLORS["blue_hover"]
        )
        save_button.pack(side="left", padx=(0, 10))

        export_button = ctk.CTkButton(
            settings_actions,
            text="Export Data",
            height=40,
            corner_radius=9,
            command=self._export_data,
            fg_color=self.COLORS["surface_alt"],
            hover_color=self.COLORS["border"],
        )
        self._enable_button_transition(
            export_button, self.COLORS["surface_alt"], self.COLORS["border"]
        )
        export_button.pack(side="left", padx=(0, 10))
        restore_button = ctk.CTkButton(
            settings_actions,
            text="Restore Data",
            height=40,
            corner_radius=9,
            command=self._restore_data,
            fg_color=self.COLORS["surface_alt"],
            hover_color=self.COLORS["border"],
        )
        self._enable_button_transition(
            restore_button, self.COLORS["surface_alt"], self.COLORS["border"]
        )
        restore_button.pack(side="left")

    def _change_accent_theme(self, theme_name: str) -> None:
        """Save a selected accent theme and rebuild widgets with its palette."""
        try:
            theme_colors = accent_theme_colors(theme_name)
        except ValueError as exc:
            self.theme_selector.set(self.accent_theme)
            self.settings_status.configure(
                text=f"Could not apply accent theme: {exc}",
                text_color=self.COLORS["red"],
            )
            return

        if theme_name == self.accent_theme:
            return

        try:
            from modules.crud import AcademicCRUD

            AcademicCRUD.save_user_theme(self.student["student_id"], theme_name)
        except Exception as exc:
            self.theme_selector.set(self.accent_theme)
            self.settings_status.configure(
                text=f"Could not save accent theme: {exc}",
                text_color=self.COLORS["red"],
            )
            return

        current_page = self.current_page or "Settings"
        settings_draft = {
            key: entry.get() for key, entry in self.settings_entries.items()
        }
        self.accent_theme = theme_name
        self.COLORS.update(theme_colors)
        self._refresh_theme_ui(current_page, settings_draft)

    def _refresh_theme_ui(
        self, page: str, settings_draft: dict[str, str] | None = None
    ) -> None:
        """Recreate widgets so cached CustomTkinter colors use the active palette."""
        for button, job in tuple(self._button_color_jobs.items()):
            try:
                button.after_cancel(job)
            except tk.TclError:
                pass
        self._button_color_jobs.clear()
        self._button_hover_states.clear()
        if self._status_reset_job is not None:
            try:
                self.after_cancel(self._status_reset_job)
            except tk.TclError:
                pass
            self._status_reset_job = None
        if self.help_window is not None and self.help_window.winfo_exists():
            self.help_window.destroy()
            self.help_window = None

        self._discard_cached_pages()
        self.sidebar.destroy()
        self.main.destroy()
        self.configure(fg_color=self.COLORS["window"])
        self._build_shell()
        self.show_page(page)
        for key, value in (settings_draft or {}).items():
            entry = self.settings_entries[key]
            if key == "student_id":
                entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value)
            if key == "student_id":
                entry.configure(state="disabled")
        if page == "Settings":
            self.settings_status.configure(
                text=f"{self.accent_theme} theme applied and saved.",
                text_color=self.COLORS["green"],
            )
        else:
            self._show_header_status(
                "ACCENT THEME RESTORED",
                self.COLORS["green"],
                reset_after=3500,
            )

    def _save_settings(self) -> None:
        name = self.settings_entries["name"].get().strip()
        student_id = self.settings_entries["student_id"].get().strip()
        semester = self.settings_entries["semester"].get().strip()
        gemini_api_key = self.settings_entries["gemini_api_key"].get().strip()
        try:
            program_credits = float(self.settings_entries["program_credits"].get())
            target_cgpa = float(self.settings_entries["target_cgpa"].get())
            current_cgpa_text = self.settings_entries["current_cgpa"].get().strip()
            current_cgpa = float(current_cgpa_text) if current_cgpa_text else None
            if (
                not name
                or not student_id
                or not semester
                or not math.isfinite(program_credits)
                or program_credits <= 0
                or not math.isfinite(target_cgpa)
                or not 0 <= target_cgpa <= self.GRADE_SCALE
                or (
                    current_cgpa is not None
                    and (
                        not math.isfinite(current_cgpa)
                        or not 0 <= current_cgpa <= self.GRADE_SCALE
                    )
                )
            ):
                raise ValueError
        except ValueError:
            self.settings_status.configure(
                text=(
                    "Enter a name, ID, semester, positive credit total, and GPAs "
                    "from 0 to 4. Current CGPA may be blank."
                ),
                text_color=self.COLORS["red"],
            )
            return

        if student_id != self.student["student_id"]:
            self.settings_status.configure(
                text="Student ID is assigned by the account and cannot be changed here.",
                text_color=self.COLORS["red"],
            )
            return
        try:
            from modules.crud import AcademicCRUD

            AcademicCRUD.save_user_settings(
                student_id,
                name,
                semester,
                program_credits,
                target_cgpa,
                current_cgpa,
                gemini_api_key,
                self.accent_theme,
            )
        except Exception as exc:
            self.settings_status.configure(
                text=f"Could not save profile: {exc}",
                text_color=self.COLORS["red"],
            )
            return

        self.student.update(name=name, semester=semester)
        self.program_credits = program_credits
        self.target_cgpa = target_cgpa
        if current_cgpa is None:
            from modules.grading import calculate_weighted_cgpa

            self.current_cgpa, _ = calculate_weighted_cgpa(self.enrollments)
        else:
            self.current_cgpa = current_cgpa
        self.gemini_api_key = gemini_api_key
        self._update_profile_badge()
        self._discard_cached_pages()
        self.show_page("Dashboard")
        self._show_header_status(
            "✓  SETTINGS SAVED",
            self.COLORS["green"],
            reset_after=3500,
        )

    def _export_data(self) -> None:
        from modules.crud import AcademicCRUD

        try:
            backup_path = AcademicCRUD.export_data()
            if backup_path is None:
                return
        except Exception as exc:
            messagebox.showerror(
                "Export failed",
                f"Could not export EduTrack data:\n{exc}",
                parent=self,
            )
            return
        messagebox.showinfo(
            "Export successful",
            f"EduTrack data was exported to:\n{backup_path}\n\n"
            "Keep this file private: it includes saved settings such as the "
            "Gemini API key. Login passwords are not included.",
            parent=self,
        )

    def _restore_data(self) -> None:
        overwrite = messagebox.askyesnocancel(
            "Restore EduTrack data",
            "Choose how to apply the backup.\n\n"
            "Yes: Merge the backup, updating matching records and preserving "
            "existing records not included in it.\n\n"
            "No: Overwrite matching profiles and replace their enrollments and "
            "settings with the backup. Unrelated profiles and login credentials "
            "will be preserved.",
            parent=self,
        )
        if overwrite is None:
            return

        from modules.crud import AcademicCRUD

        mode = "merge" if overwrite else "overwrite"
        try:
            restored = AcademicCRUD.restore_data(mode=mode)
            if restored is None:
                return
        except Exception as exc:
            messagebox.showerror(
                "Restore failed",
                f"Could not restore EduTrack data:\n{exc}",
                parent=self,
            )
            return

        previous_theme = self.accent_theme
        self._load_student_data()
        if self.accent_theme != previous_theme:
            self._refresh_theme_ui("Dashboard")
        else:
            self._update_profile_badge()
            self._discard_cached_pages()
            self.show_page("Dashboard")
        messagebox.showinfo(
            "Restore successful",
            "Restored "
            f"{restored['students']} profiles, {restored['enrollments']} "
            f"enrollments, and {restored['user_settings']} settings.",
            parent=self,
        )


if __name__ == "__main__":
    if os.environ.get("EDUTRACK_AUTHENTICATED") != "1":
        from auth_ui import EduTrackLogin

        app = EduTrackLogin()
    else:
        app = EduTrackApp()
    app.mainloop()
