"""Errors raised by the local conversation provider."""


class ConversationProviderError(RuntimeError):
    """Base class for provider errors safe to display to the user."""


class OllamaConnectionError(ConversationProviderError):
    """Ollama could not be reached or the request timed out."""


class OllamaResponseError(ConversationProviderError):
    """Ollama returned an unsuccessful HTTP response or model error."""


class OllamaProtocolError(ConversationProviderError):
    """Ollama returned an invalid or incomplete streaming response."""
