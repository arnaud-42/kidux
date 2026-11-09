"""The first-run wizard and the adult panel, as state machines (docs/dev/panel.md).

No GTK here, exactly like `flow.py`: the view reports what was tapped or
typed, and these answer with the next `Screen`. Every Screen they answer
carries `owner` "wizard" or "panel", which is how the view knows whom to
ask next; handing back to the sign-in or lock screen is answering with one
of theirs.

The panel is a set of forms (D37): each page shows everything it is about at
once, and the view sends back every field of a form together. The wizard
keeps its steps only for what needs the screen restarted between them, and
adds the first child with the same form as the panel.

Both hold the adult's token only for as long as they are open, and lock it
when they close (D6, D26). The daemon checks everything again, so nothing
here is a security boundary; it is what makes the screens say the right
thing.
"""

import pwd
import re
import unicodedata

from kidux import screen as kidux_screen
from kidux import avatars, paths, vocabulary
from kidux import modules as kidux_modules

from . import words
from .daemon import (
    Busy,
    DaemonError,
    DaemonUnavailableError,
    Invalid,
    NotUnlocked,
    SessionActive,
)
from .screen import GRANT_CHOICES, Screen

#: Each language's name in its own language, so an adult who reads only one
#: of them finds it. Never translated.
LANGUAGE_NAMES = {"es": "Español", "en": "English", "fr": "Français"}

#: The layouts offered for each language, first the most likely, by the name
#: an adult knows them by. The daemon accepts any layout name.
KEYBOARDS = {
    "es": (("es", words.KEYBOARD_ES), ("latam", words.KEYBOARD_LATAM)),
    "en": (("us", words.KEYBOARD_US), ("gb", words.KEYBOARD_GB)),
    "fr": (("fr", words.KEYBOARD_FR), ("be", words.KEYBOARD_BE), ("ca", words.KEYBOARD_CA)),
}

#: The parts of Kidux the System page lists under Kidux's version, each by
#: its package, in this order.
PARTS = (("kidux-daemon", words.PART_SERVICE), ("kidux-session", words.PART_SESSION),
         ("kidux-launcher", words.PART_CHILD_SCREEN),
         ("kidux-greeter", words.PART_SIGN_IN_SCREEN), ("python3-kidux", words.PART_COMMON),
         ("kidux-webapps", words.PART_WEB_MODULES))

#: A daily limit, in minutes, is at most a day.
MAX_DAILY_MINUTES = 24 * 60


def wifi_password_fits(password: str) -> bool:
    """What a WPA personal network can take, as the daemon checks it too:
    8 to 63 bytes, so that a letter with an accent counts as two, or the
    key's own 64 hex digits."""
    return 8 <= len(password.encode()) <= 63 or bool(re.fullmatch(r"[0-9a-fA-F]{64}", password))
#: The display scales an adult chooses from; 0 is automatic (kidux.screen, D49).
SCALES = (0.0, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)
#: A session left alone locks after these minutes, and the screen turns off
#: after the second, until an adult chooses others (D67); the daemon's
#: defaults, and the ranges it accepts.
IDLE_LOCK_MINUTES, SCREEN_OFF_MINUTES = 5, 10
IDLE_LOCK_RANGE, SCREEN_OFF_RANGE = (1, 120), (1, 240)
#: The Suspending the computer page's choices, as the daemon names them
#: (D119), and the minutes a computer may be idle before it suspends.
LID_ACTIONS = ("sleep", "nothing")
IDLE_ACTIONS = ("sleep", "screen_off_only")
IDLE_SLEEP_MINUTES, IDLE_SLEEP_RANGE = 20, (1, 240)
MODES = ("unlimited", "daily", "manual")


def is_test_module(name: str) -> bool:
    """A module that is there to test Kidux, not for a child: its name
    begins with a tag in brackets, `[Test]` or `[Prueba]` (D70)."""
    return name.lstrip().startswith("[")


def ordered(entries: list[dict]) -> list[dict]:
    """The modules as the page lists them (D73): by the ages they are for,
    the youngest first and, at the same age, the one that ends sooner; a
    module that says no age among the first; by name after that; and the
    test modules last, whatever their ages."""
    return sorted(entries, key=lambda e: (is_test_module(e.get("name", "")),
                                         int(e.get("min_age") or 0), int(e.get("max_age") or 0),
                                         e.get("name", "").lower()))


def shown_version(version: str) -> str:
    """A package's version as the adult reads it (D73): without what follows
    a `+`, which says how the program was built, not which program it is;
    and a program with no version of its own, `0+git<date>`, by the date of
    the snapshot, `2024-05-13`."""
    own, _plus, build = version.partition("+")
    if own == "0" and re.fullmatch(r"git\d{8}.*", build):
        return f"{build[3:7]}-{build[7:9]}-{build[9:11]}"
    return own

#: Every day of the week, as the access field writes the days: seven digits,
#: Monday first, 1 for a day ticked (D54).
EVERY_DAY = "1111111"

#: What a new child's form starts at: an hour a day, every day, the choice
#: most families make first. The daemon's own default is stricter (manual,
#: empty); the form always sends what it shows.
NEW_ACCESS = ("daily", 60, EVERY_DAY)


def shipped_languages() -> list[str]:
    """The locales kidux-base generates, the languages a child or the machine may have."""
    try:
        lines = (paths.DATA_ROOT / "locales").read_text().splitlines()
    except OSError:
        return ["en_US.UTF-8"]
    found = [line.split()[0] for line in lines if line.strip() and not line.startswith("#")]
    return found or ["en_US.UTF-8"]


def language_name(locale: str) -> str:
    return LANGUAGE_NAMES.get(locale.split("_")[0], locale)


def keyboards_for(locale: str) -> tuple:
    return KEYBOARDS.get(locale.split("_")[0], (("us", words.KEYBOARD_US),))


def languages() -> list[tuple[str, str]]:
    return [(locale, language_name(locale)) for locale in shipped_languages()]


def size_label(scale: float, mark: str) -> str:
    """A display scale as the System page lists it: "200 %", or "175 %*"
    with the mark for one that is not a whole multiple of 100 % (D59)."""
    percent = round(scale * 100)
    return f"{percent} %" + ("" if percent % 100 == 0 else mark)


def access_of(policy: dict) -> tuple[str, int, str]:
    """A child's policy as the form's access field: mode, the minutes a day
    in daily mode (0 otherwise) and the days as seven digits."""
    mode = policy.get("mode", "manual")
    minutes = int(policy.get("daily_minutes", 60)) if mode == "daily" else 0
    days = policy.get("days")
    digits = "".join("1" if day else "0" for day in days) \
        if isinstance(days, (list, tuple)) and len(days) == 7 else EVERY_DAY
    return (mode, minutes, digits)


def parse_access(value) -> tuple[str, int, str]:
    """'daily:60:1111100' or ('daily', 60, '1111100') → ('daily', 60,
    '1111100'); days left out are every day; anything else → NEW_ACCESS."""
    if isinstance(value, str):
        value = tuple(value.split(":"))
    if not isinstance(value, (tuple, list)) or len(value) not in (2, 3):
        return NEW_ACCESS
    mode, minutes, days = (*value, EVERY_DAY) if len(value) == 2 else value
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return NEW_ACCESS
    if mode not in MODES or not isinstance(days, str) or len(days) != 7 \
            or set(days) - {"0", "1"}:
        return NEW_ACCESS
    if mode != "daily":
        return (mode, 0, days)
    return (mode, min(MAX_DAILY_MINUTES, max(1, minutes)), days)


def day_list(days: str) -> list[bool]:
    """Seven digits as the daemon takes the days: seven true or false."""
    return [digit == "1" for digit in days]


def username_for(display_name: str, taken=None) -> str:
    """The Unix name for a child called `display_name`, never seen by anyone.

    Lower-case ASCII letters and digits from the name, accents dropped,
    starting with a letter, and made unique on this machine by a number.
    """
    exists = taken if taken is not None else _account_exists
    plain = unicodedata.normalize("NFKD", display_name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]", "", plain.lower())[:24]
    if not base or not base[0].isalpha():
        base = "child" + base
    name, number = base, 2
    while exists(name) or name in ("root", "kidux", paths.GREETER_USER):
        name, number = f"{base}{number}", number + 1
    return name


def _account_exists(name: str) -> bool:
    try:
        pwd.getpwnam(name)
    except KeyError:
        return False
    return True


def _without_passwords(fields: dict) -> dict:
    """What a form keeps of what was typed when it is drawn again: never a password."""
    return {k: v for k, v in fields.items() if k not in ("password", "again")}


class _NewChild:
    """Creating a child from the form: shared by the wizard and the panel.

    The class using it provides `_daemon`, `_token`, `_language` and
    `_keyboard`, the machine's.
    """

    def _form_data(self, *, errors=None, draft=None) -> dict:
        return {
            "avatars": avatars.available(),
            "languages": languages(),
            "modes": MODES,
            "errors": dict(errors or {}),
            "draft": dict(draft or {}),
            "defaults": {"language": self._language, "access": NEW_ACCESS,
                         "avatar": (avatars.available() or [""])[0]},
        }

    def _create(self, fields: dict) -> tuple[str | None, dict]:
        """Create the child the form describes. Returns (username, errors)."""
        errors = {}
        name = (fields.get("display_name") or "").strip()
        if not name:
            errors["display_name"] = words.NAME_NEEDED
        password, again = fields.get("password") or "", fields.get("again") or ""
        if not password:
            errors["password"] = words.PASSWORD_NEEDED
        elif password != again:
            errors["password"] = words.PASSWORDS_DIFFER
        if errors:
            return None, errors

        available = avatars.available()
        avatar = fields.get("avatar") or (available[0] if available else "")
        language = fields.get("language") or self._language
        keyboard = self._keyboard if language == self._language else keyboards_for(language)[0][0]
        mode, minutes, days = parse_access(fields.get("access"))
        username = username_for(name)
        try:
            self._daemon.create_child(self._token, username, name, language, keyboard,
                                      avatar, password)
        except Invalid:
            return None, {"display_name": words.NOT_SAVED}
        try:
            self._daemon.set_policy(self._token, username, mode, minutes or 60, day_list(days))
        except Invalid:
            return username, {"access": words.NOT_SAVED}
        if fields.get("windows"):
            try:
                self._daemon.set_profile(self._token, username, {"windows": True})
            except Invalid:
                return username, {"windows": words.NOT_SAVED}
        return username, {}


class Wizard(_NewChild):
    """The first start of a machine (panel.md section 2)."""

    def __init__(self, daemon, *, on_done) -> None:
        self._daemon = daemon
        self._on_done = on_done
        self._token = ""
        self._language = "en_US.UTF-8"
        self._keyboard = "us"
        #: Set when the screen must restart for a new keyboard layout to
        #: apply: cage takes the layout when it starts, and at no other time.
        self.exit_requested = False

    def _screen(self, name: str, notice: str | None = None, **data) -> Screen:
        return Screen(name, self._language, data, notice, owner="wizard")

    def start(self, config: dict, password_set: bool) -> Screen:
        """Where to begin, from what the daemon says is already done."""
        self._language = config.get("default_language", self._language)
        self._keyboard = config.get("default_keyboard", self._keyboard)
        if password_set:
            return self._screen("wiz_unlock")
        if config.get("language_chosen"):
            return self._screen("wiz_password")
        return self._screen("wiz_language", languages=languages())

    def choose_language(self, locale: str) -> Screen:
        self._language = locale
        return self._screen("wiz_keyboard", keyboards=keyboards_for(locale))

    def choose_keyboard(self, layout: str) -> Screen:
        try:
            self._daemon.set_config("", {"default_language": self._language,
                                         "default_keyboard": layout})
        except (DaemonUnavailableError, DaemonError):
            return self._screen("wiz_keyboard", notice=words.SOMETHING_WENT_WRONG,
                                keyboards=keyboards_for(self._language))
        self._keyboard = layout
        self.exit_requested = True
        return self._screen("restarting")

    def submit_adult_password(self, password: str, again: str) -> Screen:
        if not password:
            return self._screen("wiz_password", notice=words.PASSWORD_NEEDED)
        if password != again:
            return self._screen("wiz_password", notice=words.PASSWORDS_DIFFER)
        try:
            self._daemon.set_adult_password("", password)
            self._token = self._daemon.unlock_panel(password) or ""
        except (DaemonUnavailableError, DaemonError):
            return self._screen("wiz_password", notice=words.SOMETHING_WENT_WRONG)
        return self._screen("wiz_statistics", shared=True)

    def set_statistics(self, enabled: bool) -> Screen:
        """Whether every fetch of the archive carries an identifier of this
        machine's (D109): on unless the adult turns it off here."""
        try:
            self._daemon.set_config(self._token, {"apt_statistics": bool(enabled)})
        except (DaemonUnavailableError, DaemonError):
            return self._screen("wiz_statistics", notice=words.SOMETHING_WENT_WRONG,
                                shared=bool(enabled))
        return self._child_form()

    def submit_unlock(self, password: str) -> Screen:
        self._token = self._daemon.unlock_panel(password) or ""
        if not self._token:
            return self._screen("wiz_unlock", notice=vocabulary.WRONG_PASSWORD)
        return self._child_form()

    def _child_form(self, notice=None, errors=None, draft=None) -> Screen:
        return self._screen("wiz_child", notice, **self._form_data(errors=errors, draft=draft))

    def add_child(self, fields: dict) -> Screen:
        """The first child, from the same form the panel uses."""
        try:
            username, errors = self._create(fields)
        except NotUnlocked:
            return self._screen("wiz_unlock", notice=words.PANEL_CLOSED)
        if username is None:
            return self._child_form(notice=words.SOME_NOT_SAVED, errors=errors,
                                    draft=_without_passwords(fields))
        try:
            self._daemon.set_config(self._token, {"setup_complete": True})
        finally:
            self._daemon.lock_panel(self._token)
            self._token = ""
        return self._screen("wiz_done")

    def back(self, screen: str = "") -> Screen:
        """Back from the keyboard to the languages; the first child has no step
        before it once the password is set."""
        if screen == "wiz_child":
            return self._child_form()
        return self.start({"default_language": self._language,
                           "default_keyboard": self._keyboard}, False)

    def finish(self) -> Screen:
        return self._on_done()


class Panel(_NewChild):
    """The adult panel (panel.md section 3). Open while it holds a token."""

    def __init__(self, daemon, token: str, config: dict, *, on_close, lock_mode: bool) -> None:
        self._daemon = daemon
        self._token = token
        self._config = dict(config)
        self._language = config.get("default_language", "en_US.UTF-8")
        self._keyboard = config.get("default_keyboard", "us")
        self._on_close = on_close
        self._lock_mode = lock_mode
        #: The child whose form is shown; None is the form for a new one.
        self._selected: str | None = None
        self._first_open = True
        #: The recovery password, once the adult has asked to see it, so that
        #: the system page redrawn while an update runs keeps showing it.
        self._recovery: str | None = None
        #: What the archive offers, as the Modules page last asked it.
        self._offered: list | None = None
        #: The module being removed, and its row as last shown, which stays
        #: on the page with how far its removal has got once its manifest
        #: is gone.
        self._removing: str | None = None
        self._removing_row: dict | None = None
        #: The installed modules' rows as last drawn.
        self._rows_shown: list = []
        #: Installs and removals asked for while a job runs, in order, as
        #: ("install" | "remove" | "look", module id): each starts when the
        #: one before ends (`poll_modules`).
        self._queue: list[tuple[str, str | None]] = []
        #: The module whose removal the page is asking about, kept through
        #: the polls while a job runs.
        self._confirming: str | None = None
        #: The module the adult asked to install, whose row shows how far it
        #: has got while the job runs.
        self._installing: str | None = None
        self.exit_requested = False
        #: A setting the screen takes only when it starts, the size, the
        #: language or the keyboard, changed from the sign-in screen: closing
        #: the panel restarts the screen, so that the adult sees it applied.
        self._restart_on_close = False

    def _screen(self, name: str, notice: str | None = None, **data) -> Screen:
        # Every page says how long the panel may be left alone: the minutes
        # a child's session may be, which the adult sets (D67).
        data.setdefault("idle_seconds", self._idle_lock_minutes() * 60)
        return Screen(name, self._language, data, notice, owner="panel")

    def _idle_lock_minutes(self) -> int:
        return int(self._config.get("idle_lock_minutes", IDLE_LOCK_MINUTES))

    def _screen_off_minutes(self) -> int:
        return int(self._config.get("screen_off_minutes", SCREEN_OFF_MINUTES))

    def _guard(self, action):
        """Run a daemon call; a lost token closes the panel instead of failing."""
        try:
            return action()
        except NotUnlocked:
            return self.close(notice=words.PANEL_CLOSED)

    # --- the children --------------------------------------------------------

    def children(self, notice: str | None = None, *, errors=None, draft=None,
                 confirm_remove: bool = False) -> Screen:
        kids = self._daemon.children()
        names = [c["username"] for c in kids]
        if self._first_open:
            self._first_open = False
            self._selected = names[0] if names else None
        elif self._selected is not None and self._selected not in names:
            self._selected = names[0] if names else None
        data = {"children": kids, "selected": self._selected, "grant": GRANT_CHOICES,
                **self._form_data(errors=errors, draft=draft)}
        if self._selected is not None:
            child = next(c for c in kids if c["username"] == self._selected)
            policy = self._daemon.policy(self._selected)
            used, left = self._daemon.usage(self._selected)
            current = access_of(policy)
            data.update(child=child, policy=policy, used=used, left=left,
                        current={"display_name": child.get("display_name", ""),
                                 "avatar": avatars.resolve(child.get("avatar"))
                                 if avatars.available() else child.get("avatar", ""),
                                 "language": child.get("language") or self._language,
                                 "access": current,
                                 "windows": bool(child.get("windows"))},
                        confirm_remove=confirm_remove)
        return self._screen("panel_children", notice, **data)

    def select(self, username: str) -> Screen:
        self._selected = username
        return self.children()

    def new_child(self) -> Screen:
        self._selected = None
        return self.children()

    def save_child(self, fields: dict) -> Screen:
        """Every field of the form that changed, one call each; a field the
        daemon refuses is marked, the rest are kept."""
        username = self._selected
        if username is None:
            return self.add_child(fields)
        return self._guard(lambda: self._save(username, fields))

    def _save(self, username: str, fields: dict) -> Screen:
        child = next((c for c in self._daemon.children() if c["username"] == username), None)
        if child is None:
            return self.children()
        errors, changed = {}, False

        def attempt(field, action):
            nonlocal changed
            try:
                action()
                changed = True
            except Invalid:
                errors[field] = words.NOT_SAVED

        name = (fields.get("display_name") or "").strip()
        if "display_name" in fields and name != child.get("display_name"):
            if not name:
                errors["display_name"] = words.NAME_NEEDED
            else:
                attempt("display_name",
                        lambda: self._daemon.set_profile(self._token, username, {"display_name": name}))
        avatar = fields.get("avatar")
        if avatar and avatar != child.get("avatar"):
            attempt("avatar", lambda: self._daemon.set_profile(self._token, username, {"avatar": avatar}))
        language = fields.get("language")
        if language and language != child.get("language"):
            # A child's keyboard follows their language inside their session;
            # passwords are always typed in the machine's layout (D29).
            layout = keyboards_for(language)[0][0]
            attempt("language", lambda: self._daemon.set_profile(
                self._token, username, {"language": language, "keyboard": layout}))
        password, again = fields.get("password") or "", fields.get("again") or ""
        if password or again:
            if not password:
                errors["password"] = words.PASSWORD_NEEDED
            elif password != again:
                errors["password"] = words.PASSWORDS_DIFFER
            else:
                attempt("password",
                        lambda: self._daemon.set_child_password(self._token, username, password))
        if "windows" in fields and bool(fields["windows"]) != bool(child.get("windows")):
            attempt("windows", lambda: self._daemon.set_profile(
                self._token, username, {"windows": bool(fields["windows"])}))
        if "access" in fields:
            policy = self._daemon.policy(username)
            wanted = parse_access(fields["access"])
            if wanted != access_of(policy):
                mode, minutes, days = wanted
                attempt("access", lambda: self._daemon.set_policy(
                    self._token, username, mode, minutes or int(policy.get("daily_minutes", 60)),
                    day_list(days)))

        if errors:
            return self.children(words.SOME_NOT_SAVED, errors=errors,
                                 draft=_without_passwords(fields))
        return self.children(words.SAVED if changed else None)

    def add_child(self, fields: dict) -> Screen:
        def create():
            username, errors = self._create(fields)
            if username is None:
                return self.children(words.SOME_NOT_SAVED, errors=errors,
                                     draft=_without_passwords(fields))
            self._selected = username
            if errors:
                return self.children(words.SOME_NOT_SAVED, errors=errors)
            return self.children(words.CHILD_ADDED)
        return self._guard(create)

    def give_time(self, minutes: int) -> Screen:
        username = self._selected
        if username is None:
            return self.children()
        result = self._guard(lambda: self._daemon.grant(self._token, username, minutes))
        if isinstance(result, Screen):
            return result
        return self.children(words.TIME_GIVEN)

    def set_time_left(self, minutes: int) -> Screen:
        """What the chosen child has left today, zero included (D50)."""
        username = self._selected
        if username is None:
            return self.children()
        try:
            result = self._guard(lambda: self._daemon.set_time_left(self._token, username,
                                                                    minutes))
        except Invalid:
            return self.children(words.NO_LIMIT_TO_SET)
        if isinstance(result, Screen):
            return result
        return self.children(words.TIME_SET)

    def ask_remove(self) -> Screen:
        return self.children(confirm_remove=True)

    def remove(self, keep_home: bool) -> Screen:
        username = self._selected
        if username is None:
            return self.children()
        try:
            result = self._guard(lambda: self._daemon.delete_child(self._token, username, keep_home))
        except SessionActive:
            return self.children(words.CANNOT_REMOVE_SIGNED_IN)
        if isinstance(result, Screen):
            return result
        self._selected = None
        self._first_open = True
        return self.children(words.CHILD_REMOVED)

    # --- the other pages -----------------------------------------------------

    def modules(self, notice: str | None = None, confirm_remove: str | None = None,
                failure: str = "",
                toast: str | None = None) -> Screen:
        """Two parts. The installed modules down, every child across, a
        switch where they meet, and Remove at the end of each; names and
        descriptions in the machine's language. Then the modules the
        archive offers that are not installed, each with Install. While a
        module is installed or removed, or the lists refreshed, the page
        shows it and asks again every second."""
        self._confirming = confirm_remove
        kids = self._daemon.children()
        enabled = {child["username"]: {entry.get("id") for entry in
                                       self._daemon.modules(child["username"])
                                       if entry.get("enabled")}
                   for child in kids}
        rows = [{"id": module.id,
                 "name": kidux_modules.name_in(module, self._language),
                 "description": kidux_modules.description_in(module, self._language),
                 "enabled": {username: module.id in ids for username, ids in enabled.items()},
                 "needs_windows": module.needs_windows,
                 "min_age": module.min_age, "max_age": module.max_age,
                 "before": list(module.recommended_before),
                 "version": shown_version(module.version),
                 "settings": bool(module.settings),
                 "packaged": module.package is not None}
                for module in kidux_modules.installed()]
        update = self._update_state()
        # Asked of apt, which takes a moment: once per page, not once a
        # second while a job runs.
        if self._offered is None or update["job"] == "idle":
            try:
                self._offered = self._daemon.available_modules()
            except (DaemonUnavailableError, DaemonError):
                self._offered = []
        offered = self._offered
        installed = {row["id"] for row in rows}
        # The modules best done first by name (D55): an installed one's or
        # one on offer's, in the machine's language; its id otherwise.
        names = {entry["id"]: entry["name"] for entry in offered}
        names.update((row["id"], row["name"]) for row in rows)

        def first(entry: dict) -> list[str]:
            return [names.get(other, other) for other in entry.get("before", [])]

        # The module being installed is in the installed list from the
        # moment Install is pressed, with how far it has got where its
        # switches and buttons will be, as the archive describes it until
        # its manifest is in place; the one being removed shows the same in
        # place of its buttons. Neither moves the page.
        installing = self._installing if update["job"] == "installing" else None
        removing = self._removing if update["job"] == "removing" else None
        to_install = [module for action, module in self._queue if action == "install"]
        to_remove = [module for action, module in self._queue if action == "remove"]
        for row in rows:
            row["job"] = ("installing" if row["id"] == installing
                          else "removing" if row["id"] == removing
                          else "to-remove" if row["id"] in to_remove else None)
        if removing and removing not in installed and self._removing_row is not None:
            rows.append({**self._removing_row, "job": "removing"})
        coming = ([installing] if installing else []) + to_install
        for module in coming:
            if module in installed:
                continue
            entry = next((e for e in offered if e["id"] == module), None)
            if entry is not None:
                rows.append({"id": entry["id"], "name": entry["name"],
                             "description": entry.get("description", ""), "enabled": {},
                             "needs_windows": False, "min_age": entry.get("min_age", 0),
                             "max_age": entry.get("max_age", 0),
                             "before": list(entry.get("before", [])),
                             "version": shown_version(entry.get("offered_version", "")),
                             "settings": False, "packaged": True,
                             "job": "installing" if module == installing else "to-install"})
        rows = ordered([{**row, "first": first(row)} for row in rows])
        self._rows_shown = rows
        on_offer = ordered([{**entry, "first": first(entry),
                             "offered_version": shown_version(entry.get("offered_version", ""))}
                            for entry in offered
                            if entry["id"] not in installed and not entry["installed"]
                            and entry["id"] not in coming])
        return self._screen("panel_modules", notice, children=kids, modules=rows,
                            offered=on_offer, installing=installing,
                            source=bool(offered), confirm_remove=confirm_remove,
                            failure=failure, update=update, toast=toast,
                            # Polled while a job runs, and while one waits: the
                            # job it waited behind may have ended between the
                            # asking and this drawing, and only a poll starts it.
                            polling=update["job"] in ("checking", "installing", "removing",
                                                      "away") or bool(self._queue),
                            poll="poll_modules")

    def _module_job(self, start, toast: str | None = None,
                    confirm_remove: str | None = None) -> Screen:
        """Start installing or removing, or say why not; what waited behind
        a job that could not start is dropped, since nothing would start it."""
        try:
            result = self._guard(start)
        except SessionActive:
            self._queue.clear()
            return self.modules(words.MODULES_WAIT)
        except Busy:
            self._queue.clear()
            return self.modules(words.UPDATE_BUSY)
        except Invalid:
            self._queue.clear()
            return self.modules(words.NOT_SAVED)
        return result if isinstance(result, Screen) else self.modules(
            toast=toast, confirm_remove=confirm_remove)

    def _queued(self, action: str, module_id: str | None) -> Screen | None:
        """The job, queued while another runs: the page, with it waiting;
        None when nothing runs and it may start now."""
        if self._update_state()["job"] == "idle" and not self._queue:
            return None
        if (action, module_id) not in self._queue:
            self._queue.append((action, module_id))
        return self.modules(confirm_remove=self._confirming)

    def _start(self, action: str, module_id: str | None, toast: str | None = None,
               confirm_remove: str | None = None) -> Screen:
        """Start the job now; `toast` says how the one before went, and
        `confirm_remove` keeps a question the page is asking."""
        if action == "install":
            self._installing = module_id
            return self._module_job(lambda: self._daemon.install_module(self._token, module_id),
                                    toast, confirm_remove)
        if action == "remove":
            self._removing = module_id
            self._removing_row = next((row for row in self._rows_shown
                                       if row["id"] == module_id), None)
            return self._module_job(lambda: self._daemon.remove_module(self._token, module_id),
                                    toast, confirm_remove)
        try:
            result = self._guard(lambda: self._daemon.check_updates(self._token))
        except Busy:
            self._queue.clear()
            return self.modules(words.UPDATE_BUSY)
        return result if isinstance(result, Screen) else self.modules(
            toast=toast, confirm_remove=confirm_remove)

    def install_module(self, module_id: str) -> Screen:
        return self._queued("install", module_id) or self._start("install", module_id)

    def ask_remove_module(self, module_id: str) -> Screen:
        return self.modules(confirm_remove=module_id)

    def remove_module(self, module_id: str) -> Screen:
        return self._queued("remove", module_id) or self._start("remove", module_id)

    def look_for_modules(self) -> Screen:
        """Refresh apt's lists, which is what the list of modules to add is
        read from; allowed while children are signed in."""
        return self._queued("look", None) or self._start("look", None)

    def poll_modules(self) -> Screen:
        """Once a second while a job runs; the page it ends on says how the
        job went, and starts the next job waiting, if any."""
        update = self._update_state()
        asking = self._confirming
        if update["job"] != "idle":
            return self.modules(confirm_remove=asking)
        # How it went is said in passing, in a toast, so that the page
        # stays where it is; what apt said of a failure stays on the page.
        toast = {"installed": words.MODULE_INSTALLED, "removed": words.MODULE_REMOVED,
                 "failed": words.MODULE_FAILED}.get(update["outcome"])
        failure = update["detail"] if update["outcome"] == "failed" else ""
        if self._queue:
            action, module_id = self._queue.pop(0)
            return self._start(action, module_id, toast, asking)
        return self.modules(toast=toast, failure=failure, confirm_remove=asking)

    def module_settings(self, module_id: str, notice: str | None = None) -> Screen:
        """A module's settings, as its manifest declares them (D90): the
        settings down, every child across, each child's value where they
        meet; a secret only said to be set, never shown."""
        module = kidux_modules.read(module_id)
        if module is None or not module.settings:
            return self.modules()
        kids = self._daemon.children()
        values, secrets = {}, {}
        for child in kids:
            result = self._guard(lambda child=child: self._daemon.module_settings(
                self._token, child["username"], module_id))
            if isinstance(result, Screen):
                return result
            values[child["username"]], secrets[child["username"]] = result[0], list(result[1])
        settings = [{"key": setting.key, "kind": setting.kind,
                     "label": kidux_modules.text_in(module, setting.label, self._language),
                     "description": kidux_modules.text_in(module, setting.description,
                                                          self._language),
                     "minimum": setting.minimum, "maximum": setting.maximum}
                    for setting in module.settings]
        return self._screen("panel_module_settings", notice, module=module_id,
                            module_name=kidux_modules.name_in(module, self._language),
                            children=kids, settings=settings, values=values, secrets=secrets)

    def set_module_setting(self, module_id: str, username: str, key: str, value) -> Screen:
        """One setting for one child, saved as soon as it is changed; the
        daemon refuses what is not of its kind, and the page says so."""
        try:
            result = self._guard(lambda: self._daemon.set_module_setting(
                self._token, username, module_id, key, value))
        except Invalid:
            return self.module_settings(module_id, words.NOT_SAVED)
        if isinstance(result, Screen):
            return result
        return self.module_settings(module_id, words.SAVED)

    def set_module(self, username: str, module_id: str, enabled: bool) -> Screen:
        """One switch, saved as soon as it is flipped. A refusal draws the
        page again from what the daemon has, which puts the switch back."""
        try:
            result = self._guard(lambda: self._daemon.set_module(
                self._token, username, module_id, bool(enabled)))
        except Invalid:
            return self.modules(words.NOT_SAVED)
        if isinstance(result, Screen):
            return result
        return self.modules(words.SAVED)

    def system(self, notice: str | None = None, recovery: str | None = None,
               errors=None) -> Screen:
        scale = float(self._config.get("display_scale", 0.0))
        if recovery is not None:
            self._recovery = recovery
        update = self._update_state()
        # What automatic is on this screen, from the mode session-inner
        # exports; the view works it out from the display when nothing did.
        mode = kidux_screen.mode_from_environment()
        automatic = kidux_screen.automatic_scale(*mode) if mode else None
        try:
            versions = self._daemon.versions()
        except (DaemonUnavailableError, DaemonError):
            versions = {}
        version = versions.get("kidux-base") or self._daemon.version()
        parts = [(message, versions[package]) for package, message in PARTS
                 if versions.get(package)]
        return self._screen("panel_system", notice, version=version, parts=parts,
                            scale=scale, scales=SCALES, automatic=automatic,
                            languages=languages(),
                            language=self._language, keyboard=self._keyboard,
                            keyboards=keyboards_for(self._language),
                            recovery=self._recovery, errors=dict(errors or {}),
                            idle_lock=self._idle_lock_minutes(),
                            screen_off=self._screen_off_minutes(),
                            update=update,
                            polling=update["job"] in ("checking", "applying", "installing",
                                                      "removing", "away"),
                            poll="poll_updates")

    # --- updates (plan step 9.8) -------------------------------------------------

    def _update_state(self) -> dict:
        """What the update job is doing, for the system page. "away" while the
        daemon cannot be asked, which an update of the daemon itself causes."""
        try:
            job, fraction, package, outcome, detail, packages = self._daemon.update_state()
        except (DaemonUnavailableError, DaemonError):
            return {"job": "away", "fraction": 0.0, "package": "", "outcome": "",
                    "detail": "", "packages": []}
        return {"job": job, "fraction": fraction, "package": package, "outcome": outcome,
                "detail": detail, "packages": list(packages)}

    def look_for_updates(self) -> Screen:
        try:
            result = self._guard(lambda: self._daemon.check_updates(self._token))
        except Busy:
            return self.system(words.UPDATE_BUSY)
        return result if isinstance(result, Screen) else self.system()

    def install_updates(self) -> Screen:
        try:
            result = self._guard(lambda: self._daemon.apply_updates(self._token))
        except SessionActive:
            return self.system(words.UPDATES_WAIT)
        except Busy:
            return self.system(words.UPDATE_BUSY)
        return result if isinstance(result, Screen) else self.system()

    def poll_updates(self) -> Screen:
        return self.system()

    def restart_now(self) -> Screen:
        """After an update that needs it. No child has a session: the update
        could not have been installed otherwise."""
        try:
            self._daemon.reboot()
        except (DaemonUnavailableError, DaemonError):
            return self.system(words.SOMETHING_WENT_WRONG)
        return self._screen("turning_off")

    def tab(self, page: str) -> Screen:
        return {"children": self.children, "modules": self.modules,
                "system": self.system,
                "network": lambda: self.network(check=True)}.get(page, self.children)()

    def close(self, notice: str | None = None) -> Screen:
        token, self._token = self._token, ""
        if token:
            try:
                self._daemon.lock_panel(token)
            except (DaemonUnavailableError, DaemonError):
                pass  # it expires by itself (D26)
        if self._restart_on_close:
            # The screen starts again, and takes the new size, language or
            # keyboard, as the wizard's keyboard does.
            self.exit_requested = True
            return self._screen("restarting")
        screen = self._on_close()
        if notice and screen.notice is None:
            screen = Screen(screen.name, screen.language, screen.data, notice, screen.owner)
        return screen

    def show_recovery(self) -> Screen:
        result = self._guard(lambda: self._daemon.recovery_password(self._token))
        if isinstance(result, Screen):
            return result
        return self.system(recovery=result)

    def save_adult_password(self, current: str, password: str, again: str) -> Screen:
        if not password:
            return self.system(words.SOME_NOT_SAVED, errors={"adult_password": words.PASSWORD_NEEDED})
        if password != again:
            return self.system(words.SOME_NOT_SAVED, errors={"adult_password": words.PASSWORDS_DIFFER})
        # Unlocking again with the current password proves it and replaces
        # this connection's token with a fresh one (one token per connection).
        token = self._daemon.unlock_panel(current)
        if not token:
            return self.system(words.SOME_NOT_SAVED, errors={"current_password": vocabulary.WRONG_PASSWORD})
        self._token = token
        result = self._guard(lambda: self._daemon.set_adult_password(self._token, password))
        if isinstance(result, Screen):
            return result
        return self.system(words.SAVED)

    def set_language_keyboard(self, locale: str, layout: str) -> Screen:
        if layout not in [code for code, _ in keyboards_for(locale)]:
            layout = keyboards_for(locale)[0][0]
        result = self._guard(lambda: self._daemon.set_config(
            self._token, {"default_language": locale, "default_keyboard": layout}))
        if isinstance(result, Screen):
            return result
        self._language, self._keyboard = locale, layout
        self._config.update(default_language=locale, default_keyboard=layout)
        return self.system(self._applies())

    def set_scale(self, scale: float) -> Screen:
        result = self._guard(lambda: self._daemon.set_config(self._token,
                                                             {"display_scale": float(scale)}))
        if isinstance(result, Screen):
            return result
        self._config["display_scale"] = float(scale)
        return self.system(self._applies())

    def set_idle(self, lock_minutes: int, off_minutes: int) -> Screen:
        """The minutes a session may be left alone before it locks, and
        before the screen turns off (D67): the panel's own at once, a
        screen's the next time it starts."""
        changes = {"idle_lock_minutes": int(lock_minutes), "screen_off_minutes": int(off_minutes)}
        result = self._guard(lambda: self._daemon.set_config(self._token, changes))
        if isinstance(result, Screen):
            return result
        self._config.update(changes)
        return self.system(words.IDLE_SAVED)

    def _applies(self) -> str:
        """When a setting the screen takes at its start applies: on the
        sign-in screen, when the panel closes, which restarts the screen; on
        the lock screen, which must not restart under a child's session, the
        next time a screen starts."""
        if self._lock_mode:
            return words.APPLIES_NEXT_START
        self._restart_on_close = True
        return words.APPLIES_ON_CLOSE

    # --- suspend (D119) ----------------------------------------------------------

    def power(self, notice: str | None = None) -> Screen:
        """Whether closing the lid suspends the computer, and what a
        computer idle does, as the daemon has them now; a warning when this
        computer cannot suspend, which the daemon then does as nothing, or
        the screen off only (power.md section 2)."""
        try:
            self._config.update(self._daemon.config())
        except (DaemonUnavailableError, DaemonError):
            pass
        config = self._config
        warning = None if config.get("can_sleep", True) else words.CANNOT_SLEEP
        lid = str(config.get("lid_action", LID_ACTIONS[0]))
        idle = str(config.get("idle_action", IDLE_ACTIONS[0]))
        return self._screen(
            "panel_power", notice,
            lid=lid if lid in LID_ACTIONS else LID_ACTIONS[0], lids=list(LID_ACTIONS),
            idle=idle if idle in IDLE_ACTIONS else IDLE_ACTIONS[0], idles=list(IDLE_ACTIONS),
            idle_minutes=int(config.get("idle_sleep_minutes", IDLE_SLEEP_MINUTES)),
            warning=warning)

    def set_lid(self, action: str) -> Screen:
        """What closing the lid does: the daemon has logind take it at once."""
        if action not in LID_ACTIONS:
            return self.power(words.NOT_SAVED)
        try:
            result = self._guard(lambda: self._daemon.set_config(self._token,
                                                                 {"lid_action": action}))
        except Invalid:
            return self.power(words.NOT_SAVED)
        if isinstance(result, Screen):
            return result
        self._config["lid_action"] = action
        return self.power(words.SAVED)

    def set_idle_sleep(self, action: str, minutes: int) -> Screen:
        """What a computer still left alone does, and after how many
        minutes: a screen takes it the next time it starts."""
        if action not in IDLE_ACTIONS:
            return self.power(words.NOT_SAVED)
        changes = {"idle_action": action, "idle_sleep_minutes": int(minutes)}
        try:
            result = self._guard(lambda: self._daemon.set_config(self._token, changes))
        except Invalid:
            return self.power(words.NOT_SAVED)
        if isinstance(result, Screen):
            return result
        self._config.update(changes)
        return self.power(words.APPLIES_NEXT_START)

    # --- advanced (D52) -----------------------------------------------------------

    def advanced(self, notice: str | None = None, draft: str | None = None) -> Screen:
        """The settings that depend on the machine's hardware: the pointer's
        speed and the touchpad's scroll, a step from -2 to 2 each, and
        Chromium's flags, one a line, as the daemon has them now: they may
        have been set since the screen started."""
        try:
            config = self._daemon.config()
            self._config.update(chromium_flags=list(config.get("chromium_flags") or []),
                                pointer_speed=int(config.get("pointer_speed") or 0),
                                scroll_speed=int(config.get("scroll_speed") or 0),
                                apt_statistics=bool(config.get("apt_statistics", True)))
        except (DaemonUnavailableError, DaemonError):
            pass
        flags = "\n".join(self._config.get("chromium_flags") or [])
        return self._screen("panel_advanced", notice,
                            chromium_flags=flags if draft is None else draft,
                            pointer_speed=int(self._config.get("pointer_speed") or 0),
                            scroll_speed=int(self._config.get("scroll_speed") or 0),
                            statistics=bool(self._config.get("apt_statistics", True)))

    def set_statistics(self, enabled: bool) -> Screen:
        """Whether every fetch of the archive carries an identifier of this
        machine's (D109), applied by the daemon at once."""
        result = self._guard(lambda: self._daemon.set_config(
            self._token, {"apt_statistics": bool(enabled)}))
        if isinstance(result, Screen):
            return result
        self._config["apt_statistics"] = bool(enabled)
        return self.advanced(words.SAVED)

    def set_pointer(self, key: str, step: int) -> Screen:
        """The pointer's speed or the touchpad's scroll, `key`, a step from
        -2 to 2: a child's session takes it when it next starts."""
        if key not in ("pointer_speed", "scroll_speed"):
            return self.advanced(words.NOT_SAVED)
        try:
            result = self._guard(lambda: self._daemon.set_config(self._token,
                                                                 {key: int(step)}))
        except Invalid:
            return self.advanced(words.NOT_SAVED)
        if isinstance(result, Screen):
            return result
        self._config[key] = int(step)
        return self.advanced(words.APPLIES_NEXT_SIGN_IN)

    def save_chromium_flags(self, text: str) -> Screen:
        flags = [line.strip() for line in text.splitlines() if line.strip()]
        try:
            result = self._guard(lambda: self._daemon.set_config(self._token,
                                                                 {"chromium_flags": flags}))
        except Invalid:
            return self.advanced(words.OPTION_NOT_ACCEPTED, draft=text)
        if isinstance(result, Screen):
            return result
        self._config["chromium_flags"] = flags
        return self.advanced(words.SAVED)

    # --- the network (D62) -------------------------------------------------------

    def network(self, notice: str | None = None, *, check: bool = False,
                asking: str | None = None, confirm_forget: str | None = None,
                errors=None, failure: str = "") -> Screen:
        """The machine's connections, the router's answer and, when
        NetworkManager manages a Wi-Fi, the networks in reach. Opened, it
        looks again (a rescan, a ping of the router); while a job runs it
        asks again every second."""
        if check:
            try:
                started = self._guard(lambda: self._daemon.check_network(self._token))
            except Busy:
                started = None
            except (DaemonUnavailableError, DaemonError):
                started = None
            if isinstance(started, Screen):
                return started
        try:
            result = self._guard(lambda: self._daemon.network(self._token))
        except (DaemonUnavailableError, DaemonError):
            return self._screen("panel_network", notice or words.SOMETHING_WENT_WRONG,
                                summary={}, interfaces=[], networks=[], asking=None,
                                confirm_forget=None, errors={}, failure="", polling=False,
                                poll="poll_network")
        if isinstance(result, Screen):
            return result
        summary, interfaces, networks = result
        return self._screen("panel_network", notice, summary=dict(summary),
                            interfaces=list(interfaces), networks=list(networks),
                            asking=asking, confirm_forget=confirm_forget,
                            errors=dict(errors or {}), failure=failure,
                            polling=summary.get("job", "idle") != "idle", poll="poll_network")

    def poll_network(self) -> Screen:
        """Once a second while a job runs; the page it ends on says how the
        job went."""
        screen = self.network()
        if screen.name != "panel_network" or screen.data.get("polling"):
            return screen
        summary = screen.data.get("summary") or {}
        outcome, detail = summary.get("outcome"), summary.get("detail", "")
        if outcome == "connected":
            return self.network(words.WIFI_CONNECTED)
        if outcome == "forgotten":
            return self.network(words.WIFI_FORGOTTEN)
        if outcome == "failed" and detail == "wrong_password":
            return self.network(words.WIFI_WRONG_PASSWORD, asking=summary.get("ssid"))
        if outcome == "failed":
            return self.network(words.WIFI_NOT_CONNECTED, failure=detail)
        return screen

    def refresh_network(self) -> Screen:
        """*Look again*."""
        return self.network(check=True)

    def ask_wifi_password(self, ssid: str) -> Screen:
        return self.network(asking=ssid)

    def connect_wifi(self, ssid: str, password: str = "") -> Screen:
        """Join a network. A secured one never joined takes its password,
        which is checked for length here, before the daemon checks it again:
        8 to 63 bytes, as NetworkManager counts it, or the key's 64 hex
        digits. The job may be over before the page is read again, so the
        page that follows is the poll's, which says how it ended."""
        if password and not wifi_password_fits(password):
            return self.network(asking=ssid, errors={"password": words.WIFI_PASSWORD_LENGTH})
        try:
            result = self._guard(lambda: self._daemon.connect_wifi(self._token, ssid,
                                                                    password))
        except Busy:
            return self.network(words.NETWORK_BUSY)
        except Invalid:
            return self.network(words.WIFI_NOT_CONNECTED, asking=ssid if password else None)
        except (DaemonUnavailableError, DaemonError):
            return self.network(words.SOMETHING_WENT_WRONG)
        return result if isinstance(result, Screen) else self.poll_network()

    def ask_forget_wifi(self, ssid: str) -> Screen:
        return self.network(confirm_forget=ssid)

    def forget_wifi(self, ssid: str) -> Screen:
        try:
            result = self._guard(lambda: self._daemon.forget_wifi(self._token, ssid))
        except Busy:
            return self.network(words.NETWORK_BUSY)
        except (DaemonUnavailableError, DaemonError):
            return self.network(words.SOMETHING_WENT_WRONG)
        return result if isinstance(result, Screen) else self.poll_network()

    # --- anywhere --------------------------------------------------------------

    def back(self, screen: str = "") -> Screen:
        """Escape and *Close*: the panel closes, and nothing unsaved is kept;
        from a module's settings, Back is the Modules page."""
        if screen == "panel_module_settings":
            return self.modules()
        return self.close()

    def idle(self) -> Screen:
        """Left alone: closed, as a panel left open in a living room must be."""
        return self.close()


#: What each screen offers, by the method that answers it, as `flow.py` has
#: for the sign-in and lock screens. *Turn off* is on every wizard screen as
#: well, answered by the sign-in screen itself.
WIZARD_ACTIONS = {
    "wiz_language": ("choose_language",),
    "wiz_keyboard": ("choose_keyboard", "back"),
    "wiz_password": ("submit_adult_password",),
    "wiz_statistics": ("set_statistics",),
    "wiz_unlock": ("submit_unlock",),
    "wiz_child": ("add_child",),
    "wiz_done": ("finish",),
    "restarting": (),
}

PANEL_ACTIONS = {
    "panel_children": ("select", "new_child", "save_child", "add_child", "give_time",
                       "set_time_left",
                       "ask_remove", "remove", "tab", "close"),
    "panel_modules": ("set_module", "install_module", "ask_remove_module", "remove_module",
                      "look_for_modules", "poll_modules", "module_settings", "tab", "close"),
    "panel_module_settings": ("set_module_setting", "back", "tab", "close"),
    "panel_system": ("show_recovery", "save_adult_password", "set_language_keyboard",
                     "set_scale", "set_idle", "look_for_updates", "install_updates",
                     "poll_updates",
                     "restart_now", "advanced", "power", "tab", "close"),
    "panel_power": ("set_lid", "set_idle_sleep", "tab", "close"),
    "panel_advanced": ("save_chromium_flags", "set_pointer", "set_statistics", "tab", "close"),
    "panel_network": ("refresh_network", "poll_network", "ask_wifi_password", "connect_wifi",
                      "ask_forget_wifi", "forget_wifi", "tab", "close"),
    "turning_off": (),
}
