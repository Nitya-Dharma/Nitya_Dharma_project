"""
E10B email-file assertion helper.

Waits for exactly one filebased email written by the Celery worker.
Does not call SMTP, does not start Redis/Docker, does not touch databases.

Expected environment:
  ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR  absolute email output directory
  E10B_WORKER_PID                   optional worker PID for liveness checks
  E10B_ASSERT_TIMEOUT_SEC           optional timeout (default 60)

Exit codes:
  0 success (exactly one matching file)
  2 assertion/environment refusal
  3 timeout / worker crash / wrong file count
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path


EXPECTED_RECIPIENT = "e10b-worker-test@example.invalid"
EXPECTED_SUBJECT = "Nitya Dharma E10B Celery Worker Test"
DEFAULT_TIMEOUT_SEC = 60
POLL_INTERVAL_SEC = 0.5


class AssertRefusal(Exception):
    pass


def _fail(msg: str) -> None:
    raise AssertRefusal(msg)


def _worker_alive(pid: int | None) -> bool:
    if pid is None:
        return True
    if pid <= 0:
        return False
    try:
        # Signal 0: existence check (POSIX). On Windows, os.kill(pid, 0) also works
        # for process existence in CPython.
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except SystemError:
        return False


def _list_email_files(email_dir: Path) -> list[Path]:
    if not email_dir.is_dir():
        _fail(f"Email directory does not exist: {email_dir}")
    files = [p for p in email_dir.iterdir() if p.is_file()]
    return sorted(files)


def _file_matches(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _fail(f"Unable to read email file {path.name}: {exc}")
    has_recipient = EXPECTED_RECIPIENT in text
    has_subject = EXPECTED_SUBJECT in text
    return has_recipient and has_subject


def main() -> int:
    print("E10B assert: verifying exactly one filebased email (not producer .delay)")

    raw_dir = os.environ.get("ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR", "").strip()
    if not raw_dir:
        _fail("ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR is required")
    email_dir = Path(raw_dir)
    if not email_dir.is_absolute():
        _fail("ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR must be absolute")

    timeout_raw = os.environ.get("E10B_ASSERT_TIMEOUT_SEC", "").strip()
    timeout_sec = DEFAULT_TIMEOUT_SEC
    if timeout_raw:
        try:
            timeout_sec = int(timeout_raw)
        except ValueError as exc:
            raise AssertRefusal("E10B_ASSERT_TIMEOUT_SEC must be an integer") from exc
    if timeout_sec < 1:
        _fail("E10B_ASSERT_TIMEOUT_SEC must be >= 1")

    pid: int | None = None
    pid_raw = os.environ.get("E10B_WORKER_PID", "").strip()
    if pid_raw:
        try:
            pid = int(pid_raw)
        except ValueError as exc:
            raise AssertRefusal("E10B_WORKER_PID must be an integer") from exc

    initial = _list_email_files(email_dir)
    if initial:
        _fail(
            f"Email directory must start empty for E10B assert; "
            f"found {len(initial)} file(s)"
        )

    deadline = time.monotonic() + timeout_sec
    last_count = 0
    while time.monotonic() < deadline:
        files = _list_email_files(email_dir)
        last_count = len(files)
        alive = _worker_alive(pid)

        if last_count > 1:
            print(f"E10B assert FAILED: multiple email files ({last_count})")
            return 3

        if last_count == 1:
            path = files[0]
            if not _file_matches(path):
                # Never accept an invalid file as success.
                if not alive:
                    print(
                        "E10B assert FAILED: worker exited and the single email "
                        "file did not match expected recipient/subject"
                    )
                    return 3
                # Worker still alive: keep polling in case of a transient partial write.
                time.sleep(POLL_INTERVAL_SEC)
                continue
            print("E10B assert PASS")
            print(f"  email_file={path.name}")
            print(f"  recipient={EXPECTED_RECIPIENT}")
            print(f"  subject={EXPECTED_SUBJECT}")
            print("  file_count=1")
            print(f"  worker_alive={alive}")
            return 0

        # Zero files.
        if not alive:
            print(
                "E10B assert FAILED: worker process exited without producing "
                "the expected email file"
            )
            return 3
        time.sleep(POLL_INTERVAL_SEC)

    # After the wait window: one final directory inspection (same rules as the loop).
    files = _list_email_files(email_dir)
    last_count = len(files)
    alive = _worker_alive(pid)
    if last_count > 1:
        print(f"E10B assert FAILED: multiple email files ({last_count})")
        return 3
    if last_count == 1:
        path = files[0]
        if _file_matches(path):
            print("E10B assert PASS")
            print(f"  email_file={path.name}")
            print(f"  recipient={EXPECTED_RECIPIENT}")
            print(f"  subject={EXPECTED_SUBJECT}")
            print("  file_count=1")
            print(f"  worker_alive={alive}")
            return 0
        print(
            "E10B assert FAILED: timeout with one email file that did not match "
            "expected recipient/subject"
        )
        return 3
    if not alive:
        print(
            "E10B assert FAILED: timeout; worker exited without the expected email file"
        )
        return 3
    print(
        f"E10B assert FAILED: timeout after {timeout_sec}s "
        f"with file_count={last_count} (expected 1)"
    )
    return 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertRefusal as exc:
        print(f"E10B assert REFUSED: {exc}")
        raise SystemExit(2) from exc
