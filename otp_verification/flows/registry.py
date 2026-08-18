"""Concrete flow placeholders with no registration integration yet."""

from __future__ import annotations

from typing import Mapping

from otp_verification import constants
from otp_verification.flows.base import BaseFlow, FlowDescriptor


class PanditFlow(BaseFlow):
    descriptor = FlowDescriptor(
        name=constants.FLOW_PANDIT_REGISTRATION,
        registration_entrypoint="accounts.views.register_pandit",
    )

    def build_context(self, *, payload: Mapping[str, object]) -> Mapping[str, object]:
        raise NotImplementedError("Pandit OTP integration is implemented in a later phase.")


class ExpertFlow(BaseFlow):
    descriptor = FlowDescriptor(
        name=constants.FLOW_EXPERT_REGISTRATION,
        registration_entrypoint="services.views_expert_ui",
    )

    def build_context(self, *, payload: Mapping[str, object]) -> Mapping[str, object]:
        raise NotImplementedError("Expert OTP integration is implemented in a later phase.")


class BureauFlow(BaseFlow):
    descriptor = FlowDescriptor(
        name=constants.FLOW_BUREAU_REGISTRATION,
        registration_entrypoint="bureaus.views.register_bureau",
    )

    def build_context(self, *, payload: Mapping[str, object]) -> Mapping[str, object]:
        raise NotImplementedError("Bureau OTP integration is implemented in a later phase.")


class UserFlow(BaseFlow):
    descriptor = FlowDescriptor(
        name=constants.FLOW_USER_REGISTRATION,
        registration_entrypoint="accounts.views.register",
    )

    def build_context(self, *, payload: Mapping[str, object]) -> Mapping[str, object]:
        raise NotImplementedError("User OTP integration is implemented in a later phase.")
