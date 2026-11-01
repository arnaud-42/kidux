"""The first-run wizard and the adult panel, against a fake daemon.

docs/dev/panel.md, sections 2 and 3: every step of the wizard, where it
resumes after each interruption, every field of the panel's forms saved
through the call the table says, a refused field marked while the others
are kept, a lost token closing the panel, and no screen without a way
forward.
"""

import pytest

from kidux import vocabulary
from kidux_greeter import words
from kidux_greeter.daemon import Busy, DaemonUnavailableError, Invalid, NotUnlocked, SessionActive
from kidux_greeter.flow import FINAL, Lock, SignIn
from kidux_greeter.panel import (PANEL_ACTIONS, WIZARD_ACTIONS, access_of, parse_access,
                                 username_for)

from test_flow import ADULT, FakeDaemon, FakeGreetd


class ManagedDaemon(FakeDaemon):
    """The fake daemon of test_flow, plus what the wizard and the panel call."""

    def __init__(self):
        super().__init__()
        self.settings = {"default_language": "en_US.UTF-8", "default_keyboard": "us",
                         "display_scale": 1.0, "setup_complete": True,
                         "language_chosen": True}
        self.policies = {"ana": {"mode": "daily", "daily_minutes": 60, "granted_seconds": 0},
                         "tom": {"mode": "unlimited", "daily_minutes": 60, "granted_seconds": 0}}
        self.token_valid = True
        self.signed_in = set()

    def config(self):
        self._check()
        return dict(self.settings)

    def _token(self, token):
        if not (token == "token" and self.token_valid):
            raise NotUnlocked("org.kidux.Daemon1.Error.NotUnlocked")

    def unlock_panel(self, password):
        return "token" if password == ADULT else None

    def version(self):
        return "0.3.0"

    def set_config(self, token, changes):
        if self.password_set or set(changes) - {"default_language", "default_keyboard"}:
            self._token(token)
        if any(not flag.startswith("--") for flag in changes.get("chromium_flags", [])):
            raise Invalid("org.kidux.Daemon1.Error.InvalidArgument")
        self.calls.append(("set_config", dict(changes)))
        self.settings.update(changes)
        if "default_language" in changes:
            self.settings["language_chosen"] = True

    def set_adult_password(self, token, password):
        if self.password_set:
            self._token(token)
        self.calls.append(("set_adult_password",))
        self.password_set = True

    def recovery_password(self, token):
        self._token(token)
        return "abc123"

    def create_child(self, token, username, display_name, language, keyboard, avatar, password):
        self._token(token)
        self.calls.append(("create_child", username, display_name, language, keyboard, avatar))
        self.kids.append({"username": username, "display_name": display_name,
                          "language": language, "keyboard": keyboard, "avatar": avatar})
        self.policies[username] = {"mode": "manual", "daily_minutes": 60, "granted_seconds": 0}

    def delete_child(self, token, username, keep_home):
        self._token(token)
        if username in self.signed_in:
            raise SessionActive("org.kidux.Daemon1.Error.SessionActive")
        self.calls.append(("delete_child", username, keep_home))
        self.kids = [k for k in self.kids if k["username"] != username]

    def set_profile(self, token, username, changes):
        self._token(token)
        if changes.get("avatar") == "refused":
            raise Invalid("org.kidux.Daemon1.Error.InvalidArgument")
        self.calls.append(("set_profile", username, dict(changes)))
        for kid in self.kids:
            if kid["username"] == username:
                kid.update(changes)

    def set_child_password(self, token, username, password):
        self._token(token)
        self.calls.append(("set_child_password", username))

    def policy(self, username):
        return dict(self.policies[username])

    def set_policy(self, token, username, mode, daily_minutes, days=None):
        self._token(token)
        digits = None if days is None else "".join("1" if day else "0" for day in days)
        self.calls.append(("set_policy", username, mode, daily_minutes, digits))
        self.policies[username].update(mode=mode, daily_minutes=daily_minutes)
        if days is not None:
            self.policies[username]["days"] = list(days)

    def grant(self, token, username, minutes):
        self._token(token)
        self.calls.append(("grant", username, minutes))

    def set_time_left(self, token, username, minutes):
        self._token(token)
        if self.policies[username]["mode"] == "unlimited":
            raise Invalid("a child with no limit has no time left to set")
        self.calls.append(("set_time_left", username, minutes))

    #: What UpdateState answers: job, fraction, package, outcome, detail, packages.
    update = ("idle", 0.0, "", "", "", [])
    update_busy = False
    update_away = False

    def update_state(self):
        if self.update_away:
            raise DaemonUnavailableError("restarting")
        return self.update

    def check_updates(self, token):
        self._token(token)
        if self.update_busy:
            raise Busy("org.kidux.Daemon1.Error.Busy")
        self.calls.append(("check_updates",))
        self.update = ("checking", 0.0, "", "", "", [])

    def apply_updates(self, token):
        self._token(token)
        if self.signed_in:
            raise SessionActive("org.kidux.Daemon1.Error.SessionActive")
        self.calls.append(("apply_updates",))
        self.update = ("applying", 0.4, "kidux-greeter", "", "", [])

    def reboot(self):
        self.calls.append(("reboot",))

    #: Which modules are enabled for whom, as Modules1.List answers it.
    enabled = None

    def modules(self, username):
        switched = (self.enabled or {}).get(username, set())
        from kidux import modules
        return [{"id": m.id, "enabled": m.id in switched} for m in modules.installed()]

    def set_module(self, token, username, module_id, enabled):
        self._token(token)
        if module_id == "refused":
            raise Invalid("org.kidux.Daemon1.Error.InvalidArgument")
        self.calls.append(("set_module", username, module_id, enabled))
        self.enabled = self.enabled or {}
        switched = self.enabled.setdefault(username, set())
        (switched.add if enabled else switched.discard)(module_id)

    #: What an adult set in each module for each child, and which secrets.
    settings = None

    def module_settings(self, token, username, module_id):
        self._token(token)
        stored = (self.settings or {}).get((username, module_id), {})
        values = {k: v for k, v in stored.items() if k != "password"}
        values.setdefault("type_in", True)
        return values, ["password"] if stored.get("password") else []

    def set_module_setting(self, token, username, module_id, key, value):
        self._token(token)
        if key == "type_in" and not isinstance(value, bool):
            raise Invalid("org.kidux.Daemon1.Error.InvalidArgument")
        self.calls.append(("set_module_setting", username, module_id, key, value))
        self.settings = self.settings or {}
        self.settings.setdefault((username, module_id), {})[key] = value

    #: What Modules1.Available answers.
    offered: list = []

    def available_modules(self):
        return [dict(entry) for entry in self.offered]

    def install_module(self, token, module_id):
        self._token(token)
        if self.signed_in:
            raise SessionActive("org.kidux.Daemon1.Error.SessionActive")
        if self.update_busy:
            raise Busy("org.kidux.Daemon1.Error.Busy")
        self.calls.append(("install_module", module_id))
        self.update = ("installing", 0.2, f"kidux-module-{module_id}", "", "", [])

    def remove_module(self, token, module_id):
        self._token(token)
        if self.signed_in:
            raise SessionActive("org.kidux.Daemon1.Error.SessionActive")
        self.calls.append(("remove_module", module_id))
        self.update = ("removing", 0.5, f"kidux-module-{module_id}", "", "", [])


    # --- the network (D62) ---------------------------------------------------

    #: What GetNetwork answers: a summary, the interfaces, the networks.
    net_summary = {"manager": True, "wifi": True, "wifi_changeable": True,
                   "gateway": "192.168.1.1", "gateway_interface": "wlan0", "router": "",
                   "job": "idle", "outcome": "", "ssid": "", "detail": ""}
    net_interfaces = [{"name": "wlan0", "kind": "wifi", "up": True, "address": "192.168.1.20",
                       "network": "Home", "signal": 70, "managed": True}]
    net_networks = [
        {"ssid": "Home", "signal": 70, "secured": True, "security": "psk", "active": True,
         "known": True},
        {"ssid": "Neighbours", "signal": 40, "secured": True, "security": "psk",
         "active": False, "known": False},
    ]
    net_busy = False
    net_over_at_once = None

    def network(self, token):
        self._token(token)
        return dict(self.net_summary), [dict(i) for i in self.net_interfaces], \
            [dict(n) for n in self.net_networks]

    def check_network(self, token):
        self._token(token)
        if self.net_busy:
            raise Busy("org.kidux.Daemon1.Error.Busy")
        self.calls.append(("check_network",))
        self.net_summary = {**self.net_summary, "job": "checking"}

    def connect_wifi(self, token, ssid, password):
        self._token(token)
        if self.net_busy:
            raise Busy("org.kidux.Daemon1.Error.Busy")
        self.calls.append(("connect_wifi", ssid, password))
        self.net_summary = {**self.net_summary, "job": "connecting", "ssid": ssid}
        self._maybe_over_at_once()

    def forget_wifi(self, token, ssid):
        self._token(token)
        self.calls.append(("forget_wifi", ssid))
        self.net_summary = {**self.net_summary, "job": "forgetting", "ssid": ssid}
        self._maybe_over_at_once()

    def _maybe_over_at_once(self):
        # A job over before the page reads again: `net_over_at_once` is how
        # it ended.
        if self.net_over_at_once:
            self.finish_network_job(*self.net_over_at_once)

    def finish_network_job(self, outcome="", detail=""):
        self.net_summary = {**self.net_summary, "job": "idle", "outcome": outcome,
                            "detail": detail, "router": "answers"}


@pytest.fixture
def daemon():
    return ManagedDaemon()


@pytest.fixture
def fresh(daemon):
    """A machine never set up: no password, no children, no language."""
    daemon.password_set = False
    daemon.kids = []
    daemon.settings.update(setup_complete=False, language_chosen=False)
    return daemon


def names(screens):
    return [s.name for s in screens]


# --- the wizard --------------------------------------------------------------------


def wizard_at_the_child(fresh):
    fresh.settings["language_chosen"] = True
    signin = SignIn(fresh, FakeGreetd())
    signin.start()
    screen = signin.wizard.submit_adult_password(ADULT, ADULT)
    assert screen.name == "wiz_statistics"
    screen = signin.wizard.set_statistics(True)
    return signin, screen


def test_the_wizard_asks_whether_to_share_usage_statistics_on_by_default(fresh):
    fresh.settings["language_chosen"] = True
    signin = SignIn(fresh, FakeGreetd())
    signin.start()

    screen = signin.wizard.submit_adult_password(ADULT, ADULT)
    assert (screen.name, screen.data["shared"]) == ("wiz_statistics", True)

    screen = signin.wizard.set_statistics(False)
    assert screen.name == "wiz_child"
    assert ("set_config", {"apt_statistics": False}) in fresh.calls


def test_a_machine_never_set_up_starts_the_wizard_at_the_languages(fresh):
    screen = SignIn(fresh, FakeGreetd()).start()

    assert (screen.name, screen.owner) == ("wiz_language", "wizard")
    assert screen.data["languages"]


def test_choosing_a_language_speaks_it_and_offers_its_keyboards(fresh):
    signin = SignIn(fresh, FakeGreetd())
    signin.start()

    screen = signin.wizard.choose_language("es_ES.UTF-8")

    assert screen.language == "es_ES.UTF-8"
    assert [layout for layout, _ in screen.data["keyboards"]] == ["es", "latam"]


def test_the_keyboard_is_saved_then_the_screen_restarts_to_apply_it(fresh):
    signin = SignIn(fresh, FakeGreetd())
    signin.start()
    signin.wizard.choose_language("es_ES.UTF-8")

    screen = signin.wizard.choose_keyboard("es")

    assert screen.name == "restarting"
    assert signin.exit_requested
    assert ("set_config", {"default_language": "es_ES.UTF-8", "default_keyboard": "es"}) in fresh.calls


def test_after_the_restart_it_resumes_at_the_adult_password(fresh):
    fresh.settings.update(language_chosen=True, default_language="es_ES.UTF-8")

    screen = SignIn(fresh, FakeGreetd()).start()

    assert (screen.name, screen.language) == ("wiz_password", "es_ES.UTF-8")


def test_the_adult_password_is_typed_twice_then_the_statistics_then_the_first_childs_form(fresh):
    fresh.settings["language_chosen"] = True
    signin = SignIn(fresh, FakeGreetd())
    signin.start()

    assert signin.wizard.submit_adult_password("", "").notice == words.PASSWORD_NEEDED
    assert signin.wizard.submit_adult_password("one", "two").notice == words.PASSWORDS_DIFFER
    screen = signin.wizard.submit_adult_password(ADULT, ADULT)
    assert (screen.name, screen.owner) == ("wiz_statistics", "wizard")
    assert ("set_adult_password",) in fresh.calls
    screen = signin.wizard.set_statistics(True)
    assert (screen.name, screen.owner) == ("wiz_child", "wizard")
    # The form starts at an hour a day, in the machine's language.
    assert screen.data["defaults"]["access"] == ("daily", 60, "1111111")
    assert screen.data["defaults"]["language"] == "en_US.UTF-8"


def test_the_first_childs_form_says_what_is_missing_and_keeps_the_rest(fresh):
    _signin, _ = wizard_at_the_child(fresh)
    wizard = _signin.wizard

    screen = wizard.add_child({"display_name": " ", "password": "a", "again": "b",
                               "access": "manual:0"})

    assert screen.name == "wiz_child"
    assert screen.notice == words.SOME_NOT_SAVED
    assert screen.data["errors"] == {"display_name": words.NAME_NEEDED,
                                     "password": words.PASSWORDS_DIFFER}
    # What was typed stays, except the passwords, which are never drawn again.
    assert screen.data["draft"]["access"] == "manual:0"
    assert "password" not in screen.data["draft"]
    assert not [c for c in fresh.calls if c[0] == "create_child"]


def test_the_whole_wizard_ends_with_a_child_on_the_sign_in_screen(fresh):
    signin, _ = wizard_at_the_child(fresh)
    wizard = signin.wizard

    screen = wizard.add_child({"display_name": "Lucía", "avatar": "fox",
                               "language": "en_US.UTF-8", "password": "lucia-pw",
                               "again": "lucia-pw", "access": "daily:90"})

    assert screen.name == "wiz_done"
    assert ("create_child", "lucia", "Lucía", "en_US.UTF-8", "us", "fox") in fresh.calls
    assert ("set_policy", "lucia", "daily", 90, "1111111") in fresh.calls
    assert ("set_config", {"setup_complete": True}) in fresh.calls
    assert ("lock_panel", "token") in fresh.calls

    screen = wizard.finish()
    assert screen.name == "choose"
    assert [c["display_name"] for c in screen.data["children"]] == ["Lucía"]


def test_a_name_and_a_password_are_enough_for_the_first_child(fresh):
    signin, _ = wizard_at_the_child(fresh)

    screen = signin.wizard.add_child({"display_name": "Leo", "password": "p", "again": "p"})

    assert screen.name == "wiz_done"
    assert ("set_policy", "leo", "daily", 60, "1111111") in fresh.calls


def test_a_password_set_but_no_child_resumes_by_asking_for_it(fresh):
    fresh.password_set = True
    signin = SignIn(fresh, FakeGreetd())

    assert signin.start().name == "wiz_unlock"
    assert signin.wizard.submit_unlock("a guess").notice == vocabulary.WRONG_PASSWORD
    assert signin.wizard.submit_unlock(ADULT).name == "wiz_child"


def test_a_machine_with_children_is_never_sent_to_the_wizard(daemon):
    # Set up some other way, or before the wizard existed: usable as it is.
    daemon.settings["setup_complete"] = False

    assert SignIn(daemon, FakeGreetd()).start().name == "choose"


def test_back_from_the_keyboard_goes_to_the_languages(fresh):
    signin = SignIn(fresh, FakeGreetd())
    signin.start()
    signin.wizard.choose_language("es_ES.UTF-8")

    assert signin.wizard.back("wiz_keyboard").name == "wiz_language"


@pytest.mark.parametrize("name,expected", [
    ("Lucía", "lucia"), ("José María", "josemaria"), ("7 enanitos", "child7enanitos"),
    ("李", "child"), ("Ana", "ana2"),
])
def test_a_childs_account_name_comes_from_their_name(name, expected):
    taken = {"ana"}
    assert username_for(name, taken=lambda n: n in taken) == expected


# --- the panel -----------------------------------------------------------------


@pytest.fixture
def panel(daemon):
    signin = SignIn(daemon, FakeGreetd())
    signin.start()
    signin.tap_adult()
    screen = signin.submit_adult_password(ADULT)
    assert (screen.name, screen.owner) == ("panel_children", "panel")
    return signin.panel


ANA_AS_SHOWN = {"display_name": "Ana", "avatar": "fox", "language": "es_ES.UTF-8",
                "access": "daily:60"}


def test_the_panel_opens_on_the_first_childs_form(panel):
    screen = panel.children()

    assert [c["username"] for c in screen.data["children"]] == ["ana", "tom"]
    assert screen.data["selected"] == "ana"
    assert screen.data["current"]["access"] == ("daily", 60, "1111111")
    assert screen.data["current"]["language"] == "es_ES.UTF-8"
    assert screen.data["left"] == 600


def test_choosing_another_child_shows_their_form(panel):
    screen = panel.select("tom")

    assert screen.data["selected"] == "tom"
    assert screen.data["current"]["access"] == ("unlimited", 0, "1111111")


def test_saving_an_unchanged_form_calls_nothing(panel, daemon):
    before = list(daemon.calls)

    screen = panel.save_child(dict(ANA_AS_SHOWN))

    assert daemon.calls == before
    assert screen.notice is None


def test_every_changed_field_is_saved_through_its_own_call(panel, daemon):
    screen = panel.save_child({**ANA_AS_SHOWN, "display_name": "Anita", "avatar": "whale",
                               "language": "en_US.UTF-8", "password": "new", "again": "new",
                               "access": "manual:0"})

    assert ("set_profile", "ana", {"display_name": "Anita"}) in daemon.calls
    assert ("set_profile", "ana", {"avatar": "whale"}) in daemon.calls
    assert ("set_profile", "ana", {"language": "en_US.UTF-8", "keyboard": "us"}) in daemon.calls
    assert ("set_child_password", "ana") in daemon.calls
    assert ("set_policy", "ana", "manual", 60, "1111111") in daemon.calls
    assert (screen.name, screen.notice) == ("panel_children", words.SAVED)


def test_a_refused_field_is_marked_and_the_others_are_kept(panel, daemon):
    screen = panel.save_child({**ANA_AS_SHOWN, "display_name": "Anita", "avatar": "refused"})

    assert ("set_profile", "ana", {"display_name": "Anita"}) in daemon.calls
    assert screen.notice == words.SOME_NOT_SAVED
    assert screen.data["errors"] == {"avatar": words.NOT_SAVED}
    assert screen.data["draft"]["avatar"] == "refused"


def test_two_different_passwords_are_marked_and_nothing_else_is_lost(panel, daemon):
    screen = panel.save_child({**ANA_AS_SHOWN, "access": "daily:90", "password": "a", "again": "b"})

    assert ("set_policy", "ana", "daily", 90, "1111111") in daemon.calls
    assert ("set_child_password", "ana") not in daemon.calls
    assert screen.data["errors"] == {"password": words.PASSWORDS_DIFFER}
    assert "password" not in screen.data["draft"]


def test_the_days_are_saved_with_the_policy(panel, daemon):
    # D54: Friday, Saturday and Sunday only.
    screen = panel.save_child({**ANA_AS_SHOWN, "access": "daily:60:0000111"})

    assert ("set_policy", "ana", "daily", 60, "0000111") in daemon.calls
    assert screen.data["current"]["access"] == ("daily", 60, "0000111")
    assert panel.save_child({**ANA_AS_SHOWN, "access": "daily:60:0000111"}).notice is None


@pytest.mark.parametrize("value, parsed", [
    ("daily:45:1111100", ("daily", 45, "1111100")),
    ("daily:45", ("daily", 45, "1111111")),
    (("unlimited", 0, "0000011"), ("unlimited", 0, "0000011")),
    ("manual:30:1010101", ("manual", 0, "1010101")),
    ("daily:45:111110", ("daily", 60, "1111111")),
    ("daily:45:11111x0", ("daily", 60, "1111111")),
    ("daily:45:1111100:1", ("daily", 60, "1111111")),
    (None, ("daily", 60, "1111111")),
])
def test_the_access_field_reads_mode_minutes_and_days(value, parsed):
    assert parse_access(value) == parsed


def test_a_policy_is_the_access_field_the_form_shows():
    assert access_of({"mode": "daily", "daily_minutes": 30,
                      "days": [True] * 5 + [False] * 2}) == ("daily", 30, "1111100")
    assert access_of({"mode": "manual", "daily_minutes": 30}) == ("manual", 0, "1111111")


def test_giving_time_from_the_childs_form(panel, daemon):
    screen = panel.give_time(30)

    assert ("grant", "ana", 30) in daemon.calls
    assert (screen.notice, screen.data["selected"]) == (words.TIME_GIVEN, "ana")


def test_setting_the_time_left_from_the_childs_form(panel, daemon):
    screen = panel.set_time_left(0)

    assert ("set_time_left", "ana", 0) in daemon.calls
    assert (screen.notice, screen.data["selected"]) == (words.TIME_SET, "ana")


def test_a_child_with_no_limit_has_no_time_left_to_set(panel, daemon):
    panel.select("tom")
    screen = panel.set_time_left(5)

    assert screen.notice == words.NO_LIMIT_TO_SET
    assert not any(call[0] == "set_time_left" for call in daemon.calls)


def test_removing_a_child_asks_once_on_the_same_page(panel, daemon):
    panel.select("tom")

    asking = panel.ask_remove()
    assert (asking.name, asking.data["confirm_remove"]) == ("panel_children", True)

    screen = panel.remove(keep_home=True)
    assert ("delete_child", "tom", True) in daemon.calls
    assert (screen.name, screen.notice) == ("panel_children", words.CHILD_REMOVED)
    assert screen.data["selected"] == "ana"


def test_a_signed_in_child_cannot_be_removed_and_the_panel_says_why(panel, daemon):
    daemon.signed_in.add("tom")
    panel.select("tom")

    screen = panel.remove(keep_home=False)

    assert (screen.notice, screen.data["selected"]) == (words.CANNOT_REMOVE_SIGNED_IN, "tom")


def test_adding_a_child_from_the_same_form(panel, daemon):
    empty = panel.new_child()
    assert empty.data["selected"] is None

    screen = panel.add_child({"display_name": "Zoe", "avatar": "whale", "password": "z",
                              "again": "z", "access": "unlimited:0"})

    assert ("create_child", "zoe", "Zoe", "en_US.UTF-8", "us", "whale") in daemon.calls
    assert ("set_policy", "zoe", "unlimited", 60, "1111111") in daemon.calls
    assert (screen.notice, screen.data["selected"]) == (words.CHILD_ADDED, "zoe")


def test_saving_the_empty_form_adds_a_child(panel, daemon):
    panel.new_child()

    screen = panel.save_child({"display_name": "Zoe", "password": "z", "again": "z"})

    assert screen.notice == words.CHILD_ADDED


@pytest.fixture
def installed(tmp_path, tmp_path_factory, monkeypatch):
    """Two modules on the machine, one of them translated into Spanish; Hello
    from its package, Paint a folder put there by hand."""
    from kidux import modules, paths

    dpkg_info = tmp_path_factory.mktemp("dpkg-info")
    (dpkg_info / "kidux-module-hello.list").write_text("")
    monkeypatch.setattr(paths, "DPKG_INFO", dpkg_info)

    for module_id, name in (("hello", "Hello"), ("paint", "Paint")):
        (tmp_path / module_id).mkdir()
        (tmp_path / module_id / "module.toml").write_text(
            f'id = "{module_id}"\nname = "{name}"\ndescription = "About {name}."\n'
            f'launch = {{ exec = "/usr/bin/{module_id}" }}\n')
    monkeypatch.setattr(paths, "MODULES_DIR", tmp_path)
    spanish = {"Hello": "Hola", "About Hello.": "Sobre Hola."}

    class Catalogue(modules.gettext.NullTranslations):
        def gettext(self, message):
            return spanish.get(message, message)

    real = modules.gettext.translation

    def translation(domain, localedir=None, languages=None, fallback=False):
        if domain == "kidux-module-hello" and languages and languages[0].startswith("es"):
            return Catalogue()
        return real(domain, localedir=localedir, languages=languages, fallback=True)

    monkeypatch.setattr(modules.gettext, "translation", translation)
    return tmp_path


def test_the_modules_page_with_nothing_installed(panel, tmp_path, monkeypatch):
    from kidux import paths

    monkeypatch.setattr(paths, "MODULES_DIR", tmp_path / "none")

    screen = panel.tab("modules")

    assert (screen.name, screen.data["modules"]) == ("panel_modules", [])


def test_the_modules_page_has_a_switch_per_module_and_child(panel, daemon, installed):
    daemon.enabled = {"tom": {"paint"}}

    screen = panel.tab("modules")

    assert [c["username"] for c in screen.data["children"]] == ["ana", "tom"]
    assert screen.data["modules"] == [
        {"id": "hello", "name": "Hello", "description": "About Hello.",
         "enabled": {"ana": False, "tom": False}, "needs_windows": False,
         "min_age": 0, "max_age": 0, "before": [], "version": "", "settings": False,
         "packaged": True, "job": None, "first": []},
        {"id": "paint", "name": "Paint", "description": "About Paint.",
         "enabled": {"ana": False, "tom": True}, "needs_windows": False,
         "min_age": 0, "max_age": 0, "before": [], "version": "", "settings": False,
         "packaged": False, "job": None, "first": []},
    ]


def test_the_modules_are_named_in_the_machines_language(panel, daemon, installed):
    panel.set_language_keyboard("es_ES.UTF-8", "es")

    hello = panel.tab("modules").data["modules"][0]

    assert (hello["name"], hello["description"]) == ("Hola", "Sobre Hola.")


def test_a_switch_is_saved_as_soon_as_it_is_flipped(panel, daemon, installed):
    screen = panel.set_module("ana", "hello", True)

    assert ("set_module", "ana", "hello", True) in daemon.calls
    assert screen.notice == words.SAVED
    assert screen.data["modules"][0]["enabled"] == {"ana": True, "tom": False}

    screen = panel.set_module("ana", "hello", False)
    assert screen.data["modules"][0]["enabled"] == {"ana": False, "tom": False}


def test_a_refused_switch_is_put_back_with_a_sentence(panel, daemon, installed):
    screen = panel.set_module("ana", "refused", True)

    assert (screen.name, screen.notice) == ("panel_modules", words.NOT_SAVED)
    assert all(not any(row["enabled"].values()) for row in screen.data["modules"])


def test_a_lost_token_on_the_modules_page_closes_the_panel(panel, daemon, installed):
    daemon.token_valid = False

    screen = panel.set_module("ana", "hello", True)

    assert screen.owner != "panel"
    assert screen.notice == words.PANEL_CLOSED


GCOMPRIS = {"id": "gcompris", "name": "GCompris", "description": "Over a hundred activities",
            "installed": False, "version": ""}
HELLO = {"id": "hello", "name": "Hello", "description": "A first page to read",
         "installed": True, "version": "0.1.1"}


def test_the_modules_page_offers_what_is_not_installed(panel, daemon, installed):
    daemon.offered = [GCOMPRIS, HELLO]

    screen = panel.tab("modules")

    assert [row["id"] for row in screen.data["modules"]] == ["hello", "paint"]
    assert screen.data["offered"] == [{**GCOMPRIS, "first": [], "offered_version": ""}]
    assert screen.data["source"] is True
    assert screen.data["polling"] is False


def test_who_a_module_is_for_and_what_to_do_first_by_name(panel, daemon, installed):
    # D55: the ages as the manifest or the package says them, and the
    # modules best done first by their names in the machine's language,
    # installed or on offer, or by their ids when neither.
    (installed / "paint" / "module.toml").write_text(
        'id = "paint"\nname = "Paint"\nmin_age = 6\nmax_age = 12\n'
        'recommended_before = ["hello", "gcompris"]\nlaunch = { exec = "/usr/bin/paint" }\n')
    daemon.offered = [{**GCOMPRIS, "min_age": 2, "max_age": 0, "before": ["hello", "gone"]}]
    panel.set_language_keyboard("es_ES.UTF-8", "es")

    screen = panel.tab("modules")

    paint = screen.data["modules"][1]
    assert (paint["min_age"], paint["max_age"], paint["first"]) == (6, 12, ["Hola", "GCompris"])
    assert screen.data["offered"][0]["first"] == ["Hola", "gone"]


def test_the_lists_are_by_age_with_the_test_modules_last(panel, daemon, installed):
    # D73: the youngest first, a module with no age among them, by name at
    # the same age, and a module named [Test] last whatever its age.
    (installed / "paint" / "module.toml").write_text(
        'id = "paint"\nname = "Paint"\nmin_age = 6\nmax_age = 12\n'
        'launch = { exec = "/usr/bin/paint" }\n')
    (installed / "hello" / "module.toml").write_text(
        'id = "hello"\nname = "[Test] Hello"\nmin_age = 4\nmax_age = 8\n'
        'launch = { exec = "/usr/bin/hello" }\n')
    (installed / "sing").mkdir()
    (installed / "sing" / "module.toml").write_text(
        'id = "sing"\nname = "Sing"\nlaunch = { exec = "/usr/bin/sing" }\n')
    daemon.offered = [
        {**GCOMPRIS, "id": "scratch", "name": "Scratch", "min_age": 8, "max_age": 16},
        {**GCOMPRIS, "id": "canary", "name": "[Test] Canary", "min_age": 2, "max_age": 4},
        {**GCOMPRIS, "min_age": 2, "max_age": 10},
        {**GCOMPRIS, "id": "scratchjr", "name": "ScratchJr", "min_age": 5, "max_age": 7},
    ]

    screen = panel.tab("modules")

    assert [row["id"] for row in screen.data["modules"]] == ["sing", "paint", "hello"]
    assert [e["id"] for e in screen.data["offered"]] == ["gcompris", "scratchjr", "scratch",
                                                          "canary"]


@pytest.mark.parametrize("version,shown", [
    ("15.2.0+build2", "15.2.0"),
    ("1.3.2+git20201121", "1.3.2"),
    ("0+git20240513", "2024-05-13"),
    ("0.1.6", "0.1.6"),
    ("", ""),
])
def test_a_version_is_shown_without_how_it_was_built(version, shown):
    from kidux_greeter.panel import shown_version

    assert shown_version(version) == shown


def test_the_page_shows_versions_as_the_adult_reads_them(panel, daemon, installed):
    (installed / "paint" / "module.toml").write_text(
        'id = "paint"\nname = "Paint"\nversion = "0+git20240513"\n'
        'launch = { exec = "/usr/bin/paint" }\n')
    daemon.offered = [{**GCOMPRIS, "offered_version": "15.2.0+build2"}]

    screen = panel.tab("modules")

    paint = next(row for row in screen.data["modules"] if row["id"] == "paint")
    assert paint["version"] == "2024-05-13"
    assert screen.data["offered"][0]["offered_version"] == "15.2.0"


def test_a_machine_without_the_archive_has_no_source_of_modules(panel, daemon, installed):
    daemon.offered = []

    screen = panel.tab("modules")

    assert (screen.data["offered"], screen.data["source"]) == ([], False)


def test_installing_starts_the_job_and_the_module_is_installed_from_then_on(panel, daemon,
                                                                           installed):
    daemon.offered = [GCOMPRIS]

    screen = panel.install_module("gcompris")

    assert ("install_module", "gcompris") in daemon.calls
    assert screen.data["update"]["job"] == "installing"
    assert (screen.data["polling"], screen.data["poll"]) == (True, "poll_modules")
    # Its row is among the installed ones, as the archive describes it, with
    # how far it has got; it is no longer on offer.
    assert screen.data["installing"] == "gcompris"
    row = next(r for r in screen.data["modules"] if r["id"] == "gcompris")
    assert (row["job"], row["name"], row["enabled"], row["settings"]) == ("installing", "GCompris",
                                                                          {}, False)
    assert "gcompris" not in [e["id"] for e in screen.data["offered"]]
    assert all(r["job"] is None for r in screen.data["modules"] if r["id"] != "gcompris")

    daemon.update = ("idle", 0.0, "", "installed", "", [])
    screen = panel.poll_modules()
    assert (screen.notice, screen.data["toast"], screen.data["polling"]) == (
        None, words.MODULE_INSTALLED, False)
    assert screen.data["installing"] is None


def test_installs_and_removals_asked_while_a_job_runs_wait_their_turn(panel, daemon,
                                                                       installed):
    daemon.offered = [GCOMPRIS, {**GCOMPRIS, "id": "scratchjr", "name": "ScratchJr"}]
    panel.install_module("gcompris")

    screen = panel.install_module("scratchjr")
    screen = panel.remove_module("hello")

    # Nothing more was asked of the daemon: both wait, and the page says so.
    assert [c for c in daemon.calls if c[0] in ("install_module", "remove_module")] == [
        ("install_module", "gcompris")]
    jobs = {r["id"]: r["job"] for r in screen.data["modules"]}
    assert (jobs["gcompris"], jobs["scratchjr"], jobs["hello"]) == (
        "installing", "to-install", "to-remove")
    assert "scratchjr" not in [e["id"] for e in screen.data["offered"]]

    daemon.update = ("idle", 0.0, "", "installed", "", [])
    screen = panel.poll_modules()
    # The first done is said, and the next waiting starts at once.
    assert screen.data["toast"] == words.MODULE_INSTALLED
    assert ("install_module", "scratchjr") in daemon.calls
    assert screen.data["polling"] and screen.data["installing"] == "scratchjr"
    assert {r["id"]: r["job"] for r in screen.data["modules"]}["hello"] == "to-remove"


def test_a_job_that_waited_starts_even_when_the_one_before_ended_meanwhile(panel, daemon,
                                                                              installed):
    daemon.offered = [GCOMPRIS]
    panel.install_module("gcompris")
    panel.remove_module("hello")
    # The install ends between the removal being queued and the page being
    # drawn again: the page still polls, since a job waits, and the poll
    # starts it.
    daemon.update = ("idle", 0.0, "", "installed", "", [])
    screen = panel.modules()
    assert {r["id"]: r["job"] for r in screen.data["modules"]}["hello"] == "to-remove"
    assert (screen.data["polling"], screen.data["poll"]) == (True, "poll_modules")

    screen = panel.poll_modules()
    assert ("remove_module", "hello") in daemon.calls
    assert screen.data["toast"] == words.MODULE_INSTALLED


def test_a_removal_asked_about_while_a_job_runs_stays_asked(panel, daemon, installed):
    daemon.offered = [GCOMPRIS]
    panel.install_module("gcompris")
    assert panel.ask_remove_module("hello").data["confirm_remove"] == "hello"

    # The polls keep the question, and so does the next job starting.
    assert panel.poll_modules().data["confirm_remove"] == "hello"
    panel.install_module("gcompris")
    daemon.update = ("idle", 0.0, "", "installed", "", [])
    assert panel.poll_modules().data["confirm_remove"] == "hello"
    # Cancel takes it away.
    assert panel.modules().data["confirm_remove"] is None


def test_a_failed_job_says_so_and_what_apt_said(panel, daemon, installed):
    daemon.update = ("idle", 0.0, "", "failed", "E: Unable to locate package", [])

    screen = panel.poll_modules()

    assert (screen.data["toast"], screen.data["failure"]) == (words.MODULE_FAILED,
                                                              "E: Unable to locate package")


def test_removing_asks_first_then_removes(panel, daemon, installed, tmp_path):
    screen = panel.ask_remove_module("hello")
    assert screen.data["confirm_remove"] == "hello"
    assert daemon.calls == []

    screen = panel.remove_module("hello")
    assert ("remove_module", "hello") in daemon.calls
    assert screen.data["update"]["job"] == "removing"
    # Its row shows how far it has got, where its switches and buttons were,
    # and stays once its manifest is gone, until the job ends.
    assert [r["job"] for r in screen.data["modules"] if r["id"] == "hello"] == ["removing"]
    import shutil
    shutil.rmtree(tmp_path / "hello")
    daemon.update = ("removing", 0.8, "kidux-module-hello", "", "", [])
    screen = panel.poll_modules()
    assert [(r["job"], r["name"]) for r in screen.data["modules"] if r["id"] == "hello"] == [
        ("removing", "Hello")]

    daemon.update = ("idle", 0.0, "", "removed", "", [])
    assert panel.poll_modules().data["toast"] == words.MODULE_REMOVED


@pytest.mark.parametrize("method", ["install_module", "remove_module"])
def test_modules_wait_while_children_are_signed_in(panel, daemon, installed, method):
    daemon.signed_in = {"ana"}

    screen = getattr(panel, method)("hello")

    assert (screen.name, screen.notice) == ("panel_modules", words.MODULES_WAIT)
    assert daemon.calls == []


def test_one_job_at_a_time_on_the_modules_page(panel, daemon, installed):
    daemon.update_busy = True

    assert panel.install_module("gcompris").notice == words.UPDATE_BUSY


def test_looking_for_modules_refreshes_the_lists(panel, daemon, installed):
    screen = panel.look_for_modules()

    assert ("check_updates",) in daemon.calls
    assert (screen.name, screen.data["polling"]) == ("panel_modules", True)


def test_a_lost_token_while_installing_closes_the_panel(panel, daemon, installed):
    daemon.token_valid = False

    screen = panel.install_module("gcompris")

    assert (screen.owner, screen.notice) != ("panel", None)
    assert screen.notice == words.PANEL_CLOSED


def test_the_system_page_follows_a_module_job_too(panel, daemon):
    daemon.update = ("installing", 0.3, "kidux-module-hello", "", "", [])

    screen = panel.system()

    assert (screen.data["polling"], screen.data["poll"]) == (True, "poll_updates")


def test_the_recovery_password_is_shown_only_when_asked(panel):
    assert panel.system().data["recovery"] is None
    assert panel.show_recovery().data["recovery"] == "abc123"


def test_changing_the_adult_password_on_the_system_page(panel, daemon):
    wrong = panel.save_adult_password("a guess", "new", "new")
    assert wrong.data["errors"] == {"current_password": vocabulary.WRONG_PASSWORD}
    differ = panel.save_adult_password(ADULT, "new", "old")
    assert differ.data["errors"] == {"adult_password": words.PASSWORDS_DIFFER}
    assert panel.save_adult_password(ADULT, "new", "new").notice == words.SAVED


def test_the_machines_language_keyboard_and_scale(panel, daemon):
    screen = panel.set_language_keyboard("es_ES.UTF-8", "")
    assert ("set_config", {"default_language": "es_ES.UTF-8", "default_keyboard": "es"}) in daemon.calls
    assert (screen.name, screen.language) == ("panel_system", "es_ES.UTF-8")
    assert [layout for layout, _ in screen.data["keyboards"]] == ["es", "latam"]

    screen = panel.set_language_keyboard("es_ES.UTF-8", "latam")
    assert ("set_config", {"default_language": "es_ES.UTF-8", "default_keyboard": "latam"}) in daemon.calls

    screen = panel.set_scale(2.0)
    assert ("set_config", {"display_scale": 2.0}) in daemon.calls
    assert (screen.data["scale"], screen.notice) == (2.0, words.APPLIES_ON_CLOSE)


def test_a_computer_left_alone_locks_and_turns_off_after_minutes_the_adult_sets(panel, daemon):
    # D67: the minutes before a child's session locks, which the panel's own
    # are too, and before the screen turns off.
    screen = panel.system()
    assert (screen.data["idle_lock"], screen.data["screen_off"]) == (5, 10)
    assert screen.data["idle_seconds"] == 300

    screen = panel.set_idle(3, 20)

    assert ("set_config", {"idle_lock_minutes": 3, "screen_off_minutes": 20}) in daemon.calls
    assert (screen.data["idle_lock"], screen.data["screen_off"]) == (3, 20)
    assert screen.notice == words.IDLE_SAVED
    assert screen.data["idle_seconds"] == 180
    assert panel.tab("children").data["idle_seconds"] == 180


def test_the_system_page_says_what_the_updates_are_doing(panel, daemon):
    screen = panel.system()
    assert (screen.data["update"]["job"], screen.data["polling"]) == ("idle", False)

    screen = panel.look_for_updates()
    assert ("check_updates",) in daemon.calls
    assert (screen.data["update"]["job"], screen.data["polling"]) == ("checking", True)

    daemon.update = ("idle", 0.0, "", "checked", "", ["kidux-greeter"])
    screen = panel.poll_updates()
    assert (screen.data["update"]["packages"], screen.data["polling"]) == (["kidux-greeter"], False)

    screen = panel.install_updates()
    assert ("apply_updates",) in daemon.calls
    assert screen.data["update"]["fraction"] == 0.4


def test_updates_wait_until_every_child_has_logged_out(panel, daemon):
    daemon.signed_in.add("tom")

    screen = panel.install_updates()

    assert (screen.name, screen.notice) == ("panel_system", words.UPDATES_WAIT)
    assert ("apply_updates",) not in daemon.calls


def test_one_update_at_a_time(panel, daemon):
    daemon.update_busy = True

    assert panel.look_for_updates().notice == words.UPDATE_BUSY


def test_the_page_keeps_asking_while_the_daemon_restarts_under_an_update(panel, daemon):
    daemon.update_away = True

    screen = panel.poll_updates()

    assert (screen.data["update"]["job"], screen.data["polling"]) == ("away", True)


def test_the_recovery_password_stays_shown_while_the_page_is_redrawn(panel, daemon):
    panel.show_recovery()

    assert panel.poll_updates().data["recovery"] == "abc123"


def test_restart_now_after_an_update_that_needs_it(panel, daemon):
    daemon.update = ("idle", 0.0, "", "restart-needed", "", [])

    screen = panel.restart_now()

    assert ("reboot",) in daemon.calls
    assert screen.name == "turning_off"


def test_closing_locks_the_token_and_returns_to_the_children(panel, daemon):
    screen = panel.close()

    assert ("lock_panel", "token") in daemon.calls
    assert screen.name == "choose"


def test_escape_closes_without_saving(panel, daemon):
    assert panel.back("panel_children").name == "choose"
    assert not [c for c in daemon.calls if c[0] == "set_profile"]


def test_back_from_a_modules_settings_is_the_modules_page(panel):
    assert panel.back("panel_module_settings").name == "panel_modules"


def test_a_lost_token_closes_the_panel_and_says_so(panel, daemon):
    daemon.token_valid = False

    screen = panel.save_child({**ANA_AS_SHOWN, "display_name": "Anita"})

    assert (screen.name, screen.notice) == ("choose", words.PANEL_CLOSED)


def test_the_panel_opens_from_the_lock_screen_and_returns_to_it(daemon):
    lock = Lock(daemon, "ana")
    lock.start()
    lock.tap_adult()
    lock.submit_adult_password(ADULT)

    screen = lock.adult_choice("panel")
    assert (screen.name, screen.owner) == ("panel_children", "panel")
    assert lock.panel.close().name == "locked"


# --- no dead ends --------------------------------------------------------------


def check(screen, actions):
    if screen.owner in ("wizard", "panel"):
        assert screen.name in actions, f"{screen.name} is not a known screen"
        if screen.name not in FINAL and screen.name != "restarting":
            assert actions[screen.name], f"{screen.name} has no way forward"


def test_every_wizard_screen_has_a_way_forward(fresh):
    signin = SignIn(fresh, FakeGreetd())
    screens = [signin.start()]
    w = signin.wizard
    screens += [w.choose_language("es_ES.UTF-8"), w.back("wiz_keyboard"),
                w.choose_language("en_US.UTF-8"), w.choose_keyboard("us")]
    fresh.settings["language_chosen"] = True
    screens += [signin.start()]
    w = signin.wizard
    screens += [w.submit_adult_password("", ""), w.submit_adult_password(ADULT, ADULT),
                w.set_statistics(True),
                w.add_child({"display_name": ""}),
                w.add_child({"display_name": "Ana", "password": "x", "again": "x"})]
    for screen in screens:
        check(screen, WIZARD_ACTIONS)
    assert {"wiz_language", "wiz_keyboard", "restarting", "wiz_password", "wiz_statistics",
            "wiz_child", "wiz_done"} <= set(names(screens))


def test_every_panel_screen_has_a_way_forward(panel, daemon, with_settings):
    daemon.offered = [GCOMPRIS]
    screens = [panel.children(), panel.select("tom"), panel.ask_remove(), panel.new_child(),
               panel.tab("modules"), panel.set_module("ana", "nothing", True),
               panel.module_settings("hello"),
               panel.ask_remove_module("hello"), panel.install_module("gcompris"),
               panel.poll_modules(), panel.remove_module("hello"), panel.look_for_modules(),
               panel.tab("system"), panel.show_recovery(),
               panel.look_for_updates(), panel.restart_now(), panel.advanced(), panel.power(),
               panel.tab("network"), panel.ask_wifi_password("Neighbours"),
               panel.ask_forget_wifi("Home")]
    for screen in screens:
        check(screen, PANEL_ACTIONS)
    assert set(names(screens)) == set(PANEL_ACTIONS)


def test_every_screen_has_a_drawing():
    # view.py needs GTK and a display, which the build does not have; its
    # source says which screens it can draw, and every screen a state machine
    # can answer with must be one of them.
    import re
    from pathlib import Path

    from kidux_greeter.flow import LOCK_ACTIONS, SIGN_IN_ACTIONS

    source = (Path(__file__).resolve().parents[1] / "kidux_greeter" / "view.py").read_text()
    drawn = set(re.findall(r"^\s+(?:def )?_draw_(\w+)", source, re.MULTILINE))
    screens = set(SIGN_IN_ACTIONS) | set(LOCK_ACTIONS) | set(WIZARD_ACTIONS) | set(PANEL_ACTIONS)
    assert screens - drawn == set()


def test_every_action_a_screen_offers_exists():
    from kidux_greeter.panel import Panel, Wizard

    for actions, cls in ((WIZARD_ACTIONS, Wizard), (PANEL_ACTIONS, Panel)):
        for screen, methods in actions.items():
            for method in methods:
                assert hasattr(cls, method), f"{cls.__name__}.{method} for {screen}"


def test_the_advanced_page_has_the_usage_statistics_switch(panel, daemon):
    screen = panel.advanced()
    assert screen.data["statistics"] is True

    screen = panel.set_statistics(False)
    assert (screen.name, screen.notice) == ("panel_advanced", words.SAVED)
    assert ("set_config", {"apt_statistics": False}) in daemon.calls
    assert screen.data["statistics"] is False


def test_the_system_page_leads_to_the_advanced_settings(panel):
    panel.tab("system")
    screen = panel.advanced()

    assert (screen.name, screen.data["chromium_flags"]) == ("panel_advanced", "")


def test_the_advanced_page_shows_the_flags_as_the_daemon_has_them_now(panel, daemon):
    daemon.settings["chromium_flags"] = ["--disable-gpu"]

    assert panel.advanced().data["chromium_flags"] == "--disable-gpu"


def test_the_advanced_page_shows_the_pointer_s_steps_as_the_daemon_has_them(panel, daemon):
    daemon.settings.update(pointer_speed=1, scroll_speed=-2)

    screen = panel.advanced()

    assert (screen.data["pointer_speed"], screen.data["scroll_speed"]) == (1, -2)


def test_the_pointer_s_speed_and_the_touchpad_s_scroll_are_saved_when_chosen(panel, daemon):
    screen = panel.set_pointer("scroll_speed", -1)

    assert ("set_config", {"scroll_speed": -1}) in daemon.calls
    assert (screen.name, screen.notice) == ("panel_advanced", words.APPLIES_NEXT_SIGN_IN)
    assert screen.data["scroll_speed"] == -1
    assert panel.set_pointer("display_scale", 2).notice == words.NOT_SAVED
    assert ("set_config", {"display_scale": 2}) not in daemon.calls
    assert len(words.SPEED_STEPS) == 5


def test_chromium_s_options_are_saved_one_a_line(panel, daemon):
    screen = panel.save_chromium_flags("--disable-gpu-compositing\n\n  --use-gl=angle \n")

    assert ("set_config", {"chromium_flags": ["--disable-gpu-compositing", "--use-gl=angle"]}
            ) in daemon.calls
    assert (screen.name, screen.notice) == ("panel_advanced", words.SAVED)
    assert screen.data["chromium_flags"] == "--disable-gpu-compositing\n--use-gl=angle"


def test_an_option_not_accepted_keeps_what_was_typed(panel, daemon):
    screen = panel.save_chromium_flags("disable-gpu")

    assert (screen.name, screen.notice) == ("panel_advanced", words.OPTION_NOT_ACCEPTED)
    assert screen.data["chromium_flags"] == "disable-gpu"
    assert not any(call[0] == "set_config" for call in daemon.calls)


def test_windows_are_switched_on_for_a_child_from_the_form(panel, daemon):
    screen = panel.save_child({"windows": True})

    assert ("set_profile", "ana", {"windows": True}) in daemon.calls
    assert screen.notice == words.SAVED


def test_a_new_child_with_windows_has_them_from_the_start(panel, daemon):
    panel.new_child()
    panel.add_child({"display_name": "Lu", "password": "pw", "again": "pw",
                     "access": "daily:60", "windows": True})

    assert any(call[0] == "set_profile" and call[2] == {"windows": True}
               for call in daemon.calls)


@pytest.mark.parametrize("scale, label", [
    (1.0, "100 %"), (2.0, "200 %"), (3.0, "300 %"),
    (1.25, "125 %*"), (1.75, "175 %*"), (2.5, "250 %*"),
])
def test_a_size_that_is_not_whole_is_marked(scale, label):
    # D59: an X11 program is soft at a size that is not a whole multiple.
    from kidux_greeter.panel import size_label
    assert size_label(scale, "*") == label


# --- the Network page (D62) ------------------------------------------------------------


def test_the_network_page_looks_again_when_it_opens_and_asks_until_done(panel, daemon):
    screen = panel.tab("network")
    assert screen.name == "panel_network" and ("check_network",) in daemon.calls
    assert screen.data["polling"] and screen.data["poll"] == "poll_network"
    assert [n["ssid"] for n in screen.data["networks"]] == ["Home", "Neighbours"]
    daemon.finish_network_job()
    screen = panel.poll_network()
    assert not screen.data["polling"] and screen.data["summary"]["router"] == "answers"
    assert screen.notice is None
    assert "poll_network" in PANEL_ACTIONS["panel_network"]


def test_a_secured_network_asks_its_password_in_place_and_joins(panel, daemon):
    panel.tab("network")
    daemon.finish_network_job()
    screen = panel.ask_wifi_password("Neighbours")
    assert screen.data["asking"] == "Neighbours"
    screen = panel.connect_wifi("Neighbours", "kidux password 1")
    assert ("connect_wifi", "Neighbours", "kidux password 1") in daemon.calls
    assert screen.data["polling"]
    daemon.finish_network_job("connected")
    assert panel.poll_network().notice == words.WIFI_CONNECTED


@pytest.mark.parametrize("password", ["short", "ñ" * 32])
def test_a_password_that_does_not_fit_is_marked_without_asking_the_daemon(panel, daemon,
                                                                          password):
    panel.tab("network")
    screen = panel.connect_wifi("Neighbours", password)
    assert screen.data["errors"] == {"password": words.WIFI_PASSWORD_LENGTH}
    assert screen.data["asking"] == "Neighbours"
    assert not [c for c in daemon.calls if c[0] == "connect_wifi"]


def test_a_password_with_an_accent_fits_as_networkmanager_counts_it(panel, daemon):
    panel.tab("network")
    panel.connect_wifi("Neighbours", "contraseña de casa")
    assert ("connect_wifi", "Neighbours", "contraseña de casa") in daemon.calls


def test_a_job_over_before_the_page_reads_again_still_says_how_it_ended(panel, daemon):
    panel.tab("network")
    daemon.finish_network_job()
    daemon.net_over_at_once = ("failed", "Read-only file system")
    screen = panel.connect_wifi("Neighbours", "kidux password 1")
    assert screen.notice == words.WIFI_NOT_CONNECTED and not screen.data["polling"]
    assert screen.data["failure"] == "Read-only file system"
    daemon.net_over_at_once = ("forgotten", "")
    assert panel.forget_wifi("Home").notice == words.WIFI_FORGOTTEN


def test_a_wrong_password_asks_for_it_again(panel, daemon):
    panel.tab("network")
    panel.connect_wifi("Neighbours", "not the password")
    daemon.finish_network_job("failed", "wrong_password")
    screen = panel.poll_network()
    assert screen.notice == words.WIFI_WRONG_PASSWORD
    assert screen.data["asking"] == "Neighbours" and screen.data["errors"] == {}


def test_another_failure_says_what_networkmanager_said(panel, daemon):
    panel.tab("network")
    panel.connect_wifi("Home", "")
    daemon.finish_network_job("failed", "The Wi-Fi network could not be found")
    screen = panel.poll_network()
    assert screen.notice == words.WIFI_NOT_CONNECTED
    assert screen.data["failure"] == "The Wi-Fi network could not be found"


def test_forget_asks_once_then_forgets(panel, daemon):
    panel.tab("network")
    daemon.finish_network_job()
    assert panel.ask_forget_wifi("Home").data["confirm_forget"] == "Home"
    assert not [c for c in daemon.calls if c[0] == "forget_wifi"]
    panel.forget_wifi("Home")
    assert ("forget_wifi", "Home") in daemon.calls
    daemon.finish_network_job("forgotten")
    assert panel.poll_network().notice == words.WIFI_FORGOTTEN


def test_a_busy_network_says_so(panel, daemon):
    daemon.net_busy = True
    screen = panel.tab("network")
    assert screen.name == "panel_network"
    assert panel.connect_wifi("Home", "").notice == words.NETWORK_BUSY


def test_a_lost_token_on_the_network_page_closes_the_panel(panel, daemon):
    daemon.token_valid = False
    screen = panel.tab("network")
    assert screen.owner != "panel" and screen.notice == words.PANEL_CLOSED


# --- the versions ------------------------------------------------------------------


def test_the_system_page_says_kidux_s_version_and_each_part_s(panel, daemon):
    daemon.installed = {"kidux-base": "0.2.3", "kidux-daemon": "0.3.25",
                        "kidux-launcher": "0.3.4", "python3-kidux": "0.1.35",
                        "kidux-module-hello": "0.1.5"}
    screen = panel.tab("system")
    assert screen.data["version"] == "0.2.3"
    assert screen.data["parts"] == [(words.PART_SERVICE, "0.3.25"),
                                    (words.PART_CHILD_SCREEN, "0.3.4"),
                                    (words.PART_COMMON, "0.1.35")]


def test_without_kidux_base_the_daemon_s_version_is_said(panel, daemon):
    daemon.installed = {}
    screen = panel.tab("system")
    assert screen.data["version"] == "0.3.0" and screen.data["parts"] == []


# --- settings the screen takes at its start ---------------------------------------


def test_a_new_size_on_the_sign_in_screen_restarts_it_when_the_panel_closes(panel, daemon):
    screen = panel.set_scale(2.0)
    assert screen.notice == words.APPLIES_ON_CLOSE
    assert not panel.exit_requested
    screen = panel.close()
    assert screen.name == "restarting" and panel.exit_requested


def test_a_panel_closed_without_such_a_change_does_not_restart(panel, daemon):
    screen = panel.close()
    assert screen.name != "restarting" and not panel.exit_requested


def test_on_the_lock_screen_a_new_size_waits_for_the_next_start(panel, daemon):
    # The lock screen must not restart over a child's session.
    from kidux_greeter.panel import Panel
    token = panel._token
    locked = Panel(daemon, token, daemon.config(), on_close=lambda: panel.close(),
                   lock_mode=True)
    screen = locked.set_scale(2.0)
    assert screen.notice == words.APPLIES_NEXT_START
    assert locked.close().name != "restarting" and not locked.exit_requested


# --- a module's settings (D90) ---------------------------------------------------


@pytest.fixture
def with_settings(installed):
    """Hello declares a switch and a secret."""
    manifest = installed / "hello" / "module.toml"
    manifest.write_text(manifest.read_text() + """
[[settings]]
key = "type_in"
kind = "switch"
label = "Type it in for me"
description = "A button types the listing."
default = true

[[settings]]
key = "password"
kind = "secret"
label = "Password"
description = "What it does."
""")
    return installed


def test_a_module_with_settings_says_so_in_its_row(panel, daemon, with_settings):
    rows = {row["id"]: row for row in panel.tab("modules").data["modules"]}

    assert rows["hello"]["settings"] is True and rows["paint"]["settings"] is False


def test_the_settings_page_has_every_child_s_values_and_never_a_secret(panel, daemon,
                                                                         with_settings):
    daemon.settings = {("ana", "hello"): {"type_in": False, "password": "hunter2"}}

    screen = panel.module_settings("hello")

    assert screen.name == "panel_module_settings"
    assert [s["key"] for s in screen.data["settings"]] == ["type_in", "password"]
    assert screen.data["settings"][0]["description"] == "A button types the listing."
    assert screen.data["values"]["ana"] == {"type_in": False}
    assert screen.data["secrets"]["ana"] == ["password"]
    assert "hunter2" not in repr(screen.data)


def test_a_setting_is_saved_when_changed_and_a_wrong_one_said(panel, daemon, with_settings):
    screen = panel.set_module_setting("hello", "ana", "type_in", False)
    assert ("set_module_setting", "ana", "hello", "type_in", False) in daemon.calls
    assert (screen.name, screen.notice) == ("panel_module_settings", words.SAVED)

    screen = panel.set_module_setting("hello", "ana", "type_in", "no")
    assert screen.notice == words.NOT_SAVED


def test_a_module_without_settings_has_no_settings_page(panel, daemon, with_settings):
    assert panel.module_settings("paint").name == "panel_modules"



# --- suspend (D119) ------------------------------------------------------------------


def test_the_system_page_leads_to_suspending(panel):
    panel.tab("system")
    screen = panel.power()

    assert screen.name == "panel_power"
    assert (screen.data["lid"], screen.data["idle"], screen.data["idle_minutes"]) == \
        ("sleep", "sleep", 20)
    assert screen.data["lids"] == ["sleep", "nothing"]
    assert screen.data["idles"] == ["sleep", "screen_off_only"]
    assert screen.data["warning"] is None


def test_a_hibernating_choice_shows_as_suspend(panel, daemon):
    daemon.settings.update(lid_action="sleep_then_hibernate", idle_action="sleep_then_hibernate")

    screen = panel.power()

    assert (screen.data["lid"], screen.data["idle"]) == ("sleep", "sleep")


def test_a_computer_that_cannot_suspend_says_so(panel, daemon):
    daemon.settings.update(can_sleep=False)

    assert panel.power().data["warning"] == words.CANNOT_SLEEP


def test_the_lid_s_setting_is_saved_when_chosen(panel, daemon):
    screen = panel.set_lid("nothing")

    assert ("set_config", {"lid_action": "nothing"}) in daemon.calls
    assert (screen.name, screen.notice, screen.data["lid"]) == \
        ("panel_power", words.SAVED, "nothing")
    assert panel.set_lid("sleep_then_hibernate").notice == words.NOT_SAVED


def test_the_action_when_idle_is_saved_with_its_minutes(panel, daemon):
    screen = panel.set_idle_sleep("screen_off_only", 45)

    assert ("set_config", {"idle_action": "screen_off_only", "idle_sleep_minutes": 45}
            ) in daemon.calls
    assert (screen.notice, screen.data["idle"], screen.data["idle_minutes"]) == \
        (words.APPLIES_NEXT_START, "screen_off_only", 45)
    assert panel.set_idle_sleep("nothing", 45).notice == words.NOT_SAVED
