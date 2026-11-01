"""systemd-logind, as the daemon uses it.

logind is the authority on who has a session, and the only thing allowed to
turn the machine off. The daemon asks it rather than keeping its own record,
because a record kept by anything a child's session runs can be killed or
edited by the child.
"""

import os
from signal import SIGHUP
from dataclasses import dataclass
from typing import Protocol

from gi.repository import Gio, GLib

from kidux.log import get_logger

from .errors import Failed

_log = get_logger("logind")

LOGIND = "org.freedesktop.login1"
MANAGER_PATH = "/org/freedesktop/login1"
MANAGER = "org.freedesktop.login1.Manager"
SYSTEMD = "org.freedesktop.systemd1"
SYSTEMD_PATH = "/org/freedesktop/systemd1"
SYSTEMD_MANAGER = "org.freedesktop.systemd1.Manager"


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    uid: int
    user: str
    seat: str
    path: str
    #: logind's class: "user" for a session someone is in; "manager" for the
    #: user manager logind starts beside it, which outlives it by a few
    #: seconds (UserStopDelaySec) and is nobody being signed in.
    session_class: str = "user"


class Logind(Protocol):
    def sessions(self) -> list[SessionInfo]: ...
    def terminate_user(self, uid: int) -> None: ...
    def power_off(self) -> None: ...
    def reboot(self) -> None: ...
    def can(self, what: str) -> str: ...
    def block_inhibited(self) -> str: ...
    def suspend(self) -> None: ...
    def reload(self) -> None: ...


class SystemLogind:
    def __init__(self, connection: Gio.DBusConnection) -> None:
        self._connection = connection

    def _call(self, method: str, arguments=None, reply_type=None):
        try:
            return self._connection.call_sync(
                LOGIND,
                MANAGER_PATH,
                MANAGER,
                method,
                arguments,
                GLib.VariantType(reply_type) if reply_type else None,
                Gio.DBusCallFlags.NONE,
                10_000,
                None,
            )
        except GLib.Error as error:
            raise Failed(f"logind {method} failed: {error.message}") from error

    def sessions(self) -> list[SessionInfo]:
        reply = self._call("ListSessions", None, "(a(susso))")
        return [SessionInfo(*entry, session_class=self._session_class(entry[4]))
                for entry in reply.unpack()[0]]

    def _session_class(self, session_path: str) -> str:
        try:
            reply = self._connection.call_sync(
                LOGIND, session_path, "org.freedesktop.DBus.Properties", "Get",
                GLib.Variant("(ss)", ("org.freedesktop.login1.Session", "Class")),
                GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 10_000, None)
        except GLib.Error:
            return ""
        return str(reply.unpack()[0])

    def terminate_user(self, uid: int) -> None:
        """End every session of this user and their user manager, now."""
        self._call("TerminateUser", GLib.Variant("(u)", (uid,)))

    def power_off(self) -> None:
        self._call("PowerOff", GLib.Variant("(b)", (False,)))

    def reboot(self) -> None:
        self._call("Reboot", GLib.Variant("(b)", (False,)))

    def can(self, what: str) -> str:
        """logind's answer to `Can<what>`, such as "Suspend": "yes", "no",
        "na" or "challenge"; "na" when it cannot be asked."""
        try:
            return str(self._call(f"Can{what}", None, "(s)").unpack()[0])
        except Failed:
            return "na"

    def block_inhibited(self) -> str:
        """What the block inhibitors hold off now, "idle:sleep"."""
        try:
            reply = self._connection.call_sync(
                LOGIND, MANAGER_PATH, "org.freedesktop.DBus.Properties", "Get",
                GLib.Variant("(ss)", (MANAGER, "BlockInhibited")),
                GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 10_000, None)
        except GLib.Error as error:
            raise Failed(f"logind BlockInhibited failed: {error.message}") from error
        return str(reply.unpack()[0])

    def suspend(self) -> None:
        """`Suspend`, not interactive."""
        self._call("Suspend", GLib.Variant("(b)", (False,)))

    def reload(self) -> None:
        """logind reads its configuration again: SIGHUP to its main process,
        as `systemctl kill -s HUP systemd-logind` sends it. Never a restart,
        which would end every session on the machine."""
        try:
            self._connection.call_sync(
                SYSTEMD, SYSTEMD_PATH, SYSTEMD_MANAGER, "KillUnit",
                GLib.Variant("(ssi)", ("systemd-logind.service", "main", SIGHUP)),
                None, Gio.DBusCallFlags.NONE, 10_000, None)
        except GLib.Error as error:
            raise Failed(f"logind could not be reloaded: {error.message}") from error


class SleepGuard:
    """Locks a child's session before the computer sleeps, whatever put it
    to sleep: the lid, a computer left alone, a key (D119).

    logind is asked for a delay lock on sleep, which holds a sleep back
    until it is let go, for at most `InhibitDelayMaxSec` (kidux-session's
    logind.conf). When logind announces a sleep, `on_sleep` runs, and locks
    every unlocked session, and the lock is let go; when the computer wakes,
    a new one is taken for the next sleep.
    """

    WHO = "Kidux"
    WHY = "A child's session locks before the computer sleeps."

    def __init__(self, connection: Gio.DBusConnection, on_sleep) -> None:
        self._connection = connection
        self._on_sleep = on_sleep
        self._fd: int | None = None

    def start(self) -> None:
        self._connection.signal_subscribe(
            LOGIND, MANAGER, "PrepareForSleep", MANAGER_PATH, None,
            Gio.DBusSignalFlags.NONE, self._prepare)
        self._take()

    def _take(self) -> None:
        if self._fd is not None:
            return
        try:
            reply, fds = self._connection.call_with_unix_fd_list_sync(
                LOGIND, MANAGER_PATH, MANAGER, "Inhibit",
                GLib.Variant("(ssss)", ("sleep", self.WHO, self.WHY, "delay")),
                GLib.VariantType("(h)"), Gio.DBusCallFlags.NONE, 10_000, None, None)
        except GLib.Error as error:
            _log.warning("no delay lock on sleep: %s", error.message)
            return
        self._fd = fds.get(reply.unpack()[0])

    def _let_go(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def _prepare(self, connection, sender, path, interface, signal_name, parameters) -> None:
        (going,) = parameters.unpack()
        if not going:
            self._take()
            return
        try:
            self._on_sleep()
        except Exception:
            _log.exception("could not lock before the computer sleeps")
        finally:
            self._let_go()


class FakeLogind:
    def __init__(self) -> None:
        self.open: list[SessionInfo] = []
        self.terminated: list[int] = []
        self.powered_off = False
        self.rebooted = False
        #: logind's answers to Can*, as root would get them.
        self.answers = {"CanSuspend": "yes"}
        self.blocked = ""
        self.slept: list[str] = []
        self.reloads = 0

    def sessions(self) -> list[SessionInfo]:
        return list(self.open)

    def terminate_user(self, uid: int) -> None:
        self.terminated.append(uid)
        self.open = [session for session in self.open if session.uid != uid]

    def power_off(self) -> None:
        self.powered_off = True

    def reboot(self) -> None:
        self.rebooted = True

    def can(self, what: str) -> str:
        return self.answers.get(f"Can{what}", "na")

    def block_inhibited(self) -> str:
        return self.blocked

    def suspend(self) -> None:
        self.slept.append("Suspend")

    def reload(self) -> None:
        self.reloads += 1


def has_session(logind: Logind, uid: int) -> bool:
    """Whether this user is signed in: a session of class "user"."""
    return any(session.uid == uid and session.session_class == "user"
               for session in logind.sessions())


def has_manager(logind: Logind, uid: int) -> bool:
    """Whether logind still holds anything of this user's: their user manager,
    for the seconds after their last session, or a session of any class."""
    return any(session.uid == uid for session in logind.sessions())


class SessionWatcher:
    """Tells the daemon about sessions appearing and disappearing.

    Every session is described the same way, whether it was already running
    when the daemon started or appeared afterwards: id, object path, uid,
    class, scope unit and virtual terminal.
    """

    def __init__(self, connection: Gio.DBusConnection, on_new, on_removed) -> None:
        self._connection = connection
        self._on_new = on_new
        self._on_removed = on_removed
        self._subscriptions: list[int] = []

    def describe(self, session_path: str) -> dict | None:
        try:
            reply = self._connection.call_sync(
                LOGIND,
                session_path,
                "org.freedesktop.DBus.Properties",
                "GetAll",
                GLib.Variant("(s)", ("org.freedesktop.login1.Session",)),
                GLib.VariantType("(a{sv})"),
                Gio.DBusCallFlags.NONE,
                10_000,
                None,
            )
        except GLib.Error:
            return None
        properties = reply.unpack()[0]
        return {
            "id": properties.get("Id", ""),
            "path": session_path,
            "uid": int(properties.get("User", (0, ""))[0]),
            "class": properties.get("Class", ""),
            "scope": properties.get("Scope", ""),
            "vtnr": int(properties.get("VTNr", 0)),
        }

    def existing(self) -> list[dict]:
        found = []
        for session in SystemLogind(self._connection).sessions():
            description = self.describe(session.path)
            if description is not None:
                found.append(description)
        return found

    def start(self) -> None:
        for signal, handler in (
            ("SessionNew", self._new),
            ("SessionRemoved", self._removed),
        ):
            self._subscriptions.append(
                self._connection.signal_subscribe(
                    LOGIND, MANAGER, signal, MANAGER_PATH, None,
                    Gio.DBusSignalFlags.NONE, handler,
                )
            )

    def _new(self, connection, sender, path, interface, signal, parameters) -> None:
        _session_id, session_path = parameters.unpack()
        description = self.describe(session_path)
        if description is not None:
            self._on_new(description)

    def _removed(self, connection, sender, path, interface, signal, parameters) -> None:
        session_id, _session_path = parameters.unpack()
        self._on_removed(session_id)
