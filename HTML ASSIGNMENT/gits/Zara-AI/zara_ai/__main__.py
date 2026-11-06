"""Small terminal client for exercising the conversation engine."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from zara_ai.config import AppConfig, load_config
from zara_ai.conversation.engine import ConversationEngine
from zara_ai.conversation.errors import ConversationProviderError
from zara_ai.conversation.ollama import OllamaClient
from zara_ai.logging_config import configure_logging
from zara_ai.memory.commands import handle_memory_command
from zara_ai.memory.store import MemoryStore
from zara_ai.voice.interfaces import VoiceError
from zara_ai.voice.service import VoiceSession

logger = logging.getLogger(__name__)


async def _chat(config_path: Path | None) -> int:
    config = load_config(config_path)
    client = OllamaClient(config)
    memory_store = MemoryStore()
    engine = ConversationEngine(client, memory_store)
    print(f"Zara AI - model: {config.ollama.model}")
    print(
        "Type /exit to quit. Use /memory for memory controls. "
        "Use /voice for one push-to-talk Hindi voice turn. "
        "Press Ctrl+C to interrupt and exit.\n"
    )
    try:
        while True:
            try:
                prompt = input("You: ")
            except EOFError:
                break
            if prompt.strip().lower() in {"/exit", "/quit"}:
                break
            if handle_memory_command(prompt, memory_store):
                continue
            if prompt.strip().casefold() == "/voice":
                if not config.voice.enabled:
                    print(
                        "Voice is disabled. Set [voice].enabled = true in "
                        "config.toml and restart."
                    )
                    continue
                print("Starting one local push-to-talk turn.")
                try:
                    voice_session = _create_voice_session(config, engine)
                    await voice_session.run_turn()
                    print()
                except asyncio.CancelledError:
                    print("\n[Voice turn interrupted.]")
                except KeyboardInterrupt:
                    print("\n[Voice turn interrupted.]")
                except VoiceError as error:
                    logger.error("Voice turn failed: %s", error)
                    print(f"\n[Voice error: {error}]")
                continue
            if not prompt.strip():
                continue

            print("Zara: ", end="", flush=True)
            try:
                async for chunk in engine.stream(prompt):
                    print(chunk, end="", flush=True)
                print()
            except ConversationProviderError as error:
                print(f"\n[Error: {error}]")
            except asyncio.CancelledError:
                print("\n[Response interrupted; exiting.]")
                return 130
            except KeyboardInterrupt:
                engine.interrupt()
                print("\n[Response interrupted; exiting.]")
                return 130
    finally:
        await client.aclose()
    return 0


def _create_voice_session(
    config: AppConfig, engine: ConversationEngine
) -> VoiceSession:
    from zara_ai.voice.backends import (
        MicrophoneRecorder,
        PocketHindiSynthesizer,
        SoundDevicePlayer,
        SpeechCppRecognizer,
    )

    response_started = False

    def print_response_chunk(chunk: str) -> None:
        nonlocal response_started
        if not response_started:
            print("Zara: ", end="", flush=True)
            response_started = True
        print(chunk, end="", flush=True)

    def announce_voice_state(state: str) -> None:
        logger.info("Voice state changed to %s.", state)
        labels = {
            "transcribing": "Transcribing locally...",
            "thinking": "Zara is thinking...",
            "speaking": "Preparing or playing Hindi speech...",
        }
        label = labels.get(state)
        if label:
            print(f"\n[{label}]", flush=True)

    return VoiceSession(
        engine,
        MicrophoneRecorder(config.voice.max_record_seconds),
        SpeechCppRecognizer(config.voice),
        PocketHindiSynthesizer(config.voice),
        SoundDevicePlayer(),
        on_state=announce_voice_state,
        on_transcript=lambda transcript: print(f"\nYou (voice): {transcript}"),
        on_response_chunk=print_response_chunk,
        on_notice=lambda notice: print(f"\n[Voice: {notice}]"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with a local Ollama model.")
    parser.add_argument(
        "--config",
        type=Path,
        help="Use a specific TOML configuration file.",
    )
    parser.add_argument(
        "--setup-voice",
        action="store_true",
        help="Download the approved local voice runtime and Hindi models.",
    )
    args = parser.parse_args()
    log_path = configure_logging()
    logger.info("Zara AI conversation engine starting.")
    try:
        if args.setup_voice:
            from zara_ai.voice.setup import install_voice_assets

            install_voice_assets(load_config(args.config).voice)
            exit_code = 0
        else:
            exit_code = asyncio.run(_chat(args.config))
    except KeyboardInterrupt:
        exit_code = 130
    except (OSError, ValueError, RuntimeError) as error:
        logger.exception("Could not start Zara AI.")
        print(f"Could not start Zara AI: {error}")
        exit_code = 1
    logger.info("Zara AI conversation engine stopping.")
    if exit_code:
        raise SystemExit(exit_code)
    print(f"\nLog file: {log_path}")


if __name__ == "__main__":
    main()
