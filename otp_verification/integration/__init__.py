"""Integration boundaries for future communication with stable systems."""

from otp_verification.integration.boundaries import ApprovalGateway
from otp_verification.integration.boundaries import AuthenticationGateway
from otp_verification.integration.boundaries import EmailVerificationGateway
from otp_verification.integration.boundaries import ReferralGateway
from otp_verification.integration.boundaries import RegistrationGateway
from otp_verification.integration.boundaries import TransactionGateway

__all__ = [
    "ApprovalGateway",
    "AuthenticationGateway",
    "EmailVerificationGateway",
    "ReferralGateway",
    "RegistrationGateway",
    "TransactionGateway",
]
