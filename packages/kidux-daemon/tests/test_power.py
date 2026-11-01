"""Sleep and the lid: what a computer can do, and what it does (power.py, D119)."""

import pytest

from kiduxd import power
from kiduxd.power import Capabilities

YES = {"CanSuspend": "yes", "CanHibernate": "yes", "CanSuspendThenHibernate": "yes"}
SWAPS_DISK = ("Filename\tType\tSize\tUsed\tPriority\n"
              "/dev/nvme0n1p9                          partition\t16899068\t0\t-1\n"
              "/dev/zram0                              partition\t16132936\t0\t100\n")
SWAPS_ZRAM = ("Filename\tType\tSize\tUsed\tPriority\n"
              "/dev/zram0                              partition\t16132936\t0\t100\n")
SWAPS_NONE = "Filename\tType\tSize\tUsed\tPriority\n"
LOCKED = "none [integrity] confidentiality\n"
OPEN = "[none] integrity confidentiality\n"

CAN_ALL = Capabilities(True, True)
SLEEP_ONLY = Capabilities(True, False, power.SECURE_BOOT)
NEITHER = Capabilities(False, False, power.UNSUPPORTED)


# --- what the computer can do ---------------------------------------------------

def test_a_computer_logind_says_yes_to_can_do_everything():
    assert power.capabilities(YES, OPEN, SWAPS_DISK) == Capabilities(True, True, "")


@pytest.mark.parametrize("answer", ["no", "na", "challenge", ""])
@pytest.mark.parametrize("name", ["CanHibernate", "CanSuspendThenHibernate"])
def test_anything_but_yes_to_hibernating_is_a_computer_that_only_sleeps(name, answer):
    can = power.capabilities({**YES, name: answer}, OPEN, SWAPS_DISK)

    assert (can.sleep, can.hibernate) == (True, False)


def test_secure_boot_s_lockdown_is_the_reason_first():
    # hija, the development machine: Secure Boot on, and a swap partition.
    can = power.capabilities({**YES, "CanHibernate": "na", "CanSuspendThenHibernate": "na"},
                             LOCKED, SWAPS_DISK)

    assert can == Capabilities(True, False, power.SECURE_BOOT)


@pytest.mark.parametrize("swaps", [SWAPS_ZRAM, SWAPS_NONE, ""])
def test_without_swap_on_a_disk_the_reason_is_no_swap(swaps):
    can = power.capabilities({**YES, "CanHibernate": "na"}, OPEN, swaps)

    assert can.reason == power.NO_SWAP


def test_otherwise_the_reason_is_only_that_it_cannot():
    can = power.capabilities({**YES, "CanHibernate": "no"}, OPEN, SWAPS_DISK)

    assert can.reason == power.UNSUPPORTED


def test_a_computer_that_cannot_sleep_cannot_hibernate_either():
    can = power.capabilities({**YES, "CanSuspend": "no"}, OPEN, SWAPS_DISK)

    assert (can.sleep, can.hibernate) == (False, False)


@pytest.mark.parametrize("text, locked", [
    (LOCKED, True), (OPEN, False), ("none integrity [confidentiality]", True), ("", False),
])
def test_lockdown(text, locked):
    assert power.locked_down(text) is locked


# --- what it does ------------------------------------------------------------------

@pytest.mark.parametrize("chosen, can, done", [
    ("sleep_then_hibernate", CAN_ALL, "sleep_then_hibernate"),
    ("sleep_then_hibernate", SLEEP_ONLY, "sleep"),
    ("sleep_then_hibernate", NEITHER, "nothing"),
    ("sleep", SLEEP_ONLY, "sleep"),
    ("sleep", NEITHER, "nothing"),
    ("nothing", CAN_ALL, "nothing"),
    ("something else", CAN_ALL, "sleep_then_hibernate"),
])
def test_the_lid_does_what_was_chosen_or_the_nearest_it_can(chosen, can, done):
    assert power.lid_action(chosen, can) == done


@pytest.mark.parametrize("chosen, can, done", [
    ("sleep_then_hibernate", CAN_ALL, "sleep_then_hibernate"),
    ("sleep_then_hibernate", SLEEP_ONLY, "sleep"),
    ("sleep_then_hibernate", NEITHER, "screen_off_only"),
    ("sleep", NEITHER, "screen_off_only"),
    ("screen_off_only", CAN_ALL, "screen_off_only"),
    ("", SLEEP_ONLY, "sleep"),
])
def test_a_computer_left_alone_does_what_was_chosen_or_the_nearest_it_can(chosen, can, done):
    assert power.idle_action(chosen, can) == done


# --- the files -----------------------------------------------------------------------

@pytest.mark.parametrize("action, handle", [
    ("sleep_then_hibernate", "suspend-then-hibernate"),
    ("sleep", "suspend"),
    ("nothing", "ignore"),
])
def test_logind_s_file_handles_the_lid_alike_on_battery_and_mains_and_never_docked(
        action, handle):
    text = power.logind_conf(action)

    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert lines == ["[Login]", f"HandleLidSwitch={handle}",
                     f"HandleLidSwitchExternalPower={handle}", "HandleLidSwitchDocked=ignore"]


def test_sleep_s_file_sleeps_a_minute_then_hibernates_on_mains_too():
    text = power.sleep_conf(60, 257)

    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert lines == ["[Sleep]", "HibernateDelaySec=60s", "HibernateOnACPower=yes"]


def test_a_key_this_systemd_does_not_know_is_left_out():
    text = power.sleep_conf(60, 252)

    assert "HibernateDelaySec=60s" in text
    assert "HibernateOnACPower" not in text


@pytest.mark.parametrize("text, version", [
    ("257.13-1~deb13u1", 257), ("v254", 254), ("252", 252), ("", 0), ("unknown", 0),
])
def test_systemd_s_version(text, version):
    assert power.systemd_version(text) == version


@pytest.mark.parametrize("blocked, idle", [
    ("idle", True), ("sleep:idle", True), ("handle-lid-switch", False), ("", False),
    ("idle-something", False),
])
def test_an_idle_inhibitor(blocked, idle):
    assert power.inhibited("idle", blocked) is idle
