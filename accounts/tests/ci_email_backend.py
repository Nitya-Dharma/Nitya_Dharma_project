"""
CI-only recording file email backend for ZeptoMail integration QA.

Never used by production settings. Writes messages under EMAIL_FILE_PATH and
records an atomic per-correlation sidecar from the worker process only.

Controlled failure-before-send is driven by files under:
  {EMAIL_FILE_PATH}/_fail/{corr}
containing a positive integer N; the next N send attempts for that corr raise
before writing any message (Celery retries can then succeed).

Attempt records are written under:
  {EMAIL_FILE_PATH}/_attempts/{corr}/NNNN.json
before the fail-before-send check (so retries are observable).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.filebased import EmailBackend as FileEmailBackend

CORR_RE = re.compile(r"ndcorr\.([0-9a-f]{8,32})\.ndcorr", re.IGNORECASE)


def extract_corr(*parts: str) -> str | None:
    for part in parts:
        if not part:
            continue
        match = CORR_RE.search(str(part))
        if match:
            return match.group(1).lower()
    return None


def make_corr_token(corr: str) -> str:
    return f"ndcorr.{corr.lower()}.ndcorr"


def _allowed_email_root() -> Path:
    raw = getattr(
        settings,
        "INTEGRATION_CI_EMAIL_ALLOWED_ROOT",
        "/tmp/nitya-dharma-integration-mail",
    )
    return Path(str(raw)).resolve()


def email_root() -> Path:
    root = getattr(settings, "EMAIL_FILE_PATH", None) or os.environ.get(
        "INTEGRATION_CI_EMAIL_FILE_PATH", ""
    )
    if not root:
        raise ImproperlyConfigured(
            "EMAIL_FILE_PATH / INTEGRATION_CI_EMAIL_FILE_PATH required"
        )
    path = Path(root)
    if not path.is_absolute():
        raise ImproperlyConfigured("EMAIL_FILE_PATH must be absolute")
    if ".." in path.parts:
        raise ImproperlyConfigured("EMAIL_FILE_PATH must not contain '..'")
    path.mkdir(parents=True, exist_ok=True)
    resolved = path.resolve()
    try:
        resolved.relative_to(_allowed_email_root())
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"EMAIL_FILE_PATH {resolved} escapes CI email root "
            f"{_allowed_email_root()}"
        ) from exc
    (resolved / "_executed").mkdir(parents=True, exist_ok=True)
    (resolved / "_fail").mkdir(parents=True, exist_ok=True)
    (resolved / "_attempts").mkdir(parents=True, exist_ok=True)
    return resolved


def _atomic_write_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        dir=str(target.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def _validate_corr(corr: str | None) -> str:
    if not corr or not re.fullmatch(r"[0-9a-f]{8,32}", corr):
        raise ImproperlyConfigured(
            "RecordingFileEmailBackend require a ndcorr.<hex>.ndcorr "
            f"token (got corr={corr!r})."
        )
    return corr


def _record_attempt(corr: str, message) -> int:
    """Record a worker attempt before fail-before-send / email write."""
    corr = _validate_corr(corr)
    attempts_dir = email_root() / "_attempts" / corr
    attempts_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(attempts_dir.glob("*.json"))
    attempt_no = len(existing) + 1
    payload = {
        "corr": corr,
        "attempt": attempt_no,
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "role": "worker",
        "subject": getattr(message, "subject", "") or "",
        "to": [str(x) for x in (getattr(message, "to", None) or [])],
        "ts": time.time(),
        "phase": "pre_send",
    }
    _atomic_write_text(
        attempts_dir / f"{attempt_no:04d}.json",
        json.dumps(payload, sort_keys=True),
    )
    return attempt_no


def count_attempts(corr: str) -> int:
    corr = _validate_corr(corr)
    attempts_dir = email_root() / "_attempts" / corr
    if not attempts_dir.exists():
        return 0
    return len(list(attempts_dir.glob("*.json")))


def fail_counter_path(corr: str) -> Path:
    return email_root() / "_fail" / _validate_corr(corr)


def _consume_fail_counter(corr: str) -> None:
    """Raise if a positive fail-before-send counter remains for corr."""
    corr = _validate_corr(corr)
    fail_path = fail_counter_path(corr)
    if not fail_path.exists():
        return
    raw = fail_path.read_text(encoding="utf-8").strip()
    try:
        remaining = int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"Invalid fail-before-send counter at {fail_path}: {raw!r}"
        ) from exc
    if remaining <= 0:
        try:
            fail_path.unlink()
        except OSError:
            pass
        return
    remaining -= 1
    if remaining <= 0:
        try:
            fail_path.unlink()
        except OSError:
            pass
    else:
        _atomic_write_text(fail_path, str(remaining))
    raise RuntimeError(
        f"ci-forced-send-failure for corr={corr} "
        f"(remaining_after_decrement={remaining})"
    )


def count_logical_messages_for_corr(corr: str) -> int:
    """Count MIME blocks under EMAIL_FILE_PATH that contain the correlation token."""
    token = make_corr_token(_validate_corr(corr))
    root = email_root()
    count = 0
    token_bytes = token.lower().encode("utf-8")
    for path in root.glob("*.log"):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        # filebased backend separates messages with 79 dashes.
        for block in data.split(b"-" * 79):
            if token_bytes in block.lower():
                count += 1
    return count


def wait_for_worker_execution(
    corr: str,
    *,
    timeout_seconds: float = 60.0,
    poll_seconds: float = 0.25,
    min_messages: int = 1,
) -> dict:
    """
    Poll for the atomic execution sidecar and logical message count.

    A missing sidecar is never treated as success.
    Does not claim exactly-once delivery.
    """
    corr = _validate_corr(corr)
    deadline = time.time() + timeout_seconds
    executed = email_root() / "_executed" / f"{corr}.json"
    last_count = 0
    while time.time() < deadline:
        last_count = count_logical_messages_for_corr(corr)
        if executed.exists() and last_count >= min_messages:
            payload = json.loads(executed.read_text(encoding="utf-8"))
            return {"sidecar": payload, "message_count": last_count}
        time.sleep(poll_seconds)
    raise AssertionError(
        f"Timed out waiting for worker execution of corr={corr}; "
        f"sidecar_exists={executed.exists()} message_count={last_count}. "
        "Missing sidecar is not treated as successful worker verification."
    )


class RecordingFileEmailBackend(FileEmailBackend):
    """
    File-based backend that only sends when INTEGRATION_CI_EMAIL_ROLE=worker.

    Validates correlation/metadata before writing mail. Sidecar instrumentation
    failures after a successful write are swallowed so Celery does not retry an
    already-sent message.
    """

    def send_messages(self, email_messages):
        role = (
            getattr(settings, "INTEGRATION_CI_EMAIL_ROLE", None)
            or os.environ.get("INTEGRATION_CI_EMAIL_ROLE", "")
        ).strip().lower()
        if role != "worker":
            raise ImproperlyConfigured(
                "RecordingFileEmailBackend refuse-closed: process is not the "
                f"integration worker (INTEGRATION_CI_EMAIL_ROLE={role!r}). "
                "Test processes must only enqueue tasks; the worker sends."
            )

        if not email_messages:
            return 0

        # Validate correlation IDs and paths before any email write.
        prepared: list[tuple[object, str]] = []
        email_root()  # validates path confinement
        for message in email_messages:
            corr = _validate_corr(self._corr_for_message(message))
            prepared.append((message, corr))

        # Record attempts, then apply controlled failure-before-send.
        for message, corr in prepared:
            _record_attempt(corr, message)
            _consume_fail_counter(corr)

        sent = super().send_messages(email_messages)

        # Sidecar is test instrumentation only — never raise after a successful
        # write (would cause Celery to retry an already-sent message).
        for message, corr in prepared:
            try:
                self._write_sidecar(corr, message)
            except Exception as exc:  # noqa: BLE001 — instrumentation must not retry mail
                try:
                    _atomic_write_text(
                        email_root() / "_executed" / f"{corr}.sidecar_error",
                        f"{type(exc).__name__}: {exc}\n",
                    )
                except Exception:  # noqa: BLE001
                    pass
        return sent

    def _corr_for_message(self, message) -> str | None:
        recipients = []
        for attr in ("to", "cc", "bcc", "recipients"):
            value = getattr(message, attr, None)
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    pass
            if value:
                recipients.extend(str(x) for x in value)
        subject = getattr(message, "subject", "") or ""
        body = getattr(message, "body", "") or ""
        return extract_corr(subject, body, *recipients)

    def _write_sidecar(self, corr: str, message) -> None:
        payload = {
            "corr": corr,
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "role": "worker",
            "subject": getattr(message, "subject", "") or "",
            "to": [str(x) for x in (getattr(message, "to", None) or [])],
            "ts": time.time(),
        }
        target = email_root() / "_executed" / f"{corr}.json"
        _atomic_write_text(target, json.dumps(payload, sort_keys=True))
