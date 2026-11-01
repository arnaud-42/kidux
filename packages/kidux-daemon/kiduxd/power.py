"""Suspend: what the computer does when its lid closes, and when it is left
alone after its screen has turned off (D119, docs/dev/power.md).

Each has a setting of config.toml: `lid_action`, what closing the lid does,
`sleep` (suspend) or `nothing`, and `idle_action`, what a computer still
left alone `idle_sleep_minutes` after its last touch does, `sleep` or
`screen_off_only`. Kidux never hibernates: kidux-session forbids it in
systemd-sleep's configuration.

Whether the computer can suspend is logind's word, `CanSuspend`; on a
computer that cannot, a setting to suspend is done as nothing, or the
screen off only. logind ignores the lid (kidux-session's logind.conf):
the daemon suspends when it sees the lid close, an event, never because a
switch reads closed, and only when it still reads closed once the session
is locked and no other screen is connected. Everything here but the
reading of the machine is pure, so that it is tested as it is.
"""

import os
from pathlib import Path

from kidux import hardware

#: What closing the lid may do, and what a computer left alone may do after
#: its screen has turned off; the first of each is the default.
LID_ACTIONS = ("sleep", "nothing")
IDLE_ACTIONS = ("sleep", "screen_off_only")
#: The minutes after the last touch before a computer left alone suspends,
#: as the panel offers them.
IDLE_SLEEP_MINUTES = (1, 240)



def can_sleep(answer: str) -> bool:
    """Whether logind's answer to `CanSuspend`, asked by the daemon, which is
    root, is yes: anything else is a no."""
    return answer == "yes"


def lid_action(chosen: str, sleeps: bool) -> str:
    """What closing the lid does on this computer: `chosen`, or nothing on a
    computer that cannot suspend; an unknown value is the default."""
    if chosen not in LID_ACTIONS:
        chosen = LID_ACTIONS[0]
    return chosen if sleeps else "nothing"


def idle_action(chosen: str, sleeps: bool) -> str:
    """What a computer left alone does on this computer: `chosen`, or the
    screen off only on a computer that cannot suspend; an unknown value is
    the default."""
    if chosen not in IDLE_ACTIONS:
        chosen = IDLE_ACTIONS[0]
    return chosen if sleeps else "screen_off_only"


def docked(connectors: list[str]) -> bool:
    """Whether a screen other than the laptop's own is connected: DRM
    connectors as `/sys/class/drm` names them, "card1-HDMI-A-1", connected;
    a laptop's own panel is eDP, LVDS or DSI. Then closing the lid only
    turns the laptop's panel off, as logind's own docked rule has it."""
    for name in connectors:
        connector = name.split("-", 1)[1] if name.startswith("card") and "-" in name else name
        if not connector.startswith(hardware.PANEL_PREFIXES):
            return True
    return False


def connected_screens(drm: Path = Path("/sys/class/drm")) -> list[str]:
    """The DRM connectors with a screen connected."""
    found = []
    for status in sorted(drm.glob("card*-*/status")):
        try:
            if status.read_text().strip() == "connected":
                found.append(status.parent.name)
        except OSError:
            continue
    return found


def lid_is_closed() -> bool:
    """Whether a lid switch says the lid is closed now; False without one,
    or when none can be read."""
    for device in hardware.lid_devices():
        try:
            fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            continue
        try:
            return hardware.lid_closed(fd)
        except OSError:
            continue
        finally:
            os.close(fd)
    return False


def inhibited(what: str, block_inhibited: str) -> bool:
    """Whether logind's `BlockInhibited`, "idle:sleep", holds `what`."""
    return what in (block_inhibited or "").split(":")
