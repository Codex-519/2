"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    assistant_name: str = os.getenv("ASSISTANT_NAME", "Nova")
    ai_provider: str = os.getenv("AI_PROVIDER", "gemini").lower()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_base_url: str = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    stt_provider: str = os.getenv("STT_PROVIDER", "google").lower()
    stt_language: str = os.getenv("STT_LANGUAGE", "en-IN")
    vosk_model_path: str = os.getenv("VOSK_MODEL_PATH", "")
    listen_seconds: int = _int_env("LISTEN_SECONDS", 5)
    wake_word: str = os.getenv("WAKE_WORD", "hey nova").lower()
    tts_engine: str = os.getenv("TTS_ENGINE", "pyttsx3").lower()
    tts_voice_name: str = os.getenv("TTS_VOICE_NAME", "")
    tts_rate: int = _int_env("TTS_RATE", 175)
    tts_volume: float = _float_env("TTS_VOLUME", 1.0)
    text_file_folder: str = os.getenv("TEXT_FILE_FOLDER", "")
    screenshot_folder: str = os.getenv("SCREENSHOT_FOLDER", "")
    max_memory_turns: int = _int_env("MAX_MEMORY_TURNS", 12)

    @property
    def text_folder(self) -> Path:
        return Path(self.text_file_folder).expanduser() if self.text_file_folder else Path.home() / "Documents" / "Nova"

    @property
    def screenshot_folder_path(self) -> Path:
        return (
            Path(self.screenshot_folder).expanduser()
            if self.screenshot_folder
            else Path.home() / "Pictures" / "Nova"
        )


settings = Settings()