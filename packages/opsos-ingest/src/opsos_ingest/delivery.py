"""In-process target delivery with bounded exponential retry and dead lettering."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .event import CanonicalEvent


@dataclass(frozen=True)
class DeadLetter:
    event: CanonicalEvent
    target: str
    attempts: int
    reason: str


class DeadLetterQueue:
    def __init__(self) -> None:
        self.items: list[DeadLetter] = []

    def put(self, item: DeadLetter) -> None:
        self.items.append(item)


@dataclass
class DeliveryResult:
    target: str
    attempts: int
    delivered: bool
    attempt_log: list[tuple[int, str, float | None]] = field(default_factory=list)
    dead_lettered: bool = False
    reason: str | None = None


class Deliverer:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        sleep: Callable[[float], Any] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if base_delay < 0 or backoff_factor < 0:
            raise ValueError("retry delays and factors must be non-negative")
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.sleep = sleep or time.sleep
        self.targets: dict[str, Callable[[CanonicalEvent], bool]] = {}

    def register_target(self, name: str, fn: Callable[[CanonicalEvent], bool]) -> None:
        if not name:
            raise ValueError("target name must be non-empty")
        self.targets[name] = fn

    def deliver_to(self, target_name: str, event: CanonicalEvent) -> DeliveryResult:
        if target_name not in self.targets:
            raise KeyError(f"unknown delivery target: {target_name}")
        target_fn = self.targets[target_name]
        attempts: list[tuple[int, str, float | None]] = []

        for attempt_no in range(1, self.max_attempts + 1):
            try:
                delivered = target_fn(event) is True
                detail = "ok" if delivered else "failed"
            except Exception as exc:  # noqa: BLE001
                delivered = False
                detail = f"error: {type(exc).__name__}: {exc}"

            if delivered:
                attempts.append((attempt_no, "delivered", None))
                return DeliveryResult(target_name, attempt_no, True, attempts)

            delay = None
            if attempt_no < self.max_attempts:
                delay = self.base_delay * (self.backoff_factor ** (attempt_no - 1))
            attempts.append((attempt_no, detail, delay))
            if delay is not None:
                self.sleep(delay)

        reason = attempts[-1][1] if attempts else "failed"
        return DeliveryResult(
            target=target_name,
            attempts=self.max_attempts,
            delivered=False,
            attempt_log=attempts,
            dead_lettered=True,
            reason=f"delivery failed after {self.max_attempts} attempts: {reason}",
        )
