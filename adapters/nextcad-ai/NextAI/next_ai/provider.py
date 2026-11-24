"""Local-only OpenAI-compatible client for the shared llama.cpp server."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from urllib.parse import urlsplit

DEFAULT_ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_MODEL = "qwen3.5-0.8b"
MAX_REQUEST_BYTES = 1_000_000
MAX_RESPONSE_BYTES = 1_000_000


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
        or parts.port != 8080
        or parts.path != "/v1/chat/completions"
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ProviderError("NextAI only connects to the local model at 127.0.0.1:8080.")
    return endpoint


def chat(messages, model: str = DEFAULT_MODEL, endpoint: str = DEFAULT_ENDPOINT) -> str:
    """Send a bounded chat request to the local model; never use remote fallback."""
    url = _validated_endpoint(endpoint)
    body = json.dumps(
        {
            "model": model or DEFAULT_MODEL,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2048,
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    if len(body) > MAX_REQUEST_BYTES:
        raise ProviderError("The NextAI request is too large.")

    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=120) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, OSError) as exc:
        raise ProviderError(
            "The local NextAI model is not responding. Start the bundled local model service and try again."
        ) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProviderError("The local model response exceeded the safety limit.")
    try:
        payload = json.loads(raw.decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
    except (UnicodeDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise ProviderError("The local model returned an invalid chat response.") from exc
    if not isinstance(content, str) or not content.strip():
        raise ProviderError("The local model returned an empty response.")
    return content.strip()
