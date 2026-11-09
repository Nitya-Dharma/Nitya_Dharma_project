"""Settings-safe helpers for additive ZeptoMail env parsing (no Django imports)."""


def parse_zeptomail_enabled_flows(raw: str | None) -> frozenset[str]:
    """Parse comma-separated allowlist; empty/blank → no ZeptoMail traffic."""
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in str(raw).split(",") if part.strip())
