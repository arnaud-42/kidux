"""The clock for each child's session (daemon.md sections 7 and 8).

The daemon learns about sessions from logind and keeps time for each one
here. Nothing a child's session runs is involved: the launcher can be killed
and the clock keeps running.

A session is either **counting** (unlocked: time is charged), **stopped**
(locked: nothing is charged) or on **grace** (unlocked by an adult for a few
minutes so the child can save, charged to nobody, and locked again when the
grace runs out). Time is measured on the monotonic clock, so changing the
wall clock during a session changes nothing about that session; the wall
clock is only used to decide which day it is.

Everything is flushed to usage.toml (and access.toml, whose bank changes in
manual mode) on every tick, so a power cut, a crash or a deliberate reboot
costs at most one tick of counting.
"""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from kidux import paths, state

from .access import (
    UNLIMITED,
    DayChange,
    Policy,
    Usage,
    Warnings,
    accounting_day,
    available,
    roll_day,
    spend,
    weekday_of,
)

#: The longest a tick waits. Also the most counting a crash can lose.
TICK_SECONDS = 30


@dataclass
class Tracked:
    username: str
    uid: int
    session_id: str
    session_path: str
    scope: str
    vtnr: int
    unlocked_since: float | None = None
    carry: float = 0.0
    grace_until: float | None = None
    lock: str = "none"
    #: When the session was last given the screen back, on the monotonic
    #: clock: a lock for idleness right after is a frozen timer's (D67).
    unlocked_at: float | None = None
    warnings: Warnings = field(default_factory=Warnings)

    @property
    def locked(self) -> bool:
        return self.lock != "none"


def current_boot() -> str:
    """The kernel's identifier of this boot, or "" when it cannot be read."""
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return ""


class Timekeeper:
    def __init__(
        self,
        clock,
        *,
        reset_hour: int,
        audit: Callable[..., None],
        emit: Callable[[str, str, str, tuple], None],
        on_time_up: Callable[[Tracked], None],
        on_grace_over: Callable[[Tracked], None],
    ) -> None:
        self._clock = clock
        self._reset_hour = reset_hour
        self._audit = audit
        self._emit = emit
        self._on_time_up = on_time_up
        self._on_grace_over = on_grace_over
        self.sessions: dict[str, Tracked] = {}
        #: This boot's identifier, kept with a session's state: a lock is
        #: put back on a session found again only in the boot it was put on.
        self.boot_id = current_boot()

    # --- the files -------------------------------------------------------------

    def load(self, username: str) -> tuple[Policy, Usage, DayChange]:
        """A child's policy and usage, with the day rolled forward if it has changed."""
        policy = Policy.from_document(
            state.read(paths.child_access(username), "access", default={})
        )
        usage = Usage.from_document(
            state.read(paths.child_usage(username), "usage", default={})
        )
        today = accounting_day(self._clock.wall(), self._reset_hour)
        rolled_policy, rolled_usage, change = roll_day(policy, usage, today)

        if change.backwards or change.jump_days:
            self._audit(
                "clock jump",
                "noticed",
                child=username,
                direction="backwards" if change.backwards else "forwards",
                days=change.jump_days or 1,
            )
        if (rolled_policy, rolled_usage) != (policy, usage):
            self.save(username, rolled_policy, rolled_usage)
        return rolled_policy, rolled_usage, change

    def save(self, username: str, policy: Policy, usage: Usage) -> None:
        state.write(paths.child_access(username), policy.as_document(), "access")
        state.write(paths.child_usage(username), usage.as_document(), "usage")

    def set_session_state(self, username: str, active: bool, lock: str) -> None:
        policy, usage, _ = self.load(username)
        self.save(username, policy, replace(usage, active=active, lock=lock,
                                            boot=self.boot_id if active else ""))

    def left(self, username: str) -> int:
        policy, usage, _ = self.load(username)
        return available(policy, usage, weekday_of(usage))

    # --- sessions --------------------------------------------------------------

    def track(self, tracked: Tracked) -> None:
        """A child's session appeared. Counting starts now unless it was locked."""
        self.sessions[tracked.username] = tracked
        if not tracked.locked:
            self.resume(tracked)
        self.set_session_state(tracked.username, True, tracked.lock)

    def untrack(self, username: str) -> Tracked | None:
        tracked = self.sessions.get(username)
        if tracked is None:
            return None
        self.charge(tracked)
        del self.sessions[username]
        self.set_session_state(username, False, "none")
        return tracked

    def find(self, session_id: str) -> Tracked | None:
        for tracked in self.sessions.values():
            if tracked.session_id == session_id:
                return tracked
        return None

    def resume(self, tracked: Tracked) -> None:
        """Start counting, and set up the warnings for what is left."""
        tracked.grace_until = None
        tracked.unlocked_since = self._clock.mono()
        tracked.carry = 0.0
        tracked.warnings.arm(self.left(tracked.username))

    def pause(self, tracked: Tracked) -> None:
        """Stop counting, charging everything up to this moment first."""
        self.charge(tracked)
        tracked.unlocked_since = None
        tracked.carry = 0.0

    def start_grace(self, tracked: Tracked, seconds: int) -> None:
        """Unlocked, not counting, until `seconds` have passed."""
        self.pause(tracked)
        tracked.grace_until = self._clock.mono() + seconds

    # --- counting --------------------------------------------------------------

    def charge(self, tracked: Tracked) -> int | None:
        """Charge the unlocked time since the last charge. Returns what is left."""
        if tracked.unlocked_since is None:
            return None

        now = self._clock.mono()
        elapsed = now - tracked.unlocked_since + tracked.carry
        whole = int(elapsed)
        tracked.carry = elapsed - whole
        tracked.unlocked_since = now

        policy, usage, change = self.load(tracked.username)
        policy, usage = spend(policy, usage, whole)
        self.save(tracked.username, policy, usage)

        left = available(policy, usage, weekday_of(usage))
        if change.rolled:
            # A new day is a new allowance, or none on a day not ticked: the
            # warnings start over, and at none the tick locks.
            tracked.warnings.arm(left)
        return left

    def tick(self) -> float:
        """Charge every counting session, warn, lock at zero. Returns the next delay."""
        delay = float(TICK_SECONDS)
        now = self._clock.mono()

        for tracked in list(self.sessions.values()):
            if tracked.grace_until is not None:
                if now >= tracked.grace_until:
                    tracked.grace_until = None
                    self._on_grace_over(tracked)
                else:
                    delay = min(delay, tracked.grace_until - now)
                continue

            left = self.charge(tracked)
            if left is None or left == UNLIMITED:
                continue

            warning = tracked.warnings.due(left)
            if warning is not None:
                self._emit("Access1", "TimeWarning", "(su)", (tracked.username, left))

            if left <= 0:
                self._on_time_up(tracked)
                continue

            upcoming = tracked.warnings.next_threshold(left)
            if upcoming is not None:
                delay = min(delay, float(max(1, upcoming)))

        return max(1.0, delay)
