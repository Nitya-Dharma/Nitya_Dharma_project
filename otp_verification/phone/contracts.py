"""Phone service placeholders with no normalization logic yet."""


class PhoneNormalizer:
    """Future canonical phone normalization service."""

    def normalize(self, raw_phone: str) -> str:
        raise NotImplementedError("Phone normalization is implemented in Phase 2 Task 4.")


class PhoneFormatter:
    """Future phone formatting service."""

    def format(self, canonical_phone: str) -> str:
        raise NotImplementedError("Phone formatting is implemented in a later OTP phase.")


class PhoneValidator:
    """Future phone validation service."""

    def validate(self, raw_phone: str) -> None:
        raise NotImplementedError("Phone validation is implemented in Phase 2 Task 4.")


class CountryResolver:
    """Future country resolution service for phone numbers."""

    def resolve(self, raw_phone: str) -> str:
        raise NotImplementedError("Country resolution is implemented in Phase 2 Task 4.")


class PhoneParser:
    """Future parser for raw phone input."""

    def parse(self, raw_phone: str) -> object:
        raise NotImplementedError("Phone parsing is implemented in Phase 2 Task 4.")
