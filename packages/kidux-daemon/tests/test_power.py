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


@pytest.mark.parametrize("connectors, docked", [
    (["card1-eDP-1"], False),
    ([], False),
    (["card0-LVDS-1"], False),
    (["card1-eDP-1", "card1-HDMI-A-1"], True),
    (["card0-DP-1"], True),
    (["Virtual-1"], True),
])
def test_another_screen_connected_is_docked(connectors, docked):
    assert power.docked(connectors) is docked


def test_the_screens_connected_from_the_kernel(tmp_path):
    for name, status in (("card1-eDP-1", "connected"), ("card1-HDMI-A-1", "disconnected"),
                         ("card0-DP-1", "connected")):
        (tmp_path / name).mkdir()
        (tmp_path / name / "status").write_text(status + "\n")

    assert power.connected_screens(tmp_path) == ["card0-DP-1", "card1-eDP-1"]


@pytest.mark.parametrize("blocked, idle", [
    ("idle", True), ("sleep:idle", True), ("handle-lid-switch", False), ("", False),
    ("idle-something", False),
])
def test_an_idle_inhibitor(blocked, idle):
    assert power.inhibited("idle", blocked) is idle
