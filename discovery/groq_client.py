"""
discovery/groq_client.py

Shared Groq client wrapper with automatic key rotation on rate limits.
Both filter.py and extract_from_listings.py should import
call_groq_with_fallback() instead of creating their own client directly.
"""

import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# Collect all available Groq keys from env vars GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, ...
def _load_groq_keys() -> list[str]:
    keys = []
    primary = os.getenv("GROQ_API_KEY")
    if primary:
        keys.append(primary)

    i = 2
    while True:
        key = os.getenv(f"GROQ_API_KEY_{i}")
        if not key:
            break
        keys.append(key)
        i += 1

    return keys


_GROQ_KEYS = _load_groq_keys()
_current_key_index = 0

if not _GROQ_KEYS:
    raise RuntimeError("No GROQ_API_KEY found in .env — set at least GROQ_API_KEY")


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=_GROQ_KEYS[_current_key_index],
        base_url="https://api.groq.com/openai/v1",
    )


def call_groq_with_fallback(model: str, messages: list[dict], temperature: float = 0,
                              timeout: int = 30, max_retries_per_key: int = 2):
    """
    Calls Groq's chat completions, automatically rotating to the next
    available API key if the current one hits a rate limit (429).
    Raises the last exception if all keys are exhausted.
    """
    global _current_key_index

    keys_tried = 0
    last_exception = None

    while keys_tried < len(_GROQ_KEYS):
        client = _get_client()

        for attempt in range(1, max_retries_per_key + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    timeout=timeout,
                )
                return response
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                is_rate_limit = "429" in error_str or "rate_limit" in error_str

                if is_rate_limit:
                    print(f"Key #{_current_key_index + 1} rate-limited. Rotating to next key...")
                    break  # stop retrying this key, move to next one
                else:
                    # Non-rate-limit error — retry same key briefly, then give up on it too
                    if attempt < max_retries_per_key:
                        time.sleep(3)
                    else:
                        break

        keys_tried += 1
        _current_key_index = (_current_key_index + 1) % len(_GROQ_KEYS)

    raise RuntimeError(f"All {len(_GROQ_KEYS)} Groq keys exhausted or failed. Last error: {last_exception}")