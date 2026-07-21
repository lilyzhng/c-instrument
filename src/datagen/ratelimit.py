"""Adaptive client-side rate limiting for an opaque, Cloudflare-fronted
endpoint (the shared inference proxy).

Grounded in the consensus stack (AWS backoff-with-jitter, Cloudflare WAF
notes, aimd-bucket): we do NOT know the endpoint's real limit, and 403s
are Cloudflare burst-protection that *escalates* if you retry through it.
So:

  - AIMD pacing: start slow, additively speed up on success, multiplicatively
    slow down on failure (TCP-congestion style, discovers an opaque limit).
  - 403/429 are NOT per-request-retried; they trip a circuit breaker that
    forces a long cooldown, because retrying a 403 deepens a Cloudflare block.
  - Full jitter on every wait.

This module is the pure policy (delays, state transitions); it is
unit-tested without any network. The caller sleeps for `next_delay()`
before each call and reports the outcome via `record()`.
"""

import random

# AIMD constants (seconds of inter-request delay).
MIN_DELAY = 3.0      # never faster than this (Cloudflare burst floor)
MAX_DELAY = 45.0     # circuit-breaker cooldown ceiling
START_DELAY = 6.0    # conservative opening pace
ADDITIVE_DECREASE = 0.5   # speed up: shrink delay by this on each success
MULT_INCREASE = 2.0       # slow down: multiply delay by this on failure
CIRCUIT_TRIP_FAILURES = 3  # consecutive failures -> long cooldown


class AdaptiveLimiter:
    """AIMD inter-request pacing with a circuit breaker. Not thread-safe by
    design: callers run serial (concurrency is what trips Cloudflare)."""

    def __init__(self, start=START_DELAY, rng=None):
        self.delay = start
        self._consecutive_failures = 0
        self._rng = rng or random.Random()

    def next_delay(self):
        """Delay to sleep before the next request, with full jitter
        (uniform in [0, delay]) so bursts do not re-synchronize."""
        return self._rng.uniform(0, self.delay)

    def record(self, ok, retry_after=None):
        """Update pacing from the last outcome.

        ok=True  : additive decrease (speed up), reset failure streak.
        ok=False : multiplicative increase (slow down); on the Nth
                   consecutive failure, jump to MAX_DELAY (circuit trip).
        retry_after: server hint (seconds) overrides our delay upward.
        """
        if ok:
            self._consecutive_failures = 0
            self.delay = max(MIN_DELAY, self.delay - ADDITIVE_DECREASE)
        else:
            self._consecutive_failures += 1
            self.delay = min(MAX_DELAY, self.delay * MULT_INCREASE)
            if self._consecutive_failures >= CIRCUIT_TRIP_FAILURES:
                self.delay = MAX_DELAY
        if retry_after is not None:
            self.delay = min(MAX_DELAY, max(self.delay, float(retry_after)))
        return self.delay

    @property
    def tripped(self):
        """True once the failure streak has opened the circuit breaker;
        the caller should pause the whole run, not keep hammering."""
        return self._consecutive_failures >= CIRCUIT_TRIP_FAILURES
