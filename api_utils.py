"""
SORCERER — API Utilities
Shared retry logic for all Claude API calls.
Handles timeouts, rate limits, overload, and credit exhaustion gracefully.
"""

import time
import json
import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# Retryable HTTP status codes
_RETRYABLE = {
    408,  # Request timeout
    429,  # Rate limited
    529,  # Overloaded
    500,  # Internal server error (transient)
    502,  # Bad gateway
    503,  # Service unavailable
}

def claude_request(
    model,
    prompt,
    api_key,
    max_tokens=1200,
    timeout=45,
    retries=2,
    backoff=3.0,
    log_fn=None,
):
    """
    Make a Claude API call with automatic retry on transient failures.

    Returns parsed JSON dict on success, or {"_error": "..."} on failure.
    Never raises — always returns a dict.

    Args:
        model:      Claude model string
        prompt:     User message content (string)
        api_key:    Anthropic API key
        max_tokens: Max response tokens
        timeout:    Request timeout in seconds
        retries:    Number of retry attempts (0 = no retries)
        backoff:    Seconds to wait between retries (doubles each time)
        log_fn:     Optional logging function
    """
    if not api_key:
        return {"_error": "No API key provided"}

    headers = {
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":      model,
        "max_tokens": max_tokens,
        "messages":   [{"role": "user", "content": prompt}],
    }

    last_error = None
    for attempt in range(1 + retries):
        try:
            r = requests.post(
                ANTHROPIC_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            # ── Credit exhaustion — don't retry, it won't help ──
            if r.status_code == 400:
                body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                err_msg = body.get("error", {}).get("message", r.text[:200])
                if "credit" in err_msg.lower() or "billing" in err_msg.lower():
                    return {"_error": f"Credits exhausted: {err_msg}"}
                return {"_error": f"Bad request: {err_msg}"}

            # ── Auth error — don't retry ──
            if r.status_code in (401, 403):
                return {"_error": f"Auth failed ({r.status_code}): check ANTHROPIC_API_KEY"}

            # ── Retryable errors ──
            if r.status_code in _RETRYABLE:
                wait = backoff * (2 ** attempt)
                # Respect Retry-After header if present
                retry_after = r.headers.get("retry-after")
                if retry_after:
                    try:
                        wait = max(wait, float(retry_after))
                    except ValueError:
                        pass

                last_error = f"HTTP {r.status_code}"
                if log_fn and attempt < retries:
                    log_fn(f"  ⏳ API returned {r.status_code} — retrying in {wait:.0f}s (attempt {attempt+1}/{retries})")
                if attempt < retries:
                    time.sleep(wait)
                    continue
                return {"_error": f"API failed after {retries+1} attempts: {last_error}"}

            # ── Success ──
            r.raise_for_status()
            raw = r.json()["content"][0]["text"].strip()

            # Clean markdown fences that Claude sometimes wraps JSON in
            raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            # Got a response but couldn't parse — try to salvage
            return {"_error": f"JSON parse failed: {e}", "_raw": raw[:500]}

        except requests.exceptions.Timeout:
            last_error = f"Timeout ({timeout}s)"
            if log_fn and attempt < retries:
                log_fn(f"  ⏳ API timeout — retrying (attempt {attempt+1}/{retries})")
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
                continue

        except requests.exceptions.ConnectionError:
            last_error = "Connection error"
            if log_fn and attempt < retries:
                log_fn(f"  ⏳ Connection error — retrying (attempt {attempt+1}/{retries})")
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
                continue

        except Exception as e:
            return {"_error": str(e)}

    return {"_error": f"Failed after {retries+1} attempts: {last_error}"}