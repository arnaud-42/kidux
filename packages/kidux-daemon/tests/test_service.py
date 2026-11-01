"""The daemon's behaviour through `Service.dispatch`, without a bus.

Most of these tests try to get past a check. Each check in gate.py exists
because of something a child, a bug or a careless call could otherwise do,
and a check nobody has tried to break has not been shown to hold.
"""

import json

import pytest

from kidux import paths, state
from kidux import pointer as kidux_pointer
from kiduxd.config import Config
from kiduxd import gate as gate_module
from kiduxd.accounts import FakeAccounts
from kiduxd.adults import AdultPassword
from kiduxd.errors import (
    AccessDenied,
    Failed,
    InvalidArgument,
    NoSuchChild,
    NotAuthorized,
    NotUnlocked,
    SessionActive,
    SignInNotSet,
    WrongPassword,
)
from kiduxd.gate import Caller, Gate
from kiduxd.logind import FakeLogind, SessionInfo
from kiduxd.children import Children
from kiduxd import power
from kiduxd.service import Service
from kiduxd.tokens import Tokens

from conftest import LANGUAGES

ADMIN = Caller(":1.10", 1000)
GREETER = Caller(":1.11", 110)
ANA = Caller(":1.20", 3001)
LUIS = Caller(":1.21", 3002)
ROOT = Caller(":1.30", 0)

ADULT_PASSWORD = "a family secret"


class FakeAuthority:
    """polkit as the shipped rules describe it (50-kidux.rules)."""

    def __init__(self, accounts: FakeAccounts) -> None:
        self.accounts = accounts
        self.refuse_everything = False

    def check(self, unique_name: str, action_id: str) -> bool:
        if self.refuse_everything:
            return False
        uids = {c.unique_name: c.uid for c in (ADMIN, GREETER, ANA, LUIS, ROOT)}
        uid = uids.get(unique_name, ADMIN.uid)
        name = self.accounts.username_of(uid)
        if self.accounts.in_group(name, paths.ADMIN_GROUP):
            return True
        if name == paths.GREETER_USER:
            return True
        if self.accounts.in_group(name, paths.CHILDREN_GROUP):
            return action_id == gate_module.SELF
        return False


@pytest.fixture
def machine(fast_hasher):
    accounts = FakeAccounts()
    accounts.add_user("admin", 1000, (paths.ADMIN_GROUP, "sudo"))
    accounts.add_user(paths.GREETER_USER, 110)
    accounts.add_user("ana", 3001, (paths.CHILDREN_GROUP, "video"))
    accounts.add_user("luis", 3002, (paths.CHILDREN_GROUP, "video"))
    for child in ("ana", "luis"):
        state.write(paths.child_profile(child), {"display_name": child.title(),
                                                 "language": "es_ES.UTF-8",
                                                 "keyboard": "es", "avatar": "fox"}, "profile")

    logind = FakeLogind()
    authority = FakeAuthority(accounts)
    audit_log = []
    emitted = []

    service = Service(
        gate=Gate(authority, accounts),
        accounts=accounts,
        logind=logind,
        adults=AdultPassword(fast_hasher),
        tokens=Tokens(900),
        children=Children(accounts, logind, LANGUAGES),
        emit=lambda *signal: emitted.append(signal),
        audit=lambda action, outcome, **fields: audit_log.append((action, outcome, fields)),
    )
    service.adults.set(ADULT_PASSWORD)

    class Machine:
        pass

    m = Machine()
    m.service, m.accounts, m.logind, m.authority = service, accounts, logind, authority
    m.audit, m.emitted = audit_log, emitted
    m.call = lambda caller, interface, method, *args: service.dispatch(
        caller, interface, method, *args
    )
    m.unlock = lambda caller=ADMIN: service.dispatch(caller, "Parental1", "Unlock", ADULT_PASSWORD)
    return m


# --- polkit ------------------------------------------------------------------


def test_anyone_may_ping_and_turn_the_computer_off(machine):
    machine.authority.refuse_everything = True

    assert machine.call(ANA, "Daemon1", "Ping")
    machine.call(ANA, "System1", "Shutdown")

    assert machine.logind.powered_off


def test_a_child_may_not_list_the_children(machine):
    # Only the sign-in screen and administrators see who else uses the machine.
    with pytest.raises(AccessDenied):
        machine.call(ANA, "Children1", "List")


def test_a_child_may_not_unlock_the_panel_even_with_the_password(machine):
    # The adult password is only ever typed on a trusted screen (D6). A child's
    # session asking to unlock is exactly the fake prompt that rule is about.
    with pytest.raises(AccessDenied):
        machine.call(ANA, "Parental1", "Unlock", ADULT_PASSWORD)


def test_root_needs_no_polkit(machine):
    machine.authority.refuse_everything = True

    assert machine.call(ROOT, "Children1", "List")


def test_an_unknown_method_is_refused(machine):
    with pytest.raises(NotAuthorized):
        machine.call(ADMIN, "Children1", "DropTables")


def test_every_exported_method_has_a_polkit_decision():
    # A method added to the XML and forgotten here would be refused, which is
    # safe, but it would also be a bug nobody noticed until a screen broke.
    from gi.repository import Gio
    from kiduxd.bus import introspection_xml, short_interface

    node = Gio.DBusNodeInfo.new_for_xml(introspection_xml())
    exported = {
        (short_interface(interface.name), method.name)
        for interface in node.interfaces
        for method in interface.methods
    }
    assert exported == set(gate_module.ACTIONS)


# --- what polkit cannot see: scope -------------------------------------------


def test_a_child_may_ask_about_themselves(machine):
    assert machine.call(ANA, "Modules1", "List", "ana") == []


def test_a_child_may_not_ask_about_a_sibling(machine):
    with pytest.raises(NotAuthorized):
        machine.call(ANA, "Modules1", "List", "luis")


def test_the_greeter_may_ask_about_any_child(machine):
    assert machine.call(GREETER, "Modules1", "List", "luis") == []


# --- modules (phase-3-plan.md, step 3.1) ---------------------------------------


def install_module(module_id: str) -> None:
    directory = paths.MODULES_DIR / module_id
    directory.mkdir(parents=True)
    (directory / "module.toml").write_text(
        f'id = "{module_id}"\nname = "{module_id.title()}"\n'
        f'launch = {{ exec = "/usr/libexec/kidux-module-{module_id}" }}\n')


def enabled_in_file(username: str) -> list:
    return state.read(paths.child_modules(username), "modules")["enabled"]


def test_every_installed_module_is_listed_off_until_an_adult_enables_it(machine):
    install_module("hello")
    install_module("abc")

    assert machine.call(ANA, "Modules1", "List", "ana") == [
        {"id": "abc", "enabled": False}, {"id": "hello", "enabled": False}]


def test_an_adult_enables_a_module_for_one_child(machine):
    install_module("hello")
    token = machine.unlock()

    machine.call(ADMIN, "Modules1", "SetEnabled", token, "ana", "hello", True)

    assert machine.call(ANA, "Modules1", "List", "ana") == [{"id": "hello", "enabled": True}]
    assert machine.call(LUIS, "Modules1", "List", "luis") == [{"id": "hello", "enabled": False}]
    assert ("module enabled", "ok", {"caller": "admin", "child": "ana", "module": "hello"}) \
        in machine.audit
    assert ("Modules1", "ModulesChanged", "(s)", ("ana",)) in machine.emitted
    assert enabled_in_file("ana") == ["hello"]


def test_and_disables_it_again(machine):
    install_module("hello")
    token = machine.unlock()
    machine.call(ADMIN, "Modules1", "SetEnabled", token, "ana", "hello", True)

    machine.call(ADMIN, "Modules1", "SetEnabled", token, "ana", "hello", False)

    assert machine.call(ANA, "Modules1", "List", "ana") == [{"id": "hello", "enabled": False}]
    assert ("module disabled", "ok", {"caller": "admin", "child": "ana", "module": "hello"}) \
        in machine.audit


def test_setting_what_is_already_set_is_not_an_error_and_changes_nothing(machine):
    install_module("hello")
    token = machine.unlock()

    machine.call(ADMIN, "Modules1", "SetEnabled", token, "ana", "hello", False)

    assert not paths.child_modules("ana").exists()
    assert not [a for a in machine.audit if a[0].startswith("module")]
    assert not [e for e in machine.emitted if e[1] == "ModulesChanged"]


def test_a_module_that_is_not_installed_cannot_be_enabled(machine):
    install_module("hello")
    token = machine.unlock()

    for module_id in ("nothing", "../hello", ""):
        with pytest.raises(InvalidArgument):
            machine.call(ADMIN, "Modules1", "SetEnabled", token, "ana", module_id, True)
    assert not paths.child_modules("ana").exists()


def test_a_module_whose_package_is_gone_is_not_listed_and_stays_in_the_file(machine):
    install_module("hello")
    state.write(paths.child_modules("ana"), {"enabled": ["gone", "hello"]}, "modules")
    token = machine.unlock()

    assert machine.call(ANA, "Modules1", "List", "ana") == [{"id": "hello", "enabled": True}]
    machine.call(ADMIN, "Modules1", "SetEnabled", token, "ana", "hello", False)
    # Putting the package back restores the switch.
    assert enabled_in_file("ana") == ["gone"]


def test_switching_modules_takes_the_token_and_a_child(machine):
    install_module("hello")
    token = machine.unlock()

    with pytest.raises(NotUnlocked):
        machine.call(ADMIN, "Modules1", "SetEnabled", "not a token", "ana", "hello", True)
    with pytest.raises(NoSuchChild):
        machine.call(ADMIN, "Modules1", "SetEnabled", token, "admin", "hello", True)


def test_a_child_may_not_switch_modules_for_themselves_or_a_sibling(machine):
    install_module("hello")

    for username in ("ana", "luis"):
        with pytest.raises(AccessDenied):
            machine.call(ANA, "Modules1", "SetEnabled", "", username, "hello", True)


# --- module settings (D90) ----------------------------------------------------

SETTINGS = """
[[settings]]
key = "type_in"
kind = "switch"
label = "Type it in for me"
description = "What it does."
default = true

[[settings]]
key = "speed"
kind = "integer"
label = "Speed"
description = "What it does."
default = 3
min = 1
max = 5

[[settings]]
key = "password"
kind = "secret"
label = "Password"
description = "What it does."
"""


def install_module_with_settings(module_id: str = "basic") -> None:
    install_module(module_id)
    with (paths.MODULES_DIR / module_id / "module.toml").open("a") as manifest:
        manifest.write(SETTINGS)


def test_a_module_s_settings_are_its_defaults_until_an_adult_sets_them(machine):
    install_module_with_settings()
    token = machine.unlock()

    assert machine.call(ADMIN, "Modules1", "Settings", token, "ana", "basic") == (
        {"type_in": True, "speed": 3}, [])


def test_an_adult_sets_a_module_s_setting_for_one_child(machine):
    install_module_with_settings()
    token = machine.unlock()

    machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "basic", "type_in", False)
    machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "basic", "speed", 5)

    assert machine.call(ADMIN, "Modules1", "Settings", token, "ana", "basic")[0] == {
        "type_in": False, "speed": 5}
    assert machine.call(ADMIN, "Modules1", "Settings", token, "luis", "basic")[0] == {
        "type_in": True, "speed": 3}
    assert ("module setting", "ok") in [entry[:2] for entry in machine.audit]


def test_a_value_not_of_the_setting_s_kind_or_limits_is_refused(machine):
    install_module_with_settings()
    token = machine.unlock()

    for key, value in (("type_in", 1), ("speed", 9), ("speed", "3"), ("nothing", True)):
        with pytest.raises(InvalidArgument):
            machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "basic", key, value)
    with pytest.raises(InvalidArgument):
        machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "absent", "speed", 2)


def test_a_secret_is_never_read_back_and_never_reaches_the_child(machine):
    install_module_with_settings()
    token = machine.unlock()

    machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "basic", "password", "hunter2")

    values, secrets = machine.call(ADMIN, "Modules1", "Settings", token, "ana", "basic")
    assert "password" not in values and secrets == ["password"]
    assert "password" not in machine.call(ANA, "Modules1", "MySettings", "basic")
    path = paths.child_module_settings("ana")
    assert path.stat().st_mode & 0o077 == 0
    machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "basic", "password", "")
    assert machine.call(ADMIN, "Modules1", "Settings", token, "ana", "basic")[1] == []


def test_a_child_reads_their_own_settings_and_sets_none(machine):
    install_module_with_settings()
    token = machine.unlock()
    machine.call(ADMIN, "Modules1", "SetSetting", token, "luis", "basic", "type_in", False)

    assert machine.call(ANA, "Modules1", "MySettings", "basic") == {"type_in": True, "speed": 3}
    with pytest.raises(AccessDenied):
        machine.call(ANA, "Modules1", "SetSetting", "", "ana", "basic", "type_in", False)
    with pytest.raises(AccessDenied):
        machine.call(ANA, "Modules1", "Settings", "", "ana", "basic")


def test_settings_need_the_token(machine):
    install_module_with_settings()
    machine.unlock()

    with pytest.raises(NotUnlocked):
        machine.call(ADMIN, "Modules1", "SetSetting", "not a token", "ana", "basic", "type_in",
                     False)


SIGN_IN = """
hosts = ["example.org"]

[[settings]]
key = "email"
kind = "text"
label = "Email"
description = "The account's email address."

[[settings]]
key = "password"
kind = "secret"
label = "Password"
description = "The account's password."

[sign_in]
url = "https://example.org/auth/login"
body = { username = "{email}", password = "{password}" }
cookies = ["site.sess"]
"""


def install_site():
    directory = paths.MODULES_DIR / "site"
    directory.mkdir(parents=True)
    (directory / "module.toml").write_text(
        'id = "site"\nname = "Site"\nlaunch = { web = "https://example.org/" }\n' + SIGN_IN)


def test_a_child_is_signed_in_with_the_account_an_adult_gave_and_gets_only_cookies(machine):
    install_site()
    token = machine.unlock()
    machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "site", "email", "ana@example.org")
    machine.call(ADMIN, "Modules1", "SetSetting", token, "ana", "site", "password", "hunter2")
    sent = []
    cookie = {"name": "site.sess", "value": "abc", "domain": "example.org", "path": "/",
              "secure": True, "httpOnly": True, "sameSite": "None"}
    machine.service.sign_in_request = lambda url, body, wanted: sent.append(
        (url, body, wanted)) or [cookie]

    # The website is asked in a thread of the bus layer's: the daemon goes on
    # answering everyone else meanwhile.
    later = machine.call(ANA, "Modules1", "SignIn", "site")
    assert sent == []
    assert later.work() == [cookie]
    assert sent == [("https://example.org/auth/login",
                     {"username": "ana@example.org", "password": "hunter2"}, ("site.sess",))]
    assert "hunter2" not in repr(machine.audit)


def test_no_account_set_is_said_and_nothing_is_sent(machine):
    install_site()
    machine.service.sign_in_request = lambda *args: pytest.fail("it sent something")

    with pytest.raises(SignInNotSet):
        machine.call(ANA, "Modules1", "SignIn", "site")


def test_only_a_child_s_own_session_signs_in(machine):
    install_site()
    with pytest.raises(NotAuthorized):
        machine.call(ADMIN, "Modules1", "SignIn", "site")


def test_the_request_hands_back_only_the_named_cookies_and_says_why_it_failed():
    import io
    import urllib.error

    from kiduxd import signin
    from kiduxd.errors import SignInRefused, SignInUnreachable

    class Answer(io.BytesIO):
        def __init__(self, cookies):
            super().__init__(b"{}")
            self.headers = type("H", (), {"get_all": lambda _self, name: cookies})()

    def site(cookies):
        return lambda request, timeout: Answer(cookies)

    got = signin.request("https://example.org/auth", {"a": "b"}, ("site.sess",), opener=site([
        "site.sess=abc; path=/; samesite=none; secure; httponly", "tracker=1; path=/"]))
    assert got == [{"name": "site.sess", "value": "abc", "domain": "example.org", "path": "/",
                    "secure": True, "httpOnly": True, "sameSite": "None"}]

    def refused(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "no", {}, None)

    def away(request, timeout):
        raise urllib.error.URLError("no route")

    with pytest.raises(SignInRefused):
        signin.request("https://example.org/auth", {}, ("site.sess",), opener=refused)
    with pytest.raises(SignInUnreachable):
        signin.request("https://example.org/auth", {}, ("site.sess",), opener=away)
    with pytest.raises(SignInUnreachable):
        signin.request("https://example.org/auth", {}, ("site.sess",), opener=site([]))


# --- tokens and the adult password -------------------------------------------


def test_unlock_with_the_wrong_password_is_refused_and_audited(machine):
    with pytest.raises(WrongPassword):
        machine.call(ADMIN, "Parental1", "Unlock", "a guess")

    assert ("unlock", "denied", {"caller": "admin"}) in machine.audit


def test_a_wrong_password_is_never_written_down(machine):
    with pytest.raises(WrongPassword):
        machine.call(ADMIN, "Parental1", "Unlock", "hunter2")

    assert "hunter2" not in json.dumps(machine.audit)


def test_changes_need_a_token(machine):
    with pytest.raises(NotUnlocked):
        machine.call(ADMIN, "Children1", "SetChildPassword", "", "ana", "new")


def test_a_token_from_another_connection_is_refused(machine):
    token = machine.unlock(ADMIN)
    other_connection = Caller(":1.99", ADMIN.uid)

    with pytest.raises(NotUnlocked):
        machine.call(other_connection, "Children1", "SetChildPassword", token, "ana", "new")


def test_the_panel_closing_kills_its_token(machine):
    token = machine.unlock(ADMIN)
    machine.service.connection_closed(ADMIN.unique_name)

    with pytest.raises(NotUnlocked):
        machine.call(ADMIN, "Children1", "SetChildPassword", token, "ana", "new")


def test_the_first_password_needs_no_token(fast_hasher, machine):
    # A machine that has never been set up has no password to unlock with.
    paths.ADULTS_FILE.unlink()

    machine.call(GREETER, "Parental1", "SetPassword", "", "the first one")

    assert machine.service.adults.verify("the first one")


def test_changing_the_password_needs_a_token(machine):
    with pytest.raises(NotUnlocked):
        machine.call(ADMIN, "Parental1", "SetPassword", "", "taken over")

    assert machine.service.adults.verify(ADULT_PASSWORD)


# --- which accounts may be managed --------------------------------------------


@pytest.mark.parametrize("target", ["admin", paths.GREETER_USER, "root", "nobody-here"])
def test_only_children_are_ever_managed(machine, target):
    # Whatever the token says: this is what stops an unlocked panel, or a bug
    # in one, from deleting the account that owns the machine.
    token = machine.unlock()

    for method, args in (
        ("Delete", (target, False)),
        ("SetChildPassword", (target, "x")),
        ("SetProfile", (target, {"display_name": "x"})),
    ):
        with pytest.raises(NoSuchChild):
            machine.call(ADMIN, "Children1", method, token, *args)

    assert machine.accounts.exists("admin")


# --- creating and deleting children ------------------------------------------


def create(machine, token, username="marta", **overrides):
    arguments = {
        "display_name": "Marta",
        "language": "es_ES.UTF-8",
        "keyboard": "es",
        "avatar": "owl",
        "password": "marta's password",
    }
    arguments.update(overrides)
    machine.call(
        ADMIN, "Children1", "Create", token, username,
        arguments["display_name"], arguments["language"], arguments["keyboard"],
        arguments["avatar"], arguments["password"],
    )


def test_create_makes_an_account_and_its_files(machine):
    token = machine.unlock()
    create(machine, token)

    assert machine.accounts.in_group("marta", paths.CHILDREN_GROUP)
    assert machine.accounts.in_group("marta", "video")
    assert machine.accounts.users["marta"]["password"] == "marta's password"
    assert state.read(paths.child_profile("marta"), "profile")["avatar"] == "owl"
    # Nothing is allowed until an adult says how much.
    assert state.read(paths.child_access("marta"), "access")["mode"] == "manual"
    assert ("Children1", "ChildrenChanged", "()", ()) in machine.emitted


def test_create_shows_up_in_the_list(machine):
    token = machine.unlock()
    create(machine, token, "marta", display_name="Marta")

    names = [entry["display_name"] for entry in machine.call(GREETER, "Children1", "List")]
    assert names == ["Ana", "Luis", "Marta"]


@pytest.mark.parametrize(
    "username",
    ["Marta", "1marta", "marta smith", "../etc", "", "root", paths.GREETER_USER,
     paths.CHILDREN_GROUP, "admin", "a" * 33],
)
def test_bad_or_taken_usernames_are_refused(machine, username):
    token = machine.unlock()

    with pytest.raises(InvalidArgument):
        create(machine, token, username)


@pytest.mark.parametrize(
    "field,value",
    [
        ("language", "klingon"),
        ("avatar", "not-a-picture"),
        ("avatar", "../../etc/passwd"),
        ("keyboard", "es; rm -rf /"),
        ("display_name", ""),
        ("display_name", "x" * 65),
        ("password", ""),
        ("password", "two\nlines"),
    ],
)
def test_bad_fields_are_refused_before_anything_is_created(machine, field, value):
    token = machine.unlock()

    with pytest.raises(InvalidArgument):
        create(machine, token, **{field: value})

    assert not machine.accounts.exists("marta")
    assert not paths.child_dir("marta").exists()


@pytest.mark.parametrize("failing_step", ["chpasswd", "group:video"])
def test_a_failure_halfway_leaves_no_half_child(machine, failing_step):
    token = machine.unlock()
    machine.accounts.fail_on.add(failing_step)

    with pytest.raises(Exception):
        create(machine, token)

    assert not machine.accounts.exists("marta")
    assert not paths.child_dir("marta").exists()
    assert any(entry[:2] == ("child created", "failed") for entry in machine.audit)


def test_delete_removes_the_account_and_its_files(machine):
    token = machine.unlock()
    create(machine, token)

    machine.call(ADMIN, "Children1", "Delete", token, "marta", False)

    assert not machine.accounts.exists("marta")
    assert not paths.child_dir("marta").exists()


def test_delete_is_refused_while_the_child_is_signed_in(machine):
    token = machine.unlock()
    machine.logind.open.append(SessionInfo("3", 3001, "ana", "seat0", "/s/3"))

    with pytest.raises(SessionActive):
        machine.call(ADMIN, "Children1", "Delete", token, "ana", False)

    assert machine.accounts.exists("ana")


def test_delete_ends_the_user_manager_that_outlives_the_last_session(machine):
    # For the seconds after a child logs out, logind still holds their user
    # manager as a session of class "manager"; that is nobody being signed
    # in, and deluser refuses a user with a process, so it is ended first.
    token = machine.unlock()
    machine.logind.open.append(SessionInfo("4", 3001, "ana", "", "/s/4", session_class="manager"))

    machine.call(ADMIN, "Children1", "Delete", token, "ana", False)

    assert machine.logind.terminated == [3001]
    assert not machine.accounts.exists("ana")


def test_set_profile_changes_only_what_it_is_given(machine):
    token = machine.unlock()
    machine.call(ADMIN, "Children1", "SetProfile", token, "ana",
                 {"avatar": "owl", "age": 7})

    profile = state.read(paths.child_profile("ana"), "profile")
    assert profile["avatar"] == "owl"
    assert profile["age"] == 7
    assert profile["language"] == "es_ES.UTF-8"


def test_windows_are_a_setting_of_the_child_off_until_an_adult_turns_them_on(machine):
    token = machine.unlock(ADMIN)
    listed = {c["username"]: c for c in machine.call(ADMIN, "Children1", "List")}
    assert listed["ana"]["windows"] is False

    machine.call(ADMIN, "Children1", "SetProfile", token, "ana", {"windows": True})

    listed = {c["username"]: c for c in machine.call(ADMIN, "Children1", "List")}
    assert listed["ana"]["windows"] is True
    with pytest.raises(InvalidArgument):
        machine.call(ADMIN, "Children1", "SetProfile", token, "ana", {"windows": "yes"})


def test_set_profile_refuses_fields_it_does_not_know(machine):
    token = machine.unlock()

    with pytest.raises(InvalidArgument):
        machine.call(ADMIN, "Children1", "SetProfile", token, "ana", {"sudo": True})


def test_a_new_display_name_reaches_the_account_too(machine):
    token = machine.unlock()
    machine.call(ADMIN, "Children1", "SetProfile", token, "ana", {"display_name": "Anita"})

    assert machine.accounts.users["ana"]["display_name"] == "Anita"


def test_set_child_password(machine):
    token = machine.unlock()
    machine.call(ADMIN, "Children1", "SetChildPassword", token, "ana", "new one")

    assert machine.accounts.users["ana"]["password"] == "new one"
    assert "new one" not in json.dumps(machine.audit)


# --- config ------------------------------------------------------------------


def test_the_screens_get_the_config_they_cannot_read_themselves(machine):
    config = machine.call(GREETER, "Daemon1", "GetConfig")

    assert config["default_language"]
    assert config["reset_hour"] == 4
    assert config["setup_complete"] is False


def test_the_config_says_whether_a_language_was_chosen(machine):
    assert machine.call(GREETER, "Daemon1", "GetConfig")["language_chosen"] is False


def test_the_panel_changes_the_machines_settings(machine):
    token = machine.unlock(GREETER)

    machine.call(GREETER, "Daemon1", "SetConfig", token, {
        "default_language": "es_ES.UTF-8", "default_keyboard": "es",
        "display_scale": 2.0, "setup_complete": True,
    })

    config = machine.call(GREETER, "Daemon1", "GetConfig")
    assert config["default_language"] == "es_ES.UTF-8"
    assert config["default_keyboard"] == "es"
    assert config["display_scale"] == 2.0
    assert config["setup_complete"] is True
    assert config["language_chosen"] is True
    assert ("config set", "ok", {"caller": paths.GREETER_USER, "fields": [
        "default_keyboard", "default_language", "display_scale", "setup_complete"]}) in machine.audit


def test_settings_need_a_token_once_there_is_a_password(machine):
    with pytest.raises(NotUnlocked):
        machine.call(GREETER, "Daemon1", "SetConfig", "", {"default_language": "es_ES.UTF-8"})


def test_the_scale_is_automatic_until_an_adult_chooses_one(machine):
    assert machine.call(GREETER, "Daemon1", "GetConfig")["display_scale"] == 0.0
    token = machine.unlock(GREETER)

    machine.call(GREETER, "Daemon1", "SetConfig", token, {"display_scale": 1.75})
    assert machine.call(GREETER, "Daemon1", "GetConfig")["display_scale"] == 1.75
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"display_scale": 0.0})
    assert machine.call(GREETER, "Daemon1", "GetConfig")["display_scale"] == 0.0


def test_before_the_first_password_only_language_and_keyboard_are_open(machine):
    # The wizard sets them first, so that the password is typed in the
    # right keyboard; nothing else may be changed without a token.
    paths.ADULTS_FILE.unlink()

    machine.call(GREETER, "Daemon1", "SetConfig", "", {"default_language": "es_ES.UTF-8",
                                                        "default_keyboard": "es"})
    assert machine.call(GREETER, "Daemon1", "GetConfig")["language_chosen"] is True

    for change in ({"setup_complete": True}, {"display_scale": 2.0},
                   {"default_keyboard": "es", "setup_complete": True}):
        with pytest.raises(NotUnlocked):
            machine.call(GREETER, "Daemon1", "SetConfig", "", change)


@pytest.mark.parametrize("change", [
    {"default_language": "xx_YY.UTF-8"},
    {"default_keyboard": "not a layout"},
    {"display_scale": 0.5},
    {"display_scale": 4},
    {"display_scale": True},
    {"setup_complete": "yes"},
    {"reset_hour": 3},
    {"minutes_nobody_offers": 10},
    {"idle_lock_minutes": 0},
    {"idle_lock_minutes": 121},
    {"idle_lock_minutes": True},
    {"idle_lock_minutes": 5.5},
    {"screen_off_minutes": 0},
    {"screen_off_minutes": 241},
    {"save_minutes": 0},
    {"save_minutes": 16},
    {"screen_off_minutes": "10"},
])
def test_bad_settings_are_refused(machine, change):
    token = machine.unlock(GREETER)

    with pytest.raises(InvalidArgument):
        machine.call(GREETER, "Daemon1", "SetConfig", token, change)


def test_a_session_left_alone_locks_after_minutes_an_adult_sets(machine):
    config = machine.call(GREETER, "Daemon1", "GetConfig")
    assert (config["idle_lock_minutes"], config["screen_off_minutes"]) == (5, 10)
    token = machine.unlock(GREETER)

    machine.call(GREETER, "Daemon1", "SetConfig", token,
                 {"idle_lock_minutes": 3, "screen_off_minutes": 20})

    config = machine.call(GREETER, "Daemon1", "GetConfig")
    assert (config["idle_lock_minutes"], config["screen_off_minutes"]) == (3, 20)


def test_unlock_to_save_lasts_the_minutes_the_machine_says(machine):
    assert machine.call(GREETER, "Daemon1", "GetConfig")["save_minutes"] == 5
    token = machine.unlock(GREETER)

    machine.call(GREETER, "Daemon1", "SetConfig", token, {"save_minutes": 1})

    assert machine.call(GREETER, "Daemon1", "GetConfig")["save_minutes"] == 1


def test_the_panel_closes_after_the_same_minutes(machine):
    token = machine.unlock(GREETER)
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"idle_lock_minutes": 2})

    assert machine.service.tokens._timeout == 120


def test_the_recovery_password_is_shown_only_with_a_token(machine):
    machine.service.adults.set_grub("abc123", "grub.pbkdf2.sha512.x")

    with pytest.raises(NotUnlocked):
        machine.call(GREETER, "Parental1", "GetRecoveryPassword", "")
    token = machine.unlock(GREETER)
    assert machine.call(GREETER, "Parental1", "GetRecoveryPassword", token) == "abc123"
    assert ("recovery password shown", "ok", {"caller": paths.GREETER_USER}) in machine.audit
    assert "abc123" not in json.dumps(machine.audit)


def test_the_panel_sets_chromium_s_flags_and_the_file_follows(machine):
    token = machine.unlock(GREETER)

    machine.call(GREETER, "Daemon1", "SetConfig", token,
                 {"chromium_flags": ["--disable-gpu-compositing"]})

    assert machine.call(GREETER, "Daemon1", "GetConfig")["chromium_flags"] == [
        "--disable-gpu-compositing"]
    assert paths.CHROMIUM_FLAGS.read_text() == "--disable-gpu-compositing\n"
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"chromium_flags": []})
    assert not paths.CHROMIUM_FLAGS.exists()


def test_a_bad_chromium_flag_changes_nothing(machine):
    token = machine.unlock(GREETER)
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"chromium_flags": ["--disable-gpu"]})

    with pytest.raises(InvalidArgument):
        machine.call(GREETER, "Daemon1", "SetConfig", token, {"chromium_flags": ["--no-sandbox"]})

    assert paths.CHROMIUM_FLAGS.read_text() == "--disable-gpu\n"


def test_the_panel_sets_the_pointer_s_speed_and_the_touchpad_s_scroll(machine):
    token = machine.unlock(GREETER)
    config = machine.call(GREETER, "Daemon1", "GetConfig")
    assert (config["pointer_speed"], config["scroll_speed"]) == (0, 0)
    assert not paths.INPUT_XML.exists()

    machine.call(GREETER, "Daemon1", "SetConfig", token, {"scroll_speed": -1})

    config = machine.call(GREETER, "Daemon1", "GetConfig")
    assert (config["pointer_speed"], config["scroll_speed"]) == (0, -1)
    assert kidux_pointer.read(paths.INPUT_XML) == (0.0, 0.35)
    assert oct(paths.INPUT_XML.stat().st_mode & 0o777) == "0o644"
    for bad in (3, 1.5, True, "1"):
        with pytest.raises(InvalidArgument):
            machine.call(GREETER, "Daemon1", "SetConfig", token, {"pointer_speed": bad})
    assert kidux_pointer.read(paths.INPUT_XML) == (0.0, 0.35)
    with pytest.raises(NotUnlocked):
        machine.call(GREETER, "Daemon1", "SetConfig", "", {"pointer_speed": 1})


def test_setting_chromium_s_flags_needs_the_adult(machine):
    machine.unlock(GREETER)
    with pytest.raises(NotUnlocked):
        machine.call(GREETER, "Daemon1", "SetConfig", "", {"chromium_flags": ["--disable-gpu"]})


def test_the_panel_grants_time_without_the_password_again(machine):
    token = machine.unlock(GREETER)

    machine.call(GREETER, "Access1", "Grant", token, "ana", 30)

    assert machine.call(GREETER, "Access1", "CheckAccess", "ana") == ("allowed", 1800)
    assert ("grant", "ok", {"caller": paths.GREETER_USER, "child": "ana", "minutes": 30,
                            "source": "panel"}) in machine.audit


def test_the_panel_sets_what_a_child_has_left(machine):
    token = machine.unlock(GREETER)
    machine.call(GREETER, "Access1", "SetPolicy", token, "ana",
                 {"mode": "daily", "daily_minutes": 60})

    machine.call(GREETER, "Access1", "SetTimeLeft", token, "ana", 5)

    assert machine.call(GREETER, "Access1", "CheckAccess", "ana") == ("allowed", 300)
    machine.call(GREETER, "Access1", "SetTimeLeft", token, "ana", 0)
    assert machine.call(GREETER, "Access1", "CheckAccess", "ana") == ("blocked", 0)
    assert ("time set", "ok", {"caller": paths.GREETER_USER, "child": "ana",
                               "minutes": 0}) in machine.audit


def test_setting_the_time_left_is_checked(machine):
    with pytest.raises(NotUnlocked):
        machine.call(GREETER, "Access1", "SetTimeLeft", "", "ana", 5)
    token = machine.unlock(GREETER)
    with pytest.raises(NoSuchChild):
        machine.call(GREETER, "Access1", "SetTimeLeft", token, "admin", 5)
    with pytest.raises(InvalidArgument):
        machine.call(GREETER, "Access1", "SetTimeLeft", token, "ana", 24 * 60 + 1)
    machine.call(GREETER, "Access1", "SetPolicy", token, "ana", {"mode": "unlimited"})
    with pytest.raises(InvalidArgument):
        machine.call(GREETER, "Access1", "SetTimeLeft", token, "ana", 5)


@pytest.mark.parametrize("minutes", [0, 24 * 60 + 1, True])
def test_a_grant_from_the_panel_is_checked(machine, minutes):
    token = machine.unlock(GREETER)

    with pytest.raises(InvalidArgument):
        machine.call(GREETER, "Access1", "Grant", token, "ana", minutes)


def test_a_grant_from_the_panel_needs_a_token_and_a_child(machine):
    with pytest.raises(NotUnlocked):
        machine.call(GREETER, "Access1", "Grant", "", "ana", 30)
    token = machine.unlock(GREETER)
    with pytest.raises(NoSuchChild):
        machine.call(GREETER, "Access1", "Grant", token, "admin", 30)


# --- the network (D62) ---------------------------------------------------------


class FakeNetwork:
    def __init__(self):
        self.calls = []

    def read(self):
        self.calls.append(("read",))
        return {"manager": True}, [], []

    def check(self):
        self.calls.append(("check",))

    def connect(self, ssid, password):
        self.calls.append(("connect", ssid, password))

    def forget(self, ssid):
        self.calls.append(("forget", ssid))


def test_the_network_is_the_panel_s_with_a_token_and_never_a_child_s(machine):
    machine.service.network = FakeNetwork()
    with pytest.raises(NotUnlocked):
        machine.call(GREETER, "Network1", "GetNetwork", "not a token")
    with pytest.raises(AccessDenied):
        machine.call(ANA, "Network1", "GetNetwork", "")
    with pytest.raises(AccessDenied):
        machine.call(ANA, "Network1", "ConnectWifi", "", "Home", "kidux password 1")
    token = machine.unlock(GREETER)
    assert machine.call(GREETER, "Network1", "GetNetwork", token) == ({"manager": True}, [], [])
    machine.call(GREETER, "Network1", "Check", token)
    machine.call(GREETER, "Network1", "ConnectWifi", token, "Home", "kidux password 1")
    machine.call(GREETER, "Network1", "ForgetWifi", token, "Home")
    assert machine.service.network.calls[1:] == [
        ("check",), ("connect", "Home", "kidux password 1"), ("forget", "Home")]
    # The network's name is audited; the password never is.
    assert ("wifi join", "started", {"caller": "_greetd", "network": "Home"}) in machine.audit
    assert "kidux password 1" not in repr(machine.audit)


def test_a_daemon_without_the_network_says_so(machine):
    token = machine.unlock(GREETER)
    with pytest.raises(Failed):
        machine.call(GREETER, "Network1", "GetNetwork", token)


# --- the versions ------------------------------------------------------------------


def test_the_versions_are_dpkg_s_for_the_screens_and_not_for_a_child(machine):
    machine.service.kidux_packages = lambda: (
        "kidux-base 0.2.3 installed\nkidux-daemon 0.3.25 installed\n"
        "kidux-webapps 0.1.3 config-files\npython3-kidux 0.1.35 installed\n")
    assert machine.call(GREETER, "System1", "Versions") == {
        "kidux-base": "0.2.3", "kidux-daemon": "0.3.25", "python3-kidux": "0.1.35"}
    with pytest.raises(AccessDenied):
        machine.call(ANA, "System1", "Versions")


def test_without_dpkg_the_versions_are_none(machine):
    assert machine.call(GREETER, "System1", "Versions") == {}

    def broken():
        raise OSError("no dpkg-query")

    machine.service.kidux_packages = broken
    assert machine.call(GREETER, "System1", "Versions") == {}


def test_the_request_runs_in_a_unit_of_its_own_with_the_password_on_its_input():
    import json
    import subprocess

    from kiduxd import signin
    from kiduxd.errors import SignInRefused, SignInUnreachable

    ran = []

    def run(argv, input, capture_output, text, timeout):
        ran.append((argv, json.loads(input)))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(answer), stderr="")

    answer = {"cookies": [{"name": "sess", "value": "v"}]}
    assert signin.request_in_unit("https://example.org/auth", {"p": "hunter2"}, ("sess",),
                                  run=run) == [{"name": "sess", "value": "v"}]
    argv, given = ran[0]
    assert argv[:2] == ["systemd-run", "--wait"] and "--property=DynamicUser=yes" in argv
    assert "hunter2" not in " ".join(argv) and given["body"] == {"p": "hunter2"}

    answer = {"error": "refused", "detail": "401"}
    with pytest.raises(SignInRefused):
        signin.request_in_unit("https://example.org/auth", {}, ("sess",), run=run)
    answer = {"error": "unreachable", "detail": "no route"}
    with pytest.raises(SignInUnreachable):
        signin.request_in_unit("https://example.org/auth", {}, ("sess",), run=run)



def test_the_panel_turns_usage_statistics_off_and_on_and_the_snippet_follows(machine):
    token = machine.unlock(GREETER)
    assert machine.call(GREETER, "Daemon1", "GetConfig")["apt_statistics"] is True

    machine.call(GREETER, "Daemon1", "SetConfig", token, {"apt_statistics": False})
    assert machine.call(GREETER, "Daemon1", "GetConfig")["apt_statistics"] is False
    assert not paths.APT_STATISTICS.exists()

    machine.call(GREETER, "Daemon1", "SetConfig", token, {"apt_statistics": True})
    snippet = paths.APT_STATISTICS.read_text()
    identifier = Config.load().apt_statistics_id
    assert len(identifier) == 32
    assert f'User-Agent "Debian APT-HTTP/1.3 Kidux/{identifier}";' in snippet

    # Off and on again: the same machine, by the same identifier.
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"apt_statistics": False})
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"apt_statistics": True})
    assert Config.load().apt_statistics_id == identifier
    with pytest.raises(Exception):
        machine.call(GREETER, "Daemon1", "SetConfig", token, {"apt_statistics": "yes"})


# --- suspend and the lid (power.py, D119) ---------------------------------------


def test_the_power_settings_have_their_defaults_and_what_the_computer_can_do(machine):
    config = machine.call(GREETER, "Daemon1", "GetConfig")

    assert (config["lid_action"], config["idle_action"], config["idle_sleep_minutes"]) == \
        ("sleep", "sleep", 20)
    assert config["can_sleep"] is True
    assert not {"can_hibernate", "hibernate_reason"} & set(config)


def test_a_config_from_before_the_power_settings_takes_their_defaults_and_keeps_its_own(
        machine):
    state.write(paths.CONFIG_FILE, {"idle_lock_minutes": 7, "screen_off_minutes": 25},
                "config")

    config = machine.call(GREETER, "Daemon1", "GetConfig")

    assert (config["idle_lock_minutes"], config["screen_off_minutes"]) == (7, 25)
    assert (config["lid_action"], config["idle_sleep_minutes"]) == ("sleep", 20)


def test_a_computer_that_cannot_suspend_says_so(machine):
    machine.logind.answers.update(CanSuspend="no")

    assert machine.call(GREETER, "Daemon1", "GetConfig")["can_sleep"] is False


@pytest.mark.parametrize("change", [
    {"lid_action": "sleep_then_hibernate"},
    {"lid_action": "hibernate"},
    {"lid_action": ""},
    {"lid_action": 1},
    {"idle_action": "sleep_then_hibernate"},
    {"idle_action": "nothing"},
    {"idle_sleep_minutes": 0},
    {"idle_sleep_minutes": 241},
    {"idle_sleep_minutes": "20"},
    {"hibernate_delay_seconds": 30},
])
def test_bad_power_settings_are_refused(machine, change):
    token = machine.unlock(GREETER)

    with pytest.raises(InvalidArgument):
        machine.call(GREETER, "Daemon1", "SetConfig", token, change)


def test_the_power_settings_are_saved(machine):
    token = machine.unlock(GREETER)

    machine.call(GREETER, "Daemon1", "SetConfig", token,
                 {"lid_action": "nothing", "idle_action": "screen_off_only",
                  "idle_sleep_minutes": 45})

    config = machine.call(GREETER, "Daemon1", "GetConfig")
    assert (config["lid_action"], config["idle_action"], config["idle_sleep_minutes"]) == \
        ("nothing", "screen_off_only", 45)


def test_a_lid_closing_suspends_the_computer(machine):
    machine.service.lid_is_closed = lambda: True
    machine.service.connected_screens = lambda: ["card1-eDP-1"]

    machine.service.attention("lid_closed")

    assert machine.logind.slept == ["Suspend"]


def test_a_lid_set_to_nothing_does_not_suspend(machine):
    token = machine.unlock(GREETER)
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"lid_action": "nothing"})
    machine.service.lid_is_closed = lambda: True

    machine.service.lid_closed()

    assert machine.logind.slept == []


def test_a_lid_opened_again_before_suspending_does_not_suspend(machine):
    machine.service.lid_is_closed = lambda: False

    machine.service.lid_closed()

    assert machine.logind.slept == []


def test_a_key_typed_with_the_lid_said_to_be_closed_is_a_switch_that_lies(machine):
    # A MacBook's switch, after a failed resume, read closed with the lid
    # open: the "close" was the lid opening, and the child types at once.
    def closed_while_typing():
        machine.service.key_pressed()
        return True

    machine.service.lid_is_closed = closed_while_typing
    machine.service.connected_screens = lambda: []

    machine.service.lid_closed()

    assert machine.logind.slept == []


def test_the_lid_s_suspend_waits_for_the_keyboards_to_be_read(machine):
    # The lock blocks the main loop; a key typed meanwhile is read only
    # after it, so the switch is asked again a moment later.
    waited = []
    machine.service.later = lambda seconds, run: waited.append((seconds, run))
    machine.service.lid_is_closed = lambda: True
    machine.service.connected_screens = lambda: []

    machine.service.lid_closed()

    assert machine.logind.slept == []
    ((seconds, run),) = waited
    assert seconds == power.LID_SETTLE_SECONDS
    run()
    assert machine.logind.slept == ["Suspend"]


def test_a_key_read_while_the_sessions_locked_stops_the_lid_s_suspend(machine):
    waited = []
    machine.service.later = lambda seconds, run: waited.append(run)
    machine.service.lid_is_closed = lambda: True
    machine.service.connected_screens = lambda: []

    machine.service.lid_closed()
    machine.service.key_pressed()
    waited[0]()

    assert machine.logind.slept == []


def test_a_key_pressed_before_the_lid_closed_does_not_count(machine):
    machine.service.key_pressed()
    machine.service.lid_is_closed = lambda: True
    machine.service.connected_screens = lambda: []

    machine.service.lid_closed()

    assert machine.logind.slept == ["Suspend"]


def test_a_lid_closed_with_another_screen_connected_does_not_suspend(machine):
    machine.service.lid_is_closed = lambda: True
    machine.service.connected_screens = lambda: ["card1-eDP-1", "card1-HDMI-A-1"]

    machine.service.lid_closed()

    assert machine.logind.slept == []


def test_a_hibernating_lid_kept_from_a_development_build_suspends(machine):
    state.write(paths.CONFIG_FILE, {"lid_action": "sleep_then_hibernate"}, "config")
    machine.service.lid_is_closed = lambda: True
    machine.service.connected_screens = lambda: []

    machine.service.lid_closed()

    assert machine.logind.slept == ["Suspend"]


def test_a_lid_set_to_suspend_does_nothing_on_a_computer_that_cannot(machine):
    machine.logind.answers.update(CanSuspend="na")
    machine.service.lid_is_closed = lambda: True

    machine.service.lid_closed()

    assert machine.logind.slept == []
    assert Config.load().lid_action == "sleep"     # kept as chosen


def test_a_screen_left_alone_has_the_computer_suspend(machine):
    assert machine.call(ANA, "System1", "SleepWhenIdle") == "sleep"

    assert machine.logind.slept == ["Suspend"]


def test_screen_off_only_never_suspends(machine):
    token = machine.unlock(GREETER)
    machine.call(GREETER, "Daemon1", "SetConfig", token, {"idle_action": "screen_off_only"})

    assert machine.call(ANA, "System1", "SleepWhenIdle") == ""

    assert machine.logind.slept == []


def test_a_computer_that_cannot_suspend_does_not_when_left_alone(machine):
    machine.logind.answers.update(CanSuspend="no")

    assert machine.call(ANA, "System1", "SleepWhenIdle") == ""
    assert machine.logind.slept == []


@pytest.mark.parametrize("blocked", ["idle", "sleep", "handle-lid-switch:idle"])
def test_a_video_or_anything_holding_idleness_off_keeps_the_computer_awake(machine, blocked):
    machine.logind.blocked = blocked

    assert machine.call(ANA, "System1", "SleepWhenIdle") == ""

    assert machine.logind.slept == []


def test_only_the_screens_and_children_ask_to_sleep_when_left_alone(machine):
    machine.authority.refuse_everything = True

    with pytest.raises(AccessDenied):
        machine.call(ANA, "System1", "SleepWhenIdle")
