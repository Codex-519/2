"""Explicit installation of the approved local voice runtime and model files."""

from __future__ import annotations

import hashlib
import logging
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from zara_ai.config import VoiceConfig
from zara_ai.voice.interfaces import VoiceSetupError

logger = logging.getLogger(__name__)

_ASR_REPOSITORY = "sakasegawa/Qwen3-ASR-0.6B-GGUF"
_ASR_REVISION = "ee78f8709547f39bea3b924a16c72403826cac92"
_TTS_REPOSITORY = "prasadvittaldev/pocket-tts-hindi-female-syspin"
_TTS_REVISION = "6928c0953a018c65afbdc5b093b1f1d3f4e0a1b3"
_SPEECH_ARCHIVE_URL = (
    "https://github.com/nyosegawa/speech.cpp/releases/download/v0.8.11/"
    "speech-0.8.11-windows-x64-vulkan.zip"
)
_SPEECH_ARCHIVE_SHA256 = (
    "63f4c5b5c60aeab9d4c90193298fe4ee5d2a6c931cdbdcbc8cbb126fbffc56d0"
)
_MODEL_CHECKSUMS = {
    "asr/Qwen3-ASR-0.6B-Q4_K.gguf": (
        "981c7842de271f53684ff83362c4c9a2d84394d4d7acadabddaa1d3a7b51c0fa"
    ),
    "asr/Qwen3-ASR-0.6B-Q4_K.gguf.json": (
        "23ea4edb8a2a3dc970bddbc1e5219aae87d3151f7f57a1f35c8bb5c2083273bf"
    ),
    "tts/model_bf16.safetensors": (
        "f3f2d454a3301cf6986977ee4edbfee5869c294ce6a677ebb331048706325c23"
    ),
    "tts/tokenizer.model": (
        "2da60c2658f2419bd4bed954eaf69f382c58535540d4805bca69787d2e58b493"
    ),
    "tts/voice_prompt.wav": (
        "3f7a638d2cc9d8b624a8bc2a6f03137d2942ec0b8d948339a7a08739fbfc0e15"
    ),
}


def install_voice_assets(config: VoiceConfig, *, output=print) -> None:
    """Download only the approved model files and verified Windows runtime."""
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import HfHubHTTPError
        import yaml
    except ImportError as error:
        raise VoiceSetupError(
            'Install the optional voice dependencies with '
            '`python -m pip install -e ".[voice]"` first.'
        ) from error

    root = config.data_directory
    asr_directory = root / "asr"
    tts_directory = root / "tts"
    runtime_directory = root / "runtime"
    root.mkdir(parents=True, exist_ok=True)
    output("Downloading the approved local Hindi voice assets.")
    try:
        snapshot_download(
            repo_id=_ASR_REPOSITORY,
            revision=_ASR_REVISION,
            allow_patterns=[
                "Qwen3-ASR-0.6B-Q4_K.gguf",
                "Qwen3-ASR-0.6B-Q4_K.gguf.json",
            ],
            local_dir=asr_directory,
        )
        snapshot_download(
            repo_id=_TTS_REPOSITORY,
            revision=_TTS_REVISION,
            allow_patterns=[
                "config.yaml",
                "model_bf16.safetensors",
                "tokenizer.model",
                "voice_prompt.wav",
            ],
            local_dir=tts_directory,
        )
    except (HfHubHTTPError, OSError, ValueError) as error:
        raise VoiceSetupError(
            "Could not download the pinned voice models. Check internet access "
            "and that the approved Hugging Face repositories are available."
        ) from error
    for relative_path, expected_digest in _MODEL_CHECKSUMS.items():
        _verify_checksum(root / relative_path, expected_digest)
    _write_local_tts_config(tts_directory, yaml)
    _install_speech_runtime(runtime_directory)
    output(f"Voice assets installed under {root}.")
    output(
        "Voice remains disabled until [voice].enabled is set to true in "
        "config.toml."
    )


def _write_local_tts_config(tts_directory: Path, yaml: Any) -> None:
    source = tts_directory / "config.yaml"
    weights = tts_directory / "model_bf16.safetensors"
    tokenizer = tts_directory / "tokenizer.model"
    if not source.is_file() or not weights.is_file() or not tokenizer.is_file():
        raise VoiceSetupError(
            f"The Hindi TTS download is incomplete under {tts_directory}."
        )
    try:
        model_config = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise VoiceSetupError(
            f"Could not read the downloaded Hindi TTS config at {source}."
        ) from error
    if not isinstance(model_config, dict):
        raise VoiceSetupError("The downloaded Hindi TTS config is not a YAML map.")

    def replace_paths(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: replace_paths(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace_paths(item) for item in value]
        if isinstance(value, str):
            filename = value.rsplit("/", 1)[-1].split("@", 1)[0]
            if filename in {"model.safetensors", "model_bf16.safetensors"}:
                return str(weights)
            if filename == "tokenizer.model":
                return str(tokenizer)
        return value

    local_config = replace_paths(model_config)
    if not _contains_reference(local_config, str(weights)) or not _contains_reference(
        local_config, str(tokenizer)
    ):
        raise VoiceSetupError(
            "The Hindi TTS config does not expose the expected local weight and "
            "tokenizer paths; refusing to let it download other model files."
        )
    destination = tts_directory / "config.local.yaml"
    temporary = tts_directory / "config.local.yaml.tmp"
    try:
        temporary.write_text(
            yaml.safe_dump(local_config, sort_keys=False),
            encoding="utf-8",
        )
        temporary.replace(destination)
    except OSError as error:
        raise VoiceSetupError(
            f"Could not create the local Hindi TTS config at {destination}."
        ) from error


def _contains_reference(value: Any, reference: str) -> bool:
    if isinstance(value, str):
        return value == reference
    if isinstance(value, dict):
        return any(_contains_reference(item, reference) for item in value.values())
    if isinstance(value, list):
        return any(_contains_reference(item, reference) for item in value)
    return False


def _verify_checksum(path: Path, expected_digest: str) -> None:
    if not path.is_file():
        raise VoiceSetupError(f"Expected voice asset was not downloaded: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as asset:
            for block in iter(lambda: asset.read(1_048_576), b""):
                digest.update(block)
    except OSError as error:
        raise VoiceSetupError(f"Could not verify voice asset {path}.") from error
    if digest.hexdigest() != expected_digest:
        raise VoiceSetupError(
            f"Voice asset checksum did not match the approved pinned file: {path.name}."
        )


def _install_speech_runtime(runtime_directory: Path) -> None:
    if runtime_directory.is_dir() and any(runtime_directory.rglob("speech.exe")):
        logger.info("speech.cpp runtime already exists; reusing it.")
        return

    runtime_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="zara-speech-runtime-", dir=runtime_directory.parent
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        archive_path = temporary_root / "speech-runtime.zip"
        try:
            with urllib.request.urlopen(_SPEECH_ARCHIVE_URL, timeout=60) as response:
                with archive_path.open("wb") as archive_file:
                    shutil.copyfileobj(response, archive_file)
        except OSError as error:
            raise VoiceSetupError(
                "Could not download the approved speech.cpp Windows runtime."
            ) from error

        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if digest != _SPEECH_ARCHIVE_SHA256:
            raise VoiceSetupError(
                "The speech.cpp runtime checksum did not match the verified "
                "v0.8.11 release."
            )
        extraction_directory = temporary_root / "extracted"
        extraction_directory.mkdir()
        try:
            with zipfile.ZipFile(archive_path) as archive:
                _safe_extract(archive, extraction_directory)
        except (OSError, zipfile.BadZipFile, ValueError) as error:
            raise VoiceSetupError(
                "The downloaded speech.cpp runtime archive could not be safely "
                "extracted."
            ) from error
        if not any(extraction_directory.rglob("speech.exe")):
            raise VoiceSetupError(
                "The downloaded speech.cpp runtime did not contain speech.exe."
            )
        for item in extraction_directory.iterdir():
            destination = runtime_directory / item.name
            if destination.exists():
                raise VoiceSetupError(
                    f"Cannot install the runtime because {destination} already exists."
                )
            shutil.move(str(item), str(destination))


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    resolved_destination = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if target != resolved_destination and resolved_destination not in target.parents:
            raise ValueError("Archive contains a path outside its destination.")
    archive.extractall(destination)
