"""Bilingual/Hinglish command recognition without executing model-generated code."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from assistant.automation import AutomationResult, SafeAutomation


@dataclass
class CommandIntent:
    name: str
    args: dict[str, Any]


class CommandRouter:
    def __init__(self, automation: SafeAutomation, assistant_name: str = "Nova") -> None:
        self.automation = automation
        self.assistant_name = assistant_name

    def detect(self, text: str) -> CommandIntent | None:
        normalized = " ".join(text.lower().strip().split())
        if not normalized:
            return None

        if re.search(r"\b(chrome|google chrome)\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
            return CommandIntent("open_app", {"app": "chrome"})
        if re.search(r"\b(vs code|vscode|visual studio code)\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
            return CommandIntent("open_app", {"app": "vs code"})
        if re.search(r"\b(notepad)\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
            return CommandIntent("open_app", {"app": "notepad"})
        if re.search(r"\b(calculator|calc)\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
            return CommandIntent("open_app", {"app": "calculator"})
        if re.search(r"\b(file explorer|explorer)\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
            return CommandIntent("open_app", {"app": "file explorer"})
        if re.search(r"\b(you tube|youtube)\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
            return CommandIntent("open_url", {"url": "https://www.youtube.com"})
        if re.search(r"\bgoogle\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
            return CommandIntent("open_url", {"url": "https://www.google.com"})
        if re.search(r"\bhub\b", normalized) and re.search(r"\b(open|kholo|khol|launch|chalao)\b", normalized):
                    return CommandIntent("open_url", {"url": "https://xhamster.desi › tags › pornhub-com"})

        for service, platform_pattern in (("youtube", r"youtube|you tube"), ("google", r"google|गूगल")):
            platform = re.search(platform_pattern, normalized)
            if platform and re.search(r"\b(search|dhundo|dhoondo|talash)\b", normalized):
                query = self._search_query(normalized[platform.end() :])
                if query:
                    return CommandIntent("search", {"service": service, "query": query})
        search = re.search(
            r"(?:search|find|dhundo|dhoondo|talash)\s+"
            r"(?:(?:on|in|par|pe)\s+)?(?:(?:google|youtube)\s+)?"
            r"(?:(?:for|par|pe|me)\s+)?(.+)",
            normalized,
        )
        if search:
            query = self._search_query(search.group(1))
            if query:
                service = "youtube" if "youtube" in normalized else "google"
                return CommandIntent("search", {"service": service, "query": query})

        if re.search(r"(?:date|tarikh|तारीख).{0,30}(?:today|aaj|kya|what)", normalized) or re.search(
            r"\b(what is|batao).{0,20}(?:date|tarikh)", normalized
        ):
            return CommandIntent("date_time", {})
        if re.search(r"\b(time|samay|waqt)\b", normalized) and re.search(r"\b(what|kya|batao|current|abhi)\b", normalized):
            return CommandIntent("date_time", {})

        if re.search(
            r"(?:(?:create|make|bana|banao).{0,40}(?:text file|file|txt)"
            r"|(?:text file|file|txt).{0,40}(?:bana|banao|create|make))",
            normalized,
        ):
            content_match = re.search(r"(?:saying|with|jisme|content)\s+(.+)", normalized)
            return CommandIntent("create_text", {"content": content_match.group(1) if content_match else ""})
        if re.search(r"(?:read|padho|padh).{0,20}(?:text file|file)", normalized):
            path_match = re.search(r"(?:file|path)\s+(.+)", text, re.IGNORECASE)
            return CommandIntent("read_text", {"path": path_match.group(1) if path_match else ""})
        if re.search(r"(?:screenshot|screen shot|screen capture|स्क्रीनशॉट)", normalized):
            return CommandIntent("screenshot", {})

        media_terms = {
            "play_pause": r"(?:play|pause|play pause|chalao|rok do|रोक)",
            "next": r"(?:next|agla|अगला)",
            "previous": r"(?:previous|pichla|पिछला)",
            "volume_up": r"(?:volume up|awaaz badha|आवाज़ बढ़ा)",
            "volume_down": r"(?:volume down|awaaz kam|आवाज़ कम)",
        }
        for action, pattern in media_terms.items():
            if re.search(pattern, normalized):
                return CommandIntent("media", {"key": action})

        return None

    @staticmethod
    def _search_query(raw: str) -> str:
        """Remove conversational filler while keeping the user's full query."""
        query = re.sub(r"^(?:on|in|par|pe|me|for)\s+", "", raw.strip())
        query = re.sub(r"\b(?:search|dhundo|dhoondo|talash)\b", " ", query)
        query = re.sub(r"\b(?:karo|kar do|please|do)\b", " ", query)
        return " ".join(query.split()).strip(" .,!?'\"")

    def run(self, intent: CommandIntent) -> AutomationResult:
        if intent.name == "open_app":
            return self.automation.open_app(intent.args["app"])
        if intent.name == "open_url":
            result = self.automation.open_url(intent.args["url"])
            if result.success:
                result.message = "Opening the website."
            return result
        if intent.name == "search":
            return self.automation.search_web(intent.args["query"], intent.args["service"])
        if intent.name == "date_time":
            now = datetime.now()
            return AutomationResult(True, f"It is {now:%A, %d %B %Y}, {now:%I:%M %p}.")
        if intent.name == "create_text":
            return self.automation.create_text_file(intent.args.get("content", ""))
        if intent.name == "read_text":
            path = str(intent.args.get("path", "")).strip()
            if not path:
                return AutomationResult(False, "Please say the full path of the .txt file.")
            return self.automation.read_text_file(path)
        if intent.name == "screenshot":
            return self.automation.take_screenshot()
        if intent.name == "media":
            return self.automation.media_key(intent.args["key"])
        return AutomationResult(False, "I don't know how to perform that action safely.")