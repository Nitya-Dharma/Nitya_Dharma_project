"""Provider discovery and resolution helpers (no business OTP logic)."""

from __future__ import annotations

from importlib import import_module
from typing import Callable

from otp_verification.exceptions import ProviderException, ProviderNotFoundException
from otp_verification.interfaces.providers import BaseOTPProvider
from otp_verification.providers.base import ProviderDescriptor
from otp_verification.providers.registry import OTPProviderRegistry


class ProviderResolver:
    """Resolves provider descriptors from the registry without if/else vendor chains."""

    def __init__(
        self,
        *,
        registry: OTPProviderRegistry,
        provider_factory: Callable[[ProviderDescriptor], BaseOTPProvider] | None = None,
    ) -> None:
        self.registry = registry
        self.provider_factory = provider_factory

    def discover(self) -> tuple[ProviderDescriptor, ...]:
        return self.registry.discover()

    def resolve_descriptor(self, provider_name: str) -> ProviderDescriptor:
        if not self.registry.has_provider(provider_name):
            raise ProviderNotFoundException(
                f"OTP provider '{provider_name}' is not registered."
            )
        return self.registry.get(provider_name)

    def resolve(self, provider_name: str) -> BaseOTPProvider:
        """Resolve and instantiate a provider through the injected factory."""

        descriptor = self.resolve_descriptor(provider_name)
        if self.provider_factory is None:
            raise ProviderException(
                "ProviderResolver requires a provider_factory for instantiation."
            )
        provider = self.provider_factory(descriptor)
        if not isinstance(provider, BaseOTPProvider):
            raise ProviderException(
                f"Resolved object for '{provider_name}' is not a BaseOTPProvider."
            )
        return provider


def load_provider_class(dotted_path: str):
    """Import a provider class from a dotted path."""

    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path or not class_name:
        raise ProviderException(f"Invalid provider dotted path '{dotted_path}'.")
    module = import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as exc:
        raise ProviderException(
            f"Provider class '{class_name}' not found in '{module_path}'."
        ) from exc
