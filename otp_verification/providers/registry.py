"""Registry foundation for configuration-driven OTP provider resolution.

Task 1 defines provider discovery and registration only. Task 3 extends the
registry with discovery helpers without changing existing register/get contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from otp_verification.exceptions import ProviderException, ProviderNotFoundException
from otp_verification.providers.base import ProviderDescriptor


@dataclass
class OTPProviderRegistry:
    """In-memory registry for provider descriptors."""

    descriptors: dict[str, ProviderDescriptor] = field(default_factory=dict)

    def register(self, descriptor: ProviderDescriptor) -> None:
        """Register a provider descriptor for future resolution."""

        if descriptor.name in self.descriptors:
            raise ProviderException(f"OTP provider '{descriptor.name}' is already registered.")
        self.descriptors[descriptor.name] = descriptor

    def get(self, provider_name: str) -> ProviderDescriptor:
        """Return a provider descriptor by name."""

        try:
            return self.descriptors[provider_name]
        except KeyError as exc:
            raise ProviderNotFoundException(
                f"OTP provider '{provider_name}' is not registered."
            ) from exc

    def has_provider(self, provider_name: str) -> bool:
        """Return whether the registry contains the requested provider."""

        return provider_name in self.descriptors

    def list_providers(self) -> tuple[str, ...]:
        """Return registered provider names in insertion order."""

        return tuple(self.descriptors.keys())

    def discover(self) -> tuple[ProviderDescriptor, ...]:
        """Return all registered provider descriptors."""

        return tuple(self.descriptors.values())
