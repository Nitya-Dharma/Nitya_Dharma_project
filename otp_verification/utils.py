"""Small reusable helpers for the OTP foundation package."""


def module_path(*parts: str) -> str:
    """Return a dotted module path for internal documentation or registration."""

    return ".".join(part.strip(".") for part in parts if part)
