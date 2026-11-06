"""Configuration loading and local configuration-file creation."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = """\
[ollama]
base_url = "http://127.0.0.1:11434"
model = "qwen2.5:7b"
request_timeout_seconds = 300

[generation]
temperature = 0.7
num_ctx = 4096

[voice]
enabled = false
max_record_seconds = 60
"""


@dataclass(frozen=True, slots=True)
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:7b"
    request_timeout_seconds: float = 300


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    temperature: float = 0.7
    num_ctx: int = 4096


def default_voice_data_directory() -> Path:
    """Return the per-user directory for optional voice models and runtime."""
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base_directory = (
            Path(local_app_data)
            if local_app_data
            else Path.home() / "AppData" / "Local"
        )
        return base_directory / "ZaraAI" / "voice"

    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home) / "zara-ai" / "voice"
    return Path.home() / ".local" / "share" / "zara-ai" / "voice"


def default_voice_reference_wav() -> Path:
    """Return the bundled reference voice WAV."""
    project_root = Path(__file__).resolve().parent.parent
    return project_root / "assets" / "voice_samples" / "speech-1792953435497.wav"


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    enabled: bool = False
    max_record_seconds: int = 60
    data_directory: Path = field(default_factory=default_voice_data_directory)
    reference_wav: Path = field(default_factory=default_voice_reference_wav)


@dataclass(frozen=True, slots=True)
class AppConfig:
    ollama: OllamaConfig = OllamaConfig()
    generation: GenerationConfig = GenerationConfig()
    voice: VoiceConfig = field(default_factory=VoiceConfig)


def default_config_path() -> Path:
    """Return the per-user configuration path for the current platform."""
    if os.name == "nt":
        app_data = os.environ.get("APPDATA")
        if not app_data:
            raise RuntimeError("APPDATA is not set; cannot locate Zara AI config.")
        return Path(app_data) / "ZaraAI" / "config.toml"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "zara-ai" / "config.toml"
    return Path.home() / ".config" / "zara-ai" / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    """Load TOML configuration and apply documented environment overrides."""
    config_path = path or default_config_path()
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")

    with config_path.open("rb") as config_file:
        raw: dict[str, Any] = tomllib.load(config_file)

    ollama_values = raw.get("ollama", {})
    generation_values = raw.get("generation", {})
    voice_values = raw.get("voice", {})
    default_ollama = OllamaConfig()
    default_generation = GenerationConfig()
    default_voice = VoiceConfig()
    ollama = OllamaConfig(
        base_url=os.environ.get(
            "ZARA_OLLAMA_BASE_URL",
            str(ollama_values.get("base_url", default_ollama.base_url)),
        ).rstrip("/"),
        model=os.environ.get(
            "ZARA_OLLAMA_MODEL",
            str(ollama_values.get("model", default_ollama.model)),
        ),
        request_timeout_seconds=float(
            ollama_values.get(
                "request_timeout_seconds",
                default_ollama.request_timeout_seconds,
            )
        ),
    )
    generation = GenerationConfig(
        temperature=float(
            generation_values.get("temperature", default_generation.temperature)
        ),
        num_ctx=int(generation_values.get("num_ctx", default_generation.num_ctx)),
    )
    voice_enabled = voice_values.get("enabled", default_voice.enabled)
    if not isinstance(voice_enabled, bool):
        raise ValueError("voice.enabled must be true or false.")
    voice_directory = voice_values.get(
        "data_directory", str(default_voice.data_directory)
    )
    if not isinstance(voice_directory, str) or not voice_directory.strip():
        raise ValueError("voice.data_directory must be a non-empty path.")
    reference_wav_value = voice_values.get(
        "reference_wav", str(default_voice.reference_wav)
    )
    if not isinstance(reference_wav_value, str) or not reference_wav_value.strip():
        raise ValueError("voice.reference_wav must be a non-empty path.")
    reference_wav = Path(
        os.path.expandvars(reference_wav_value)
    ).expanduser()
    if not reference_wav.is_absolute():
        reference_wav = config_path.resolve().parent / reference_wav
    voice = VoiceConfig(
        enabled=voice_enabled,
        max_record_seconds=int(
            voice_values.get(
                "max_record_seconds", default_voice.max_record_seconds
            )
        ),
        data_directory=Path(os.path.expandvars(voice_directory)).expanduser(),
        reference_wav=reference_wav.resolve(),
    )
    _validate_config(ollama, generation, voice)
    return AppConfig(ollama=ollama, generation=generation, voice=voice)


def _validate_config(
    ollama: OllamaConfig,
    generation: GenerationConfig,
    voice: VoiceConfig,
) -> None:
    if not ollama.base_url.startswith(("http://", "https://")):
        raise ValueError("Ollama base_url must use http:// or https://.")
    if not ollama.model.strip():
        raise ValueError("Ollama model must not be empty.")
    if ollama.request_timeout_seconds <= 0:
        raise ValueError("request_timeout_seconds must be greater than zero.")
    if not 0 <= generation.temperature <= 2:
        raise ValueError("temperature must be between 0 and 2.")
    if generation.num_ctx <= 0:
        raise ValueError("num_ctx must be greater than zero.")
    if not 1 <= voice.max_record_seconds <= 300:
        raise ValueError("voice.max_record_seconds must be between 1 and 300.")
