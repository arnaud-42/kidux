"""The daemon's behaviour, independent of D-Bus.

Every exported method is a method here named `<Interface>_<Method>`, taking
the caller first. `dispatch` is the single way in: it runs the polkit gate and
then the method. The bus layer (bus.py) only translates between D-Bus values
and these calls, so everything that decides anything can be tested here,
without a bus, in milliseconds.

Every call that changes something, and every attempt at a password, is
audited with its outcome. Passwords and tokens are never audited: kidux.log
drops them whatever is passed in, and nothing here passes them.
"""

import subprocess
import time
from dataclasses import replace
from datetime import datetime
from typing import Callable

from kidux import log, paths, pointer, state
from kidux import modules as kidux_modules

from . import VERSION, catalogue, signin
from .access import (
    MAX_MINUTES, UNLIMITED, available, check_access, days_text, grant, set_left,
    validate_policy, weekday_of,
)
from .adults import AdultPassword
from .advanced import check_flags, write_flags, write_input
from . import power, statistics
from .children import Children
from .config import Config
from .errors import (
    Failed,
    InvalidArgument,
    NoSession,
    NoTimeLeft,
    NotAuthorized,
    SignInNotSet,
    SessionActive,
    WrongPassword,
)
from .gate import Caller, Gate
from .locker import Locker
from .logind import Logind
from .network import Network
from .sessions import Timekeeper, Tracked
from .tokens import Tokens
from .updates import Updates

_log = log.get_logger("service")

#: An adult may unlock a session so the child can save for at most this long.
MAX_GRACE_MINUTES = 15

#: What SetConfig may change. The reset hour is not offered anywhere, so
#: nothing may set it.
SETTABLE = ("default_language", "default_keyboard", "display_scale", "setup_complete",
            "chromium_flags", "idle_lock_minutes", "screen_off_minutes", "save_minutes",
            "pointer_speed", "scroll_speed", "apt_statistics", "lid_action", "idle_action",
            "idle_sleep_minutes")
#: The minutes a session may be left alone before it locks, and before the
#: screen turns off, as the panel offers them (D67).
IDLE_LOCK_MINUTES = (1, 120)
SCREEN_OFF_MINUTES = (1, 240)
#: A lock for idleness this soon after the session was given the screen
#: back is a timer that ran out while the session was frozen, not a child
#: who walked away, and is refused.
IDLE_LOCK_GRACE_SECONDS = 10
#: Why a session may lock itself, besides its Lock button (D67).
LOCK_REASONS = ("idle", "lid")

#: What SetConfig may change on a machine with no adult password yet, when
#: there is no token to be had: what the first-run wizard sets before the
#: password, because the password has to be typed in the right keyboard.
BEFORE_PASSWORD = frozenset({"default_language", "default_keyboard"})

MIN_SCALE, MAX_SCALE = 1.0, 3.0


class SystemClock:
    def wall(self) -> datetime:
        return datetime.now().astimezone()

    def mono(self) -> float:
        return time.monotonic()

Emit = Callable[[str, str, str, tuple], None]


class Later:
    """An answer that takes time, such as a website's: `work`, run by the
    bus layer in a thread of its own so that the daemon goes on answering
    everyone else, and answered when it returns or raises."""

    def __init__(self, work: Callable[[], object]) -> None:
        self.work = work


class Service:
    def __init__(
        self,
        *,
        gate: Gate,
        accounts,
        logind: Logind,
        adults: AdultPassword | None = None,
        tokens: Tokens | None = None,
        children: Children | None = None,
        locker: Locker | None = None,
        clock=None,
        check_child_password: Callable[[str, str], bool] | None = None,
        emit: Emit | None = None,
        audit: Callable[..., None] = log.audit,
        updates: Updates | None = None,
        modules_offered: Callable[[], tuple[str, str]] | None = None,
        network: Network | None = None,
        kidux_packages: Callable[[], str] | None = None,
    ) -> None:
        config = Config.load()
        self.gate = gate
        self.accounts = accounts
        self.logind = logind
        self.adults = adults or AdultPassword()
        self.tokens = tokens or Tokens(config.idle_lock_minutes * 60)
        self._clock = clock or SystemClock()
        self.children = children or Children(accounts, logind)
        self.locker = locker
        #: Sessions being ended, on purpose or for having lost their
        #: compositor, until logind says they are gone: closing, but not
        #: abandoned (end_abandoned_locks).
        self._ending: set[str] = set()
        self._emit = emit or (lambda interface, signal, signature, args: None)
        self._audit = audit
        #: How a child is signed in to a module's website: one HTTPS request,
        #: replaced in the tests by a fake website.
        self.sign_in_request = signin.request_in_unit
        #: The lid's switch and the screens connected, read from the machine;
        #: replaced in the tests.
        self.lid_is_closed = power.lid_is_closed
        self.connected_screens = power.connected_screens
        #: When a key was last pressed, on the clock's monotonic seconds.
        self._last_key = float("-inf")
        if check_child_password is None:
            from .pamcheck import check_password as check_child_password
        self._check_child_password = check_child_password
        self.timekeeper = Timekeeper(
            self._clock,
            reset_hour=int(config.reset_hour),
            audit=audit,
            emit=lambda *signal: self._emit(*signal),
            on_time_up=lambda tracked: self._lock(tracked, "time_up"),
            on_grace_over=lambda tracked: self._lock(tracked, "grace"),
        )
        #: Called whenever the next tick may be due sooner than planned.
        self.on_timing_changed: Callable[[], None] = lambda: None
        #: The update job (section 12); None on a daemon that cannot run one.
        self.updates = updates
        #: Called when a job starts, so the main loop watches its status file.
        self.on_update_started: Callable[[], None] = lambda: None
        #: What apt and dpkg say about the module packages (catalogue.py):
        #: the output of `apt-cache search` and of `dpkg-query`.
        self.modules_offered = modules_offered
        #: The machine's network, for the panel's Network page (D62); None
        #: on a daemon that cannot read it.
        self.network = network
        #: What dpkg says about the Kidux packages (Machine.kidux_packages).
        self.kidux_packages = kidux_packages

    # --- the way in ----------------------------------------------------------

    def dispatch(self, caller: Caller, interface: str, method: str, *args):
        self.gate.require(caller, interface, method)
        handler = getattr(self, f"{interface}_{method}")
        return handler(caller, *args)

    def connection_closed(self, unique_name: str) -> None:
        """A connection left the bus: whatever token it held is dead."""
        if self.tokens.revoke_name(unique_name):
            self._audit("panel locked", "ok", reason="connection closed")

    def expire_tokens(self) -> None:
        for uid in self.tokens.expire():
            self._audit("panel locked", "ok", reason="idle", uid=uid)

    # --- helpers -------------------------------------------------------------

    def _who(self, caller: Caller) -> str:
        return self.accounts.username_of(caller.uid) or str(caller.uid)

    def _require_token(self, caller: Caller, token: str) -> None:
        self.tokens.check(token, caller.unique_name, caller.uid)

    # --- Daemon1 -------------------------------------------------------------

    def Daemon1_Ping(self, caller: Caller) -> str:
        return VERSION

    def Daemon1_GetConfig(self, caller: Caller) -> dict:
        config = Config.load()
        return {
            "default_language": config.default_language,
            "default_keyboard": config.default_keyboard,
            "display_scale": float(config.display_scale),
            "reset_hour": int(config.reset_hour),
            "setup_complete": bool(config.setup_complete),
            "language_chosen": bool(config.language_chosen),
            "chromium_flags": list(config.chromium_flags),
            "pointer_speed": int(config.pointer_speed),
            "scroll_speed": int(config.scroll_speed),
            "idle_lock_minutes": int(config.idle_lock_minutes),
            "screen_off_minutes": int(config.screen_off_minutes),
            "save_minutes": int(config.save_minutes),
            "apt_statistics": bool(config.apt_statistics),
            **self._power_config(config),
        }

    def _power_config(self, config: Config) -> dict:
        """The power settings as chosen, and whether this computer can
        suspend, for the panel to warn when it cannot (power.py, D119)."""
        return {
            "lid_action": str(config.lid_action),
            "idle_action": str(config.idle_action),
            "idle_sleep_minutes": int(config.idle_sleep_minutes),
            "can_sleep": self.can_sleep(),
        }

    def Daemon1_SetConfig(self, caller: Caller, token: str, changes: dict) -> None:
        unknown = set(changes) - set(SETTABLE)
        if unknown:
            raise InvalidArgument(f"not a setting that can be changed: {', '.join(sorted(unknown))}")
        # Like SetPassword: a machine never set up has no token to give, and
        # the wizard sets the language and keyboard before the password.
        # Nothing else is open before then.
        if self.adults.is_set() or not set(changes) <= BEFORE_PASSWORD:
            self._require_token(caller, token)

        config = Config.load()
        if "default_language" in changes:
            config.default_language = self.children.check_language(changes["default_language"])
            config.language_chosen = True
        if "default_keyboard" in changes:
            config.default_keyboard = self.children.check_keyboard(changes["default_keyboard"])
        if "display_scale" in changes:
            scale = changes["display_scale"]
            if isinstance(scale, bool) or not isinstance(scale, (int, float)) \
                    or not (scale == 0 or MIN_SCALE <= scale <= MAX_SCALE):
                raise InvalidArgument(f"the display scale is 0, automatic, or from {MIN_SCALE} "
                                      f"to {MAX_SCALE}")
            config.display_scale = float(scale)
        for key in ("setup_complete", "apt_statistics"):
            if key in changes:
                if not isinstance(changes[key], bool):
                    raise InvalidArgument(f"{key} is true or false")
                setattr(config, key, changes[key])
        if "chromium_flags" in changes:
            try:
                config.chromium_flags = check_flags(changes["chromium_flags"])
            except ValueError as error:
                raise InvalidArgument(str(error)) from error
        for key in ("pointer_speed", "scroll_speed"):
            if key in changes:
                try:
                    setattr(config, key, pointer.step(changes[key]))
                except ValueError as error:
                    raise InvalidArgument(f"{key}: {error}") from error
        for key, choices in (("lid_action", power.LID_ACTIONS),
                             ("idle_action", power.IDLE_ACTIONS)):
            if key in changes:
                if changes[key] not in choices:
                    raise InvalidArgument(f"{key} is one of {', '.join(choices)}")
                setattr(config, key, changes[key])
        for key, (least, most) in (("idle_lock_minutes", IDLE_LOCK_MINUTES),
                                   ("screen_off_minutes", SCREEN_OFF_MINUTES),
                                   ("idle_sleep_minutes", power.IDLE_SLEEP_MINUTES),
                                   ("save_minutes", (1, MAX_GRACE_MINUTES))):
            if key in changes:
                minutes = changes[key]
                if isinstance(minutes, bool) or not isinstance(minutes, int) \
                        or not least <= minutes <= most:
                    raise InvalidArgument(f"{key} is a whole number from {least} to {most}")
                setattr(config, key, minutes)
        config.save()
        if "idle_lock_minutes" in changes:
            self.tokens.set_timeout(config.idle_lock_minutes * 60)
        if "chromium_flags" in changes:
            write_flags(config.chromium_flags)
        if {"pointer_speed", "scroll_speed"} & set(changes):
            write_input(config.pointer_speed, config.scroll_speed)
        if "apt_statistics" in changes:
            statistics.apply(config)
        self._audit("config set", "ok", caller=self._who(caller), fields=sorted(changes))

    # --- Parental1 -----------------------------------------------------------

    def Parental1_IsPasswordSet(self, caller: Caller) -> bool:
        return self.adults.is_set()

    def Parental1_Unlock(self, caller: Caller, password: str) -> str:
        if not self.adults.verify(password):
            self._audit("unlock", "denied", caller=self._who(caller))
            raise WrongPassword("that is not the adult password")
        token = self.tokens.issue(caller.unique_name, caller.uid)
        self._audit("unlock", "ok", caller=self._who(caller))
        return token

    def Parental1_Lock(self, caller: Caller, token: str) -> None:
        if self.tokens.revoke(token, caller.unique_name):
            self._audit("panel locked", "ok", caller=self._who(caller))

    def Parental1_SetPassword(self, caller: Caller, token: str, new_password: str) -> None:
        # On a machine that has never been set up there is no password to
        # unlock with, so the first one is set without a token. polkit has
        # already limited who may call this at all; from then on, changing it
        # takes the old one.
        first_time = not self.adults.is_set()
        if not first_time:
            self._require_token(caller, token)
        self.adults.set(new_password)
        self._audit(
            "adult password set",
            "ok",
            caller=self._who(caller),
            first_time=first_time,
        )

    def Parental1_GetRecoveryPassword(self, caller: Caller, token: str) -> str:
        """The GRUB recovery password, for the adult to read off the panel."""
        self._require_token(caller, token)
        password, _ = self.adults.grub()
        self._audit("recovery password shown", "ok", caller=self._who(caller))
        return password or ""

    # --- Children1 -----------------------------------------------------------

    def Children1_List(self, caller: Caller) -> list[dict]:
        return self.children.list()

    def Children1_Create(
        self,
        caller: Caller,
        token: str,
        username: str,
        display_name: str,
        language: str,
        keyboard: str,
        avatar: str,
        password: str,
    ) -> None:
        self._require_token(caller, token)
        self.gate.validate_new_username(username)
        try:
            self.children.create(username, display_name, language, keyboard, avatar, password)
        except Exception as error:
            self._audit("child created", "failed", caller=self._who(caller), child=username,
                        reason=str(error))
            raise
        self._audit("child created", "ok", caller=self._who(caller), child=username)
        self._emit("Children1", "ChildrenChanged", "()", ())

    def Children1_Delete(self, caller: Caller, token: str, username: str, keep_home: bool) -> None:
        self._require_token(caller, token)
        self.gate.require_child(username)
        self.children.delete(username, keep_home)
        self._audit("child deleted", "ok", caller=self._who(caller), child=username,
                    keep_home=keep_home)
        self._emit("Children1", "ChildrenChanged", "()", ())

    def Children1_SetProfile(self, caller: Caller, token: str, username: str, changes: dict) -> None:
        self._require_token(caller, token)
        self.gate.require_child(username)
        changed = self.children.set_profile(username, changes)
        self._audit("profile changed", "ok", caller=self._who(caller), child=username,
                    fields=sorted(changed))
        self._emit("Children1", "ChildrenChanged", "()", ())

    def Children1_SetChildPassword(self, caller: Caller, token: str, username: str,
                                   password: str) -> None:
        self._require_token(caller, token)
        self.gate.require_child(username)
        self.children.set_password(username, password)
        self._audit("child password set", "ok", caller=self._who(caller), child=username)

    # --- Modules1 ------------------------------------------------------------

    def Modules1_List(self, caller: Caller, username: str) -> list[dict]:
        """Every installed module, with whether it is enabled for this child.

        An id in the child's file whose module is no longer installed is not
        listed, and stays in the file: removing a package must not rewrite
        every child's file, and putting it back restores the switch.
        """
        self.gate.require_self(caller, username)
        self.gate.require_child(username)
        enabled = set(self._enabled_modules(username))
        return [{"id": module.id, "enabled": module.id in enabled}
                for module in kidux_modules.installed()]

    def Modules1_SetEnabled(self, caller: Caller, token: str, username: str, module_id: str,
                            enabled: bool) -> None:
        self._require_token(caller, token)
        self.gate.require_child(username)
        if kidux_modules.read(module_id) is None:
            raise InvalidArgument(f"no module called {module_id!r} is installed")
        ids = self._enabled_modules(username)
        if (module_id in ids) == bool(enabled):
            return
        ids = ids + [module_id] if enabled else [i for i in ids if i != module_id]
        state.write(paths.child_modules(username), {"enabled": ids}, "modules")
        self._audit("module enabled" if enabled else "module disabled", "ok",
                    caller=self._who(caller), child=username, module=module_id)
        self._emit("Modules1", "ModulesChanged", "(s)", (username,))

    def Modules1_Available(self, caller: Caller) -> list[dict]:
        """Every module the archive offers, installed or not, from apt's
        lists as they are: as fresh as the last CheckUpdates."""
        if self.modules_offered is None:
            return []
        offered, installed = self.modules_offered()
        language = Config.load().default_language

        def installed_of(module_id: str) -> dict | None:
            module = kidux_modules.read(module_id)
            if module is None:
                return None
            return {"name": kidux_modules.name_in(module, language),
                    "min_age": module.min_age, "max_age": module.max_age,
                    "before": list(module.recommended_before)}

        return catalogue.available(offered, installed, installed_of,
                                   catalogue.language_of(language))

    def Modules1_Install(self, caller: Caller, token: str, module_id: str) -> None:
        self._module_job(caller, token, "install", module_id)

    def Modules1_Remove(self, caller: Caller, token: str, module_id: str) -> None:
        self._module_job(caller, token, "remove", module_id)

    def _module_job(self, caller: Caller, token: str, kind: str, module_id: str) -> None:
        """Install or remove one module's package, as the update job does.

        The caller names a module, never a package: the id is checked here
        and the package name made from it, and kidux-update checks it again.
        Never while a child has a session, locked or not: dpkg must not
        replace or remove what a session may be running.
        """
        self._require_token(caller, token)
        if not kidux_modules.ID.match(module_id or "") or module_id.startswith(catalogue.PREFIX):
            raise InvalidArgument(f"not a module id: {module_id!r}")
        if self.timekeeper.sessions:
            raise SessionActive("children are signed in; modules wait until they log out")
        self._updates().start(kind, catalogue.package_of(module_id))
        self._audit(f"module {kind} started", "ok", caller=self._who(caller), module=module_id)
        self.on_update_started()

    # --- module settings (D90) -------------------------------------------------

    def _module_with_settings(self, module_id: str) -> kidux_modules.Module:
        module = kidux_modules.read(module_id) if kidux_modules.ID.match(module_id or "") else None
        if module is None:
            raise InvalidArgument(f"no module called {module_id!r} is installed")
        return module

    def _stored_settings(self, username: str) -> dict:
        return state.read(paths.child_module_settings(username), "settings", default={})

    def _settings_of(self, username: str, module: kidux_modules.Module) -> tuple[dict, list]:
        """A module's settings for a child: every one but the secrets, its
        stored value when it is still of its kind and its default otherwise;
        and the keys of the secrets that are set."""
        stored = self._stored_settings(username).get(module.id, {})
        values, secrets = {}, []
        for setting in module.settings:
            if setting.kind == "secret":
                if stored.get(setting.key):
                    secrets.append(setting.key)
                continue
            try:
                values[setting.key] = setting.value(stored[setting.key])
            except (KeyError, ValueError):
                values[setting.key] = setting.default
        return values, secrets

    def Modules1_Settings(self, caller: Caller, token: str, username: str,
                          module_id: str) -> tuple[dict, list]:
        self._require_token(caller, token)
        self.gate.require_child(username)
        return self._settings_of(username, self._module_with_settings(module_id))

    def Modules1_SetSetting(self, caller: Caller, token: str, username: str, module_id: str,
                            key: str, value) -> None:
        """One setting of a module for a child, refused unless the module
        declares it and the value is of its kind and within its limits. A
        secret set to "" is a secret forgotten."""
        self._require_token(caller, token)
        self.gate.require_child(username)
        module = self._module_with_settings(module_id)
        setting = next((s for s in module.settings if s.key == key), None)
        if setting is None:
            raise InvalidArgument(f"{module_id} has no setting called {key!r}")
        try:
            value = setting.value(value)
        except ValueError as error:
            raise InvalidArgument(str(error)) from error
        document = self._stored_settings(username)
        document.pop("schema_version", None)
        table = dict(document.get(module_id, {}))
        if setting.kind == "secret" and value == "":
            table.pop(key, None)
        else:
            table[key] = value
        document[module_id] = table
        state.write(paths.child_module_settings(username), document, "settings", mode=0o600)
        self._audit("module setting", "ok", caller=self._who(caller), child=username,
                    module=module_id, setting=key)

    def Modules1_MySettings(self, caller: Caller, module_id: str) -> dict:
        """A module's settings for the child asking, never a secret: what
        their own session hands the module when it starts."""
        username = self.accounts.username_of(caller.uid)
        if username is None or not self.gate.caller_is_child(caller):
            raise NotAuthorized("only a child's own session asks for its module settings")
        return self._settings_of(username, self._module_with_settings(module_id))[0]

    def Modules1_SignIn(self, caller: Caller, module_id: str) -> list[dict]:
        """Sign the child asking in to their module's website, with the
        account an adult gave it (phase-4c-plan.md, 4.17), and hand back
        only the cookies the module names: the password never leaves the
        daemon. What is sent where is the manifest's `sign_in`, data the
        daemon acts on; nothing of the module's runs here."""
        username = self.accounts.username_of(caller.uid)
        if username is None or not self.gate.caller_is_child(caller):
            raise NotAuthorized("only a child's own session signs in to a module")
        module = self._module_with_settings(module_id)
        if module.sign_in is None:
            raise InvalidArgument(f"{module_id} does not sign in")
        stored = self._stored_settings(username).get(module_id, {})
        values = {}
        for setting in module.settings:
            try:
                values[setting.key] = str(setting.value(stored[setting.key]))
            except (KeyError, ValueError):
                values[setting.key] = ""
        body = {}
        for field, template in module.sign_in.body:
            filled = template
            for key, value in values.items():
                if "{" + key + "}" in filled:
                    if not value:
                        raise SignInNotSet(f"{module_id}: no {key} is set for {username}")
                    filled = filled.replace("{" + key + "}", value)
            body[field] = filled
        self._audit("module sign-in", "asked", child=username, module=module_id)
        request, url, wanted = self.sign_in_request, module.sign_in.url, module.sign_in.cookies
        return Later(lambda: request(url, body, wanted))

    def _enabled_modules(self, username: str) -> list[str]:
        document = state.read(paths.child_modules(username), "modules", default={"enabled": []})
        return [i for i in document.get("enabled", []) if isinstance(i, str)]

    # --- sessions, as logind reports them --------------------------------------

    def session_appeared(self, info: dict) -> None:
        """A logind session appeared. Tracked if it is a child's graphical session."""
        # A new sign-in screen is what greetd starting again looks like, and
        # greetd stopping is what abandons a locked session.
        self.end_abandoned_locks()
        if info.get("class") != "user":
            return
        username = self.accounts.username_of(info["uid"])
        if username is None or not self.gate.caller_is_child(Caller("", info["uid"])):
            return
        if username in self.timekeeper.sessions:
            self._audit("second session", "noticed", child=username, session=info["id"])
            return

        _, usage, _ = self.timekeeper.load(username)
        tracked = Tracked(
            username=username,
            uid=info["uid"],
            session_id=info["id"],
            session_path=info["path"],
            scope=info.get("scope", ""),
            vtnr=int(info.get("vtnr", 0)),
            lock=usage.lock if self._locked_this_boot(usage) else "none",
        )
        self.timekeeper.track(tracked)
        self._audit("session started", "ok", child=username, session=info["id"])

        if tracked.locked:
            # The daemon restarted while this session was locked, and the lock
            # screen may or may not have survived: put it up again.
            reason = tracked.lock
            tracked.lock = "none"
            self._lock(tracked, reason)
        elif self.locker is not None:
            # A lock that never ended, because the daemon was away when its
            # session did, may have left the child's user manager frozen.
            self.locker.thaw_user_manager(tracked)
        self.on_timing_changed()

    def _locked_this_boot(self, usage) -> bool:
        """Whether a child's state says their session is active and locked
        in this boot: the daemon started again under it. A state from
        another boot is a computer turned off, or hung, under a session,
        and the session now appearing is a new sign-in, which the password
        has already let in. A state without a boot, written by a daemon
        that kept none, counts as this boot's."""
        return usage.active and usage.boot in ("", self.timekeeper.boot_id)

    def session_disappeared(self, session_id: str) -> None:
        tracked = self.timekeeper.find(session_id)
        if tracked is None:
            return
        if tracked.locked and self.locker is not None:
            # The session is already gone; only its lock screen is left.
            self.locker.release(tracked)
        self.timekeeper.untrack(tracked.username)
        self._ending.discard(session_id)
        self._audit("session ended", "ok", child=tracked.username, session=session_id)
        if not self.timekeeper.sessions and self.updates is not None:
            # The last child has gone: Debian's daily upgrade, if it was
            # skipped for a child's session, runs now (D115).
            try:
                self.updates.make_up_daily()
            except Exception:
                _log.warning("could not start the daily upgrade", exc_info=True)

    def end_abandoned_locks(self) -> None:
        """End every locked session that has lost its compositor (locker.py,
        `abandoned`): thawed, its scope stopped, and its lock screen taken
        down, as when a session ends by itself."""
        if self.locker is None:
            return
        for tracked in list(self.timekeeper.sessions.values()):
            if (not tracked.locked or tracked.session_id in self._ending
                    or not self.locker.abandoned(tracked)):
                continue
            self._ending.add(tracked.session_id)
            self._audit("abandoned session ended", "ok", child=tracked.username,
                        session=tracked.session_id)
            try:
                self.locker.end_abandoned(tracked)
            except Exception:
                _log.warning("could not end %s's abandoned session", tracked.username,
                             exc_info=True)

    def tick(self) -> float:
        self.end_abandoned_locks()
        return self.timekeeper.tick()

    def attention(self, source: str) -> None:
        """The power button or Ctrl+Alt+Escape (D16), or the lid closing
        (D119)."""
        if source == "lid_closed":
            self.lid_closed()
            return
        for tracked in self.timekeeper.sessions.values():
            if not tracked.locked:
                self._lock(tracked, "power_button")
                return
        self._emit("Daemon1", "AttentionRequested", "(s)", (source,))

    # --- locking ---------------------------------------------------------------

    def _lock(self, tracked: Tracked, reason: str) -> None:
        if tracked.locked:
            return
        if self.locker is None:
            raise Failed("this daemon cannot lock sessions")
        self.timekeeper.pause(tracked)
        if self.locker.lock(tracked, reason):
            tracked.lock = reason
            self.timekeeper.set_session_state(tracked.username, True, reason)
            self._emit("Access1", "Locked", "(ss)", (tracked.username, reason))

    def _unlock(self, tracked: Tracked, grace_seconds: int | None = None) -> None:
        if self.locker is None:
            raise Failed("this daemon cannot unlock sessions")
        self.locker.unlock(tracked)
        tracked.lock = "none"
        tracked.unlocked_at = self._clock.mono()
        if grace_seconds:
            self.timekeeper.start_grace(tracked, grace_seconds)
        else:
            self.timekeeper.resume(tracked)
        self.timekeeper.set_session_state(tracked.username, True, "none")
        self._emit("Access1", "Unlocked", "(s)", (tracked.username,))
        self.on_timing_changed()

    def _locked_session(self, username: str | None = None) -> Tracked:
        for tracked in self.timekeeper.sessions.values():
            if tracked.locked and (username is None or tracked.username == username):
                return tracked
        raise NoSession("there is no locked session")

    def _adult_or_denied(self, caller: Caller, password: str, action: str, **fields) -> bool:
        if self.adults.verify(password):
            return True
        self._audit(action, "denied", caller=self._who(caller), **fields)
        return False

    def _check_minutes(self, minutes: int, most: int) -> int:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= most:
            raise InvalidArgument(f"minutes must be from 1 to {most}")
        return minutes

    # --- Access1 -------------------------------------------------------------

    def Access1_GetPolicy(self, caller: Caller, username: str) -> dict:
        self.gate.require_child(username)
        policy, _, _ = self.timekeeper.load(username)
        return policy.as_document()

    def Access1_SetPolicy(self, caller: Caller, token: str, username: str, changes: dict) -> None:
        self._require_token(caller, token)
        self.gate.require_child(username)
        try:
            wanted = validate_policy(changes)
        except ValueError as error:
            raise InvalidArgument(str(error))
        policy, usage, _ = self.timekeeper.load(username)
        # The bank is not part of a policy: time is given by a grant, which is
        # audited, never by rewriting the bank. Days not sent are kept.
        policy = replace(wanted, granted_seconds=policy.granted_seconds,
                         days=wanted.days if "days" in changes else policy.days)
        self.timekeeper.save(username, policy, usage)
        self._audit("policy set", "ok", caller=self._who(caller), child=username,
                    mode=policy.mode, daily_minutes=policy.daily_minutes,
                    days=days_text(policy.days))
        tracked = self.timekeeper.sessions.get(username)
        if tracked is not None and not tracked.locked:
            tracked.warnings.arm(available(policy, usage, weekday_of(usage)))
            self.on_timing_changed()

    def Access1_CheckAccess(self, caller: Caller, username: str) -> tuple[str, int]:
        self.gate.require_child(username)
        # Installing an update is refused while a child has a session; the
        # other half of that rule is that no session starts while one is
        # being installed, by the panel or by Debian's daily upgrade (D115),
        # or dpkg would replace the launcher under it.
        if self.updates is not None and self.updates.installing():
            return "updating", 0
        policy, usage, _ = self.timekeeper.load(username)
        return check_access(policy, usage, weekday_of(usage))

    def Access1_Usage(self, caller: Caller, username: str) -> tuple[int, int]:
        self.gate.require_self(caller, username)
        self.gate.require_child(username)
        tracked = self.timekeeper.sessions.get(username)
        if tracked is not None:
            # Charge up to this second, so the launcher shows the truth.
            self.timekeeper.charge(tracked)
        policy, usage, _ = self.timekeeper.load(username)
        return usage.seconds_used_today, available(policy, usage, weekday_of(usage))

    def _grant(self, caller: Caller, action: str, adult_password: str, username: str,
               minutes: int) -> bool:
        self.gate.require_child(username)
        self._check_minutes(minutes, 24 * 60)
        if not self._adult_or_denied(caller, adult_password, action, child=username):
            return False
        tracked = self.timekeeper.sessions.get(username)
        if tracked is not None and not tracked.locked:
            self.timekeeper.charge(tracked)
        policy, usage, _ = self.timekeeper.load(username)
        policy = grant(policy, usage, weekday_of(usage), minutes)
        self.timekeeper.save(username, policy, usage)
        self._audit(action, "ok", caller=self._who(caller), child=username, minutes=minutes)
        return True

    def Access1_Grant(self, caller: Caller, token: str, username: str, minutes: int) -> None:
        """Time given from the panel, by an adult who has already unlocked it.

        The same deposit as GrantExtraTime, without typing the password again.
        It unlocks nothing: a locked session is continued from the lock screen.
        """
        self._require_token(caller, token)
        self.gate.require_child(username)
        self._check_minutes(minutes, 24 * 60)
        tracked = self.timekeeper.sessions.get(username)
        if tracked is not None and not tracked.locked:
            # Charged up to now, so the minutes are on top of what is left.
            self.timekeeper.charge(tracked)
        policy, usage, _ = self.timekeeper.load(username)
        self.timekeeper.save(username, grant(policy, usage, weekday_of(usage), minutes), usage)
        self._audit("grant", "ok", caller=self._who(caller), child=username, minutes=minutes,
                    source="panel")
        if tracked is not None and not tracked.locked:
            tracked.warnings.arm(self.timekeeper.left(username))
            self.on_timing_changed()

    def Access1_SetTimeLeft(self, caller: Caller, token: str, username: str,
                            minutes: int) -> None:
        """What a child has left today, set from the panel, zero included
        (D50). A session up is charged first, so the minutes set are what it
        has from now; at zero it locks at the next tick, as when its time runs
        out by itself."""
        self._require_token(caller, token)
        self.gate.require_child(username)
        if isinstance(minutes, bool) or not isinstance(minutes, int) \
                or not 0 <= minutes <= MAX_MINUTES:
            raise InvalidArgument(f"minutes must be from 0 to {MAX_MINUTES}")
        tracked = self.timekeeper.sessions.get(username)
        if tracked is not None and not tracked.locked:
            self.timekeeper.charge(tracked)
        policy, usage, _ = self.timekeeper.load(username)
        try:
            policy = set_left(policy, usage, weekday_of(usage), minutes)
        except ValueError as error:
            raise InvalidArgument(str(error)) from error
        self.timekeeper.save(username, policy, usage)
        self._audit("time set", "ok", caller=self._who(caller), child=username, minutes=minutes)
        if tracked is not None and not tracked.locked:
            tracked.warnings.arm(self.timekeeper.left(username))
            self.on_timing_changed()

    def Access1_AuthoriseSession(self, caller: Caller, adult_password: str, username: str,
                                 minutes: int) -> bool:
        return self._grant(caller, "grant", adult_password, username, minutes)

    def Access1_GrantExtraTime(self, caller: Caller, adult_password: str, username: str,
                               minutes: int) -> bool:
        if not self._grant(caller, "grant", adult_password, username, minutes):
            return False
        tracked = self.timekeeper.sessions.get(username)
        if tracked is None:
            return True
        if tracked.lock == "time_up":
            self._unlock(tracked)
        elif not tracked.locked:
            tracked.warnings.arm(self.timekeeper.left(username))
            self.on_timing_changed()
        return True

    def Access1_Lock(self, caller: Caller) -> None:
        if self.gate.caller_is_child(caller):
            username = self.accounts.username_of(caller.uid)
            tracked = self.timekeeper.sessions.get(username)
        else:
            tracked = next(
                (t for t in self.timekeeper.sessions.values() if not t.locked), None
            )
        if tracked is None or tracked.locked:
            raise NoSession("there is no unlocked session to lock")
        self._lock(tracked, "requested")

    def Access1_LockFor(self, caller: Caller, reason: str) -> None:
        """The child's own session locks itself, for `reason`: left alone
        for the minutes the adult chose, `idle`, or its lid closed, `lid`
        (D67). A lock for idleness within IDLE_LOCK_GRACE_SECONDS of the
        session being given the screen back is refused."""
        if reason not in LOCK_REASONS:
            raise InvalidArgument(f"a session locks itself for {' or '.join(LOCK_REASONS)}")
        username = self.accounts.username_of(caller.uid)
        tracked = self.timekeeper.sessions.get(username)
        if tracked is None or tracked.locked:
            raise NoSession("there is no unlocked session to lock")
        if reason == "idle" and tracked.unlocked_at is not None \
                and self._clock.mono() - tracked.unlocked_at < IDLE_LOCK_GRACE_SECONDS:
            raise NoSession("the session was given the screen back a moment ago")
        self._lock(tracked, reason)

    def Access1_UnlockForSaving(self, caller: Caller, adult_password: str, minutes: int) -> bool:
        self._check_minutes(minutes, MAX_GRACE_MINUTES)
        tracked = self._locked_session()
        if not self._adult_or_denied(caller, adult_password, "unlock to save",
                                     child=tracked.username):
            return False
        self._unlock(tracked, grace_seconds=minutes * 60)
        self._audit("unlock to save", "ok", caller=self._who(caller), child=tracked.username,
                    minutes=minutes)
        return True

    def _who_answered(self, username: str, password: str) -> str | None:
        """'adult' or 'child' for whichever password this is, or None.

        The adult's is checked first, here, so that it never reaches PAM: PAM
        would log it as a failed attempt at the child's account and make the
        adult wait for pam_faildelay before the answer.
        """
        if self.adults.verify(password):
            return "adult"
        if self._check_child_password(username, password):
            return "child"
        return None

    def Access1_ContinueSession(self, caller: Caller, username: str, password: str) -> bool:
        self.gate.require_child(username)
        tracked = self._locked_session(username)
        who = self._who_answered(username, password)
        if who is None:
            self._audit("continue", "denied", child=username)
            return False
        left = self.timekeeper.left(username)
        if left != UNLIMITED and left <= 0:
            self._audit("continue", "no time left", child=username, by=who)
            raise NoTimeLeft(f"{username} has no time left")
        self._unlock(tracked)
        self._audit("continue", "ok", child=username, by=who)
        return True

    def Access1_EndSession(self, caller: Caller, username: str, password: str) -> bool:
        self.gate.require_child(username)
        tracked = self.timekeeper.sessions.get(username)
        if tracked is None:
            raise NoSession(f"{username} is not signed in")
        who = self._who_answered(username, password)
        if who is None:
            self._audit("log out", "denied", child=username)
            return False
        if self.locker is None:
            raise Failed("this daemon cannot end sessions")
        # Closing on purpose: not an abandoned session while logind ends it.
        self._ending.add(tracked.session_id)
        self.locker.end(tracked)
        self._audit("log out", "ok", child=username, by=who)
        return True

    # --- System1 -------------------------------------------------------------

    def System1_Shutdown(self, caller: Caller) -> None:
        self._audit("shutdown", "ok", caller=self._who(caller))
        self.thaw_locked()
        self.logind.power_off()

    def System1_Reboot(self, caller: Caller) -> None:
        self._audit("reboot", "ok", caller=self._who(caller))
        self.thaw_locked()
        self.logind.reboot()

    # --- suspend (power.py, D119) ------------------------------------------------

    def can_sleep(self) -> bool:
        """Whether this computer can suspend, as logind says now."""
        return power.can_sleep(self.logind.can("Suspend"))

    def key_pressed(self) -> None:
        """A key was pressed on a keyboard the daemon reads (attention.py)."""
        self._last_key = self._clock.mono()

    def lid_closed(self) -> None:
        """The lid was seen to close (attention.py): the computer suspends,
        as the adult chose and it can, unless another screen is connected.
        A child's session locks first, and the lid is asked again after:
        opened in the meantime, nothing happens."""
        closed_at = self._clock.mono()
        config = Config.load()
        if power.lid_action(config.lid_action, self.can_sleep()) != "sleep":
            return
        if power.docked(self.connected_screens()):
            _log.info("the lid closed with another screen connected: not suspending")
            return
        for tracked in list(self.timekeeper.sessions.values()):
            if not tracked.locked:
                try:
                    self._lock(tracked, "lid")
                except Failed:
                    _log.exception("could not lock %s for the lid", tracked.username)
        if not self.lid_is_closed():
            _log.info("the lid opened again before suspending: not suspending")
            return
        if self._last_key >= closed_at:
            # Nobody types on a closed laptop: a switch that reads closed
            # while someone does is one that lies, as a MacBook's can after
            # a failed resume, reading closed open and open closed.
            _log.warning("a key was pressed with the lid said to be closed: not suspending")
            return
        _log.info("the lid closed: suspending")
        self._audit("suspend for the lid", "ok")
        self.logind.suspend()

    def System1_SleepWhenIdle(self, caller: Caller) -> str:
        """A screen left alone `idle_sleep_minutes` asks this (kidux-idle):
        the computer suspends, as the adult chose and as it can, unless
        something holds idleness or sleep off, a video, a call,
        `systemd-inhibit --what=idle`. What it did, "sleep", or "" for
        nothing."""
        config = Config.load()
        action = power.idle_action(config.idle_action, self.can_sleep())
        if action != "sleep":
            return ""
        blocked = self.logind.block_inhibited()
        for what in ("idle", "sleep"):
            if power.inhibited(what, blocked):
                _log.info("left alone, but %s is inhibited: not sleeping", what)
                return ""
        self._audit("sleep when idle", "ok", caller=self._who(caller), done=action)
        self.logind.suspend()
        return action

    def going_to_sleep(self) -> None:
        """The computer is about to sleep, whatever asked it to: every
        unlocked child's session locks first, so that a closed lid is never
        a way out of a time limit."""
        for tracked in list(self.timekeeper.sessions.values()):
            if not tracked.locked:
                try:
                    self._lock(tracked, "sleep")
                except Failed:
                    _log.exception("could not lock %s before sleeping", tracked.username)

    def thaw_locked(self) -> None:
        """Thaw every locked session's units, without unlocking, before the
        machine goes down or the daemon stops: systemd refuses to stop a
        frozen unit, and a frozen module could not save. The lock screen
        keeps the display, and a daemon that starts again locks again."""
        if self.locker is None:
            return
        for tracked in self.timekeeper.sessions.values():
            if tracked.locked:
                self.locker.thaw(tracked)

    def stopping(self) -> None:
        """The daemon was asked to stop."""
        self.thaw_locked()

    def _updates(self) -> Updates:
        if self.updates is None:
            raise Failed("this daemon cannot run updates")
        return self.updates

    def System1_CheckUpdates(self, caller: Caller, token: str) -> None:
        """Refresh the package lists and say what would change: UpdatesChecked.
        Allowed while children have sessions, because it changes nothing."""
        self._require_token(caller, token)
        self._updates().start("check")
        self._audit("update check", "started", caller=self._who(caller))
        self.on_update_started()

    def System1_ApplyUpdates(self, caller: Caller, token: str) -> None:
        """Install every update: UpdateProgress, then UpdateFinished.

        Never while a child has a session, locked or not: dpkg must not
        replace the launcher or a module under a session that runs them.
        """
        self._require_token(caller, token)
        if self.timekeeper.sessions:
            raise SessionActive("children are signed in; updates wait until they log out")
        self._updates().start("apply")
        self._audit("update started", "ok", caller=self._who(caller))
        self.on_update_started()

    def System1_UpdateState(self, caller: Caller) -> tuple:
        if self.updates is None:
            return ("idle", 0.0, "", "", "", [])
        return self.updates.state()

    def System1_Versions(self, caller: Caller) -> dict:
        """Every Kidux package installed and its version: kidux-base's is
        Kidux's, the one the sign-in screen and the panel show."""
        if self.kidux_packages is None:
            return {}
        try:
            return catalogue.installed_versions(self.kidux_packages())
        except (OSError, ValueError, subprocess.SubprocessError):
            _log.warning("dpkg-query could not be read", exc_info=True)
            return {}

    # --- Network1 (D62) --------------------------------------------------------

    def _network(self) -> Network:
        if self.network is None:
            raise Failed("this daemon cannot read the network")
        return self.network

    def Network1_GetNetwork(self, caller: Caller, token: str) -> tuple:
        """What the Network page shows: a summary, the interfaces, and the
        Wi-Fi networks in reach when NetworkManager manages a Wi-Fi."""
        self._require_token(caller, token)
        return self._network().read()

    def Network1_Check(self, caller: Caller, token: str) -> None:
        """Look again: a rescan and a ping of the gateway, in a job."""
        self._require_token(caller, token)
        self._network().check()

    def Network1_ConnectWifi(self, caller: Caller, token: str, ssid: str,
                             password: str) -> None:
        """Join a network, in a job; the page asks GetNetwork how it went.
        The password is never audited: only the network's name is."""
        self._require_token(caller, token)
        self._network().connect(ssid, password)
        self._audit("wifi join", "started", caller=self._who(caller), network=ssid)

    def Network1_ForgetWifi(self, caller: Caller, token: str, ssid: str) -> None:
        self._require_token(caller, token)
        self._network().forget(ssid)
        self._audit("wifi forget", "started", caller=self._who(caller), network=ssid)
