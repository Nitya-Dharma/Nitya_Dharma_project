"""
Custom email backends for production when SMTP is blocked (e.g. Railway Free/Hobby).

ResendBackend: sends via Resend HTTP API (HTTPS, port 443) so it works where
outbound SMTP (port 587) is blocked. Set RESEND_API_KEY and RESEND_FROM_EMAIL in env.
"""
import json
import logging
import urllib.error
import urllib.request
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class ResendBackend(BaseEmailBackend):
    """
    Send email via Resend API (HTTPS). Use when SMTP is blocked (e.g. Railway).
    Env: RESEND_API_KEY (required), RESEND_FROM_EMAIL (e.g. 'Nitya Dharma <onboarding@resend.dev>'
    or your verified domain).
    """

    def __init__(self, api_key=None, from_email=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        from django.conf import settings
        self._api_key = api_key or getattr(settings, "RESEND_API_KEY", "") or ""
        self._from_email = from_email or getattr(settings, "RESEND_FROM_EMAIL", None) or getattr(settings, "DEFAULT_FROM_EMAIL", "")

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self._api_key:
            if not self.fail_silently:
                raise ValueError("ResendBackend: RESEND_API_KEY is not set")
            return 0
        sent = 0
        for message in email_messages:
            try:
                self._send_one(message)
                sent += 1
            except Exception as e:
                logger.exception("ResendBackend send failed: %s", e)
                if not self.fail_silently:
                    raise
        return sent

    def _send_one(self, message):
        to_list = list(message.to)
        if not to_list:
            return
        from_addr = message.from_email or self._from_email
        if not from_addr:
            raise ValueError("ResendBackend: from email is missing (set RESEND_FROM_EMAIL or DEFAULT_FROM_EMAIL)")
        html_content = None
        if hasattr(message, "alternatives") and message.alternatives:
            for alt_content, alt_type in message.alternatives:
                if alt_type == "text/html":
                    html_content = alt_content
                    break
        if not html_content and message.body:
            html_content = message.body.replace("\n", "<br>\n")

        payload = {
            "from": from_addr,
            "to": to_list,
            "subject": message.subject,
        }
        if html_content:
            payload["html"] = html_content
        if message.body:
            payload["text"] = message.body
        if "html" not in payload and "text" not in payload:
            payload["text"] = ""

        req = urllib.request.Request(
            RESEND_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status not in (200, 201, 202):
                    body = resp.read().decode("utf-8", errors="replace")
                    raise Exception(f"Resend API returned {resp.status}: {body}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise Exception(f"Resend API error {e.code}: {body}")
        except urllib.error.URLError as e:
            raise Exception(f"Resend API request failed: {e.reason}")
