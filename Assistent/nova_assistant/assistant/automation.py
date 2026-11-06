"""Safe Windows automation. No AI-generated shell commands are ever executed."""

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from config import Settings


@dataclass
class AutomationResult:
    success: bool
    message: str
    needs_confirmation: bool = False


class SafeAutomation:
    """Allowlisted, parameter-validated desktop actions."""

    APP_ALIASES = {
        "chrome": ("chrome.exe", "Chrome"),
        "google chrome": ("chrome.exe", "Chrome"),
        "vs code": ("code.exe", "Visual Studio Code"),
        "vscode": ("code.exe", "Visual Studio Code"),
        "visual studio code": ("code.exe", "Visual Studio Code"),
        "notepad": ("notepad.exe", "Notepad"),
        "calculator": ("calc.exe", "Calculator"),
        "calc": ("calc.exe", "Calculator"),
        "file explorer": ("explorer.exe", "File Explorer"),
        "explorer": ("explorer.exe", "File Explorer"),
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def open_app(self, app_name: str) -> AutomationResult:
        key = app_name.lower().strip()
        if key not in self.APP_ALIASES:
            return AutomationResult(False, f"I don't have permission to open '{app_name}'.")
        executable, display_name = self.APP_ALIASES[key]
        try:
            subprocess.Popen([executable], shell=False)
            return AutomationResult(True, f"Opening {display_name}.")
        except FileNotFoundError:
            return AutomationResult(
                False,
                f"I couldn't find {display_name}. Make sure it is installed and on your Windows PATH.",
            )
        except PermissionError:
            return AutomationResult(False, f"Windows denied access to {display_name}.")
        except OSError as exc:
            return AutomationResult(False, f"I couldn't open {display_name}: {exc}")

    def open_url(self, url: str) -> AutomationResult:
        if not re.match(r"^https?://[^\s]+$", url, flags=re.IGNORECASE):
            return AutomationResult(False, "That doesn't look like a safe web address.")
        try:
            opened = webbrowser.open(url, new=2)
            return AutomationResult(opened, "Opening the website." if opened else "Windows could not open the website.")
        except OSError as exc:
            return AutomationResult(False, f"I couldn't open the website: {exc}")

    def search_web(self, query: str, service: str = "google") -> AutomationResult:
        query = query.strip()
        if not query:
            return AutomationResult(False, "Tell me what you want me to search for.")
        domain = "www.youtube.com/results?search_query=" if service == "youtube" else "www.google.com/search?q="
        return self.open_url(f"https://{domain}{quote_plus(query)}")

    def open_path(self, raw_path: str) -> AutomationResult:
        path = Path(raw_path.strip().strip("\"'")).expanduser()
        if not path.exists():
            return AutomationResult(False, f"I couldn't find {path}.")
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return AutomationResult(True, f"Opening {path.name or path}.")
        except PermissionError:
            return AutomationResult(False, f"Windows denied access to {path}.")
        except OSError as exc:
            return AutomationResult(False, f"I couldn't open that path: {exc}")

    def create_text_file(self, content: str = "") -> AutomationResult:
        folder = self.settings.text_folder
        try:
            folder.mkdir(parents=True, exist_ok=True)
            filename = f"nova_note_{datetime.now():%Y%m%d_%H%M%S}.txt"
            path = folder / filename
            path.write_text(content or "Created by Nova.\n", encoding="utf-8")
            os.startfile(str(path))  # type: ignore[attr-defined]
            return AutomationResult(True, f"I created {filename} in your Nova folder.")
        except PermissionError:
            return AutomationResult(False, "Windows denied permission to create the text file.")
        except OSError as exc:
            return AutomationResult(False, f"I couldn't create the text file: {exc}")

    def read_text_file(self, raw_path: str) -> AutomationResult:
        path = Path(raw_path.strip().strip("\"'")).expanduser()
        if path.suffix.lower() != ".txt":
            return AutomationResult(False, "For safety, I can only read .txt files.")
        if not path.exists() or not path.is_file():
            return AutomationResult(False, f"I couldn't find the text file {path}.")
        try:
            content = path.read_text(encoding="utf-8")
            excerpt = content[:4000] or "The file is empty."
            return AutomationResult(True, f"Here is the file content:\n\n{excerpt}")
        except (PermissionError, UnicodeError, OSError) as exc:
            return AutomationResult(False, f"I couldn't read that text file: {exc}")

    def take_screenshot(self) -> AutomationResult:
        try:
            from PIL import ImageGrab

            folder = self.settings.screenshot_folder_path
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"nova_screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
            image = ImageGrab.grab(all_screens=True)
            image.save(path)
            return AutomationResult(True, f"I saved the screenshot to {path}.")
        except ImportError:
            return AutomationResult(False, "Screenshot support needs Pillow installed.")
        except (PermissionError, OSError) as exc:
            return AutomationResult(False, f"I couldn't take the screenshot: {exc}")

    def media_key(self, key: str) -> AutomationResult:
        if os.name != "nt":
            return AutomationResult(False, "Media keys are available on Windows only.")
        key_codes = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "volume_up": 0xAF, "volume_down": 0xAE}
        code = key_codes.get(key)
        if code is None:
            return AutomationResult(False, "That media action is not allowlisted.")
        try:
            ctypes.windll.user32.keybd_event(code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(code, 0, 2, 0)
            return AutomationResult(True, "Done.")
        except OSError as exc:
            return AutomationResult(False, f"I couldn't send the media key: {exc}")