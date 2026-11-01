"""A screen left alone (D67, docs/dev/session.md section 5).

What `kidux-idle` decides, without starting anything, so that it is tested
as it is. `kidux-idle` runs beside every screen, the sign-in and lock
screens under cage and a child's session under labwc, and keeps `swayidle`
running only while its screen's terminal is the one in front: a session
frozen under the lock screen, or a lock screen whose terminal is not
shown, counts nothing, and a count starts afresh when its screen comes to
the front, so that a timer that ran out while a session was frozen never
locks it on thaw.
"""

#: How often `kidux-idle` looks at which terminal is in front, in seconds.
LOOK_SECONDS = 2
#: A gap longer than this between two looks means the process was frozen
#: in between: its screen was under the lock screen.
FROZEN_GAP_SECONDS = 10


def step(own_vt: int | None, active_vt: int | None, running: bool, gap: float) -> str | None:
    """What to do at one look: "start" `swayidle`, "stop" it, "restart" it,
    or None. `own_vt` is this screen's terminal, None when it is not known,
    and then the screen is taken to be in front; `gap` is the seconds since
    the last look."""
    in_front = own_vt is None or active_vt == own_vt
    if not in_front:
        return "stop" if running else None
    if not running:
        return "start"
    if gap > FROZEN_GAP_SECONDS:
        return "restart"
    return None


def swayidle_argv(lock_seconds: int, off_seconds: int, program: str,
                  sleep_seconds: int = 0) -> list[str]:
    """`swayidle`'s command line: after `lock_seconds` without a touch the
    session locks, after `off_seconds` the screen turns off and the first
    touch turns it on, and after `sleep_seconds` the daemon is asked to put
    the computer to sleep (D119); a time of 0 is not armed. `program` is
    kidux-idle's own path, which the timeouts run."""
    argv = ["swayidle", "-w"]
    if lock_seconds > 0:
        argv += ["timeout", str(lock_seconds), f"{program} lock"]
    if off_seconds > 0:
        argv += ["timeout", str(off_seconds), f"{program} screen off",
                 "resume", f"{program} screen on"]
    if sleep_seconds > 0:
        argv += ["timeout", str(sleep_seconds), f"{program} sleep"]
    return argv


def sleep_seconds(config: dict) -> int:
    """The seconds a screen is left alone before the daemon is asked to put
    the computer to sleep, from the daemon's `GetConfig`: none when the
    adult chose the screen off only, or the computer cannot sleep."""
    if config.get("idle_action", "sleep_then_hibernate") == "screen_off_only":
        return 0
    if not config.get("can_sleep", True):
        return 0
    return int(config.get("idle_sleep_minutes", 20)) * 60


def seconds(environ, name: str, default: int) -> int:
    """A whole number of seconds from the environment; `default` when it is
    missing or not a whole number, and never below 0."""
    try:
        return max(0, int(environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def vt_number(value) -> int | None:
    """A terminal's number from `XDG_VTNR` or `/sys/class/tty/tty0/active`
    ("tty7"); None when it is not one."""
    text = str(value or "").strip()
    if text.startswith("tty"):
        text = text[3:]
    return int(text) if text.isdigit() else None
