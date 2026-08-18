"""Provider metadata types for registry-driven provider resolution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDescriptor:
    """Describes a future provider implementation without instantiating it."""

    name: str
    dotted_path: str
    channel: str
    supports_mock_mode: bool = False
