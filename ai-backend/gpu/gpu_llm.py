"""Client for the local llama.cpp OpenAI-compatible chat endpoint."""

from __future__ import annotations

import json
import os
from time import monotonic
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LLAMA_CPP_BASE_URL = os.environ.get("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
LLAMA_CPP_TIMEOUT_SECONDS = 120


class LLMResponse(TypedDict):
    reply: str
    tokens: int
    latency_ms: int


class LLMRuntimeError(RuntimeError):
    """Raised when llama.cpp is unavailable or returns an invalid response."""


def run_llm(prompt: str, system_prompt: str | None = None) -> LLMResponse:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps(
        {
            "model": "local-model",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 256,
            "stream": False,
        }
    ).encode("utf-8")
    request = Request(
        f"{LLAMA_CPP_BASE_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started_at = monotonic()

    try:
        with urlopen(request, timeout=LLAMA_CPP_TIMEOUT_SECONDS) as response:
            result = json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace").strip()
        raise LLMRuntimeError(
            f"llama.cpp returned HTTP {error.code}: {details or error.reason}"
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise LLMRuntimeError(
            "Cannot reach llama.cpp at "
            f"{LLAMA_CPP_BASE_URL}. Start run-llama-server.bat and try again."
        ) from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise LLMRuntimeError("llama.cpp returned an invalid JSON response.") from error

    try:
        reply = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise LLMRuntimeError("llama.cpp response did not contain a chat reply.") from error
    if not isinstance(reply, str) or not reply.strip():
        raise LLMRuntimeError("llama.cpp returned an empty chat reply.")

    usage = result.get("usage", {})
    completion_tokens = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0

    return {
        "reply": reply.strip(),
        "tokens": completion_tokens if isinstance(completion_tokens, int) else 0,
        "latency_ms": round((monotonic() - started_at) * 1000),
    }
