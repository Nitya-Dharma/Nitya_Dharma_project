"""Registration flow abstraction for future OTP integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class FlowDescriptor:
    """Metadata that documents a future registration flow adapter."""

    name: str
    registration_entrypoint: str
    verified_token_required: bool = True


class BaseFlow(ABC):
    """Base contract for future registration flow adapters."""

    descriptor: FlowDescriptor

    @abstractmethod
    def build_context(self, *, payload: Mapping[str, object]) -> Mapping[str, object]:
        """Build a flow-specific context payload for OTP processing."""
