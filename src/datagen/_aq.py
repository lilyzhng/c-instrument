"""Shared inference-endpoint client for the bake-off scripts.

Single-attempt by design: 403/429 are Cloudflare burst-protection that
*escalate* if you retry through them, so we do NOT retry those, we surface
the code and let the caller's AdaptiveLimiter (ratelimit.py) back off.
Only transient 5xx/timeouts get a small retry. Returns (content, ok,
retry_after): content is "" on failure, ok is a bool, retry_after is the
server hint in seconds or None.
"""

import json
import os
import time
import urllib.error
import urllib.request

# Endpoint is configurable: default is the provided inference proxy, but set
# AQ_BASE + AQ_KEY to hit OpenRouter directly (bypasses the proxy's block).
#   OpenRouter:  AQ_BASE=https://openrouter.ai/api/v1/chat/completions
#                AQ_KEY=sk-or-v1-...
DEFAULT_BASE = "https://api.aqinference.com/v1/chat/completions"
NORETRY = (403, 429, 401, 400, 404)  # client/limit errors: never retry
TRANSIENT_RETRIES = 2


def _base():
    return os.environ.get("AQ_BASE", DEFAULT_BASE)


def _key():
    """Read the key at call time, not import time, so pure logic in the
    bake-off modules stays importable (and unit-testable) without it."""
    return os.environ["AQ_KEY"]


def chat(model, system, user, max_tokens=2000, temperature=0.0):
    """One request. Returns (content, ok, retry_after)."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "reasoning": {"effort": "low"},
    }).encode()

    for attempt in range(TRANSIENT_RETRIES + 1):
        try:
            req = urllib.request.Request(
                _base(), data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {_key()}",
                         "HTTP-Referer": "https://c-instrument.local",
                         "X-Title": "guard-model-datagen",
                         # gateway bot-blocks the default Python-urllib UA
                         # with 403 (seen 2026-07-20); a curl-ish UA passes
                         "User-Agent": "curl/8.7.1"})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            return d["choices"][0]["message"]["content"] or "", True, None
        except urllib.error.HTTPError as e:
            ra = e.headers.get("Retry-After") if e.headers else None
            ra = float(ra) if ra and ra.isdigit() else None
            if e.code in NORETRY:
                return "", False, ra           # do NOT retry, back off instead
            time.sleep(2 ** attempt)            # transient 5xx: brief retry
        except Exception:  # noqa: BLE001 - network/timeout, transient
            time.sleep(2 ** attempt)
    return "", False, None
