"""Suspend: what the computer does when its lid closes, and when it is left
alone after its screen has turned off (D119, docs/dev/power.md).

Each has a setting of config.toml: `lid_action`, what closing the lid does,
`sleep` (suspend) or `nothing`, and `idle_action`, what a computer still
left alone `idle_sleep_minutes` after its last touch does, `sleep` or
`screen_off_only`. Kidux never hibernates: kidux-session forbids it in
systemd-sleep's configuration.

Whether the computer can suspend is logind's word, `CanSuspend`; on a
computer that cannot, a setting to suspend is done as nothing, or the
screen off only. The lid is logind's to handle, from `50-kidux-power.conf`
in `/etc/systemd/logind.conf.d`, which the daemon writes. Everything here
is pure, so that it is tested as it is.
"""

#: What closing the lid may do, and what a computer left alone may do after
#: its screen has turned off; the first of each is the default.
LID_ACTIONS = ("sleep", "nothing")
IDLE_ACTIONS = ("sleep", "screen_off_only")
#: The minutes after the last touch before a computer left alone suspends,
#: as the panel offers them.
IDLE_SLEEP_MINUTES = (1, 240)

#: logind's `HandleLidSwitch=` for each lid action.
LID_HANDLES = {"sleep": "suspend", "nothing": "ignore"}


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


def logind_conf(action: str) -> str:
    """`50-kidux-power.conf` for logind, for a lid `action` this computer
    can do: the same on battery and on mains power, and nothing while
    another screen is connected or the laptop is docked."""
    handle = LID_HANDLES[action]
    return (
        "# Written by kidux-daemon from the panel's *Suspending the computer*\n"
        "# page (docs/dev/power.md). Changes here are lost at the next change there.\n"
        "[Login]\n"
        f"HandleLidSwitch={handle}\n"
        f"HandleLidSwitchExternalPower={handle}\n"
        "HandleLidSwitchDocked=ignore\n"
    )


def inhibited(what: str, block_inhibited: str) -> bool:
    """Whether logind's `BlockInhibited`, "idle:sleep", holds `what`."""
    return what in (block_inhibited or "").split(":")
