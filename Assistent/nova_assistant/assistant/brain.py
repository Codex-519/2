"""Provider-neutral AI response layer, with Gemini as the default provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import requests

from config import Settings
from assistant.memory import ConversationMemory


SYSTEM_PROMPT = """You are Nova, a warm and capable personal voice assistant.
Speak naturally and concisely unless the user asks for detail. Support English,
Hindi, and Hinglish. Reply in the same language style as the user whenever
possible. Use Devanagari when the user uses Hindi, and simple Roman Hindi for
Hinglish. Never claim that you opened an app or performed an action unless the
desktop automation layer explicitly reports that it succeeded. You cannot
access private accounts, change passwords, disable security tools, or run
arbitrary commands. If asked to do something unsafe or unavailable, say so
clearly and suggest a safe alternative."""


class AIProvider(Protocol):
    def reply(self, messages: list[dict[str, str]]) -> str:
        """Return a response or raise a provider-specific exception."""


class AIProviderError(RuntimeError):
    """A user-facing AI provider failure."""


@dataclass
class GeminiProvider:
    settings: Settings

    def reply(self, messages: list[dict[str, str]]) -> str:
        if not self.settings.gemini_api_key:
            raise AIProviderError(
                "Gemini is not configured yet. Add GEMINI_API_KEY to your local .env file."
            )

        contents = [
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{"text": message["content"]}],
            }
            for message in messages
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.6,
                "maxOutputTokens": 8192,
            },
        }
        endpoint = (
            f"{self.settings.gemini_base_url}/models/"
            f"{self.settings.gemini_model}:generateContent"
        )
        try:
            response = requests.post(
                endpoint,
                params={"key": self.settings.gemini_api_key},
                json=payload,
                timeout=90,
            )
            if response.status_code in {401, 403}:
                raise AIProviderError(
                    "Gemini rejected the API key. Check GEMINI_API_KEY in your local .env file."
                )
            response.raise_for_status()
            data = response.json()
            answer = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            if not answer:
                feedback = data.get("promptFeedback", {})
                raise AIProviderError(
                    "Gemini did not return a response."
                    + (f" Safety feedback: {feedback}" if feedback else "")
                )
            return answer
        except AIProviderError:
            raise
        except requests.RequestException as exc:
            raise AIProviderError(
                "I can't reach Gemini right now. Check your internet connection "
                "and GEMINI_API_KEY."
            ) from exc
        except (ValueError, KeyError, IndexError, AttributeError) as exc:
            raise AIProviderError("Gemini returned an unexpected response.") from exc


@dataclass
class OllamaProvider:
    settings: Settings

    def reply(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            "stream": False,
            "options": {"temperature": 0.6},
        }
        try:
            response = requests.post(
                f"{self.settings.ollama_url}/api/chat",
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("message", {}).get("content", "").strip()
            if not answer:
                raise AIProviderError("Ollama returned an empty response.")
            return answer
        except requests.RequestException as exc:
            raise AIProviderError(
                f"I can't reach Ollama right now. Start Ollama and make sure "
                f"the '{self.settings.ollama_model}' model is installed."
            ) from exc
        except (ValueError, KeyError) as exc:
            raise AIProviderError("Ollama returned an unexpected response.") from exc


class AssistantBrain:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory = ConversationMemory(settings.max_memory_turns)
        self.provider = self._build_provider()

    def _build_provider(self) -> AIProvider:
        if self.settings.ai_provider == "gemini":
            return GeminiProvider(self.settings)
        if self.settings.ai_provider == "ollama":
            return OllamaProvider(self.settings)
        raise AIProviderError(
            f"Unsupported AI_PROVIDER '{self.settings.ai_provider}'. "
            "Use AI_PROVIDER=gemini or AI_PROVIDER=ollama."
        )

    def ask(self, user_text: str) -> str:
        self.memory.add("user", user_text)
        try:
            answer = self.provider.reply(self.memory.as_dicts())
        except AIProviderError:
            # Keep the user's message in context, but don't add an error as if
            # it was generated by the model.
            raise
        self.memory.add("assistant", answer)
        return answer