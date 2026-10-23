"""Broadcast.run / Omni SMS API provider — delivery only, no OTP ownership."""

from __future__ import annotations

import json
import logging
import os

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
POST_SEND_URL = "https://dashboard.broadcast.run/api/v1/send"
SENDER_ID = "NDHRMA"
PE_ID = "1701177338710464858"
DLT_TEMPLATE_ID = "1777178575487318004"
CHAIN_VALUE = "1701177338710464858,1702157434240941334"
TIMEOUT_SECONDS = 10

# GET transport embeds the engine OTP into the approved wording via {otp}.
_OTP_SMS_TEMPLATE = (
    "Hello Your Nitya Dharma Registration OTP is {otp} "
    "It is valid for 10 minutes. Please do not share this OTP with anyone. "
    "https://nityadharma.com"
)

# POST transport keeps approved wording; provider substitutes {#var1#}.
_OTP_SMS_TEMPLATE_POST = (
    "Hello Your Nitya Dharma Registration OTP is {#var1#} "
    "It is valid for 10 minutes. Please do not share this OTP with anyone. "
    "https://nityadharma.com"
)


def _normalize_number(destination: str) -> str:
    """Ensure Indian mobiles are sent as 91XXXXXXXXXX when possible."""

    raw = str(destination).strip()
    if raw.startswith("+"):
        raw = raw[1:]
    if len(raw) == 10 and raw.isdigit():
        return f"91{raw}"
    return raw


def _resolve_transport() -> str:
    """Return 'get' or 'post'. Absent/empty settings+env => 'get'."""

    setting_raw = getattr(settings, "BROADCAST_SMS_TRANSPORT", None)
    if setting_raw is not None and str(setting_raw).strip() != "":
        value = str(setting_raw).strip().lower()
    else:
        value = str(os.environ.get("BROADCAST_SMS_TRANSPORT", "") or "").strip().lower()

    if value == "":
        return "get"
    if value in {"get", "post"}:
        return value
    raise ConfigurationException(
        "BROADCAST_SMS_TRANSPORT must be 'get' or 'post'."
    )


def _parse_provider_reference(response: requests.Response) -> str:
    # Raise outside the handler so a response body inside ValueError is not chained.
    non_json = False
    try:
        payload = response.json()
    except ValueError:
        non_json = True
    if non_json:
        raise ProviderFailureException(
            "broadcast_sms returned a non-JSON response."
        )

    if not isinstance(payload, dict):
        raise ProviderFailureException(
            "broadcast_sms returned an unexpected response format."
        )
    code = str(payload.get("code") or "").strip()
    if code and code != "200":
        raise ProviderFailureException(
            "broadcast_sms delivery failed with a non-success API code."
        )

    message_raw = payload.get("message")
    if isinstance(message_raw, str) and message_raw.strip():
        try:
            entries = json.loads(message_raw)
        except (TypeError, ValueError):
            entries = None
        if isinstance(entries, list) and entries:
            first_entry = entries[0]
            if isinstance(first_entry, dict):
                message_id = str(first_entry.get("messageId") or "").strip()
                if message_id:
                    return message_id

    raise ProviderFailureException(
        "broadcast_sms success response missing provider messageId."
    )


class BroadcastSmsProvider(BaseOTPProvider):
    """SMS delivery adapter for broadcast.run (GET default; optional POST)."""

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

        transport = _resolve_transport()
        api_key = self._resolve_api_key()
        number = _normalize_number(request.destination)

        if transport == "get":
            return self._send_get(
                api_key=api_key,
                number=number,
                otp_code=str(request.message),
            )
        return self._send_post(
            api_key=api_key,
            number=number,
            otp_code=str(request.message),
        )

    def _send_get(
        self, *, api_key: str, number: str, otp_code: str
    ) -> ProviderResponse:
        # request.message / otp_code is the engine OTP only — never log or store it.
        text = _OTP_SMS_TEMPLATE.format(otp=otp_code)

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

        logger.info(
            "Broadcast SMS request started",
            extra={
                "provider_name": self.provider_name,
                "outcome": "request_started",
                "transport": "get",
            },
        )

        # Record transport failures, then raise outside this handler. The requests
        # exception message can contain the URL, API key, OTP, and phone number.
        transport_error: ProviderTimeoutException | ProviderUnavailableException | None = None
        try:
            response = requests.get(
                SEND_URL,
                params=params,
                headers=headers,
                timeout=TIMEOUT_SECONDS,
            )
        except requests.Timeout:
            logger.error(
                "Broadcast SMS timeout",
                extra={
                    "provider_name": self.provider_name,
                    "outcome": "timeout",
                    "transport": "get",
                },
            )
            transport_error = ProviderTimeoutException(
                "broadcast_sms request timed out."
            )
        except requests.ConnectionError:
            logger.error(
                "Broadcast SMS connection error",
                extra={
                    "provider_name": self.provider_name,
                    "outcome": "unavailable",
                    "transport": "get",
                },
            )
            transport_error = ProviderUnavailableException(
                "broadcast_sms provider unavailable."
            )
        if transport_error is not None:
            raise transport_error

        logger.info(
            "Broadcast SMS response received",
            extra={
                "provider_name": self.provider_name,
                "http_status": response.status_code,
                "outcome": "http_response",
                "transport": "get",
            },
        )

        if response.status_code != 200:
            raise ProviderFailureException(
                f"broadcast_sms delivery failed with HTTP {response.status_code}."
            )

        provider_reference = _parse_provider_reference(response)
        return ProviderResponse(
            accepted=True,
            provider_name=self.provider_name,
            provider_reference=provider_reference,
            metadata={},
        )

    def _send_post(
        self, *, api_key: str, number: str, otp_code: str
    ) -> ProviderResponse:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "channel": "SMS",
            "to": [number],
            "from": SENDER_ID,
            "content": {
                "data": {
                    "dlttemplateid": DLT_TEMPLATE_ID,
                    "text": _OTP_SMS_TEMPLATE_POST,
                    "peid": PE_ID,
                    "chainvalue": CHAIN_VALUE,
                },
                "params": {"var1": otp_code},
            },
        }

        logger.info(
            "Broadcast SMS request started",
            extra={
                "provider_name": self.provider_name,
                "outcome": "request_started",
                "transport": "post",
            },
        )

        transport_error: ProviderTimeoutException | ProviderUnavailableException | None = None
        try:
            response = requests.post(
                POST_SEND_URL,
                json=body,
                headers=headers,
                timeout=TIMEOUT_SECONDS,
            )
        except requests.Timeout:
            logger.error(
                "Broadcast SMS timeout",
                extra={
                    "provider_name": self.provider_name,
                    "outcome": "timeout",
                    "transport": "post",
                },
            )
            transport_error = ProviderTimeoutException(
                "broadcast_sms request timed out."
            )
        except requests.ConnectionError:
            logger.error(
                "Broadcast SMS connection error",
                extra={
                    "provider_name": self.provider_name,
                    "outcome": "unavailable",
                    "transport": "post",
                },
            )
            transport_error = ProviderUnavailableException(
                "broadcast_sms provider unavailable."
            )
        if transport_error is not None:
            raise transport_error

        logger.info(
            "Broadcast SMS response received",
            extra={
                "provider_name": self.provider_name,
                "http_status": response.status_code,
                "outcome": "http_response",
                "transport": "post",
            },
        )

        if response.status_code != 200:
            raise ProviderFailureException(
                f"broadcast_sms delivery failed with HTTP {response.status_code}."
            )

        provider_reference = _parse_provider_reference(response)
        return ProviderResponse(
            accepted=True,
            provider_name=self.provider_name,
            provider_reference=provider_reference,
            metadata={},
        )
