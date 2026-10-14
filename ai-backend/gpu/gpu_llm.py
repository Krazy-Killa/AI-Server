"""Client for the local llama.cpp OpenAI-compatible chat endpoint."""

from __future__ import annotations

import json
from collections.abc import Iterator
from time import monotonic
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import settings

LLAMA_CPP_BASE_URL = settings.llama_cpp_base_url
LLAMA_CPP_TIMEOUT_SECONDS = settings.llama_cpp_timeout_seconds


class LLMResponse(TypedDict):
    reply: str
    tokens: int
    latency_ms: int


class LLMRuntimeError(RuntimeError):
    """Raised when llama.cpp is unavailable or returns an invalid response."""


def _build_request(prompt: str, system_prompt: str | None, stream: bool) -> Request:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps(
        {
            "model": "local-model",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": settings.llm_max_tokens,
            "stream": stream,
        }
    ).encode("utf-8")
    return Request(
        f"{LLAMA_CPP_BASE_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )


def _http_error(error: HTTPError) -> LLMRuntimeError:
    details = error.read().decode("utf-8", errors="replace").strip()
    return LLMRuntimeError(f"llama.cpp returned HTTP {error.code}: {details or error.reason}")


def _unreachable_error() -> LLMRuntimeError:
    return LLMRuntimeError(
        "Cannot reach llama.cpp at "
        f"{LLAMA_CPP_BASE_URL}. Start run-llama-server.bat and try again."
    )


def stream_llm(prompt: str, system_prompt: str | None = None) -> Iterator[str]:
    """Yield reply text chunks as llama.cpp generates them.

    Closing the generator closes the HTTP connection, which stops generation.
    """
    request = _build_request(prompt, system_prompt, stream=True)
    produced_text = False

    try:
        with urlopen(request, timeout=LLAMA_CPP_TIMEOUT_SECONDS) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    text = chunk["choices"][0]["delta"].get("content")
                except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError) as error:
                    raise LLMRuntimeError("llama.cpp sent an invalid streaming chunk.") from error
                if isinstance(text, str) and text:
                    produced_text = True
                    yield text
    except HTTPError as error:
        raise _http_error(error) from error
    except (URLError, TimeoutError, OSError) as error:
        raise _unreachable_error() from error

    if not produced_text:
        raise LLMRuntimeError("llama.cpp returned an empty chat reply.")


def run_llm(prompt: str, system_prompt: str | None = None) -> LLMResponse:
    request = _build_request(prompt, system_prompt, stream=False)
    started_at = monotonic()

    try:
        with urlopen(request, timeout=LLAMA_CPP_TIMEOUT_SECONDS) as response:
            result = json.load(response)
    except HTTPError as error:
        raise _http_error(error) from error
    except (URLError, TimeoutError, OSError) as error:
        raise _unreachable_error() from error
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
