"""The sign-in and lock screens as a state machine (docs/dev/greeter.md).

No GTK here. The view reports what was tapped or typed; this decides what
happens and answers with the next `Screen`: its name, the language to draw it
in, and whatever it needs to show. Everything a child can run into is decided
here, so everything a child can run into is tested here, against a fake
daemon and a fake greetd.

The rule the tests hold it to above all: from every screen there is a way
forward. A child is never left looking at something with no button that does
anything.
"""

from kidux import idle as kidux_idle
from kidux import vocabulary

from .daemon import DaemonError, DaemonUnavailableError, NoTimeLeft
from .greetd import GreetdError
from .panel import Panel, Wizard
from .screen import GRANT_CHOICES, Screen

__all__ = ["GRANT_CHOICES", "Lock", "SAVE_MINUTES", "Screen", "SignIn"]

SESSION_COMMAND = ["/usr/libexec/kidux-session"]

#: How long an adult may unlock a session so the child can save, in minutes.
SAVE_MINUTES = 5


def kidux_version(daemon) -> str:
    """Kidux's version, as dpkg has kidux-base; "" when the daemon cannot
    say, which never stops a screen."""
    try:
        return daemon.versions().get("kidux-base", "")
    except (DaemonUnavailableError, DaemonError):
        return ""


class SignIn:
    """The sign-in screen: greetd's greeter on terminal 7."""

    def __init__(self, daemon, greetd) -> None:
        self._daemon = daemon
        self._greetd = greetd
        self._config: dict = {}
        self._children: list[dict] = []
        self._child: dict | None = None
        self._authenticated = False
        #: The first-run wizard and the adult panel, while they are open.
        self.wizard: Wizard | None = None
        self.panel: Panel | None = None
        #: Set once greetd has been asked to start a session: the greeter's
        #: work is done and it must exit for greetd to start it.
        self.session_started = False
        #: Kidux's version, kidux-base's, which the screen says under the
        #: children; "" when the daemon cannot say.
        self.kidux_version = ""

    # --- helpers -------------------------------------------------------------

    @property
    def default_language(self) -> str:
        return self._config.get("default_language", "en_US.UTF-8")

    def _language(self) -> str:
        if self._child and self._child.get("language"):
            return self._child["language"]
        return self.default_language

    def _screen(self, name: str, notice: str | None = None, **data) -> Screen:
        if self._child is not None:
            data.setdefault("child", self._child)
        return Screen(name, self._language(), data, notice)

    def _forget_child(self) -> None:
        if self._authenticated or self._child is not None:
            self._greetd.cancel()
        self._child = None
        self._authenticated = False

    def _waiting(self) -> Screen:
        self._forget_child()
        return Screen("waiting", self.default_language, notice=vocabulary.CANNOT_REACH_DAEMON)

    # --- starting --------------------------------------------------------------

    def start(self) -> Screen:
        """The first screen, and the one every "try again" comes back to."""
        try:
            self._config = self._daemon.config()
            password_set = self._daemon.password_is_set()
            self._children = self._daemon.children()
        except (DaemonUnavailableError, DaemonError):
            return self._waiting()
        self.kidux_version = kidux_version(self._daemon)
        # A machine never set up, or set up only as far as the adult password,
        # goes to the wizard. One with children goes to them, set up or not:
        # it was set up some other way, and is usable.
        if not password_set or (not self._config.get("setup_complete") and not self._children):
            self.wizard = Wizard(self._daemon, on_done=self.start)
            return self.wizard.start(self._config, password_set)
        self.wizard = None
        return self.choose()

    @property
    def exit_requested(self) -> bool:
        """The screen must restart: a session was started, or a new keyboard set."""
        return self.session_started or any(
            part is not None and part.exit_requested for part in (self.wizard, self.panel))

    def choose(self) -> Screen:
        self._forget_child()
        self.panel = None
        return Screen("choose", self.default_language, {"children": list(self._children),
                                                         "kidux_version": self.kidux_version})

    def children_changed(self, showing: str) -> Screen | None:
        """The daemon says the children changed.

        The list is refreshed for the next time it is shown, and redrawn now
        only if it is what is on the screen: a child half-way through signing
        in, or an adult in the panel, is never pulled away from it.
        """
        try:
            self._children = self._daemon.children()
        except (DaemonUnavailableError, DaemonError):
            return None
        return self.choose() if showing == "choose" else None

    # --- a child -----------------------------------------------------------------

    def tap_child(self, username: str) -> Screen:
        child = next((c for c in self._children if c.get("username") == username), None)
        if child is None:
            return self.choose()
        self._forget_child()
        self._child = child
        return self._screen("password")

    def submit_password(self, password: str) -> Screen:
        if self._child is None:
            return self.choose()
        if not password:
            return self._screen("password")
        try:
            outcome = self._greetd.authenticate(self._child["username"], password)
        except GreetdError:
            return self._screen("password", notice=vocabulary.CANNOT_REACH_DAEMON)
        if not outcome.authenticated:
            return self._screen("password", notice=vocabulary.WRONG_PASSWORD)
        self._authenticated = True
        return self._after_authentication()

    def _after_authentication(self) -> Screen:
        """The password was right. Now, and only now, may this child play?"""
        try:
            state, _seconds = self._daemon.check_access(self._child["username"])
        except (DaemonUnavailableError, DaemonError):
            return self._waiting()
        if state == "allowed":
            return self._start_session()
        if state == "needs_adult":
            return self._screen("needs_adult", notice=vocabulary.ASK_AN_ADULT,
                                choices=GRANT_CHOICES, **self._time_left())
        if state == "updating":
            # An update is being installed: the waiting screen tries again by
            # itself, and the session greetd began is let go.
            self._forget_child()
            return Screen("waiting", self.default_language, notice=vocabulary.UPDATING)
        if state == "day_off":
            # A day of the week not ticked for this child (D54): the same
            # screen as a spent day, which leads to an adult's grant.
            return self._screen("blocked", notice=vocabulary.NOT_TODAY)
        return self._screen("blocked", notice=vocabulary.TIME_SPENT_TODAY)

    def _start_session(self) -> Screen:
        # The machine's settings as they are now, not as they were when this
        # screen started: an adult may have changed the minutes since (D67).
        try:
            self._config = self._daemon.config()
        except (DaemonUnavailableError, DaemonError):
            pass
        environment = {
            # kidux-session turns this into LANG and LC_ALL (docs/dev/session.md, section 3).
            "KIDUX_LANGUAGE": self._language(),
            "KIDUX_DISPLAY_SCALE": str(self._config.get("display_scale", 0.0)),
            # The launcher shows it; the child's session cannot read profiles.
            "KIDUX_AVATAR": self._child.get("avatar") or "",
            # A session left alone locks, and its screen turns off (D67).
            "KIDUX_IDLE_LOCK_SECONDS": str(int(self._config.get("idle_lock_minutes", 5)) * 60),
            "KIDUX_SCREEN_OFF_SECONDS": str(int(self._config.get("screen_off_minutes", 10)) * 60),
            # Still left alone, the computer sleeps, as the adult chose (D119).
            "KIDUX_IDLE_SLEEP_SECONDS": str(kidux_idle.sleep_seconds(self._config)),
        }
        keyboard = self._child.get("keyboard") or self._config.get("default_keyboard")
        if keyboard:
            environment["XKB_DEFAULT_LAYOUT"] = keyboard
        if self._child.get("windows"):
            # The launcher opens this child's modules in windows (D46).
            environment["KIDUX_WINDOWS"] = "1"
        try:
            self._greetd.start(SESSION_COMMAND, environment)
        except GreetdError:
            self._authenticated = False
            return self._screen("password", notice=vocabulary.CANNOT_REACH_DAEMON)
        self.session_started = True
        return self._screen("starting")

    def ask_adult(self) -> Screen:
        """From "your time is used up": an adult can give more."""
        if self._child is None:
            return self.choose()
        return self._screen("needs_adult", choices=GRANT_CHOICES, **self._time_left())

    def _time_left(self) -> dict:
        """How much time the child has left, for the adult about to give more."""
        try:
            _used, left = self._daemon.usage(self._child["username"])
        except (DaemonUnavailableError, DaemonError):
            return {}
        return {"left": left}

    def adult_grants(self, adult_password: str, minutes: int) -> Screen:
        if self._child is None or not self._authenticated:
            return self.choose()
        try:
            granted = self._daemon.authorise_session(adult_password, self._child["username"], minutes)
        except (DaemonUnavailableError, DaemonError):
            return self._waiting()
        if not granted:
            return self._screen("needs_adult", notice=vocabulary.WRONG_PASSWORD,
                                choices=GRANT_CHOICES)
        return self._after_authentication()

    def back(self) -> Screen:
        return self.choose()

    def idle(self) -> Screen:
        """A minute without a touch on a child's screen: back to everyone."""
        return self.choose()

    # --- the adult and the power ---------------------------------------------

    def tap_adult(self) -> Screen:
        self._forget_child()
        return Screen("adult", self.default_language)

    def submit_adult_password(self, password: str) -> Screen:
        try:
            token = self._daemon.unlock_panel(password)
        except (DaemonUnavailableError, DaemonError):
            return self._waiting()
        if not token:
            return Screen("adult", self.default_language, notice=vocabulary.WRONG_PASSWORD)
        self.panel = Panel(self._daemon, token, self._config, on_close=self.start,
                           lock_mode=False)
        return self.panel.children()

    def tap_power(self) -> Screen:
        self._forget_child()
        return Screen("power", self.default_language)

    def attention(self) -> Screen:
        """The power button, pressed with nobody signed in (D16)."""
        return self.tap_power()

    def power(self, choice: str) -> Screen:
        try:
            if choice == "off":
                self._daemon.shutdown()
            elif choice == "restart":
                self._daemon.reboot()
            else:
                return self.choose()
        except (DaemonUnavailableError, DaemonError):
            return self._waiting()
        return Screen("turning_off", self.default_language)


class Lock:
    """The lock screen: `kidux-greeter --lock <child>` on terminal 8."""

    def __init__(self, daemon, username: str) -> None:
        self._daemon = daemon
        self._username = username
        self._child: dict = {"username": username}
        self._language = "en_US.UTF-8"
        #: What the child's password is being asked for: "continue" or "log_out".
        self._purpose = "continue"
        self._adult_password = ""
        #: How long *Unlock to save* gives, the machine's setting.
        self._save_minutes = SAVE_MINUTES
        #: The adult panel, while it is open over this lock screen.
        self.panel: Panel | None = None
        self.exit_requested = False
        self.kidux_version = ""

    def _screen(self, name: str, notice: str | None = None, **data) -> Screen:
        data.setdefault("child", self._child)
        data.setdefault("kidux_version", self.kidux_version)
        #: What the child's password will do, so its button can say so.
        data.setdefault("purpose", self._purpose)
        return Screen(name, self._language, data, notice)

    def start(self) -> Screen:
        self.panel = None
        try:
            config = self._daemon.config()
            self._language = config.get("default_language", self._language)
            self._save_minutes = int(config.get("save_minutes", SAVE_MINUTES))
            for child in self._daemon.children():
                if child.get("username") == self._username:
                    self._child = child
                    self._language = child.get("language") or self._language
            _used, left = self._daemon.usage(self._username)
        except (DaemonUnavailableError, DaemonError):
            return self._screen("locked", notice=vocabulary.CANNOT_REACH_DAEMON, time_up=False)
        self.kidux_version = kidux_version(self._daemon)
        time_up = left == 0
        return self._screen("locked", notice=vocabulary.TIME_IS_UP if time_up else None,
                            time_up=time_up)

    # --- the child ---------------------------------------------------------------

    def tap_continue(self) -> Screen:
        self._purpose = "continue"
        return self._screen("child_password")

    def tap_log_out(self) -> Screen:
        self._purpose = "log_out"
        return self._screen("child_password")

    def submit_child_password(self, password: str) -> Screen:
        try:
            if self._purpose == "log_out":
                ok = self._daemon.end_session(self._username, password)
                return self._screen("ending") if ok else self._screen(
                    "child_password", notice=vocabulary.WRONG_PASSWORD)
            ok = self._daemon.continue_session(self._username, password)
        except NoTimeLeft:
            return self._screen("locked", notice=vocabulary.TIME_SPENT_TODAY, time_up=True)
        except (DaemonUnavailableError, DaemonError):
            return self._screen("locked", notice=vocabulary.CANNOT_REACH_DAEMON, time_up=False)
        if not ok:
            return self._screen("child_password", notice=vocabulary.WRONG_PASSWORD)
        return self._screen("unlocking")

    # --- the adult ---------------------------------------------------------------

    def tap_adult(self) -> Screen:
        return self._screen("adult_password")

    def submit_adult_password(self, password: str) -> Screen:
        """The password is checked by whichever action the adult then picks."""
        if not password:
            return self._screen("adult_password")
        self._adult_password = password
        return self._screen("adult_choice", choices=GRANT_CHOICES, save_minutes=self._save_minutes,
                            **self._time_left())

    def _time_left(self) -> dict:
        """How much time the child has left, for the adult about to give more."""
        try:
            _used, left = self._daemon.usage(self._username)
        except (DaemonUnavailableError, DaemonError):
            return {}
        return {"left": left}

    def adult_choice(self, choice: str, minutes: int = 0) -> Screen:
        password, self._adult_password = self._adult_password, ""
        try:
            if choice == "grant":
                ok = self._daemon.grant_extra_time(password, self._username, minutes)
                if ok:
                    self._resume(password)
            elif choice == "save":
                ok = self._daemon.unlock_for_saving(password, self._save_minutes)
            elif choice == "log_out":
                ok = self._daemon.end_session(self._username, password)
            elif choice == "panel":
                return self._open_panel(password)
            else:
                return self.back()
        except (DaemonUnavailableError, DaemonError):
            return self._screen("locked", notice=vocabulary.CANNOT_REACH_DAEMON, time_up=False)
        if not ok:
            return self._screen("adult_password", notice=vocabulary.WRONG_PASSWORD)
        return self._screen("ending" if choice == "log_out" else "unlocking")

    def _open_panel(self, adult_password: str) -> Screen:
        token = self._daemon.unlock_panel(adult_password)
        if not token:
            return self._screen("adult_password", notice=vocabulary.WRONG_PASSWORD)
        self.panel = Panel(self._daemon, token, self._daemon.config(), on_close=self.start,
                           lock_mode=True)
        return self.panel.children()

    def _resume(self, adult_password: str) -> None:
        """Unlock after the adult gave time.

        The daemon's grant unlocks by itself only a session locked because
        its time ran out. Locked by the power button or the Lock button, the
        session would stay locked with more time on it; the adult who gave
        time means "carry on", so the lock screen continues it with the
        adult's password, which ContinueSession accepts.
        """
        try:
            self._daemon.continue_session(self._username, adult_password)
        except DaemonUnavailableError:
            raise
        except (DaemonError, NoTimeLeft):
            pass  # already unlocked by the grant

    # --- anyone ------------------------------------------------------------------

    def back(self) -> Screen:
        self._adult_password = ""
        return self.start()

    def tap_power(self) -> Screen:
        return self._screen("power")

    def power(self, choice: str) -> Screen:
        try:
            if choice == "off":
                self._daemon.shutdown()
                return self._screen("turning_off")
        except (DaemonUnavailableError, DaemonError):
            pass
        return self.back()


#: What each screen offers, by the method that answers it. The view draws
#: exactly these, and the tests check that every screen that can be reached
#: offers at least one, unless the program is about to end on purpose.
SIGN_IN_ACTIONS: dict[str, tuple[str, ...]] = {
    "waiting": ("start", "tap_power"),
    "choose": ("tap_child", "tap_adult", "tap_power"),
    "password": ("submit_password", "back"),
    "needs_adult": ("adult_grants", "back"),
    "blocked": ("ask_adult", "back"),
    "adult": ("submit_adult_password", "back"),
    "power": ("power",),
    "starting": (),
    "turning_off": (),
}

LOCK_ACTIONS: dict[str, tuple[str, ...]] = {
    "locked": ("tap_continue", "tap_adult", "tap_log_out", "tap_power"),
    "child_password": ("submit_child_password", "back"),
    "adult_password": ("submit_adult_password", "back"),
    "adult_choice": ("adult_choice", "back"),
    "power": ("power",),
    "unlocking": (),
    "ending": (),
    "turning_off": (),
}

#: Screens after which the program ends: greetd starts the session once the
#: greeter exits, the daemon stops the lock screen's unit, the machine powers
#: off, or the greeter restarts to take a new keyboard layout.
FINAL = frozenset({"starting", "turning_off", "unlocking", "ending", "restarting"})
