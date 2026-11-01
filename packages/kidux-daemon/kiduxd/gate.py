"""Who may call what, and on whose behalf (daemon.md section 2, D27).

Two halves, kept in one module so that every rule about permission is in one
place and each one has a test that tries to get past it.

**polkit decides who may call a method.** `ACTIONS` maps every method to one
of three polkit actions, or to none for the handful anyone may call. The
rules that say which users hold which action ship in
`/usr/share/polkit-1/rules.d/50-kidux.rules`.

**The daemon decides which child a call may touch**, because polkit sees the
action and the caller and never the arguments. A child allowed to ask about
their own time could otherwise ask about a sibling's, and an unlocked panel
could delete the account that owns the machine.
"""

import re
from dataclasses import dataclass
from typing import Protocol

from gi.repository import Gio, GLib

from kidux import paths

from .errors import AccessDenied, InvalidArgument, NoSuchChild, NotAuthorized

MANAGE = "org.kidux.daemon.manage"
SCREENS = "org.kidux.daemon.screens"
SELF = "org.kidux.daemon.self"

#: Every method the daemon exports, and the polkit action it needs. None means
#: anyone on the bus may call it: a child may always turn the computer off.
ACTIONS: dict[tuple[str, str], str | None] = {
    ("Daemon1", "Ping"): None,
    ("Daemon1", "GetConfig"): SCREENS,
    ("Daemon1", "SetConfig"): MANAGE,
    ("Parental1", "IsPasswordSet"): SCREENS,
    ("Parental1", "Unlock"): MANAGE,
    ("Parental1", "Lock"): MANAGE,
    ("Parental1", "SetPassword"): MANAGE,
    ("Parental1", "GetRecoveryPassword"): MANAGE,
    ("Children1", "List"): SCREENS,
    ("Children1", "Create"): MANAGE,
    ("Children1", "Delete"): MANAGE,
    ("Children1", "SetProfile"): MANAGE,
    ("Children1", "SetChildPassword"): MANAGE,
    ("Access1", "GetPolicy"): SCREENS,
    ("Access1", "SetPolicy"): MANAGE,
    ("Access1", "Grant"): MANAGE,
    ("Access1", "SetTimeLeft"): MANAGE,
    ("Access1", "CheckAccess"): SCREENS,
    ("Access1", "Usage"): SELF,
    ("Access1", "AuthoriseSession"): SCREENS,
    ("Access1", "GrantExtraTime"): SCREENS,
    ("Access1", "Lock"): SELF,
    ("Access1", "LockFor"): SELF,
    ("Access1", "UnlockForSaving"): SCREENS,
    ("Access1", "ContinueSession"): SCREENS,
    ("Access1", "EndSession"): SCREENS,
    ("Modules1", "List"): SELF,
    ("Modules1", "SetEnabled"): MANAGE,
    ("Modules1", "Available"): SCREENS,
    ("Modules1", "Install"): MANAGE,
    ("Modules1", "Remove"): MANAGE,
    ("Modules1", "Settings"): MANAGE,
    ("Modules1", "SetSetting"): MANAGE,
    ("Modules1", "MySettings"): SELF,
    ("Modules1", "SignIn"): SELF,
    ("System1", "Shutdown"): None,
    ("System1", "Reboot"): None,
    ("System1", "SleepWhenIdle"): SELF,
    ("System1", "CheckUpdates"): MANAGE,
    ("System1", "ApplyUpdates"): MANAGE,
    ("System1", "UpdateState"): SCREENS,
    ("System1", "Versions"): SCREENS,
    ("Network1", "GetNetwork"): MANAGE,
    ("Network1", "Check"): MANAGE,
    ("Network1", "ConnectWifi"): MANAGE,
    ("Network1", "ForgetWifi"): MANAGE,
}

USERNAME = re.compile(r"\A[a-z][a-z0-9-]{0,31}\Z")

#: Names no child may be given, whatever the panel sends.
RESERVED_NAMES = frozenset(
    {
        "root",
        paths.GREETER_USER,
        paths.ADMIN_GROUP,
        paths.CHILDREN_GROUP,
        "kidux",
    }
)


@dataclass(frozen=True)
class Caller:
    """Who is on the other end of a call: the connection and its uid."""

    unique_name: str
    uid: int


class Authority(Protocol):
    def check(self, unique_name: str, action_id: str) -> bool: ...


class PolkitAuthority:
    """Asks polkitd, never interactively: there is no agent to answer."""

    def __init__(self, connection: Gio.DBusConnection) -> None:
        self._connection = connection

    def check(self, unique_name: str, action_id: str) -> bool:
        subject = ("system-bus-name", {"name": GLib.Variant("s", unique_name)})
        try:
            reply = self._connection.call_sync(
                "org.freedesktop.PolicyKit1",
                "/org/freedesktop/PolicyKit1/Authority",
                "org.freedesktop.PolicyKit1.Authority",
                "CheckAuthorization",
                GLib.Variant("((sa{sv})sa{ss}us)", (subject, action_id, {}, 0, "")),
                GLib.VariantType("((bba{ss}))"),
                Gio.DBusCallFlags.NONE,
                10_000,
                None,
            )
        except GLib.Error:
            # polkit unreachable is a refusal. A daemon that grants everything
            # while polkit restarts would be a hole exactly as wide as the
            # restart.
            return False
        return bool(reply.unpack()[0][0])


class Gate:
    def __init__(self, authority: Authority, accounts) -> None:
        self._authority = authority
        self._accounts = accounts

    # --- polkit --------------------------------------------------------------

    def require(self, caller: Caller, interface: str, method: str) -> None:
        if (interface, method) not in ACTIONS:
            raise NotAuthorized(f"{interface}.{method} is not a method of this daemon")

        action = ACTIONS[(interface, method)]
        if action is None:
            return

        # root owns the machine already; asking polkit would add nothing.
        if caller.uid == 0:
            return

        if not self._authority.check(caller.unique_name, action):
            raise AccessDenied(f"{interface}.{method} is not allowed for this caller")

    # --- what polkit cannot see ----------------------------------------------

    def caller_is_child(self, caller: Caller) -> bool:
        name = self._accounts.username_of(caller.uid)
        return name is not None and self._accounts.in_group(name, paths.CHILDREN_GROUP)

    def require_self(self, caller: Caller, username: str) -> None:
        """A child may ask only about themselves. Anyone else may ask about anyone."""
        if not self.caller_is_child(caller):
            return
        if self._accounts.uid_of(username) != caller.uid:
            raise NotAuthorized("a child may only ask about themselves")

    def require_child(self, username: str) -> None:
        """Only members of kidux-children are ever managed.

        Never the administrator, never _greetd, never a system account,
        whatever the token says. This is what stops an unlocked panel, or a
        bug in one, from deleting the account that owns the machine.
        """
        if not USERNAME.match(username or ""):
            raise NoSuchChild(f"{username!r} is not a child on this computer")
        if not self._accounts.in_group(username, paths.CHILDREN_GROUP):
            raise NoSuchChild(f"{username!r} is not a child on this computer")

    def validate_new_username(self, username: str) -> None:
        if not USERNAME.match(username or ""):
            raise InvalidArgument(
                "a child's username is lower-case letters, digits and hyphens, "
                "starting with a letter, at most 32 characters"
            )
        if username in RESERVED_NAMES:
            raise InvalidArgument(f"{username!r} is reserved")
        if self._accounts.exists(username):
            raise InvalidArgument(f"{username!r} already exists on this computer")
