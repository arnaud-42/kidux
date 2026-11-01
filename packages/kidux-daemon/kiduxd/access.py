"""Policy and time: how much a child may use, and what using it costs.

Pure functions over plain values and an injected clock (daemon.md section 7).
No D-Bus, no files, no clock of its own: everything here has a way to be
quietly wrong, so everything here is tested against a clock the tests control.

Seconds are whole numbers throughout. The session tracker carries the
fraction of a second between ticks itself, so nothing is lost and nothing
here has to reason about floats.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from typing import Protocol

MODES = ("unlimited", "daily", "manual")

#: When the launcher warns, in seconds left: ten, five and one minute.
WARNINGS = (600, 300, 60)

#: A grant or a daily allowance, in minutes, is never more than this.
MAX_MINUTES = 24 * 60

UNLIMITED = -1

#: Every day of the week ticked, Monday first, as a new child has them.
EVERY_DAY = (True,) * 7


class Clock(Protocol):
    def wall(self) -> datetime: ...
    def mono(self) -> float: ...


@dataclass(frozen=True)
class Policy:
    mode: str = "manual"
    daily_minutes: int = 60
    granted_seconds: int = 0
    #: The days of the week the child's time is for, Monday first (D54).
    #: Manual mode is by grant any day, and does not ask them.
    days: tuple[bool, ...] = EVERY_DAY

    @classmethod
    def from_document(cls, document: dict) -> "Policy":
        days = document.get("days", EVERY_DAY)
        return cls(
            mode=document.get("mode", "manual"),
            daily_minutes=int(document.get("daily_minutes", 60)),
            granted_seconds=int(document.get("granted_seconds", 0)),
            days=tuple(bool(day) for day in days) if len(days) == 7 else EVERY_DAY,
        )

    def as_document(self) -> dict:
        return {
            "mode": self.mode,
            "daily_minutes": self.daily_minutes,
            "granted_seconds": self.granted_seconds,
            "days": list(self.days),
        }

    def day_off(self, weekday: int) -> bool:
        """Whether `weekday` (Monday 0) is a day the computer is not the
        child's: one not ticked, in the modes that have days."""
        return self.mode != "manual" and not self.days[weekday]


@dataclass(frozen=True)
class Usage:
    last_day: str = ""
    seconds_used_today: int = 0
    active: bool = False
    lock: str = "none"
    #: The boot the session was active in: a session found active and
    #: locked in another boot is one the computer was turned off under.
    boot: str = ""

    @classmethod
    def from_document(cls, document: dict) -> "Usage":
        session = document.get("session", {})
        return cls(
            last_day=document.get("last_day", ""),
            seconds_used_today=int(document.get("seconds_used_today", 0)),
            active=bool(session.get("active", False)),
            lock=session.get("lock", "none"),
            boot=str(session.get("boot", "")),
        )

    def as_document(self) -> dict:
        return {
            "last_day": self.last_day,
            "seconds_used_today": self.seconds_used_today,
            "session": {"active": self.active, "lock": self.lock, "boot": self.boot},
        }


@dataclass(frozen=True)
class DayChange:
    """What `roll_day` found, for the audit trail."""

    rolled: bool = False
    backwards: bool = False
    jump_days: int = 0


def accounting_day(wall: datetime, reset_hour: int) -> date:
    """The day a moment is charged to. The day changes at reset_hour, not midnight."""
    return (wall - timedelta(hours=reset_hour)).date()


def weekday_of(usage: Usage) -> int:
    """The day of the week, Monday 0, of the day a usage is charged to:
    today's, once `roll_day` has seen it, or a later one when the clock was
    set back, which, like the counters, it never goes back from."""
    return date.fromisoformat(usage.last_day).weekday()


def roll_day(policy: Policy, usage: Usage, today: date) -> tuple[Policy, Usage, DayChange]:
    """Start a new day if the calendar says one has begun.

    Only a later day starts a new one. A clock moved backwards never resets
    a counter: that would hand a child a fresh allowance for turning a dial.
    A jump of more than a day either way is reported so it can be audited.
    """
    if not usage.last_day:
        return policy, replace(usage, last_day=today.isoformat()), DayChange()

    last = date.fromisoformat(usage.last_day)
    days = (today - last).days

    if days > 0:
        usage = replace(usage, last_day=today.isoformat(), seconds_used_today=0)
        if policy.mode != "manual":
            # An extra grant in daily mode is for today only (D14); in
            # unlimited mode it only counts on a day not ticked (D54), and
            # is for that day too.
            policy = replace(policy, granted_seconds=0)
        return policy, usage, DayChange(rolled=True, jump_days=days if days > 1 else 0)

    if days < 0:
        return policy, usage, DayChange(backwards=True, jump_days=-days if days < -1 else 0)

    return policy, usage, DayChange()


def allowance(policy: Policy, weekday: int) -> int | None:
    """The day's seconds before any grant, on `weekday` (the accounting
    day's, Monday 0): the daily minutes; none on a day not ticked (D54), in
    unlimited mode too; None for a child with no limit on a ticked day.
    Manual mode has no day's allowance: its time is the bank."""
    if policy.mode == "manual" or policy.day_off(weekday):
        return 0
    if policy.mode == "unlimited":
        return None
    return policy.daily_minutes * 60


def available(policy: Policy, usage: Usage, weekday: int) -> int:
    """Seconds the child may still use now, or UNLIMITED.

    On a day not ticked (D54) a child in daily or unlimited mode has what an
    adult gave that day and nothing more, as if the day's allowance were
    none."""
    if policy.mode == "manual":
        return max(0, policy.granted_seconds)
    day = allowance(policy, weekday)
    if day is None:
        return UNLIMITED
    return max(0, day + policy.granted_seconds - usage.seconds_used_today)


def check_access(policy: Policy, usage: Usage, weekday: int) -> tuple[str, int]:
    """What the sign-in screen does next, once the child's password was accepted."""
    seconds = available(policy, usage, weekday)
    if seconds == UNLIMITED:
        return "allowed", UNLIMITED
    if seconds > 0:
        return "allowed", seconds
    if policy.day_off(weekday):
        return "day_off", 0
    if policy.mode == "daily":
        return "blocked", 0
    return "needs_adult", 0


def spend(policy: Policy, usage: Usage, seconds: int) -> tuple[Policy, Usage]:
    """Charge `seconds` of unlocked time.

    Everything counts towards today's total, which the launcher shows. In
    manual mode it also comes out of the bank, which never goes below zero.
    Unlimited children are counted too, so an adult can see how long they
    spent, but nothing is ever taken from them.
    """
    if seconds <= 0:
        return policy, usage
    usage = replace(usage, seconds_used_today=usage.seconds_used_today + seconds)
    if policy.mode == "manual":
        policy = replace(policy, granted_seconds=max(0, policy.granted_seconds - seconds))
    return policy, usage


def grant(policy: Policy, usage: Usage, weekday: int, minutes: int) -> Policy:
    """The policy with `minutes` more from now (D14). A grant always gives
    its minutes: when the day's allowance and the grants so far are below
    what was used today, because the allowance was cut or is none on a day
    not ticked after time was used, that difference is covered first, so
    the child has exactly `minutes` more than they had, which was nothing."""
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= MAX_MINUTES:
        raise ValueError("minutes out of range")
    day = allowance(policy, weekday)
    behind = 0
    if policy.mode != "manual" and day is not None:
        behind = max(0, usage.seconds_used_today - day - policy.granted_seconds)
    return replace(policy, granted_seconds=policy.granted_seconds + behind + minutes * 60)


def set_left(policy: Policy, usage: Usage, weekday: int, minutes: int) -> Policy:
    """The policy that leaves exactly `minutes` for today, zero included,
    as an adult sets it on the panel (D50). What was used today stays as it
    was; the difference is a grant, which may be negative in daily mode and
    goes with the day, as every grant in daily mode does. On a day not
    ticked the day's allowance is none, in unlimited mode too. Nothing to
    set for a child with no limit today: ValueError."""
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 0 <= minutes <= MAX_MINUTES:
        raise ValueError("minutes out of range")
    if policy.mode == "manual":
        return replace(policy, granted_seconds=minutes * 60)
    day = allowance(policy, weekday)
    if day is None:
        raise ValueError("a child with no limit has no time left to set")
    return replace(policy, granted_seconds=minutes * 60 - day + usage.seconds_used_today)


def validate_policy(document: dict) -> Policy:
    """A policy from the panel, checked. Raises ValueError with what is wrong."""
    unknown = set(document) - {"mode", "daily_minutes", "days"}
    if unknown:
        raise ValueError(f"not part of a policy: {', '.join(sorted(unknown))}")
    mode = document.get("mode")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    minutes = document.get("daily_minutes", 60)
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 0 <= minutes <= MAX_MINUTES:
        raise ValueError("daily_minutes is a whole number of minutes in a day")
    days = document.get("days", EVERY_DAY)
    if not isinstance(days, (list, tuple)) or len(days) != 7 \
            or not all(isinstance(day, bool) for day in days):
        raise ValueError("days is seven true or false, Monday first")
    return Policy(mode=mode, daily_minutes=minutes, days=tuple(days))


def days_text(days: tuple[bool, ...]) -> str:
    """The days as seven digits, Monday first, 1 for a day ticked: 1111100."""
    return "".join("1" if day else "0" for day in days)


@dataclass
class Warnings:
    """Which of the ten, five and one minute warnings have been given.

    Each fires once per unlocked stretch. When a stretch starts — at sign-in,
    or after a grant — the thresholds the child is already below count as
    given, so a child who signs in with three minutes gets the one-minute
    warning and not a burst of three at once.
    """

    given: set[int] = field(default_factory=set)

    def arm(self, seconds_left: int) -> None:
        if seconds_left == UNLIMITED:
            self.given = set(WARNINGS)
        else:
            self.given = {t for t in WARNINGS if seconds_left <= t}

    def due(self, seconds_left: int) -> int | None:
        """The warning to give now, if any. Only the most urgent one."""
        if seconds_left == UNLIMITED:
            return None
        crossed = [t for t in WARNINGS if seconds_left <= t and t not in self.given]
        if not crossed:
            return None
        self.given.update(crossed)
        return min(crossed)

    def next_threshold(self, seconds_left: int) -> int | None:
        """Seconds until the next warning or zero, so a tick can be timed to it."""
        if seconds_left == UNLIMITED:
            return None
        pending = [seconds_left - t for t in WARNINGS if t not in self.given and seconds_left > t]
        pending.append(seconds_left)
        return max(0, min(pending))
