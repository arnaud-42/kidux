"""The sign-in and lock screens' decisions, against a fake daemon and greetd.

Every arrow of docs/dev/greeter.md, section 2, and every row of section 3.
Above all: from every screen a child can reach, some button leads somewhere.
"""

import pytest

from kidux import vocabulary
from kidux_greeter.daemon import DaemonError, DaemonUnavailableError, NoTimeLeft
from kidux_greeter.flow import FINAL, LOCK_ACTIONS, SIGN_IN_ACTIONS, Lock, SignIn
from kidux_greeter.greetd import Outcome

ADULT = "adult secret"
ANA = {"username": "ana", "display_name": "Ana", "language": "es_ES.UTF-8",
       "keyboard": "es", "avatar": "fox"}
TOM = {"username": "tom", "display_name": "Tom", "language": "en_US.UTF-8",
       "keyboard": "gb", "avatar": "owl"}


class FakeDaemon:
    def __init__(self):
        self.available = True
        self.password_set = True
        self.kids = [dict(ANA), dict(TOM)]
        self.access = {"ana": ("allowed", 1800), "tom": ("allowed", -1)}
        self.left = {"ana": 600, "tom": -1}
        self.calls = []
        self.no_time_left = False
        self.not_locked = False
        self.settings = {"default_language": "en_US.UTF-8", "default_keyboard": "us",
                         "display_scale": 2.0}

    def _check(self):
        if not self.available:
            raise DaemonUnavailableError("down")

    def config(self):
        self._check()
        return dict(self.settings)

    def password_is_set(self):
        self._check()
        return self.password_set

    def children(self):
        self._check()
        return list(self.kids)

    def check_access(self, username):
        self._check()
        return self.access[username]

    def usage(self, username):
        self._check()
        return 0, self.left.get(username, -1)

    def policy(self, username):
        self._check()
        return {"mode": "daily", "daily_minutes": 60, "granted_seconds": 0}

    def authorise_session(self, password, username, minutes):
        self.calls.append(("authorise", username, minutes))
        if password != ADULT:
            return False
        self.access[username] = ("allowed", minutes * 60)
        return True

    def grant_extra_time(self, password, username, minutes):
        self.calls.append(("grant", username, minutes))
        return password == ADULT

    def unlock_for_saving(self, password, minutes):
        self.calls.append(("save", minutes))
        return password == ADULT

    def continue_session(self, username, password):
        self.calls.append(("continue", username))
        if self.not_locked:
            raise DaemonError("org.kidux.Daemon1.Error.NoSession")
        if password == ADULT or password == f"{username}-pw":
            if self.no_time_left:
                raise NoTimeLeft()
            return True
        return False

    def end_session(self, username, password):
        self.calls.append(("end", username))
        return password in (ADULT, f"{username}-pw")

    def unlock_panel(self, password):
        return "token" if password == ADULT else None

    def lock_panel(self, token):
        self.calls.append(("lock_panel", token))

    #: What System1.Versions answers.
    installed = {"kidux-base": "0.2.3", "kidux-daemon": "0.3.25"}

    def versions(self):
        self._check()
        return dict(self.installed)

    def shutdown(self):
        self.calls.append(("shutdown",))

    def reboot(self):
        self.calls.append(("reboot",))


class FakeGreetd:
    def __init__(self):
        self.calls = []

    def authenticate(self, username, password):
        self.calls.append(("authenticate", username))
        return Outcome(authenticated=password == f"{username}-pw",
                       wrong_password=password != f"{username}-pw")

    def start(self, command, environment):
        self.calls.append(("start", command, environment))

    def cancel(self):
        self.calls.append(("cancel",))


@pytest.fixture
def daemon():
    return FakeDaemon()


@pytest.fixture
def greetd():
    return FakeGreetd()


@pytest.fixture
def signin(daemon, greetd):
    flow = SignIn(daemon, greetd)
    flow.start()
    return flow


def check_way_forward(screen, actions):
    if screen.owner:
        return  # the wizard's and the panel's own screens: test_panel.py
    assert screen.name in actions, f"{screen.name} is not a known screen"
    if screen.name not in FINAL:
        assert actions[screen.name], f"{screen.name} has no way forward"


# --- sign-in: choose ---------------------------------------------------------


def test_the_first_screen_shows_every_child_in_the_default_language(daemon, greetd):
    screen = SignIn(daemon, greetd).start()

    assert screen.name == "choose"
    assert screen.language == "en_US.UTF-8"
    assert [c["username"] for c in screen.data["children"]] == ["ana", "tom"]


def test_tapping_a_child_switches_to_their_language(signin):
    screen = signin.tap_child("ana")

    assert screen.name == "password"
    assert screen.language == "es_ES.UTF-8"
    assert screen.data["child"]["username"] == "ana"


def test_going_back_returns_to_everyone_in_the_default_language(signin, greetd):
    signin.tap_child("ana")

    screen = signin.back()

    assert screen.name == "choose"
    assert screen.language == "en_US.UTF-8"


def test_a_machine_never_set_up_goes_to_the_wizard(daemon, greetd):
    daemon.password_set = False

    screen = SignIn(daemon, greetd).start()
    assert (screen.name, screen.owner) == ("wiz_language", "wizard")


def test_a_daemon_not_yet_up_is_waited_for_and_retried(daemon, greetd):
    daemon.available = False
    flow = SignIn(daemon, greetd)

    screen = flow.start()
    assert screen.name == "waiting"
    assert screen.notice == vocabulary.CANNOT_REACH_DAEMON

    daemon.available = True
    assert flow.start().name == "choose"


# --- sign-in: passwords and access ---------------------------------------------


def test_the_right_password_with_time_starts_the_session_with_the_childs_environment(signin, greetd):
    signin.tap_child("ana")

    screen = signin.submit_password("ana-pw")

    assert screen.name == "starting"
    assert signin.session_started
    _, command, environment = greetd.calls[-1]
    assert command == ["/usr/libexec/kidux-session"]
    assert environment == {"KIDUX_LANGUAGE": "es_ES.UTF-8",
                           "XKB_DEFAULT_LAYOUT": "es", "KIDUX_DISPLAY_SCALE": "2.0",
                           "KIDUX_AVATAR": "fox",
                           # a session left alone locks, and its screen turns off (D67)
                           "KIDUX_IDLE_LOCK_SECONDS": "300", "KIDUX_SCREEN_OFF_SECONDS": "600",
                           # and, still left alone, the computer sleeps (D119)
                           "KIDUX_IDLE_SLEEP_SECONDS": "1200"}



def test_a_session_gets_the_minutes_as_they_are_when_it_starts(signin, greetd, daemon):
    signin.tap_child("ana")
    daemon.settings["idle_lock_minutes"] = 1

    signin.submit_password("ana-pw")

    _, _, environment = greetd.calls[-1]
    assert environment["KIDUX_IDLE_LOCK_SECONDS"] == "60"


def test_a_session_on_a_computer_set_to_the_screen_off_only_never_asks_to_sleep(
        signin, greetd, daemon):
    signin.tap_child("ana")
    daemon.settings.update(idle_action="screen_off_only")

    signin.submit_password("ana-pw")

    _, _, environment = greetd.calls[-1]
    assert environment["KIDUX_IDLE_SLEEP_SECONDS"] == "0"


def test_a_child_with_windows_has_a_session_that_knows(signin, greetd, daemon):
    daemon.kids[0]["windows"] = True
    signin.tap_child("ana")

    signin.submit_password("ana-pw")

    _, _, environment = greetd.calls[-1]
    assert environment["KIDUX_WINDOWS"] == "1"


def test_a_wrong_password_says_so_kindly_and_stays(signin):
    signin.tap_child("ana")

    screen = signin.submit_password("a guess")

    assert screen.name == "password"
    assert screen.notice == vocabulary.WRONG_PASSWORD
    assert screen.data["child"]["username"] == "ana"
    assert not signin.session_started


def test_access_is_only_checked_after_the_password(signin, daemon):
    # A wrong password and a spent allowance must never be the same message.
    daemon.access["ana"] = ("blocked", 0)
    signin.tap_child("ana")

    assert signin.submit_password("a guess").notice == vocabulary.WRONG_PASSWORD
    assert signin.submit_password("ana-pw").notice == vocabulary.TIME_SPENT_TODAY


def test_a_spent_day_offers_an_adult(signin, daemon):
    daemon.access["ana"] = ("blocked", 0)
    signin.tap_child("ana")
    signin.submit_password("ana-pw")

    screen = signin.ask_adult()

    assert screen.name == "needs_adult"
    assert screen.data["choices"] == (15, 30, 60)
    assert screen.data["left"] == daemon.left["ana"]


def test_a_day_not_ticked_says_so_and_an_adult_can_give_time(signin, daemon):
    # D54: the day of the week is not this child's; the screen says why,
    # and an adult's grant still lets them in.
    daemon.access["ana"] = ("day_off", 0)
    signin.tap_child("ana")

    screen = signin.submit_password("ana-pw")

    assert screen.name == "blocked"
    assert screen.notice == vocabulary.NOT_TODAY
    assert signin.ask_adult().name == "needs_adult"
    assert signin.adult_grants(ADULT, 15).name == "starting"


def test_the_adult_sees_how_much_time_the_child_has_left(signin, daemon):
    daemon.access["ana"] = ("needs_adult", 0)
    daemon.left["ana"] = 12 * 60
    signin.tap_child("ana")

    screen = signin.submit_password("ana-pw")

    assert screen.name == "needs_adult"
    assert screen.data["left"] == 12 * 60


def test_an_adult_grants_time_and_the_session_starts(signin, daemon):
    daemon.access["ana"] = ("needs_adult", 0)
    signin.tap_child("ana")
    assert signin.submit_password("ana-pw").name == "needs_adult"

    screen = signin.adult_grants(ADULT, 30)

    assert ("authorise", "ana", 30) in daemon.calls
    assert screen.name == "starting"


def test_a_wrong_adult_password_gives_nothing(signin, daemon):
    daemon.access["ana"] = ("needs_adult", 0)
    signin.tap_child("ana")
    signin.submit_password("ana-pw")

    screen = signin.adult_grants("a guess", 30)

    assert screen.name == "needs_adult"
    assert screen.notice == vocabulary.WRONG_PASSWORD
    assert not signin.session_started


def test_granting_without_the_childs_password_first_is_impossible(signin):
    signin.tap_child("ana")

    assert signin.adult_grants(ADULT, 30).name == "choose"


def test_leaving_a_half_made_session_cancels_it(signin, greetd):
    signin.tap_child("ana")
    signin.submit_password("a guess")
    greetd.calls.clear()

    signin.idle()

    assert ("cancel",) in greetd.calls


# --- sign-in: the adult and the power -------------------------------------------


def test_the_adult_button_asks_for_the_password_then_opens_the_panel(signin):
    assert signin.tap_adult().name == "adult"
    assert signin.submit_adult_password("a guess").notice == vocabulary.WRONG_PASSWORD
    screen = signin.submit_adult_password(ADULT)
    assert (screen.name, screen.owner) == ("panel_children", "panel")


def test_the_power_button_asks_before_turning_off(signin, daemon):
    assert signin.attention().name == "power"
    assert signin.power("cancel").name == "choose"
    assert signin.power("off").name == "turning_off"
    assert ("shutdown",) in daemon.calls


# --- the lock screen --------------------------------------------------------------


@pytest.fixture
def lock(daemon):
    return Lock(daemon, "ana")


def test_the_lock_screen_is_in_the_childs_language(lock):
    screen = lock.start()

    assert screen.name == "locked"
    assert screen.language == "es_ES.UTF-8"
    assert screen.data["time_up"] is False


def test_the_lock_screen_says_when_time_is_up(lock, daemon):
    daemon.left["ana"] = 0

    screen = lock.start()

    assert screen.data["time_up"] is True
    assert screen.notice == vocabulary.TIME_IS_UP


def test_the_child_continues_with_their_own_password(lock, daemon):
    lock.start()
    assert lock.tap_continue().data["purpose"] == "continue"

    assert lock.submit_child_password("a guess").notice == vocabulary.WRONG_PASSWORD
    assert lock.submit_child_password("ana-pw").name == "unlocking"


def test_continuing_with_no_time_left_explains_rather_than_blames(lock, daemon):
    daemon.no_time_left = True
    lock.start()
    lock.tap_continue()

    screen = lock.submit_child_password("ana-pw")

    assert screen.name == "locked"
    assert screen.notice == vocabulary.TIME_SPENT_TODAY


@pytest.mark.parametrize("choice,call", [
    ("grant", ("grant", "ana", 30)),
    ("save", ("save", 5)),
    ("log_out", ("end", "ana")),
])
def test_the_adult_can_give_time_unlock_to_save_or_log_out(lock, daemon, choice, call):
    lock.start()
    lock.tap_adult()
    options = lock.submit_adult_password(ADULT)
    assert options.name == "adult_choice"
    assert options.data["left"] == daemon.left["ana"]

    screen = lock.adult_choice(choice, 30)

    assert call in daemon.calls
    assert screen.name in ("unlocking", "ending")


def test_unlock_to_save_gives_the_minutes_the_machine_says(lock, daemon):
    daemon.settings["save_minutes"] = 1
    lock.start()
    lock.tap_adult()
    options = lock.submit_adult_password(ADULT)
    assert options.data["save_minutes"] == 1

    lock.adult_choice("save")

    assert ("save", 1) in daemon.calls


def test_a_wrong_adult_password_on_the_lock_screen_goes_back_to_asking(lock):
    lock.start()
    lock.tap_adult()
    lock.submit_adult_password("a guess")

    screen = lock.adult_choice("grant", 30)

    assert screen.name == "adult_password"
    assert screen.notice == vocabulary.WRONG_PASSWORD


def test_the_child_logs_out_with_their_password(lock, daemon):
    lock.start()
    assert lock.tap_log_out().data["purpose"] == "log_out"

    assert lock.submit_child_password("ana-pw").name == "ending"
    assert ("end", "ana") in daemon.calls


# --- no dead ends -------------------------------------------------------------------


def test_a_child_waits_while_an_update_is_being_installed(daemon, greetd):
    daemon.access["ana"] = ("updating", 0)
    flow = SignIn(daemon, greetd)
    flow.start()
    flow.tap_child("ana")

    screen = flow.submit_password("ana-pw")

    assert (screen.name, screen.notice) == ("waiting", vocabulary.UPDATING)
    assert ("cancel",) in greetd.calls


def test_every_sign_in_screen_has_a_way_forward(daemon, greetd):
    # Walk every screen the flow can produce, in every situation the tests
    # above create, and check each one offers something.
    seen = set()
    for access in (("allowed", 60), ("needs_adult", 0), ("blocked", 0), ("day_off", 0),
                   ("updating", 0)):
        for available in (True, False):
            d, g = FakeDaemon(), FakeGreetd()
            d.access["ana"] = access
            flow = SignIn(d, g)
            d.available = available
            screens = [flow.start()]
            d.available = True
            screens += [flow.start(), flow.tap_child("ana"), flow.submit_password("x"),
                        flow.submit_password("ana-pw"), flow.ask_adult(),
                        flow.adult_grants("x", 15), flow.back(), flow.tap_adult(),
                        flow.submit_adult_password("x"), flow.submit_adult_password(ADULT),
                        flow.tap_power(), flow.power("cancel")]
            for screen in screens:
                check_way_forward(screen, SIGN_IN_ACTIONS)
                seen.add(screen.name)
    assert {"choose", "password", "needs_adult", "blocked", "adult", "panel_children", "power",
            "starting", "waiting"} <= seen


def test_every_lock_screen_has_a_way_forward(daemon):
    seen = set()
    for no_time in (False, True):
        d = FakeDaemon()
        d.no_time_left = no_time
        flow = Lock(d, "ana")
        screens = [flow.start(), flow.tap_continue(), flow.submit_child_password("x"),
                   flow.submit_child_password("ana-pw"), flow.back(), flow.tap_adult(),
                   flow.submit_adult_password(""), flow.submit_adult_password("x"),
                   flow.adult_choice("grant", 15), flow.tap_log_out(),
                   flow.submit_child_password("ana-pw"), flow.tap_power(), flow.power("cancel")]
        for screen in screens:
            check_way_forward(screen, LOCK_ACTIONS)
            seen.add(screen.name)
    assert {"locked", "child_password", "adult_password", "adult_choice", "power",
            "unlocking", "ending"} <= seen


def test_leaving_the_panel_locks_it(signin, daemon):
    signin.tap_adult()
    signin.submit_adult_password(ADULT)

    signin.panel.close()

    assert ("lock_panel", "token") in daemon.calls


def test_an_adult_giving_time_carries_the_session_on_whatever_locked_it(lock, daemon):
    # Locked by the power button, a grant alone would leave it locked.
    lock.start()
    lock.tap_adult()
    lock.submit_adult_password(ADULT)

    assert lock.adult_choice("grant", 15).name == "unlocking"
    assert daemon.calls[-2:] == [("grant", "ana", 15), ("continue", "ana")]


def test_a_grant_that_already_unlocked_is_not_an_error(lock, daemon):
    # Locked because time ran out, the grant unlocks by itself and there is
    # nothing left for ContinueSession to do.
    daemon.not_locked = True
    lock.start()
    lock.tap_adult()
    lock.submit_adult_password(ADULT)

    assert lock.adult_choice("grant", 15).name == "unlocking"


def test_a_new_child_appears_on_the_list_at_once(signin, daemon):
    daemon.kids.append({"username": "zoe", "display_name": "Zoe", "avatar": "fox"})

    screen = signin.children_changed("choose")

    assert [c["username"] for c in screen.data["children"]] == ["ana", "tom", "zoe"]


@pytest.mark.parametrize("showing", ["password", "panel", "power"])
def test_a_change_to_the_children_never_pulls_anyone_away(signin, daemon, showing):
    signin.tap_adult()
    signin.submit_adult_password(ADULT)
    daemon.kids.append({"username": "zoe", "display_name": "Zoe", "avatar": "fox"})

    assert signin.children_changed(showing) is None
    assert ("lock_panel", "token") not in daemon.calls
    assert [c["username"] for c in signin.back().data["children"]] == ["ana", "tom", "zoe"]


def test_the_sign_in_screen_says_which_kidux_this_is(daemon, greetd):
    screen = SignIn(daemon, greetd).start()
    assert screen.data["kidux_version"] == "0.2.3"
    daemon.installed = {}
    assert SignIn(daemon, greetd).start().data["kidux_version"] == ""
