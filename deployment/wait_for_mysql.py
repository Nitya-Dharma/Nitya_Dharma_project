#!/usr/bin/env python3
"""
Wait until MySQL is reachable on TCP (host/port from env).
Used by Docker Compose so Gunicorn does not start before mysqld accepts connections.

Stdlib only — no Django, no mysqlclient.
"""
from __future__ import annotations

import os
import socket
import sys
import time


def _host() -> str:
    return (
        os.environ.get("DB_HOST")
        or os.environ.get("DATABASE_HOST")
        or "db"
    )


def _port() -> int:
    raw = os.environ.get("DB_PORT") or os.environ.get("DATABASE_PORT") or "3306"
    return int(raw)


INTERVAL_SEC = 2
MAX_WAIT_SEC = 30
CONNECT_TIMEOUT_SEC = 2


def main() -> int:
    host = _host()
    port = _port()
    deadline = time.monotonic() + MAX_WAIT_SEC

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SEC):
                print(
                    f"[wait_for_mysql] {host}:{port} is accepting connections.",
                    flush=True,
                )
                return 0
        except OSError as exc:
            remaining = max(0.0, deadline - time.monotonic())
            print(
                f"[wait_for_mysql] {host}:{port} not ready ({exc!s}); "
                f"retry in {INTERVAL_SEC}s (timeout in {remaining:.0f}s)...",
                flush=True,
            )
            time.sleep(INTERVAL_SEC)

    print(
        f"[wait_for_mysql] Timed out after {MAX_WAIT_SEC}s waiting for {host}:{port}.",
        file=sys.stderr,
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
