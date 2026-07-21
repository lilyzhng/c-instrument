"""Minimal client for a vLLM OpenAI-compatible server (stdlib only)."""

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


class VLLMClient:
    def __init__(self, base_url, model, timeout=120, retries=3):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.retries = retries

    def _post(self, path, payload):
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        last_err = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except Exception as e:  # noqa: BLE001 - retry then surface
                last_err = e
                time.sleep(2**attempt)
        raise RuntimeError(f"vLLM request failed after {self.retries} tries: {last_err}")

    def generate(self, endpoint, built, n, temperature, max_tokens):
        """Return a list of n completion strings for one prompt."""
        payload = {
            "model": self.model,
            "n": n,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if endpoint == "completions":
            payload["prompt"] = built
            out = self._post("/v1/completions", payload)
            return [c["text"] for c in out["choices"]]
        payload["messages"] = built
        out = self._post("/v1/chat/completions", payload)
        return [c["message"]["content"] for c in out["choices"]]

    def generate_batch(self, endpoint, builts, n, temperature, max_tokens, workers=16):
        """Concurrent generation over many prompts; order preserved."""
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(
                pool.map(
                    lambda b: self.generate(endpoint, b, n, temperature, max_tokens),
                    builts,
                )
            )
