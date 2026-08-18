"""In-memory provider metrics (never persisted)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock


@dataclass
class ProviderMetricsSnapshot:
    total_executions: int = 0
    successful_executions: int = 0
    failures: int = 0
    timeouts: int = 0
    unavailable: int = 0
    total_duration_ms: float = 0.0
    available: bool = True

    @property
    def average_execution_duration_ms(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_duration_ms / self.total_executions


@dataclass
class ProviderMetrics:
    """Process-local metrics collector for provider executions."""

    _lock: RLock = field(default_factory=RLock, repr=False)
    _snapshot: ProviderMetricsSnapshot = field(default_factory=ProviderMetricsSnapshot)

    def record(
        self,
        *,
        success: bool = False,
        failure: bool = False,
        timeout: bool = False,
        unavailable: bool = False,
        duration_ms: float = 0.0,
        available: bool | None = None,
    ) -> None:
        with self._lock:
            self._snapshot.total_executions += 1
            self._snapshot.total_duration_ms += max(duration_ms, 0.0)
            if success:
                self._snapshot.successful_executions += 1
            if failure:
                self._snapshot.failures += 1
            if timeout:
                self._snapshot.timeouts += 1
            if unavailable:
                self._snapshot.unavailable += 1
            if available is not None:
                self._snapshot.available = available

    def snapshot(self) -> ProviderMetricsSnapshot:
        with self._lock:
            current = self._snapshot
            return ProviderMetricsSnapshot(
                total_executions=current.total_executions,
                successful_executions=current.successful_executions,
                failures=current.failures,
                timeouts=current.timeouts,
                unavailable=current.unavailable,
                total_duration_ms=current.total_duration_ms,
                available=current.available,
            )

    def reset(self) -> None:
        with self._lock:
            self._snapshot = ProviderMetricsSnapshot()
