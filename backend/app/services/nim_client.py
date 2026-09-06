"""Async client for NVIDIA NIM vision-language model chat-completions API."""

import httpx

from app.core.config import settings


class NimError(RuntimeError):
    """Raised when the NVIDIA NIM API returns an error or unexpected payload."""


async def call_vlm(
    image_data_uri: str | None,
    prompt: str,
    max_tokens: int = 512,
    timeout: float = 60.0,
) -> str:
    """
    Send a text prompt (and optionally an image as a base64 data URI) to the
    configured NIM VLM endpoint and return the raw text content of the response.

    When image_data_uri is None or empty, a text-only message is sent (some NIM
    VLMs accept text-only prompts for generation tasks).
    """
    if not settings.nvidia_api_key:
        raise NimError(
            "NVIDIA_NIM API key is not configured. Set NVIDIA_API_KEY in backend/.env "
            "(get one at https://build.nvidia.com)."
        )

    content: list[dict] = []
    if image_data_uri:
        content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
    content.append({"type": "text", "text": prompt})

    payload = {
        "messages": [{"role": "user", "content": content}],
        "model": settings.nim_model,
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "top_p": 1,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Accept": "application/json",
    }

    request_timeout = max(timeout, settings.nim_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            resp = await client.post(settings.nim_endpoint, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise NimError(
            f"NIM request timed out after {request_timeout:g}s. "
            "The vision model may be busy; try again or increase NIM_TIMEOUT_SECONDS."
        ) from exc
    except httpx.RequestError as exc:
        raise NimError(f"Could not reach the NIM endpoint: {exc}") from exc

    if resp.status_code != 200:
        raise NimError(f"NIM API returned HTTP {resp.status_code}: {resp.text[:500]}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise NimError(f"NIM API returned invalid JSON: {resp.text[:500]}") from exc
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise NimError(f"Unexpected NIM API response shape: {str(data)[:500]}")

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Some OpenAI-compatible providers return content blocks instead of a string.
        text_parts = [block.get("text", "") for block in content if isinstance(block, dict)]
        result = "".join(part for part in text_parts if isinstance(part, str)).strip()
        if result:
            return result
    raise NimError(f"Unexpected NIM message content: {str(content)[:500]}")
