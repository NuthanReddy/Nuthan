"""
Notification System - Simulation

Simulates a notification service with:
- Multi-channel delivery (Push, SMS, Email) via Strategy pattern
- Template rendering with variable substitution
- User preference filtering (channel opt-in/out, quiet hours, frequency caps)
- Priority queue with 4 priority levels
- Delivery tracking with status logging
- Retry with exponential backoff
- Circuit breaker for provider fault tolerance
- Rate limiting per user per channel

Run:
    .venv\\Scripts\\python.exe SystemDesign\\NotificationSystem\\notification_system.py
"""

from __future__ import annotations

import heapq
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import IntEnum, Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Priority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class ChannelType(str, Enum):
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"


class DeliveryStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    SUPPRESSED = "suppressed"


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Template:
    template_id: str
    name: str
    category: str
    channel_bodies: dict[ChannelType, str]

    def render(self, channel: ChannelType, params: dict[str, str]) -> str:
        body = self.channel_bodies.get(channel, "")
        for key, value in params.items():
            body = body.replace("{{" + key + "}}", value)
        return body


@dataclass
class UserPreference:
    user_id: str
    enabled_channels: dict[ChannelType, bool] = field(default_factory=dict)
    quiet_start_hour: Optional[int] = None
    quiet_end_hour: Optional[int] = None
    # Quiet hours are interpreted in the user's local time. Stored as a fixed
    # UTC offset in hours (e.g. -5 for US Eastern, +5.5 for IST) to stay
    # dependency-free and correct on platforms without an IANA tz database.
    utc_offset_hours: float = 0.0
    frequency_caps: dict[ChannelType, int] = field(default_factory=dict)
    opted_out_categories: set[str] = field(default_factory=set)


@dataclass
class Notification:
    notification_id: str
    user_id: str
    template_id: str
    template_params: dict[str, str]
    channels: list[ChannelType]
    priority: Priority
    category: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(order=True)
class QueueEntry:
    """Wrapper for the priority queue (heapq needs ordering)."""
    priority: int
    created_ts: float
    notification: Notification = field(compare=False)
    channel: ChannelType = field(compare=False)
    rendered_content: str = field(compare=False)


@dataclass
class DeliveryRecord:
    log_id: str
    notification_id: str
    channel: ChannelType
    status: DeliveryStatus
    attempt: int
    latency_ms: int
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Simple circuit breaker for external provider calls."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_sec: float = 10.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_sec
        self.success_threshold = success_threshold
        self.last_failure_time: Optional[float] = None

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        # HALF_OPEN
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.success_count = 0


# ---------------------------------------------------------------------------
# Channel Strategy (Strategy Pattern)
# ---------------------------------------------------------------------------

class NotificationChannel(ABC):
    """Abstract base for delivery channels."""

    def __init__(self, channel_type: ChannelType, failure_rate: float = 0.0):
        self.channel_type = channel_type
        self.failure_rate = failure_rate
        self.circuit_breaker = CircuitBreaker(name=channel_type.value)

    @abstractmethod
    def _do_send(self, user_id: str, content: str) -> tuple[bool, Optional[str]]:
        """Channel-specific send logic. Returns (success, error_message)."""

    def send(self, user_id: str, content: str) -> tuple[bool, Optional[str]]:
        if not self.circuit_breaker.allow_request():
            return False, f"Circuit OPEN for {self.channel_type.value}"
        success, error = self._do_send(user_id, content)
        if success:
            self.circuit_breaker.record_success()
        else:
            self.circuit_breaker.record_failure()
        return success, error


class PushChannel(NotificationChannel):
    def __init__(self, failure_rate: float = 0.1):
        super().__init__(ChannelType.PUSH, failure_rate)

    def _do_send(self, user_id: str, content: str) -> tuple[bool, Optional[str]]:
        latency = random.uniform(0.01, 0.05)
        time.sleep(latency)
        if random.random() < self.failure_rate:
            return False, "FCM timeout"
        return True, None


class SMSChannel(NotificationChannel):
    def __init__(self, failure_rate: float = 0.15):
        super().__init__(ChannelType.SMS, failure_rate)

    def _do_send(self, user_id: str, content: str) -> tuple[bool, Optional[str]]:
        latency = random.uniform(0.02, 0.08)
        time.sleep(latency)
        if random.random() < self.failure_rate:
            return False, "Twilio rate limit"
        return True, None


class EmailChannel(NotificationChannel):
    def __init__(self, failure_rate: float = 0.05):
        super().__init__(ChannelType.EMAIL, failure_rate)

    def _do_send(self, user_id: str, content: str) -> tuple[bool, Optional[str]]:
        latency = random.uniform(0.03, 0.10)
        time.sleep(latency)
        if random.random() < self.failure_rate:
            return False, "SES throttle"
        return True, None


# ---------------------------------------------------------------------------
# Rate Limiter (Sliding Window)
# ---------------------------------------------------------------------------

class RateLimiter:
    """Per-user, per-channel sliding window rate limiter."""

    def __init__(self) -> None:
        # {(user_id, channel): [timestamps]}
        self._windows: dict[tuple[str, ChannelType], list[float]] = defaultdict(list)

    def is_allowed(
        self,
        user_id: str,
        channel: ChannelType,
        limit: int,
        window_seconds: float = 3600.0,
    ) -> bool:
        key = (user_id, channel)
        now = time.time()
        cutoff = now - window_seconds
        # Prune old entries
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]
        if len(self._windows[key]) >= limit:
            return False
        self._windows[key].append(now)
        return True


# ---------------------------------------------------------------------------
# Notification Service
# ---------------------------------------------------------------------------

class NotificationService:
    """
    Central notification service that orchestrates:
    validation -> preference check -> template rendering -> priority queueing
    -> channel dispatch -> delivery tracking -> retry.
    """

    MAX_RETRIES_BY_PRIORITY = {
        Priority.CRITICAL: 5,
        Priority.HIGH: 3,
        Priority.NORMAL: 2,
        Priority.LOW: 1,
    }

    BASE_BACKOFF_SEC = {
        Priority.CRITICAL: 0.05,
        Priority.HIGH: 0.1,
        Priority.NORMAL: 0.2,
        Priority.LOW: 0.5,
    }

    def __init__(self) -> None:
        # Registries
        self.templates: dict[str, Template] = {}
        self.user_prefs: dict[str, UserPreference] = {}

        # Channels (Strategy registry)
        self.channels: dict[ChannelType, NotificationChannel] = {
            ChannelType.PUSH: PushChannel(failure_rate=0.10),
            ChannelType.SMS: SMSChannel(failure_rate=0.15),
            ChannelType.EMAIL: EmailChannel(failure_rate=0.05),
        }

        # Priority queue (min-heap)
        self._queue: list[QueueEntry] = []

        # Delivery log
        self.delivery_log: list[DeliveryRecord] = []

        # Rate limiter
        self.rate_limiter = RateLimiter()

        # Dead letter queue
        self.dlq: list[dict[str, Any]] = []

        # Stats
        self._stats: dict[str, int] = defaultdict(int)

    # -- Template management -------------------------------------------------

    def register_template(self, template: Template) -> None:
        self.templates[template.template_id] = template

    # -- User preference management ------------------------------------------

    def set_user_preference(self, pref: UserPreference) -> None:
        self.user_prefs[pref.user_id] = pref

    def _check_preferences(
        self, user_id: str, channel: ChannelType, category: str
    ) -> tuple[bool, str]:
        """Return (allowed, reason)."""
        pref = self.user_prefs.get(user_id)
        if pref is None:
            return True, "no preferences set (allow all)"

        # Channel opt-out
        if not pref.enabled_channels.get(channel, True):
            return False, f"user opted out of {channel.value}"

        # Category opt-out
        if category in pref.opted_out_categories:
            return False, f"user opted out of category '{category}'"

        # Quiet hours, evaluated in the user's local time (UTC + offset).
        if pref.quiet_start_hour is not None and pref.quiet_end_hour is not None:
            utc_now = datetime.now(timezone.utc)
            local_now = utc_now + timedelta(hours=pref.utc_offset_hours)
            current_hour = local_now.hour
            start, end = pref.quiet_start_hour, pref.quiet_end_hour
            in_quiet = False
            if start > end:  # crosses midnight
                in_quiet = current_hour >= start or current_hour < end
            else:
                in_quiet = start <= current_hour < end
            if in_quiet:
                return False, "quiet hours active"

        # Frequency cap
        cap = pref.frequency_caps.get(channel)
        if cap is not None and not self.rate_limiter.is_allowed(user_id, channel, cap):
            return False, f"frequency cap reached ({cap}/hr) for {channel.value}"

        return True, "allowed"

    # -- Submit notification -------------------------------------------------

    def submit(self, notification: Notification) -> str:
        """Validate, filter, render, and enqueue a notification."""
        # Validate template exists
        template = self.templates.get(notification.template_id)
        if template is None:
            raise ValueError(
                f"Template '{notification.template_id}' not found"
            )

        enqueued_channels: list[str] = []

        for channel in notification.channels:
            # Preference check
            allowed, reason = self._check_preferences(
                notification.user_id, channel, notification.category
            )
            if not allowed:
                self._record_delivery(
                    notification.notification_id,
                    channel,
                    DeliveryStatus.SUPPRESSED,
                    attempt=0,
                    latency_ms=0,
                    error=reason,
                )
                self._stats["suppressed"] += 1
                continue

            # Render content
            rendered = template.render(channel, notification.template_params)

            # Enqueue with priority
            entry = QueueEntry(
                priority=int(notification.priority),
                created_ts=time.time(),
                notification=notification,
                channel=channel,
                rendered_content=rendered,
            )
            heapq.heappush(self._queue, entry)
            enqueued_channels.append(channel.value)
            self._stats["enqueued"] += 1

        return (
            f"[{notification.notification_id}] "
            f"enqueued={enqueued_channels}"
        )

    # -- Process queue -------------------------------------------------------

    def process_queue(self) -> None:
        """Drain the priority queue, dispatching each item."""
        while self._queue:
            entry = heapq.heappop(self._queue)
            self._dispatch_with_retry(entry)

    def _dispatch_with_retry(self, entry: QueueEntry) -> None:
        max_retries = self.MAX_RETRIES_BY_PRIORITY[
            Priority(entry.priority)
        ]
        base_backoff = self.BASE_BACKOFF_SEC[Priority(entry.priority)]

        for attempt in range(1, max_retries + 1):
            channel_impl = self.channels[entry.channel]
            start = time.time()
            success, error = channel_impl.send(
                entry.notification.user_id, entry.rendered_content
            )
            latency_ms = int((time.time() - start) * 1000)

            if success:
                self._record_delivery(
                    entry.notification.notification_id,
                    entry.channel,
                    DeliveryStatus.DELIVERED,
                    attempt=attempt,
                    latency_ms=latency_ms,
                )
                self._stats["delivered"] += 1
                return

            # Retry with exponential backoff + jitter
            if attempt < max_retries:
                delay = base_backoff * (2 ** (attempt - 1))
                jitter = random.uniform(0, delay * 0.5)
                time.sleep(delay + jitter)
                self._stats["retries"] += 1
            else:
                # Exhausted retries: record failure and send to DLQ
                self._record_delivery(
                    entry.notification.notification_id,
                    entry.channel,
                    DeliveryStatus.FAILED,
                    attempt=attempt,
                    latency_ms=latency_ms,
                    error=error,
                )
                self._stats["failed"] += 1
                self.dlq.append(
                    {
                        "notification_id": entry.notification.notification_id,
                        "channel": entry.channel.value,
                        "last_error": error,
                        "attempts": attempt,
                    }
                )

    # -- Delivery tracking ---------------------------------------------------

    def _record_delivery(
        self,
        notification_id: str,
        channel: ChannelType,
        status: DeliveryStatus,
        attempt: int,
        latency_ms: int,
        error: Optional[str] = None,
    ) -> None:
        record = DeliveryRecord(
            log_id=str(uuid.uuid4())[:8],
            notification_id=notification_id,
            channel=channel,
            status=status,
            attempt=attempt,
            latency_ms=latency_ms,
            error=error,
        )
        self.delivery_log.append(record)

    # -- Reporting -----------------------------------------------------------

    def print_delivery_report(self) -> None:
        print("\n" + "=" * 78)
        print("DELIVERY REPORT")
        print("=" * 78)

        header = (
            f"{'Notif ID':<14} {'Channel':<8} {'Status':<12} "
            f"{'Attempt':<8} {'Latency':<10} {'Error'}"
        )
        print(header)
        print("-" * 78)

        for rec in self.delivery_log:
            latency_str = f"{rec.latency_ms}ms" if rec.latency_ms > 0 else "-"
            error_str = rec.error or "-"
            print(
                f"{rec.notification_id:<14} {rec.channel.value:<8} "
                f"{rec.status.value:<12} {rec.attempt:<8} "
                f"{latency_str:<10} {error_str}"
            )

    def print_stats(self) -> None:
        print("\n" + "=" * 78)
        print("STATISTICS")
        print("=" * 78)
        for key in ["enqueued", "delivered", "failed", "suppressed", "retries"]:
            print(f"  {key:<14}: {self._stats[key]}")
        print(f"  {'dlq_depth':<14}: {len(self.dlq)}")

    def print_dlq(self) -> None:
        if not self.dlq:
            print("\nDead Letter Queue: empty")
            return
        print("\n" + "=" * 78)
        print("DEAD LETTER QUEUE")
        print("=" * 78)
        for item in self.dlq:
            print(
                f"  notif={item['notification_id']}  "
                f"channel={item['channel']}  "
                f"error={item['last_error']}  "
                f"attempts={item['attempts']}"
            )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _make_id() -> str:
    return str(uuid.uuid4())[:8]


def main() -> None:
    random.seed(42)  # reproducible demo

    svc = NotificationService()

    # -- Register templates --------------------------------------------------
    svc.register_template(
        Template(
            template_id="welcome",
            name="Welcome Message",
            category="transactional",
            channel_bodies={
                ChannelType.PUSH: "Welcome, {{user_name}}! Tap to explore.",
                ChannelType.SMS: "Hi {{user_name}}, welcome aboard! Visit {{url}}",
                ChannelType.EMAIL: (
                    "Subject: Welcome {{user_name}}\n"
                    "Hello {{user_name}},\n"
                    "Thanks for joining. Get started at {{url}}."
                ),
            },
        )
    )

    svc.register_template(
        Template(
            template_id="alert",
            name="Security Alert",
            category="alerts",
            channel_bodies={
                ChannelType.PUSH: "ALERT: {{message}}",
                ChannelType.SMS: "Security alert: {{message}}. Act now.",
                ChannelType.EMAIL: (
                    "Subject: Security Alert\n"
                    "{{message}}\n"
                    "If this was not you, reset your password immediately."
                ),
            },
        )
    )

    svc.register_template(
        Template(
            template_id="promo",
            name="Promotional Offer",
            category="marketing",
            channel_bodies={
                ChannelType.PUSH: "{{discount}} off! Use code {{code}}.",
                ChannelType.EMAIL: (
                    "Subject: Special offer for you!\n"
                    "Get {{discount}} off with code {{code}} at {{url}}."
                ),
            },
        )
    )

    print("Templates registered: welcome, alert, promo")

    # -- Set user preferences ------------------------------------------------
    svc.set_user_preference(
        UserPreference(
            user_id="alice",
            enabled_channels={
                ChannelType.PUSH: True,
                ChannelType.SMS: True,
                ChannelType.EMAIL: True,
            },
            frequency_caps={ChannelType.SMS: 5},
        )
    )

    svc.set_user_preference(
        UserPreference(
            user_id="bob",
            enabled_channels={
                ChannelType.PUSH: True,
                ChannelType.SMS: False,  # Bob opted out of SMS
                ChannelType.EMAIL: True,
            },
            opted_out_categories={"marketing"},  # Bob does not want promos
        )
    )

    svc.set_user_preference(
        UserPreference(
            user_id="charlie",
            enabled_channels={
                ChannelType.PUSH: True,
                ChannelType.SMS: True,
                ChannelType.EMAIL: True,
            },
            frequency_caps={ChannelType.PUSH: 2},
        )
    )

    print("User preferences set: alice, bob, charlie\n")

    # -- Submit notifications ------------------------------------------------
    notifications = [
        # Critical security alert to alice (all channels)
        Notification(
            notification_id=_make_id(),
            user_id="alice",
            template_id="alert",
            template_params={"message": "Login from new device in Tokyo"},
            channels=[ChannelType.PUSH, ChannelType.SMS, ChannelType.EMAIL],
            priority=Priority.CRITICAL,
            category="alerts",
        ),
        # Welcome for bob (push + email, SMS should be suppressed)
        Notification(
            notification_id=_make_id(),
            user_id="bob",
            template_id="welcome",
            template_params={
                "user_name": "Bob",
                "url": "https://app.example.com",
            },
            channels=[ChannelType.PUSH, ChannelType.SMS, ChannelType.EMAIL],
            priority=Priority.HIGH,
            category="transactional",
        ),
        # Promo to bob (should be suppressed - opted out of marketing)
        Notification(
            notification_id=_make_id(),
            user_id="bob",
            template_id="promo",
            template_params={
                "discount": "25%",
                "code": "WINTER25",
                "url": "https://shop.example.com",
            },
            channels=[ChannelType.PUSH, ChannelType.EMAIL],
            priority=Priority.LOW,
            category="marketing",
        ),
        # Normal welcome for charlie (push + SMS + email)
        Notification(
            notification_id=_make_id(),
            user_id="charlie",
            template_id="welcome",
            template_params={
                "user_name": "Charlie",
                "url": "https://app.example.com/start",
            },
            channels=[ChannelType.PUSH, ChannelType.SMS, ChannelType.EMAIL],
            priority=Priority.NORMAL,
            category="transactional",
        ),
        # Multiple alerts for charlie (push cap = 2, third should be capped)
        Notification(
            notification_id=_make_id(),
            user_id="charlie",
            template_id="alert",
            template_params={"message": "Password changed"},
            channels=[ChannelType.PUSH],
            priority=Priority.HIGH,
            category="alerts",
        ),
        Notification(
            notification_id=_make_id(),
            user_id="charlie",
            template_id="alert",
            template_params={"message": "New API key generated"},
            channels=[ChannelType.PUSH],
            priority=Priority.HIGH,
            category="alerts",
        ),
    ]

    print("Submitting notifications...")
    print("-" * 50)
    for notif in notifications:
        result = svc.submit(notif)
        print(f"  {result}")

    # -- Process queue -------------------------------------------------------
    print("\nProcessing priority queue...")
    svc.process_queue()

    # -- Reports -------------------------------------------------------------
    svc.print_delivery_report()
    svc.print_stats()
    svc.print_dlq()

    # -- Verify circuit breaker state ----------------------------------------
    print("\n" + "=" * 78)
    print("CIRCUIT BREAKER STATUS")
    print("=" * 78)
    for ch_type, ch_impl in svc.channels.items():
        cb = ch_impl.circuit_breaker
        print(
            f"  {ch_type.value:<8}: state={cb.state.value}  "
            f"failures={cb.failure_count}"
        )

    print("\n[done]")


if __name__ == "__main__":
    main()
