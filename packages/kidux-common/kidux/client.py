"""Talking to the daemon.

The greeter, the lock screen, the launcher and the adult panel all reach the
daemon through this, so the method names, the argument order and the meaning of
what comes back are decided once. The wire protocol is in the phase 1 plan,
section 7; this is its only client.

Two things it deliberately does not do.

It does not cache. A child's remaining time changes while they sit there, and
an answer that is thirty seconds old is a wrong answer to the only question
that matters.

It does not decide anything. Every rule about who may do what lives in the
daemon, because everything that runs as the child can eventually be killed,
edited or lied to by the child. This client is a telephone, not a gatekeeper.
"""

from typing import Any

from gi.repository import Gio, GLib

from . import paths
from .log import get_logger

_log = get_logger("client")

#: How long to wait for the daemon before giving up, in milliseconds. Long
#: enough for a slow machine waking a disk, short enough that a screen a child
#: is looking at never appears frozen.
DEFAULT_TIMEOUT_MS = 10_000


class DaemonError(Exception):
    """The daemon refused a call or could not be reached."""


class DaemonUnavailableError(DaemonError):
    """The daemon is not on the bus.

    Usually means the machine is still starting. Screens should say so and
    offer to wait, never show an error a child cannot act on.
    """


class PermissionDeniedError(DaemonError):
    """polkit or the daemon refused this caller.

    A bug rather than something to show a child: the screens are only ever
    given buttons for things their user is allowed to do.
    """


class Client:
    """A connection to org.kidux.Daemon1 on the system bus."""

    def __init__(self, *, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None:
        self._timeout_ms = timeout_ms
        self._connection: Gio.DBusConnection | None = None

    # --- connection ----------------------------------------------------------

    @property
    def connection(self) -> Gio.DBusConnection:
        if self._connection is None:
            try:
                self._connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            except GLib.Error as error:
                raise DaemonUnavailableError(
                    f"cannot reach the system bus: {error.message}"
                ) from error
        return self._connection

    def call(
        self,
        interface: str,
        method: str,
        arguments: GLib.Variant | None = None,
        reply_type: GLib.VariantType | None = None,
        timeout_ms: int | None = None,
    ) -> GLib.Variant:
        """Call one method and return its reply, waiting `timeout_ms` for
        it, or the client's own time.

        `interface` is the short name, without the bus prefix: "Parental1",
        "Access1", "Children1", "Modules1", "System1", or "" for the daemon's
        own interface.
        """
        full_interface = paths.BUS_NAME if not interface else f"{paths.BUS_NAME}.{interface}"

        try:
            return self.connection.call_sync(
                paths.BUS_NAME,
                paths.OBJECT_PATH,
                full_interface,
                method,
                arguments,
                reply_type,
                Gio.DBusCallFlags.NONE,
                timeout_ms or self._timeout_ms,
                None,
            )
        except GLib.Error as error:
            raise _translate_error(error, method) from error

    # --- the daemon itself ---------------------------------------------------

    def ping(self) -> str:
        """Check the daemon is there and answering. Returns its version."""
        return self.call("", "Ping", None, GLib.VariantType("(s)"))[0]

    # --- Parental1 -----------------------------------------------------------

    def is_password_set(self) -> bool:
        """Whether an adult password exists yet.

        False on a machine that has never been set up, which is what sends the
        first-run wizard to the front instead of the sign-in screen.
        """
        return self.call(
            "Parental1", "IsPasswordSet", None, GLib.VariantType("(b)")
        )[0]

    def unlock(self, password: str) -> str:
        """Check the adult password and open a privileged session.

        Returns a token that every configuration change then has to carry. The
        token is bound to this connection and dies with it, so the panel cannot
        be left unlocked behind someone's back.

        Callable only from the trusted screens: the adult password is never
        typed inside a child's session, where a child who can run code could
        put a convincing fake prompt on the screen.
        """
        return self.call(
            "Parental1",
            "Unlock",
            GLib.Variant("(s)", (password,)),
            GLib.VariantType("(s)"),
        )[0]

    def lock(self, token: str) -> None:
        """Give up a privileged session. The token is dead afterwards."""
        self.call("Parental1", "Lock", GLib.Variant("(s)", (token,)))

    def set_adult_password(self, token: str, new_password: str) -> None:
        """Set the adult password. The first one, on a machine never set up,
        needs no token: pass an empty one."""
        self.call(
            "Parental1",
            "SetPassword",
            GLib.Variant("(ss)", (token, new_password)),
        )

    def recovery_password(self, token: str) -> str:
        """The GRUB recovery password, for the adult to read off the panel."""
        return self.call(
            "Parental1", "GetRecoveryPassword", GLib.Variant("(s)", (token,)),
            GLib.VariantType("(s)"),
        )[0]

    # --- Daemon1 -------------------------------------------------------------

    def config(self) -> dict[str, Any]:
        """The machine's settings: default language and keyboard, display scale,
        whether setup is complete and whether a language was chosen."""
        return dict(self.call("", "GetConfig", None, GLib.VariantType("(a{sv})"))[0])

    def set_config(self, token: str, changes: dict[str, Any]) -> None:
        """Change the machine's settings. Before the first adult password,
        the language and keyboard may be set with an empty token."""
        self.call("", "SetConfig", GLib.Variant("(sa{sv})", (token, _variants(changes))))

    # --- Children1 -----------------------------------------------------------

    def list_children(self) -> list[dict[str, Any]]:
        """Every child on this machine, in the order they should be shown."""
        reply = self.call(
            "Children1", "List", None, GLib.VariantType("(aa{sv})")
        )
        return [dict(entry) for entry in reply[0]]

    def create_child(self, token: str, username: str, display_name: str, language: str,
                     keyboard: str, avatar: str, password: str) -> None:
        self.call(
            "Children1", "Create",
            GLib.Variant("(sssssss)", (token, username, display_name, language, keyboard,
                                       avatar, password)),
        )

    def delete_child(self, token: str, username: str, keep_home: bool) -> None:
        self.call("Children1", "Delete", GLib.Variant("(ssb)", (token, username, keep_home)))

    def set_profile(self, token: str, username: str, changes: dict[str, Any]) -> None:
        """Change a child's name, language, keyboard, avatar or age."""
        self.call("Children1", "SetProfile",
                  GLib.Variant("(ssa{sv})", (token, username, _variants(changes))))

    def set_child_password(self, token: str, username: str, password: str) -> None:
        self.call("Children1", "SetChildPassword",
                  GLib.Variant("(sss)", (token, username, password)))

    # --- Access1 -------------------------------------------------------------

    def policy(self, username: str) -> dict[str, Any]:
        """A child's mode, daily minutes, days and the time in their bank."""
        return dict(self.call("Access1", "GetPolicy", GLib.Variant("(s)", (username,)),
                              GLib.VariantType("(a{sv})"))[0])

    def set_policy(self, token: str, username: str, mode: str, daily_minutes: int,
                   days: list[bool] | None = None) -> None:
        """A child's mode and daily minutes, and the days of the week their
        time is for, Monday first; days left out are kept as they are."""
        changes = {"mode": mode, "daily_minutes": daily_minutes}
        if days is not None:
            changes["days"] = list(days)
        self.call("Access1", "SetPolicy",
                  GLib.Variant("(ssa{sv})", (token, username, _variants(changes))))

    def grant(self, token: str, username: str, minutes: int) -> None:
        """Give a child time from the panel, without the password again."""
        self.call("Access1", "Grant", GLib.Variant("(ssu)", (token, username, minutes)))

    def set_time_left(self, token: str, username: str, minutes: int) -> None:
        """Set what a child has left today, zero included, from the panel."""
        self.call("Access1", "SetTimeLeft", GLib.Variant("(ssu)", (token, username, minutes)))

    def check_access(self, username: str) -> tuple[str, int]:
        """Whether this child may start a session now, and for how long.

        Returns the state — "allowed", "needs_adult", "blocked", "day_off"
        or "updating" — and the seconds available, or -1 for a child with no
        limit.

        The greeter calls this *after* the child's password has been accepted,
        so that a wrong password and a spent allowance are never confused for
        one another on screen. A child who has used up their day should be told
        exactly that, not left wondering whether they typed it wrong.
        """
        reply = self.call(
            "Access1",
            "CheckAccess",
            GLib.Variant("(s)", (username,)),
            GLib.VariantType("(si)"),
        )
        return reply[0], reply[1]

    def usage(self, username: str) -> tuple[int, int]:
        """Seconds used today, and seconds still available (-1 for no limit).

        The one method a child's own session may call about itself, because the
        launcher shows the remaining time all day.
        """
        reply = self.call(
            "Access1",
            "Usage",
            GLib.Variant("(s)", (username,)),
            GLib.VariantType("(ui)"),
        )
        return reply[0], reply[1]

    def request_lock(self) -> None:
        """Put the trusted lock screen up over the running session.

        What the launcher's Lock button calls. Also what the daemon does by
        itself when time runs out and when the power button is pressed. The
        session is frozen underneath, never ended: a timer must never destroy
        work a child has not saved.
        """
        self.call("Access1", "Lock")

    def request_lock_for(self, reason: str) -> None:
        """Lock the caller's own session for `reason`: `idle`, left alone for
        the minutes an adult chose, or `lid`, its lid closed (D67). Refused
        with NoSession for idleness right after the session was continued,
        which is a timer that ran out while the session was frozen."""
        self.call("Access1", "LockFor", GLib.Variant("(s)", (reason,)))

    # --- Modules1 ------------------------------------------------------------

    def list_modules(self, username: str) -> list[dict[str, Any]]:
        """Every installed module, by id, with whether it is enabled for this
        child: [{"id": "hello", "enabled": True}, ...], sorted by id.

        A child may ask about themselves only; the trusted screens about
        anyone. The names and pictures are in the manifests (kidux.modules).
        """
        reply = self.call(
            "Modules1",
            "List",
            GLib.Variant("(s)", (username,)),
            GLib.VariantType("(aa{sv})"),
        )
        return [dict(entry) for entry in reply[0]]

    def set_module_enabled(self, token: str, username: str, module_id: str,
                           enabled: bool) -> None:
        """Switch one installed module on or off for one child."""
        self.call("Modules1", "SetEnabled",
                  GLib.Variant("(sssb)", (token, username, module_id, enabled)))

    def module_settings(self, token: str, username: str,
                        module_id: str) -> tuple[dict[str, Any], list[str]]:
        """What an adult has set in a module for a child (D90): the values of
        every setting but the secrets, defaults where nothing is set, and the
        keys of the secrets that are set. A secret is never read back."""
        reply = self.call("Modules1", "Settings",
                          GLib.Variant("(sss)", (token, username, module_id)),
                          GLib.VariantType("(a{sv}as)"))
        return dict(reply[0]), list(reply[1])

    def set_module_setting(self, token: str, username: str, module_id: str, key: str,
                           value: Any) -> None:
        """Set one of a module's settings for a child; the daemon refuses a
        value not of the setting's kind or outside its limits."""
        self.call("Modules1", "SetSetting",
                  GLib.Variant("(ssssv)", (token, username, module_id, key,
                                           _variants({"value": value})["value"])))

    def my_module_settings(self, module_id: str) -> dict[str, Any]:
        """A module's settings for the child asking, from their own session:
        every one but the secrets, defaults where nothing is set."""
        reply = self.call("Modules1", "MySettings", GLib.Variant("(s)", (module_id,)),
                          GLib.VariantType("(a{sv})"))
        return dict(reply[0])

    def sign_in_module(self, module_id: str) -> list[dict[str, Any]]:
        """Ask the daemon to sign the child asking in to their module's
        website (phase-4c-plan.md, 4.17): the session's cookies, never the
        password. The error's text names SignInNotSet, SignInRefused or
        SignInUnreachable when it fails."""
        reply = self.call("Modules1", "SignIn", GLib.Variant("(s)", (module_id,)),
                          GLib.VariantType("(aa{sv})"), timeout_ms=60000)
        return [dict(cookie) for cookie in reply[0]]

    def available_modules(self) -> list[dict[str, Any]]:
        """Every module the archive offers, installed or not, as apt's lists
        know them: [{"id", "name", "description", "installed", "version",
        "min_age", "max_age", "before"}]."""
        reply = self.call("Modules1", "Available", None, GLib.VariantType("(aa{sv})"))
        return [dict(entry) for entry in reply[0]]

    def install_module(self, token: str, module_id: str) -> None:
        """Start installing a module's package; UpdateState says how it goes.
        Refused while a child is signed in."""
        self.call("Modules1", "Install", GLib.Variant("(ss)", (token, module_id)))

    def remove_module(self, token: str, module_id: str) -> None:
        """Start removing a module's package, the children's files kept."""
        self.call("Modules1", "Remove", GLib.Variant("(ss)", (token, module_id)))

    # --- System1 -------------------------------------------------------------

    def shutdown(self) -> None:
        """Turn the machine off. A child may always do this."""
        self.call("System1", "Shutdown")

    def reboot(self) -> None:
        self.call("System1", "Reboot")

    def sleep_when_idle(self) -> str:
        """A screen left alone the minutes an adult chose: the computer
        sleeps, or suspends and then hibernates, unless the adult chose
        the screen off only or something holds idleness off (D119). What
        the daemon did, "" for nothing."""
        return self.call("System1", "SleepWhenIdle").unpack()[0]

    def check_updates(self, token: str) -> None:
        """Start looking for updates; UpdateState says when it is done."""
        self.call("System1", "CheckUpdates", GLib.Variant("(s)", (token,)))

    def apply_updates(self, token: str) -> None:
        """Start installing every update. Refused while a child is signed in."""
        self.call("System1", "ApplyUpdates", GLib.Variant("(s)", (token,)))

    def update_state(self) -> tuple[str, float, str, str, str, list[str]]:
        """The job (idle, checking, applying, installing, removing), how far
        it is, the package it is on, and the last job's outcome, detail and
        the packages it found."""
        reply = self.call("System1", "UpdateState", None,
                          GLib.VariantType("(sdsssas)"))
        return reply[0], reply[1], reply[2], reply[3], reply[4], list(reply[5])

    def versions(self) -> dict[str, str]:
        """The version of every Kidux package installed, by package name:
        what the sign-in screen and the panel say this machine runs."""
        reply = self.call("System1", "Versions", None, GLib.VariantType("(a{sv})"))
        return {str(k): str(v) for k, v in reply[0].items()}

    # --- Network1 (D62) ------------------------------------------------------

    def network(self, token: str) -> tuple[dict[str, Any], list[dict[str, Any]],
                                           list[dict[str, Any]]]:
        """What the Network page shows: a summary (the job running, the
        router's answer, how the last job ended), the interfaces, and the
        Wi-Fi networks in reach."""
        reply = self.call("Network1", "GetNetwork", GLib.Variant("(s)", (token,)),
                          GLib.VariantType("(a{sv}aa{sv}aa{sv})"))
        return dict(reply[0]), [dict(e) for e in reply[1]], [dict(e) for e in reply[2]]

    def check_network(self, token: str) -> None:
        """Look again: a rescan and a ping of the gateway, in a job."""
        self.call("Network1", "Check", GLib.Variant("(s)", (token,)))

    def connect_wifi(self, token: str, ssid: str, password: str) -> None:
        """Start joining a Wi-Fi network; `network` says how it went."""
        self.call("Network1", "ConnectWifi", GLib.Variant("(sss)", (token, ssid, password)))

    def forget_wifi(self, token: str, ssid: str) -> None:
        self.call("Network1", "ForgetWifi", GLib.Variant("(ss)", (token, ssid)))


def _variants(values: dict[str, Any]) -> dict[str, GLib.Variant]:
    """A dict of plain values as the a{sv} D-Bus wants."""
    wrapped = {}
    for key, value in values.items():
        if isinstance(value, bool):
            wrapped[key] = GLib.Variant("b", value)
        elif isinstance(value, int):
            wrapped[key] = GLib.Variant("i", value)
        elif isinstance(value, float):
            wrapped[key] = GLib.Variant("d", value)
        elif isinstance(value, (list, tuple)) and value \
                and all(isinstance(item, bool) for item in value):
            wrapped[key] = GLib.Variant("ab", list(value))
        elif isinstance(value, (list, tuple)):
            wrapped[key] = GLib.Variant("as", [str(item) for item in value])
        else:
            wrapped[key] = GLib.Variant("s", str(value))
    return wrapped


def _translate_error(error: GLib.Error, method: str) -> DaemonError:
    """Turn a D-Bus error into something a screen can act on."""
    message = error.message or str(error)

    if Gio.DBusError.is_remote_error(error):
        remote = Gio.DBusError.get_remote_error(error) or ""
        if remote.endswith(".ServiceUnknown") or remote.endswith(".NameHasNoOwner"):
            return DaemonUnavailableError(f"the daemon is not running ({method})")
        if "AccessDenied" in remote or "NotAuthorized" in remote:
            return PermissionDeniedError(f"{method} was refused: {message}")

    _log.debug("%s failed: %s", method, message)
    return DaemonError(f"{method} failed: {message}")
