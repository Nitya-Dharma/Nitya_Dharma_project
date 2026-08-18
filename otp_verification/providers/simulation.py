"""Deterministic simulation engine for the mock OTP provider."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from otp_verification.config import OTPConfiguration
from otp_verification.enums import ProviderResultStatus, SimulationMode
from otp_verification.exceptions import ConfigurationException


@dataclass(frozen=True)
class SimulationOutcome:
    """Secret-free simulation outcome used to build provider responses."""

    status: str
    accepted: bool
    provider_message: str
    provider_reference: str
    timestamp: datetime
    duration_ms: float


class MockSimulationEngine:
    """Configuration-driven deterministic mock delivery simulator."""

    def __init__(self, *, configuration: OTPConfiguration) -> None:
        self.configuration = configuration

    def _mode(self) -> str:
        mode = self.configuration.mock_simulation_mode
        try:
            return SimulationMode(mode).value
        except ValueError as exc:
            raise ConfigurationException(
                f"Unsupported mock simulation mode '{mode}'."
            ) from exc

    def execute(self) -> SimulationOutcome:
        """Execute a deterministic simulation for the configured mode."""

        if self.configuration.mock_allow_random:
            # Explicitly unsupported in Task 3 unless a later phase defines behavior.
            raise ConfigurationException(
                "OTP_MOCK_ALLOW_RANDOM is enabled but random simulation is not implemented."
            )

        delay_ms = self.configuration.mock_execution_delay_ms
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        mode = self._mode()
        now = datetime.now(timezone.utc)
        reference = f"mock-{uuid.uuid4()}"

        if mode == SimulationMode.SUCCESS:
            return SimulationOutcome(
                status=ProviderResultStatus.SUCCESS,
                accepted=True,
                provider_message="Mock provider simulated successful delivery.",
                provider_reference=reference,
                timestamp=now,
                duration_ms=float(delay_ms),
            )
        if mode == SimulationMode.FAILURE:
            return SimulationOutcome(
                status=ProviderResultStatus.FAILURE,
                accepted=False,
                provider_message="Mock provider simulated delivery failure.",
                provider_reference=reference,
                timestamp=now,
                duration_ms=float(delay_ms),
            )
        if mode == SimulationMode.TIMEOUT:
            return SimulationOutcome(
                status=ProviderResultStatus.TIMEOUT,
                accepted=False,
                provider_message="Mock provider simulated timeout.",
                provider_reference=reference,
                timestamp=now,
                duration_ms=float(delay_ms),
            )
        if mode == SimulationMode.UNAVAILABLE:
            return SimulationOutcome(
                status=ProviderResultStatus.UNAVAILABLE,
                accepted=False,
                provider_message="Mock provider simulated unavailable state.",
                provider_reference=reference,
                timestamp=now,
                duration_ms=float(delay_ms),
            )
        return SimulationOutcome(
            status=ProviderResultStatus.ERROR,
            accepted=False,
            provider_message="Mock provider simulated unknown provider error.",
            provider_reference=reference,
            timestamp=now,
            duration_ms=float(delay_ms),
        )
