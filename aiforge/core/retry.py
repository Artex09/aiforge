"""Retry with exponential backoff and full jitter.

Live providers fail transiently (rate limits, 5xx, dropped connections). This
wraps a call so those don't surface as hard errors on the first blip.
"""
from __future__ import annotations

import random
import time
from typing import Any, Callable, Iterable, Optional, Tuple, Type

from .errors import ProviderError


def with_retries(
    fn: Callable[[], Any],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 20.0,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
    sleep: Callable[[float], None] = time.sleep,
    rng: Optional[random.Random] = None,
) -> Any:
    """Call ``fn`` up to ``attempts`` times, backing off between failures.

    Delay for attempt *n* (0-indexed) is a "full jitter" draw from
    ``[0, min(max_delay, base_delay * 2**n)]``. Re-raises the last error once
    attempts are exhausted.
    """
    rng = rng or random
    last: Optional[BaseException] = None
    for attempt in range(max(1, attempts)):
        try:
            return fn()
        except retry_on as exc:  # noqa: BLE001 - deliberately broad, caller narrows
            last = exc
            if attempt == attempts - 1:
                break
            ceiling = min(max_delay, base_delay * (2 ** attempt))
            delay = rng.uniform(0, ceiling)
            if on_retry is not None:
                on_retry(attempt + 1, exc, delay)
            sleep(delay)
    assert last is not None
    raise last


class RetryPolicy:
    """A reusable retry configuration."""

    def __init__(
        self,
        attempts: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 20.0,
        retry_on: Iterable[Type[BaseException]] = (ProviderError, ConnectionError, TimeoutError),
    ):
        self.attempts = attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retry_on = tuple(retry_on)

    def run(self, fn: Callable[[], Any], on_retry=None) -> Any:
        return with_retries(
            fn,
            attempts=self.attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            retry_on=self.retry_on,
            on_retry=on_retry,
        )
