"""Durable OTP challenge persistence models (Phase 2 Task 8)."""

from __future__ import annotations

from django.db import models


class OTPChallenge(models.Model):
    """Durable challenge row mirroring ChallengeRecord (hash only, never plaintext OTP)."""

    challenge_id = models.CharField(max_length=64, primary_key=True)
    flow_type = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=32, db_index=True)
    otp_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField(db_index=True)
    max_attempts = models.PositiveIntegerField()
    attempt_count = models.PositiveIntegerField(default=0)
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "otp_verification"
        indexes = [
            models.Index(fields=["status", "expires_at"], name="otp_chal_status_exp_idx"),
        ]
        verbose_name = "OTP challenge"
        verbose_name_plural = "OTP challenges"

    def __str__(self) -> str:
        return f"{self.challenge_id} ({self.status})"


class OTPReplayToken(models.Model):
    """Durable consumed-challenge marker for cross-worker replay protection."""

    token = models.CharField(max_length=64, primary_key=True)
    consumed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "otp_verification"
        verbose_name = "OTP replay token"
        verbose_name_plural = "OTP replay tokens"

    def __str__(self) -> str:
        return self.token
