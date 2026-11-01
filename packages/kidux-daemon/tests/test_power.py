"""Suspend: what a computer can do, and what it does (power.py, D119)."""

import pytest

from kiduxd import power


@pytest.mark.parametrize("answer, sleeps", [
    ("yes", True), ("no", False), ("na", False), ("challenge", False), ("", False),
])
def test_only_yes_to_can_suspend_is_a_computer_that_suspends(answer, sleeps):
    assert power.can_sleep(answer) is sleeps


@pytest.mark.parametrize("chosen, sleeps, done", [
    ("sleep", True, "sleep"),
    ("sleep", False, "nothing"),
    ("nothing", True, "nothing"),
    ("sleep_then_hibernate", True, "sleep"),     # no hibernation: the default
    ("something else", True, "sleep"),
])
def test_the_lid_does_what_was_chosen_or_what_it_can(chosen, sleeps, done):
    assert power.lid_action(chosen, sleeps) == done


@pytest.mark.parametrize("chosen, sleeps, done", [
    ("sleep", True, "sleep"),
    ("sleep", False, "screen_off_only"),
    ("screen_off_only", True, "screen_off_only"),
    ("sleep_then_hibernate", True, "sleep"),
    ("", True, "sleep"),
])
def test_a_computer_left_alone_does_what_was_chosen_or_what_it_can(chosen, sleeps, done):
    assert power.idle_action(chosen, sleeps) == done


@pytest.mark.parametrize("action, handle", [("sleep", "suspend"), ("nothing", "ignore")])
def test_logind_s_file_handles_the_lid_alike_on_battery_and_mains_and_never_docked(
        action, handle):
    text = power.logind_conf(action)

    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    assert lines == ["[Login]", f"HandleLidSwitch={handle}",
                     f"HandleLidSwitchExternalPower={handle}", "HandleLidSwitchDocked=ignore"]


@pytest.mark.parametrize("blocked, idle", [
    ("idle", True), ("sleep:idle", True), ("handle-lid-switch", False), ("", False),
    ("idle-something", False),
])
def test_an_idle_inhibitor(blocked, idle):
    assert power.inhibited("idle", blocked) is idle
