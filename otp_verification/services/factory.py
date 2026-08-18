"""Dependency-injection factory for the OTP engine and provider layer."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from django.conf import settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration, get_configuration, validate_msg91_configuration
from otp_verification.enums import DeliveryChannel
from otp_verification.exceptions import ConfigurationException
from otp_verification.interfaces.providers import BaseOTPProvider
from otp_verification.interfaces.security import BaseReplayProtector
from otp_verification.interfaces.storage import BaseChallengeRepository
from otp_verification.providers.base import ProviderDescriptor
from otp_verification.providers.metrics import ProviderMetrics
from otp_verification.providers.registry import OTPProviderRegistry
from otp_verification.providers.resolver import ProviderResolver, load_provider_class
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.core import ChallengeManager, OTPGenerator, OTPHasher, OTPValidator
from otp_verification.services.orchestration import ProviderOrchestrator
from otp_verification.services.policies import AttemptTracker, LockoutManager
from otp_verification.services.support import AuditLogger, StructuredLoggingBackend
from otp_verification.storage.django_db import DjangoChallengeRepository
from otp_verification.storage.memory import InMemoryChallengeRepository
from otp_verification.storage.replay_db import DatabaseReplayProtection
from otp_verification.transport.http import RequestsHttpTransport

# Process-local defaults for memory backend (tests / explicit OTP_CHALLENGE_STORAGE=memory).
_process_repository: InMemoryChallengeRepository | None = None
_process_replay_protector: ReplayProtection | None = None
_process_storage_lock = Lock()


def get_challenge_storage_backend() -> str:
    """Return configured challenge storage backend (`database` or `memory`)."""

    raw = getattr(
        settings,
        constants.FEATURE_FLAG_CHALLENGE_STORAGE,
        constants.DEFAULT_CHALLENGE_STORAGE,
    )
    backend = str(raw or constants.DEFAULT_CHALLENGE_STORAGE).strip().lower()
    if backend not in constants.CHALLENGE_STORAGE_CHOICES:
        raise ConfigurationException(
            f"{constants.FEATURE_FLAG_CHALLENGE_STORAGE} must be one of "
            f"{constants.CHALLENGE_STORAGE_CHOICES}."
        )
    return backend


def get_process_challenge_repository() -> InMemoryChallengeRepository:
    """Return the process-scoped in-memory challenge repository."""

    global _process_repository
    with _process_storage_lock:
        if _process_repository is None:
            _process_repository = InMemoryChallengeRepository()
        return _process_repository


def get_process_replay_protector() -> ReplayProtection:
    """Return the process-scoped replay protector."""

    global _process_replay_protector
    with _process_storage_lock:
        if _process_replay_protector is None:
            _process_replay_protector = ReplayProtection()
        return _process_replay_protector


def resolve_challenge_repository() -> BaseChallengeRepository:
    """Resolve the configured challenge repository implementation."""

    if get_challenge_storage_backend() == constants.CHALLENGE_STORAGE_MEMORY:
        return get_process_challenge_repository()
    return DjangoChallengeRepository()


def resolve_replay_protector() -> BaseReplayProtector:
    """Resolve the configured replay protector implementation."""

    if get_challenge_storage_backend() == constants.CHALLENGE_STORAGE_MEMORY:
        return get_process_replay_protector()
    return DatabaseReplayProtection()


def reset_otp_process_storage() -> None:
    """Clear process-scoped OTP storage (unit tests / worker recycle helpers).

    For the database backend, also clears durable challenge and replay rows when
    the DB is available (TestCase). Memory backend clears process singletons only.
    """

    global _process_repository, _process_replay_protector
    with _process_storage_lock:
        if _process_repository is not None:
            _process_repository.clear()
        if _process_replay_protector is not None:
            _process_replay_protector.clear()
        _process_repository = None
        _process_replay_protector = None

    try:
        if get_challenge_storage_backend() == constants.CHALLENGE_STORAGE_DATABASE:
            DjangoChallengeRepository().clear()
            DatabaseReplayProtection().clear()
    except Exception:
        # Tests without migrations / SimpleTestCase may not touch DB.
        pass


@dataclass
class OTPEngine:
    """Wired OTP engine graph for internal use."""

    configuration: OTPConfiguration
    repository: BaseChallengeRepository
    challenge_manager: ChallengeManager
    generator: OTPGenerator
    hasher: OTPHasher
    validator: OTPValidator
    attempt_tracker: AttemptTracker
    lockout_manager: LockoutManager
    replay_protector: BaseReplayProtector
    audit_logger: AuditLogger


@dataclass
class OTPProviderRuntime:
    """Wired provider + orchestration graph for internal use."""

    configuration: OTPConfiguration
    engine: OTPEngine
    registry: OTPProviderRegistry
    resolver: ProviderResolver
    metrics: ProviderMetrics
    provider: BaseOTPProvider
    orchestrator: ProviderOrchestrator
    transport: RequestsHttpTransport


def _register_default_providers(registry: OTPProviderRegistry) -> None:
    if not registry.has_provider(constants.PROVIDER_MOCK_SMS):
        registry.register(
            ProviderDescriptor(
                name=constants.PROVIDER_MOCK_SMS,
                dotted_path=constants.MOCK_PROVIDER_DOTTED_PATH,
                channel=DeliveryChannel.SMS,
                supports_mock_mode=True,
            )
        )
    if not registry.has_provider(constants.PROVIDER_MSG91):
        registry.register(
            ProviderDescriptor(
                name=constants.PROVIDER_MSG91,
                dotted_path=constants.MSG91_PROVIDER_DOTTED_PATH,
                channel=DeliveryChannel.SMS,
                supports_mock_mode=False,
            )
        )
    if not registry.has_provider(constants.PROVIDER_BROADCAST_SMS):
        registry.register(
            ProviderDescriptor(
                name=constants.PROVIDER_BROADCAST_SMS,
                dotted_path=constants.BROADCAST_SMS_PROVIDER_DOTTED_PATH,
                channel=DeliveryChannel.SMS,
                supports_mock_mode=False,
            )
        )


def build_otp_engine(
    *,
    configuration: OTPConfiguration | None = None,
    repository: BaseChallengeRepository | None = None,
    replay_protector: BaseReplayProtector | None = None,
    audit_logger: AuditLogger | None = None,
) -> OTPEngine:
    """Resolve OTP engine dependencies through interfaces."""

    config = configuration or get_configuration()
    # Default repository/replay follow OTP_CHALLENGE_STORAGE. Callers may inject
    # isolated instances (tests) via repository=/replay_protector=.
    repo = repository if repository is not None else resolve_challenge_repository()
    hasher = OTPHasher()
    generator = OTPGenerator(configuration=config)
    attempt_tracker = AttemptTracker(repository=repo)
    protector = (
        replay_protector if replay_protector is not None else resolve_replay_protector()
    )
    audit = audit_logger or AuditLogger(backend=StructuredLoggingBackend())
    validator = OTPValidator(
        hasher=hasher,
        repository=repo,
        attempt_tracker=attempt_tracker,
    )
    lockout_manager = LockoutManager(repository=repo, configuration=config)
    challenge_manager = ChallengeManager(
        repository=repo,
        audit_logger=audit,
        generator=generator,
        hasher=hasher,
        validator=validator,
        attempt_tracker=attempt_tracker,
        replay_protector=protector,
        configuration=config,
        policies=(lockout_manager,),
    )
    return OTPEngine(
        configuration=config,
        repository=repo,
        challenge_manager=challenge_manager,
        generator=generator,
        hasher=hasher,
        validator=validator,
        attempt_tracker=attempt_tracker,
        lockout_manager=lockout_manager,
        replay_protector=protector,
        audit_logger=audit,
    )


def build_otp_provider_runtime(
    *,
    configuration: OTPConfiguration | None = None,
    engine: OTPEngine | None = None,
    registry: OTPProviderRegistry | None = None,
    audit_logger: AuditLogger | None = None,
    metrics: ProviderMetrics | None = None,
    transport: RequestsHttpTransport | None = None,
) -> OTPProviderRuntime:
    """Wire engine + registry + providers + orchestrator via DI only."""

    config = configuration or (engine.configuration if engine else get_configuration())
    if config.provider == constants.PROVIDER_MSG91:
        validate_msg91_configuration(config)

    audit = audit_logger or (engine.audit_logger if engine else None) or AuditLogger(
        backend=StructuredLoggingBackend()
    )
    otp_engine = engine or build_otp_engine(configuration=config, audit_logger=audit)
    provider_registry = registry or OTPProviderRegistry()
    _register_default_providers(provider_registry)
    provider_metrics = metrics or ProviderMetrics()
    http_transport = transport or RequestsHttpTransport()

    def provider_factory(descriptor: ProviderDescriptor) -> BaseOTPProvider:
        from otp_verification.providers.broadcast_sms import BroadcastSmsProvider
        from otp_verification.providers.mock import MockOTPProvider
        from otp_verification.providers.msg91 import Msg91SmsProvider

        provider_cls = load_provider_class(descriptor.dotted_path)
        if provider_cls is MockOTPProvider:
            return MockOTPProvider(
                configuration=config,
                audit_logger=audit,
                metrics=provider_metrics,
            )
        if provider_cls is Msg91SmsProvider:
            return Msg91SmsProvider(
                configuration=config,
                audit_logger=audit,
                metrics=provider_metrics,
                transport=http_transport,
            )
        if provider_cls is BroadcastSmsProvider:
            return BroadcastSmsProvider()
        return provider_cls(
            configuration=config,
            audit_logger=audit,
            metrics=provider_metrics,
            transport=http_transport,
        )

    resolver = ProviderResolver(
        registry=provider_registry,
        provider_factory=provider_factory,
    )
    provider = resolver.resolve(config.provider)
    orchestrator = ProviderOrchestrator(
        challenge_manager=otp_engine.challenge_manager,
        provider_resolver=resolver,
        audit_logger=audit,
        configuration=config,
    )
    return OTPProviderRuntime(
        configuration=config,
        engine=otp_engine,
        registry=provider_registry,
        resolver=resolver,
        metrics=provider_metrics,
        provider=provider,
        orchestrator=orchestrator,
        transport=http_transport,
    )
