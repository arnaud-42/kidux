"""The power button and Ctrl+Alt+Escape: the keys that always reach a trusted
screen; and the lid closing, which suspends the computer (D119).

daemon.md section 11, D16. An adult presses the power button *before* typing
the adult password, and whatever screen appears is real, because the daemon
reads the key straight from the input device and nothing a child runs can
stop it. The devices are read, never grabbed: the compositor still gets
every key.

`Chords` is the pure part: it is fed key and switch events and says when
one of the keys has been pressed, or the lid closed: a close, never the
lid's state, so that a lid switch that reads closed with the lid open, as
a MacBook's can after a failed resume, suspends nothing. `InputWatcher` opens the real devices with
python3-evdev and feeds it from the GLib main loop.
"""

from pathlib import Path
from typing import Callable

from kidux.log import get_logger

_log = get_logger("attention")

# Linux input event codes (linux/input-event-codes.h). Plain numbers so the
# pure part can be tested without evdev installed.
EV_KEY = 1
EV_SW = 5
SW_LID = 0
KEY_ESC = 1
KEY_LEFTCTRL = 29
KEY_LEFTALT = 56
KEY_RIGHTCTRL = 97
KEY_RIGHTALT = 100
KEY_POWER = 116

CTRL = {KEY_LEFTCTRL, KEY_RIGHTCTRL}
ALT = {KEY_LEFTALT, KEY_RIGHTALT}

PRESS, RELEASE = 1, 0

INPUT_DIR = Path("/dev/input")


class Chords:
    """Turns key events into "the power button" or "Ctrl+Alt+Escape"."""

    def __init__(self, on_attention: Callable[[str], None]) -> None:
        self._on_attention = on_attention
        # Held keys per device: a modifier on one keyboard and Escape on
        # another is not the chord.
        self._held: dict[str, set[int]] = {}

    def feed(self, device: str, code: int, value: int) -> None:
        held = self._held.setdefault(device, set())

        if value == RELEASE:
            held.discard(code)
            return
        if value != PRESS:
            # Auto-repeat of a key already held.
            return

        held.add(code)

        if code == KEY_POWER:
            self._on_attention("power_button")
        elif code == KEY_ESC and held & CTRL and held & ALT:
            self._on_attention("ctrl_alt_escape")

    def switch(self, code: int, value: int) -> None:
        """A switch event: the lid closing, value 1, is "lid_closed"."""
        if code == SW_LID and value == 1:
            self._on_attention("lid_closed")

    def forget(self, device: str) -> None:
        self._held.pop(device, None)


def wanted(capabilities: set[int], switches: set[int] = frozenset()) -> bool:
    """A device worth reading: one with a power key, a keyboard with the
    chord, or the lid's switch."""
    if KEY_POWER in capabilities or SW_LID in switches:
        return True
    return KEY_ESC in capabilities and bool(capabilities & CTRL) and bool(capabilities & ALT)


class InputWatcher:
    """Reads every device that can send one of the keys, including ones plugged in later."""

    def __init__(self, chords: Chords) -> None:
        self._chords = chords
        self._devices: dict[str, tuple[object, int]] = {}
        self._monitor = None

    def start(self) -> None:
        from gi.repository import Gio

        for path in sorted(INPUT_DIR.glob("event*")):
            self._open(str(path))

        self._monitor = Gio.File.new_for_path(str(INPUT_DIR)).monitor_directory(
            Gio.FileMonitorFlags.NONE, None
        )
        self._monitor.connect("changed", self._on_changed)

    def _on_changed(self, monitor, file, other, event) -> None:
        from gi.repository import Gio

        path = file.get_path()
        if not Path(path).name.startswith("event"):
            return
        if event == Gio.FileMonitorEvent.CREATED:
            self._open(path)
        elif event == Gio.FileMonitorEvent.DELETED:
            self._close(path)

    def _open(self, path: str) -> None:
        if path in self._devices:
            return
        try:
            import evdev
            from gi.repository import GLib

            device = evdev.InputDevice(path)
            capabilities = device.capabilities()
            keys = set(capabilities.get(EV_KEY, []))
            if not wanted(keys, set(capabilities.get(EV_SW, []))):
                device.close()
                return
            source = GLib.io_add_watch(
                device.fd,
                GLib.PRIORITY_HIGH,
                GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR,
                self._on_readable,
                path,
            )
            self._devices[path] = (device, source)
            _log.info("watching %s (%s)", path, device.name)
        except (OSError, ImportError) as error:
            _log.debug("not watching %s: %s", path, error)

    def _close(self, path: str) -> None:
        entry = self._devices.pop(path, None)
        self._chords.forget(path)
        if entry is None:
            return
        device, source = entry
        from gi.repository import GLib

        GLib.source_remove(source)
        try:
            device.close()
        except OSError:
            pass

    def _on_readable(self, fd, condition, path) -> bool:
        from gi.repository import GLib

        entry = self._devices.get(path)
        if entry is None:
            return GLib.SOURCE_REMOVE
        device, _ = entry
        try:
            for event in device.read():
                if event.type == EV_KEY:
                    self._chords.feed(path, event.code, event.value)
                elif event.type == EV_SW:
                    self._chords.switch(event.code, event.value)
        except BlockingIOError:
            pass
        except OSError:
            # Unplugged: the directory monitor will say so too.
            self._devices.pop(path, None)
            self._chords.forget(path)
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE
