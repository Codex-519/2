"""Modern dark Tkinter desktop interface for Nova."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable


class NovaWindow:
    BG = "#10131a"
    PANEL = "#171c26"
    PANEL_2 = "#1e2532"
    TEXT = "#f2f5f9"
    MUTED = "#96a0b3"
    ACCENT = "#8b7dff"
    GREEN = "#48d597"
    ORANGE = "#ffb86b"

    def __init__(
        self,
        assistant_name: str,
        on_text_submitted: Callable[[str], None],
        on_listening_toggle: Callable[[], None],
        on_settings: Callable[[], None],
        on_close: Callable[[], None],
    ) -> None:
        self.root = tk.Tk()
        self.root.title(f"{assistant_name} — Voice Assistant")
        self.root.geometry("900x680")
        self.root.minsize(700, 520)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<Control-space>", lambda _event: on_listening_toggle())
        self._on_text_submitted = on_text_submitted
        self._on_listening_toggle = on_listening_toggle
        self._on_settings = on_settings
        self._on_close = on_close
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.listening = False
        self._build(assistant_name)
        self.root.after(100, self._drain_events)

    def _build(self, assistant_name: str) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Nova.TButton", background=self.ACCENT, foreground="white", borderwidth=0, padding=(16, 10), font=("Segoe UI", 10, "bold"))
        style.map("Nova.TButton", background=[("active", "#a49aff")])
        style.configure("Nova.Secondary.TButton", background=self.PANEL_2, foreground=self.TEXT, borderwidth=0, padding=(12, 9), font=("Segoe UI", 10))
        style.map("Nova.Secondary.TButton", background=[("active", "#2a3446")])

        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill="x", padx=28, pady=(24, 12))
        tk.Label(header, text=assistant_name, fg=self.TEXT, bg=self.BG, font=("Segoe UI", 25, "bold")).pack(side="left")
        tk.Label(header, text="PERSONAL VOICE ASSISTANT", fg=self.ACCENT, bg=self.BG, font=("Segoe UI", 9, "bold")).pack(side="left", padx=14, pady=(8, 0))
        ttk.Button(header, text="Settings", style="Nova.Secondary.TButton", command=self._on_settings).pack(side="right")

        status_panel = tk.Frame(self.root, bg=self.PANEL, highlightthickness=1, highlightbackground="#252d3a")
        status_panel.pack(fill="x", padx=28, pady=(0, 14))
        self.status_dot = tk.Label(status_panel, text="●", fg=self.GREEN, bg=self.PANEL, font=("Segoe UI", 18))
        self.status_dot.pack(side="left", padx=(16, 6), pady=12)
        self.status_label = tk.Label(status_panel, text="Ready", fg=self.TEXT, bg=self.PANEL, font=("Segoe UI", 11, "bold"))
        self.status_label.pack(side="left", pady=12)
        tk.Label(status_panel, text="Wake word: Hey Nova  •  Ctrl + Space to start/stop", fg=self.MUTED, bg=self.PANEL, font=("Segoe UI", 9)).pack(side="right", padx=16)

        chat_frame = tk.Frame(self.root, bg=self.BG)
        chat_frame.pack(fill="both", expand=True, padx=28)
        self.chat = tk.Text(chat_frame, bg=self.PANEL, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", wrap="word", padx=20, pady=18, font=("Segoe UI", 11), state="disabled")
        self.chat.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(chat_frame, orient="vertical", command=self.chat.yview)
        scrollbar.pack(side="right", fill="y")
        self.chat.configure(yscrollcommand=scrollbar.set)
        self.chat.tag_configure("user_label", foreground="#9d91ff", font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("nova_label", foreground=self.GREEN, font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("body", foreground=self.TEXT, spacing3=12)
        self.chat.tag_configure("muted", foreground=self.MUTED, font=("Segoe UI", 10, "italic"))
        self.add_message("Nova", "Hi, I’m Nova. Say “Hey Nova” or press Ctrl + Space when you want to talk.")

        composer = tk.Frame(self.root, bg=self.BG)
        composer.pack(fill="x", padx=28, pady=(14, 24))
        self.entry = tk.Entry(composer, bg=self.PANEL_2, fg=self.TEXT, insertbackground=self.TEXT, relief="flat", font=("Segoe UI", 11))
        self.entry.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 10))
        self.entry.bind("<Return>", lambda _event: self._submit_text())
        ttk.Button(composer, text="Send", style="Nova.TButton", command=self._submit_text).pack(side="right", padx=(0, 8))
        self.listen_button = ttk.Button(composer, text="Start listening", style="Nova.Secondary.TButton", command=self._on_listening_toggle)
        self.listen_button.pack(side="right")

    def _submit_text(self) -> None:
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.add_message("You", text)
            self._on_text_submitted(text)

    def add_message(self, speaker: str, message: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{speaker}\n", "user_label" if speaker == "You" else "nova_label")
        self.chat.insert("end", f"{message}\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def set_status(self, text: str, color: str | None = None) -> None:
        self.status_label.configure(text=text)
        self.status_dot.configure(fg=color or self.GREEN)

    def set_listening(self, active: bool) -> None:
        self.listening = active
        self.listen_button.configure(text="Stop listening" if active else "Start listening")

    def post(self, event: str, data: object = "") -> None:
        self.events.put((event, data))

    def _drain_events(self) -> None:
        try:
            while True:
                event, data = self.events.get_nowait()
                if event == "status":
                    self.set_status(str(data))
                elif event == "user":
                    self.add_message("You", str(data))
                elif event == "assistant":
                    self.add_message("Nova", str(data))
                elif event == "listening":
                    self.set_listening(bool(data))
                elif event == "error":
                    self.add_message("Nova", str(data))
                    self.set_status("Ready", self.ORANGE)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def show_settings(self, voices: list[dict[str, str]], current_voice: str) -> str | None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Nova voice settings")
        dialog.configure(bg=self.BG)
        dialog.geometry("580x220")
        dialog.transient(self.root)
        tk.Label(dialog, text="Choose a Windows voice", fg=self.TEXT, bg=self.BG, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=24, pady=(22, 6))
        options = [f"{voice['name']}  |  {voice['id']}" for voice in voices]
        variable = tk.StringVar(value=next((item for item in options if current_voice.lower() in item.lower()), options[0] if options else ""))
        combo = ttk.Combobox(dialog, textvariable=variable, values=options, state="readonly", width=68)
        combo.pack(padx=24, fill="x")
        tk.Label(dialog, text="To save this choice permanently, copy the selected voice ID into TTS_VOICE_NAME in .env.", fg=self.MUTED, bg=self.BG, wraplength=520, justify="left").pack(anchor="w", padx=24, pady=14)
        selected: list[str | None] = [None]
        def save() -> None:
            selected[0] = variable.get().split("  |  ", 1)[-1] if variable.get() else None
            dialog.destroy()
        ttk.Button(dialog, text="Use voice for this session", style="Nova.TButton", command=save).pack(anchor="e", padx=24, pady=4)
        self.root.wait_window(dialog)
        return selected[0]

    def _close(self) -> None:
        self._on_close()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()