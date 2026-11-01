"""The keys that reach a trusted screen, and the lid closing (attention.py)."""

from kiduxd.attention import EV_SW, KEY_ESC, KEY_LEFTALT, KEY_LEFTCTRL, KEY_POWER, SW_LID
from kiduxd.attention import Chords, wanted


def chords():
    heard = []
    return Chords(heard.append), heard


def test_the_power_button_is_heard():
    keys, heard = chords()

    keys.feed("kbd", KEY_POWER, 1)

    assert heard == ["power_button"]


def test_the_lid_closing_is_heard_and_its_opening_is_not():
    keys, heard = chords()

    keys.switch(SW_LID, 1)
    keys.switch(SW_LID, 0)

    assert heard == ["lid_closed"]


def test_another_switch_is_not_the_lid():
    keys, heard = chords()

    keys.switch(SW_LID + 1, 1)

    assert heard == []


def test_every_key_pressed_is_told_and_a_release_is_not():
    pressed = []
    keys = Chords(lambda source: None, lambda: pressed.append(1))

    keys.feed("kbd", KEY_ESC, 1)
    keys.feed("kbd", KEY_ESC, 0)
    keys.feed("kbd", KEY_ESC, 2)

    assert pressed == [1]


def test_the_lid_s_device_is_read():
    assert wanted(set(), {SW_LID})
    assert wanted({KEY_POWER})
    assert wanted({KEY_ESC, KEY_LEFTCTRL, KEY_LEFTALT})
    assert not wanted({KEY_ESC}, set())
    assert EV_SW == 5
