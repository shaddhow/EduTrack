"""Shared readable typography for the EduTrack desktop interfaces."""

from __future__ import annotations

import customtkinter as ctk
import tkinter as tk


_FONT_SIZE_SCALE = {
    8: 11,
    9: 12,
    10: 13,
    11: 14,
    12: 15,
    13: 16,
    14: 18,
    15: 19,
    16: 20,
    17: 21,
}


def readable_font_size(size: int) -> int:
    """Map compact legacy sizes to legible UI sizes while preserving display fonts."""
    return _FONT_SIZE_SCALE.get(size, size)


def app_font(
    *, size: int, family: str = "Segoe UI", weight: str = "normal"
) -> ctk.CTkFont:
    """Create an application font using the shared accessible size scale."""
    readable_size = readable_font_size(size)
    return ctk.CTkFont(family=family, size=readable_size, weight=weight)


def maximize_window(window: ctk.CTk) -> None:
    """Open fullscreen; bind F11 to toggle and Escape to exit fullscreen."""
    window.update_idletasks()
    screen_geometry = (
        f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}+0+0"
    )
    windowed_geometry = window.geometry()
    fullscreen_supported = True
    is_fullscreen = True
    try:
        window.attributes("-fullscreen", True)
    except tk.TclError:
        fullscreen_supported = False
        window.geometry(screen_geometry)
        try:
            window.state("zoomed")
        except tk.TclError:
            pass

    def enter_fullscreen() -> None:
        nonlocal fullscreen_supported, is_fullscreen
        if fullscreen_supported:
            try:
                window.attributes("-fullscreen", True)
                is_fullscreen = True
                return
            except tk.TclError:
                fullscreen_supported = False
        window.geometry(screen_geometry)
        is_fullscreen = True

    def exit_fullscreen() -> None:
        nonlocal fullscreen_supported, is_fullscreen
        if fullscreen_supported:
            try:
                window.attributes("-fullscreen", False)
                is_fullscreen = False
                try:
                    window.state("zoomed")
                except tk.TclError:
                    window.geometry(windowed_geometry)
                return
            except tk.TclError:
                fullscreen_supported = False
        window.geometry(windowed_geometry)
        is_fullscreen = False

    def toggle_fullscreen(_event: tk.Event | None = None) -> str:
        nonlocal fullscreen_supported, is_fullscreen
        if is_fullscreen:
            exit_fullscreen()
        else:
            enter_fullscreen()
        return "break"

    def escape_fullscreen(_event: tk.Event | None = None) -> str:
        if is_fullscreen:
            exit_fullscreen()
        return "break"

    window.bind_all("<F11>", toggle_fullscreen)
    window.bind_all("<Escape>", escape_fullscreen)
