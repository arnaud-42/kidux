"""Suspend and hibernate: what the computer does when its lid closes, and
when it is left alone after its screen has turned off (D119,
docs/dev/power.md).

Each has a setting of config.toml: `lid_action`, what closing the lid does,
and `idle_action`, what a computer still left alone `idle_sleep_minutes`
after its last touch does; and `hibernate_delay_seconds`, which no page
offers, how long a computer that suspends and then hibernates is suspended
first. "sleep" in the names is suspend.

What a computer can do is logind's word, `CanSuspend`, `CanHibernate` and
`CanSuspendThenHibernate`; when it cannot hibernate, the kernel's
lockdown and its swap spaces say why. A setting the computer cannot do is
done as the nearest one it can: suspend instead of suspending and then
hibernating, and nothing, or only the screen off, instead of suspend.

The lid is logind's to handle, from `50-kidux-power.conf` in
`/etc/systemd/logind.conf.d`, which the daemon writes; the minutes a
computer sleeps before it hibernates, from the file of the same name
in `/etc/systemd/sleep.conf.d`. Everything here but the reading of the
machine's files is pure, so that it is tested as it is.
"""

import re
from dataclasses import dataclass
from pathlib import Path

#: What closing the lid may do, and what a computer left alone may do after
#: its screen has turned off; the first of each is the default.
LID_ACTIONS = ("sleep_then_hibernate", "sleep", "nothing")
IDLE_ACTIONS = ("sleep_then_hibernate", "sleep", "screen_off_only")
#: The minutes after the last touch before a computer left alone sleeps, as
#: the panel offers them.
IDLE_SLEEP_MINUTES = (1, 240)

#: Why a computer cannot hibernate: Secure Boot's lockdown, no swap
#: space on a disk to save its memory in, or something else logind knows.
SECURE_BOOT, NO_SWAP, UNSUPPORTED = "secure_boot", "no_swap", "unsupported"

#: logind's `HandleLidSwitch=` for each lid action.
LID_HANDLES = {"sleep_then_hibernate": "suspend-then-hibernate", "sleep": "suspend",
               "nothing": "ignore"}
#: The logind method for each idle action; none for the screen off only.
IDLE_METHODS = {"sleep_then_hibernate": "SuspendThenHibernate", "sleep": "Suspend",
                "screen_off_only": None}

#: The first systemd version that knows each key of sleep.conf written here.
SLEEP_KEYS_SINCE = {"HibernateDelaySec": 239, "HibernateOnACPower": 254}


@dataclass(frozen=True)
class Capabilities:
    """What this computer can do: sleep, and suspend and then hibernate;
    when it cannot hibernate, why (`SECURE_BOOT`, `NO_SWAP`,
    `UNSUPPORTED`), and "" when it can."""

    sleep: bool
    hibernate: bool
    reason: str = ""


def capabilities(answers: dict[str, str], lockdown: str = "", swaps: str = "") -> Capabilities:
    """The computer's capabilities from logind's answers, `CanSuspend`,
    `CanHibernate` and `CanSuspendThenHibernate` to the daemon, which is
    root: anything but "yes" is a no. `lockdown` is the kernel's
    `/sys/kernel/security/lockdown`, `swaps` its `/proc/swaps`, read only to
    say why."""
    sleep = answers.get("CanSuspend") == "yes"
    hibernate = sleep and all(answers.get(name) == "yes"
                              for name in ("CanHibernate", "CanSuspendThenHibernate"))
    if hibernate:
        return Capabilities(True, True)
    if locked_down(lockdown):
        reason = SECURE_BOOT
    elif not has_disk_swap(swaps):
        reason = NO_SWAP
    else:
        reason = UNSUPPORTED
    return Capabilities(sleep, False, reason)


def locked_down(text: str) -> bool:
    """Whether the kernel is locked down, "none [integrity] confidentiality"
    with anything but none chosen, as it is under Secure Boot: then it
    refuses to save its memory to disk."""
    chosen = re.search(r"\[(\w+)\]", text or "")
    return chosen is not None and chosen.group(1) != "none"


def has_disk_swap(text: str) -> bool:
    """Whether `/proc/swaps` lists a swap space on a disk: one in memory,
    zram, cannot hold the memory while the computer is off."""
    for line in (text or "").splitlines()[1:]:
        fields = line.split()
        if fields and not fields[0].startswith("/dev/zram"):
            return True
    return False


def lid_action(chosen: str, can: Capabilities) -> str:
    """What closing the lid does on this computer: `chosen`, or the nearest
    it can do; an unknown value is the default."""
    if chosen not in LID_ACTIONS:
        chosen = LID_ACTIONS[0]
    if chosen == "sleep_then_hibernate" and not can.hibernate:
        chosen = "sleep"
    if chosen == "sleep" and not can.sleep:
        chosen = "nothing"
    return chosen


def idle_action(chosen: str, can: Capabilities) -> str:
    """What a computer left alone does on this computer: `chosen`, or the
    nearest it can do; an unknown value is the default."""
    if chosen not in IDLE_ACTIONS:
        chosen = IDLE_ACTIONS[0]
    if chosen == "sleep_then_hibernate" and not can.hibernate:
        chosen = "sleep"
    if chosen == "sleep" and not can.sleep:
        chosen = "screen_off_only"
    return chosen


def logind_conf(action: str) -> str:
    """`50-kidux-power.conf` for logind, for a lid `action` this computer
    can do: the same on battery and on mains power, and nothing while
    another screen is connected or the laptop is docked."""
    handle = LID_HANDLES[action]
    return (
        "# Written by kidux-daemon from the panel's *Suspend and hibernate* page\n"
        "# (docs/dev/power.md). Changes here are lost at the next change there.\n"
        "[Login]\n"
        f"HandleLidSwitch={handle}\n"
        f"HandleLidSwitchExternalPower={handle}\n"
        "HandleLidSwitchDocked=ignore\n"
    )


def sleep_conf(delay_seconds: int, systemd_version: int) -> str:
    """`50-kidux-power.conf` for systemd-sleep: sleep `delay_seconds`, then
    hibernate, on battery and on mains power alike; each key only
    where this systemd knows it."""
    lines = [
        "# Written by kidux-daemon (docs/dev/power.md): how long a computer that",
        "# suspends and then hibernates sleeps first.",
        "[Sleep]",
    ]
    for key, value in (("HibernateDelaySec", f"{int(delay_seconds)}s"),
                       ("HibernateOnACPower", "yes")):
        if systemd_version >= SLEEP_KEYS_SINCE[key]:
            lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def systemd_version(text: str) -> int:
    """systemd's major version from its manager's `Version`,
    "257.13-1~deb13u1"; 0 when it is not one."""
    found = re.match(r"\s*v?(\d+)", text or "")
    return int(found.group(1)) if found else 0


def inhibited(what: str, block_inhibited: str) -> bool:
    """Whether logind's `BlockInhibited`, "idle:sleep", holds `what`."""
    return what in (block_inhibited or "").split(":")


def read(path: Path) -> str:
    """A file of the kernel's, or "" when it cannot be read."""
    try:
        return path.read_text()
    except OSError:
        return ""
