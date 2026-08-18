"""Broadcast.run / Omni SMS API provider — delivery only, no OTP ownership."""

from __future__ import annotations

import json
import logging
import os
import re

import requests
from django.conf import settings

from otp_verification import constants
from otp_verification.exceptions import (
    ConfigurationException,
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    ValidationException,
)
from otp_verification.interfaces.providers import BaseOTPProvider, ProviderRequest, ProviderResponse

logger = logging.getLogger(__name__)

SEND_URL = "https://dashboard.broadcast.run/api/v1/sms/sendsms"
SENDER_ID = "NDHRMA"
PE_ID = "1701177338710464858"
DLT_TEMPLATE_ID = "1777178575487318004"
TIMEOUT_SECONDS = 10

# DLT-approved template; {#num#} is replaced with the engine OTP at send time.
_OTP_SMS_TEMPLATE = (
    "Hello Your Nitya Dharma Registration OTP is {otp} "
    "It is valid for 10 minutes. Please do not share this OTP with anyone. "
    "https://nityadharma.com"
)


def _redact_url(url: str) -> str:
    return re.sub(r"([?&]ApiKey=)[^&]+", r"\1***", url)


def _normalize_number(destination: str) -> str:
    """Ensure Indian mobiles are sent as 91XXXXXXXXXX when possible."""

    raw = str(destination).strip()
    if raw.startswith("+"):
        raw = raw[1:]
    if len(raw) == 10 and raw.isdigit():
        return f"91{raw}"
    return raw


def _parse_provider_reference(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderFailureException(
            "broadcast_sms returned a non-JSON response."
        ) from exc

    code = str(payload.get("code") or "").strip()
    if code and code != "200":
        api_message = str(payload.get("message") or "").strip()
        raise ProviderFailureException(
            f"broadcast_sms delivery failed with API code {code}"
            + (f": {api_message}" if api_message else ".")
        )

    message_raw = payload.get("message")
    if isinstance(message_raw, str) and message_raw.strip():
        try:
            entries = json.loads(message_raw)
        except (TypeError, ValueError):
            entries = None
        if isinstance(entries, list) and entries:
            message_id = str(entries[0].get("messageId") or "").strip()
            if message_id:
                return message_id

    raise ProviderFailureException(
        "broadcast_sms success response missing provider messageId."
    )


class BroadcastSmsProvider(BaseOTPProvider):
    """SMS delivery adapter for broadcast.run Omni SMS (GET + query params)."""

    provider_name = constants.PROVIDER_BROADCAST_SMS

    def __init__(self, **_kwargs) -> None:
        # Accept factory DI kwargs (configuration/audit/metrics/transport) unused here.
        pass

    def _resolve_api_key(self) -> str:
        key = getattr(settings, "SMS_API_KEY", None) or os.environ.get("SMS_API_KEY", "")
        key = str(key or "").strip()
        if not key:
            raise ConfigurationException(
                "SMS_API_KEY is required for broadcast_sms provider."
            )
        return key

    def send(self, request: ProviderRequest) -> ProviderResponse:
        """Deliver an engine-generated OTP via broadcast.run SMS API."""

        if not isinstance(request, ProviderRequest):
            raise ValidationException("Provider request must be a ProviderRequest.")
        if not request.destination:
            raise ValidationException("Provider request requires destination.")
        if not request.message:
            raise ValidationException("Provider request requires message.")

        api_key = self._resolve_api_key()
        # request.message is the engine OTP only — never log or store it.
        text = _OTP_SMS_TEMPLATE.format(otp=request.message)
        number = _normalize_number(request.destination)

        params = {
            "ApiKey": api_key,
            "Number": number,
            "SenderId": SENDER_ID,
            "Text": text,
            "PeId": PE_ID,
            "DLTTemplateId": DLT_TEMPLATE_ID,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        prepared = requests.Request("GET", SEND_URL, params=params, headers=headers).prepare()
        logger.info(
            "Broadcast SMS Request",
            extra={
                "url": _redact_url(prepared.url or SEND_URL),
                "headers": {"Authorization": "Bearer ***"},
            },
        )

        try:
            response = requests.get(
                SEND_URL,
                params=params,
                headers=headers,
                timeout=TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            logger.error("Broadcast SMS timeout", exc_info=True)
            raise ProviderTimeoutException("broadcast_sms request timed out.") from exc
        except requests.ConnectionError as exc:
            logger.error("Broadcast SMS connection error", exc_info=True)
            raise ProviderUnavailableException(
                "broadcast_sms provider unavailable."
            ) from exc

        logger.info(
            "Broadcast SMS Response",
            extra={
                "status": response.status_code,
                "body": response.text[:1000],
            },
        )

        if response.status_code != 200:
            raise ProviderFailureException(
                f"broadcast_sms delivery failed with HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        provider_reference = _parse_provider_reference(response)
        return ProviderResponse(
            accepted=True,
            provider_name=self.provider_name,
            provider_reference=provider_reference,
            metadata={},
        )
