"""EduTrack sign-in window backed by the initialized local SQLite database.

Fresh installations include a demo student and faculty account. Both use
``EduTrack2026!`` as the initial demo password; change those credentials before
using real student data.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import customtkinter as ctk

from modules.typography import app_font, maximize_window


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class EduTrackLogin(ctk.CTk):
    """Dark-themed local sign-in screen that launches the main dashboard."""

    COLORS = {
        "background": "#080F1D",
        "panel": "#101A2B",
        "panel_light": "#14233A",
        "border": "#263750",
        "text": "#F4F7FC",
        "muted": "#91A2B9",
        "blue": "#3B82F6",
        "cyan": "#38BDF8",
        "red": "#FB7185",
        "green": "#34D399",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("EduTrack | Sign in")
        self.geometry("1030x680")
        self.minsize(900, 610)
        maximize_window(self)
        self.configure(fg_color=self.COLORS["background"])

        self.grid_columnconfigure(0, weight=11)
        self.grid_columnconfigure(1, weight=9)
        self.grid_rowconfigure(0, weight=1)
        self._build_brand_panel()
        self._build_login_panel()
        self.bind("<Return>", lambda _event: self._authenticate())

    def _build_brand_panel(self) -> None:
        panel = ctk.CTkFrame(
            self,
            fg_color=self.COLORS["panel"],
            corner_radius=0,
        )
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        brand = ctk.CTkFrame(panel, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=44, pady=(36, 0))
        mark = ctk.CTkFrame(
            brand,
            width=44,
            height=44,
            corner_radius=13,
            fg_color=self.COLORS["blue"],
        )
        mark.pack(side="left", padx=(0, 12))
        mark.pack_propagate(False)
        ctk.CTkLabel(
            mark,
            text="E",
            font=app_font(family="Segoe UI", size=24, weight="bold"),
            text_color="white",
        ).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(
            brand,
            text="EduTrack",
            font=app_font(family="Segoe UI", size=23, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(side="left")

        message = ctk.CTkFrame(panel, fg_color="transparent")
        message.grid(row=1, column=0, sticky="w", padx=44, pady=(70, 24))
        ctk.CTkLabel(
            message,
            text="YOUR NEXT CHAPTER,\nBY THE NUMBERS.",
            justify="left",
            font=app_font(family="Segoe UI", size=32, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            message,
            text="Understand your progress. Set a clear goal.\nMake every semester move you forward.",
            justify="left",
            font=app_font(family="Segoe UI", size=13),
            text_color=self.COLORS["muted"],
        ).pack(anchor="w", pady=(13, 0))

        visual = ctk.CTkFrame(
            panel,
            fg_color=self.COLORS["panel_light"],
            corner_radius=18,
            border_width=1,
            border_color=self.COLORS["border"],
        )
        visual.grid(row=2, column=0, sticky="nsew", padx=44, pady=(0, 30))
        visual.grid_columnconfigure(0, weight=1)
        visual.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            visual,
            text="ACADEMIC TRAJECTORY",
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLORS["muted"],
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 10))
        chart = ctk.CTkCanvas(
            visual,
            height=220,
            background=self.COLORS["panel_light"],
            highlightthickness=0,
            bd=0,
        )
        chart.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        chart.bind("<Configure>", lambda _event: self._draw_trajectory(chart))
        self._draw_trajectory(chart)
        stats = ctk.CTkFrame(visual, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="ew", padx=22, pady=(8, 20))
        for column in range(3):
            stats.grid_columnconfigure(column, weight=1, uniform="stat")
        for column, (value, label) in enumerate(
            (("4.00", "GPA CEILING"), ("142", "CREDIT PLAN"), ("1", "CLEAR DIRECTION"))
        ):
            item = ctk.CTkFrame(stats, fg_color="transparent")
            item.grid(row=0, column=column, sticky="ew", padx=(0, 10))
            ctk.CTkLabel(
                item,
                text=value,
                font=app_font(family="Segoe UI", size=17, weight="bold"),
                text_color=self.COLORS["text"],
            ).pack(anchor="center", pady=(0, 4))
            ctk.CTkLabel(
                item,
                text=label,
                font=app_font(family="Segoe UI", size=8, weight="bold"),
                text_color=self.COLORS["muted"],
                justify="center",
                wraplength=115,
            ).pack(anchor="center")
        ctk.CTkLabel(
            panel,
            text="BUBT  ·  COMPUTER SCIENCE & ENGINEERING",
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLORS["muted"],
        ).grid(row=3, column=0, sticky="w", padx=44, pady=(0, 24))

    def _draw_trajectory(self, chart: ctk.CTkCanvas) -> None:
        chart.delete("all")
        width = max(chart.winfo_width(), 300)
        height = max(chart.winfo_height(), 150)
        left, right = 42, width - 20
        top, bottom = 20, height - 37
        for index in range(5):
            value = 4 - index
            y = top + index * (bottom - top) / 4
            chart.create_line(
                left, y, right, y, fill=self.COLORS["border"], width=1
            )
            chart.create_text(
                left - 9,
                y,
                text=f"{value}.0",
                fill=self.COLORS["muted"],
                font=("Segoe UI", 9),
                anchor="e",
            )
        chart.create_line(left, top, left, bottom, fill=self.COLORS["border"], width=1)
        chart.create_line(
            left, bottom, right, bottom, fill=self.COLORS["border"], width=1
        )
        values = (0.16, 0.30, 0.28, 0.51, 0.66, 0.88)
        points = [
            (
                left + index * (right - left) / (len(values) - 1),
                bottom - value * (bottom - top),
            )
            for index, value in enumerate(values)
        ]
        for index, (x, _y) in enumerate(points):
            chart.create_text(
                x,
                bottom + 15,
                text=f"S{index + 1}",
                fill=self.COLORS["muted"],
                font=("Segoe UI", 9),
                anchor="n",
            )
        chart.create_line(
            *[coordinate for point in points for coordinate in point],
            fill=self.COLORS["cyan"],
            width=3,
            smooth=True,
            splinesteps=24,
        )
        for index, (x, y) in enumerate(points):
            radius = 5 if index == len(points) - 1 else 3
            chart.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=self.COLORS["cyan"],
                outline=self.COLORS["panel_light"],
                width=2,
            )
        last_x, last_y = points[-1]
        chart.create_text(
            last_x - 8,
            max(top + 10, last_y - 12),
            text=f"{values[-1] * 4:.2f}",
            fill=self.COLORS["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="e",
        )

    def _build_login_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=self.COLORS["background"], corner_radius=0)
        panel.grid(row=0, column=1, sticky="nsew", padx=48)
        panel.grid_columnconfigure(0, weight=1)

        form = ctk.CTkFrame(panel, fg_color="transparent")
        form.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92)
        ctk.CTkLabel(
            form,
            text="WELCOME BACK",
            font=app_font(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLORS["cyan"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            form,
            text="Sign in to EduTrack",
            font=app_font(family="Segoe UI", size=27, weight="bold"),
            text_color=self.COLORS["text"],
        ).pack(anchor="w", pady=(7, 4))
        ctk.CTkLabel(
            form,
            text="Your academic workspace is ready.",
            font=app_font(family="Segoe UI", size=11),
            text_color=self.COLORS["muted"],
        ).pack(anchor="w", pady=(0, 24))

        self._field_label(form, "ROLE")
        self.role = ctk.CTkOptionMenu(
            form,
            values=["Student", "Faculty"],
            height=42,
            corner_radius=10,
            fg_color=self.COLORS["panel_light"],
            button_color=self.COLORS["blue"],
            button_hover_color="#2563EB",
            dropdown_fg_color=self.COLORS["panel"],
            font=app_font(family="Segoe UI", size=11),
        )
        self.role.pack(fill="x", pady=(0, 16))

        self._field_label(form, "STUDENT / FACULTY ID")
        self.user_id = ctk.CTkEntry(
            form,
            height=44,
            corner_radius=10,
            border_width=1,
            border_color=self.COLORS["border"],
            placeholder_text="Enter your institutional ID",
            font=app_font(family="Segoe UI", size=11),
        )
        self.user_id.pack(fill="x", pady=(0, 16))
        self.user_id.insert(0, "20255103311")

        self._field_label(form, "PASSWORD")
        self.password = ctk.CTkEntry(
            form,
            height=44,
            corner_radius=10,
            border_width=1,
            border_color=self.COLORS["border"],
            placeholder_text="Enter your password",
            show="*",
            font=app_font(family="Segoe UI", size=11),
        )
        self.password.pack(fill="x", pady=(0, 8))

        self.status = ctk.CTkLabel(
            form,
            text="",
            height=30,
            anchor="w",
            wraplength=350,
            justify="left",
            font=app_font(family="Segoe UI", size=10),
            text_color=self.COLORS["red"],
        )
        self.status.pack(fill="x", pady=(0, 6))

        self.login_button = ctk.CTkButton(
            form,
            text="Sign in to your workspace   →",
            height=46,
            corner_radius=11,
            font=app_font(family="Segoe UI", size=12, weight="bold"),
            command=self._authenticate,
        )
        self.login_button.pack(fill="x")

        ctk.CTkLabel(
            form,
            text="Demo access: enter any ID and password to continue.",
            font=app_font(family="Segoe UI", size=9),
            text_color=self.COLORS["muted"],
            wraplength=350,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))

    @staticmethod
    def _field_label(parent: ctk.CTkFrame, text: str) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=app_font(family="Segoe UI", size=9, weight="bold"),
            text_color="#B6C3D5",
        ).pack(anchor="w", pady=(0, 7))

    def _authenticate(self) -> None:
        user_id = self.user_id.get().strip()
        password = self.password.get()
        role = self.role.get()
        if not user_id or not password:
            self._show_status(
                "Enter both your institutional ID and password.",
                self.COLORS["red"],
            )
            return

        display_name = "Faculty Member" if role == "Faculty" else "CSE Student"
        launch_env = os.environ.copy()
        launch_env["EDUTRACK_USER_ID"] = user_id
        launch_env["EDUTRACK_USER_NAME"] = display_name
        launch_env["EDUTRACK_USER_ROLE"] = role
        launch_env["EDUTRACK_AUTHENTICATED"] = "1"
        dashboard_path = Path(__file__).with_name("main.py")
        try:
            subprocess.Popen(
                [sys.executable, str(dashboard_path)],
                cwd=str(dashboard_path.parent),
                env=launch_env,
            )
        except OSError as exc:
            self._show_status(
                f"Could not start the dashboard: {exc}",
                self.COLORS["red"],
            )
            return
        self.destroy()

    def _show_status(self, text: str, color: str) -> None:
        self.status.configure(text=text, text_color=color)


if __name__ == "__main__":
    app = EduTrackLogin()
    app.mainloop()
