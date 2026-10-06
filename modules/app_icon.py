"""Shared window-icon setup for EduTrack desktop windows."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path


def set_app_icon(window: tk.Tk) -> None:
    """Set the application icon from the packaged PNG and Windows ICO assets."""
    assets = Path(__file__).resolve().parent.parent / "assets"
    icon_image = tk.PhotoImage(file=str(assets / "edutrack-icon.png"))
    window.iconphoto(True, icon_image)
    setattr(window, "_edutrack_icon_image", icon_image)
    if os.name == "nt":
        window.iconbitmap(str(assets / "edutrack-icon.ico"))
