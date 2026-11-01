"""The lid: the screen and the keyboard's light off while it is closed, on
again when it opens (D61, D97).

The lid is an input switch the kernel lists (`kidux.hardware.lid_devices`),
readable by anyone since `kidux-session`'s udev rule; the launcher reads it
in GLib's main loop and asks the compositor, through `wlopm`
(wlr-output-power-management), to power the machine's own panel off or on.
Closing it also locks the session, as the Lock button does (D67), so that a
laptop closed and carried away is locked when it is opened, and turns the
keyboard's light off after the screen, remembered where the lock screen,
on which the lid is opened, finds it to give it back (D97). Nothing else
changes: the screen's brightness stays what it was, windows stay where
they are, and an external screen stays on. Whether the computer then
suspends is logind's, as the adult set it on the panel's *Suspending
the computer* page (power.md, D119); before it sleeps the daemon locks the session
itself, so closing the lid is never a way out of a time limit.
"""

import logging
import os
import subprocess

from gi.repository import GLib

from kidux import hardware

log = logging.getLogger("kidux.launcher")

def _wlopm(*args: str) -> str:
    try:
        done = subprocess.run(["wlopm", *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as error:
        log.warning("wlopm did not run: %s", error)
        return ""
    return done.stdout


def set_screen(on: bool) -> None:
    for name in hardware.panel_outputs(hardware.wlopm_outputs(_wlopm())):
        _wlopm("--on" if on else "--off", name)
        log.info("the lid %s: %s %s", "opened" if on else "closed", name, "on" if on else "off")


class Lid:
    def __init__(self, devices: list[str], set_screen=set_screen, on_closed=None,
                 light_off=hardware.keyboard_light_off,
                 light_back=hardware.keyboard_light_back) -> None:
        self._set_screen = set_screen
        self._light_off, self._light_back = light_off, light_back
        #: Called when the lid closes, before the screen goes off: the
        #: launcher locks the session (D67).
        self._on_closed = on_closed
        self.closed: bool | None = None
        self._fds: list[int] = []
        for device in devices:
            try:
                fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
            except OSError as error:
                log.warning("the lid switch %s cannot be read: %s", device, error)
                continue
            self._fds.append(fd)
            GLib.io_add_watch(fd, GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN,
                              self._readable)
            try:
                self._apply(hardware.lid_closed(fd))
            except OSError as error:
                log.warning("the lid's state cannot be read: %s", error)

    def _readable(self, fd: int, _condition) -> bool:
        try:
            data = os.read(fd, 4096)
        except BlockingIOError:
            return GLib.SOURCE_CONTINUE
        except OSError as error:
            log.warning("the lid switch went away: %s", error)
            return GLib.SOURCE_REMOVE
        for closed in hardware.lid_events(data):
            self._apply(closed)
        return GLib.SOURCE_CONTINUE

    def _apply(self, closed: bool) -> None:
        if closed == self.closed:
            return
        # The lid's state when the launcher starts is not a closing.
        closing = closed and self.closed is not None
        self.closed = closed
        if closing and self._on_closed is not None:
            self._on_closed()
        if closed:
            self._set_screen(False)
            self._light_off()
        else:
            self._light_back()
            self._set_screen(True)
