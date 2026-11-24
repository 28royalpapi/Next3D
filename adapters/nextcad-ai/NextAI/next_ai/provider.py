"""Local-only OpenAI-compatible client for the shared Ollama service."""
from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from urllib.parse import urlsplit

DEFAULT_ENDPOINT = "http://127.0.0.1:11434/v1/chat/completions"
DEFAULT_MODEL = "hf.co/turintech/Qwen3.5-0.8B-Artemis-GGUF:Q4_K_M"
MINIMUM_OLLAMA_VERSION = (0, 40, 11)
MAX_REQUEST_BYTES = 16_000_000
MAX_RESPONSE_BYTES = 2_000_000
MAX_STATUS_BYTES = 1_000_000


class ProviderError(RuntimeError):
    """The local model could not complete a request."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _validated_endpoint(endpoint: str = DEFAULT_ENDPOINT) -> str:
    parts = urlsplit(endpoint)
    if (
        parts.scheme != "http"
        or parts.hostname != "127.0.0.1"
        or parts.port != 11434
        or parts.path != "/v1/chat/completions"
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ProviderError("NextAI only connects to the local model at 127.0.0.1:11434.")
    return endpoint


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(value))
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


def _local_get(path: str) -> dict:
    if path not in {"/api/version", "/api/tags"}:
        raise ProviderError("NextAI requested an unsupported local runtime status path.")
    request = Request(
        "http://127.0.0.1:11434" + path,
        headers={"Accept": "application/json"},
        method="GET",
    )
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=5) as response:
            raw = response.read(MAX_STATUS_BYTES + 1)
    except (HTTPError, URLError, OSError) as exc:
        raise ProviderError(
            "Ollama is not responding on 127.0.0.1:11434. Start the local Ollama service first."
        ) from exc
    if len(raw) > MAX_STATUS_BYTES:
        raise ProviderError("The local model service returned an oversized status response.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProviderError("The local model service returned invalid status data.") from exc
    if not isinstance(value, dict):
        raise ProviderError("The local model service returned an invalid status object.")
    return value


def runtime_status() -> dict:
    """Check the local Ollama version and whether the selected multimodal model is installed."""
    version_payload = _local_get("/api/version")
    version = str(version_payload.get("version", ""))
    if _version_tuple(version) < MINIMUM_OLLAMA_VERSION:
        return {
            "ready": False,
            "version": version or "unknown",
            "model": DEFAULT_MODEL,
            "message": (
                "Ollama " + (version or "unknown")
                + " is too old for this multimodal model. Update Ollama to 0.40.11 or newer."
            ),
        }

    tags_payload = _local_get("/api/tags")
    models = tags_payload.get("models", [])
    installed = []
    if isinstance(models, list):
        installed = [
            str(item.get("name", ""))
            for item in models
            if isinstance(item, dict) and item.get("name")
        ]
    found = any(name.casefold() == DEFAULT_MODEL.casefold() for name in installed)
    if not found:
        return {
            "ready": False,
            "version": version,
            "model": DEFAULT_MODEL,
            "message": (
                "The selected local model and its vision projector are not installed. "
                "Run: ollama run " + DEFAULT_MODEL
            ),
        }
    return {
        "ready": True,
        "version": version,
        "model": DEFAULT_MODEL,
        "message": "Local NextAI model is installed and ready. Image input is enabled if the model pull included its vision projector.",
    }


def build_payload(messages, model: str = DEFAULT_MODEL) -> dict:
    """Build a bounded text or multimodal request without changing its content."""
    if not isinstance(messages, list) or not messages:
        raise ProviderError("NextAI needs at least one conversation message.")
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {
            "system", "user", "assistant", "tool"
        }:
            raise ProviderError("NextAI received an invalid conversation message.")
        content = message.get("content")
        if not isinstance(content, (str, list)):
            raise ProviderError("Message content must be text or multimodal content.")
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict) or part.get("type") not in {"text", "image_url"}:
                    raise ProviderError("NextAI received an unsupported multimodal content block.")
                if part["type"] == "text" and not isinstance(part.get("text"), str):
                    raise ProviderError("Text content blocks must contain text.")
                if part["type"] == "image_url":
                    image_url = part.get("image_url")
                    if not isinstance(image_url, dict) or not str(image_url.get("url", "")).startswith(
                        "data:image/"
                    ):
                        raise ProviderError("Images must be supplied as local image data, not remote URLs.")
    return {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
        "stream": False,
    }


def chat(messages, model: str = DEFAULT_MODEL, endpoint: str = DEFAULT_ENDPOINT) -> str:
    """Send a bounded local text/image request; never use remote fallback."""
    url = _validated_endpoint(endpoint)
    payload = build_payload(messages, model)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_REQUEST_BYTES:
        raise ProviderError("The NextAI request is too large. Reduce the number or size of attached drawings.")

    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=180) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, OSError) as exc:
        raise ProviderError(
            "The local NextAI model is not responding. Start the selected local Ollama model and try again."
        ) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProviderError("The local model response exceeded the safety limit.")
    try:
        response_data = json.loads(raw.decode("utf-8"))
        content = response_data["choices"][0]["message"]["content"]
    except (UnicodeDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise ProviderError("The local model returned an invalid chat response.") from exc
    if not isinstance(content, str) or not content.strip():
        raise ProviderError("The local model returned an empty chat response.")
    return content.strip()
