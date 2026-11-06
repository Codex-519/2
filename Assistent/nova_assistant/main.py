"""Nova entry point."""

from __future__ import annotations

import threading

from assistant.automation import SafeAutomation
from assistant.brain import AssistantBrain, AIProviderError
from assistant.commands import CommandRouter
from assistant.speech_to_text import MicrophoneWorker, SpeechRecognitionError, SpeechToText
from assistant.text_to_speech import TextToSpeech, TextToSpeechError
from config import settings
from ui.window import NovaWindow


class NovaApp:
    def __init__(self) -> None:
        self.brain = AssistantBrain(settings)
        self.automation = SafeAutomation(settings)
        self.router = CommandRouter(self.automation, settings.assistant_name)
        self.stt = SpeechToText(
            provider=settings.stt_provider,
            language=settings.stt_language,
            listen_seconds=settings.listen_seconds,
            vosk_model_path=settings.vosk_model_path,
        )
        self.tts = TextToSpeech(
            engine_name=settings.tts_engine,
            voice_name=settings.tts_voice_name,
            rate=settings.tts_rate,
            volume=settings.tts_volume,
        )
        self.microphone = MicrophoneWorker(self.stt)
        self.window = NovaWindow(
            assistant_name=settings.assistant_name,
            on_text_submitted=self.handle_text,
            on_listening_toggle=self.toggle_listening,
            on_settings=self.open_settings,
            on_close=self.shutdown,
        )

    def start(self) -> None:
        # Start in passive wake-word mode. The button/keyboard can stop this
        # and start one-command manual listening without changing the worker.
        self.microphone.start(
            start_armed=True,
            wake_word=settings.wake_word,
            on_wake=lambda: self.window.post("status", "Listening..."),
            on_command=self._handle_voice_command,
            on_error=lambda message: self.window.post("error", message),
        )
        self.window.post("status", f"Listening for “{settings.wake_word}”...")
        self.window.post("listening", True)
        self.window.run()

    def toggle_listening(self) -> None:
        if self.microphone.thread and self.microphone.thread.is_alive():
            self.microphone.stop()
            self.window.post("status", "Ready")
            self.window.post("listening", False)
            return
        self.microphone.start(
            start_armed=False,
            wake_word=settings.wake_word,
            on_wake=lambda: self.window.post("status", "Listening..."),
            on_command=self._handle_voice_command,
            on_error=lambda message: self.window.post("error", message),
        )
        self.window.post("status", "Listening...")
        self.window.post("listening", True)

    def _handle_voice_command(self, text: str) -> None:
        self.window.post("user", text)
        self.handle_text(text, already_displayed=True)

    def handle_text(self, text: str, already_displayed: bool = False) -> None:
        threading.Thread(
            target=self._process_text,
            args=(text, already_displayed),
            daemon=True,
            name="nova-response",
        ).start()

    def _process_text(self, text: str, already_displayed: bool) -> None:
        self.window.post("status", "Thinking...")
        intent = self.router.detect(text)
        if intent:
            result = self.router.run(intent)
            response = result.message
        else:
            try:
                response = self.brain.ask(text)
            except AIProviderError as exc:
                response = str(exc)
        self.window.post("assistant", response)
        self.window.post("status", "Speaking...")
        try:
            self.tts.speak(response)
        except TextToSpeechError as exc:
            self.window.post("error", str(exc))
        finally:
            self.window.post("status", "Listening for “Hey Nova”..." if self.microphone.thread and self.microphone.thread.is_alive() else "Ready")

    def open_settings(self) -> None:
        try:
            voices = self.tts.available_voices()
            selected = self.window.show_settings(voices, settings.tts_voice_name)
            if selected:
                self.tts.voice_name = selected
                self.window.post("assistant", f"I’ll use the {selected} voice for this session.")
        except TextToSpeechError as exc:
            self.window.post("error", str(exc))

    def shutdown(self) -> None:
        self.microphone.stop()


if __name__ == "__main__":
    try:
        NovaApp().start()
    except KeyboardInterrupt:
        pass