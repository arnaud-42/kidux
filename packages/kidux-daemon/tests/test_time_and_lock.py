"""Time, warnings and the lock, through the service, against a fake machine.

The fake machine records every call to systemd and logind, so these tests can
say not only *that* a session was locked but *how*: locker started, seat
switched, scope frozen, in that order. The adversarial cases of the phase 1
plan, step 9.4 item 7, are here by name wherever they can be decided without
a real machine; the rest are in the VM run.
"""

from datetime import datetime, timedelta, timezone

import pytest

from kidux import paths, state
from kiduxd.access import Policy
from kiduxd.accounts import FakeAccounts
from kiduxd.adults import AdultPassword
from kiduxd.children import Children
from kiduxd.errors import (
    AccessDenied,
    Failed,
    InvalidArgument,
    NoSession,
    NoTimeLeft,
    NotAuthorized,
    NotUnlocked,
    SessionActive,
)
from kiduxd.gate import Gate
from kiduxd.locker import LOCK_VT, Locker
from kiduxd.logind import FakeLogind
from kiduxd.service import Service
from kiduxd.tokens import Tokens

from conftest import LANGUAGES
from test_service import ADMIN, ANA, GREETER, LUIS, FakeAuthority

ADULT = "a family secret"
CHILD_VT = 7
SESSION = {
    "id": "3",
    "path": "/org/freedesktop/login1/session/_33",
    "uid": ANA.uid,
    "class": "user",
    "scope": "session-3.scope",
    "vtnr": CHILD_VT,
}


class FakeClock:
    def __init__(self) -> None:
        self.now_wall = datetime(2026, 9, 22, 17, 0, tzinfo=timezone(timedelta(hours=2)))
        self.now_mono = 1000.0

    def wall(self) -> datetime:
        return self.now_wall

    def mono(self) -> float:
        return self.now_mono

    def advance(self, seconds: float) -> None:
        self.now_wall += timedelta(seconds=seconds)
        self.now_mono += seconds


class FakeMachine:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.vt = CHILD_VT
        self.locker_up = False
        self.switch_works = True
        self.locker_starts = True
        self.locker_refused = False
        self.terminate_fails = False
        #: Session paths logind is ending (session_closing).
        self.closing: set[str] = set()

    def start_locker(self, username):
        self.calls.append(("start_locker", username))
        if self.locker_refused:
            raise Failed("StartUnit failed: Unit kidux-locker@ana.service not found")
        self.locker_up = self.locker_starts

    def stop_locker(self, username):
        self.calls.append(("stop_locker", username))
        self.locker_up = False

    def locker_ready(self):
        return self.locker_up

    def switch_to(self, vt):
        self.calls.append(("switch_to", vt))
        if self.switch_works:
            self.vt = vt

    def session_active(self, session_path):
        return self.vt == CHILD_VT

    def freeze(self, scope):
        self.calls.append(("freeze", scope))

    def thaw(self, scope):
        self.calls.append(("thaw", scope))

    def terminate(self, session_path):
        self.calls.append(("terminate", session_path))
        if self.terminate_fails:
            raise RuntimeError("no such session")

    def session_closing(self, session_path):
        return session_path in self.closing

    def stop_scope(self, scope):
        self.calls.append(("stop_scope", scope))

    def wake_input(self):
        self.calls.append(("wake_input",))


class Harness:
    def __init__(self, fast_hasher) -> None:
        self.accounts = FakeAccounts()
        self.accounts.add_user("admin", ADMIN.uid, (paths.ADMIN_GROUP,))
        self.accounts.add_user(paths.GREETER_USER, GREETER.uid)
        self.accounts.add_user("ana", ANA.uid, (paths.CHILDREN_GROUP,))
        self.accounts.add_user("luis", LUIS.uid, (paths.CHILDREN_GROUP,))
        self.clock = FakeClock()
        self.machine = FakeMachine()
        self.audit: list[tuple] = []
        self.signals: list[tuple] = []
        self.hasher = fast_hasher
        #: Every password PAM was asked about, as (user, password).
        self.pam_asked: list[tuple[str, str]] = []
        self.build()

    def pam(self, user, password) -> bool:
        self.pam_asked.append((user, password))
        return password == f"{user}-pw"

    def build(self) -> None:
        """A daemon, as if freshly started. Call again to simulate a restart."""
        audit = lambda action, outcome, **fields: self.audit.append((action, outcome, fields))
        logind = FakeLogind()
        self.service = Service(
            gate=Gate(FakeAuthority(self.accounts), self.accounts),
            accounts=self.accounts,
            logind=logind,
            adults=AdultPassword(self.hasher),
            tokens=Tokens(900),
            children=Children(self.accounts, logind, LANGUAGES),
            locker=Locker(self.machine, audit, sleep=lambda seconds: None),
            clock=self.clock,
            check_child_password=self.pam,
            emit=lambda *signal: self.signals.append(signal),
            audit=audit,
        )
        if not self.service.adults.is_set():
            self.service.adults.set(ADULT)

    def policy(self, username="ana", **fields) -> None:
        state.write(paths.child_access(username), Policy(**fields).as_document(), "access")

    def call(self, caller, interface, method, *args):
        return self.service.dispatch(caller, interface, method, *args)

    def play(self, seconds: int, step: int = 10) -> None:
        """Let the child use the computer, the daemon ticking as it would."""
        for _ in range(0, seconds, step):
            self.clock.advance(step)
            self.service.tick()

    def used(self, username="ana") -> int:
        return self.call(ADMIN, "Access1", "Usage", username)[0]

    def left(self, username="ana") -> int:
        return self.call(ADMIN, "Access1", "Usage", username)[1]

    def signal_names(self) -> list[str]:
        return [signal[1] for signal in self.signals]


@pytest.fixture
def h(fast_hasher):
    return Harness(fast_hasher)


# --- the clock ---------------------------------------------------------------


def test_a_session_counts_while_unlocked(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)

    h.play(120)

    assert h.used() == 120
    assert h.left() == 3600 - 120


def test_the_clock_keeps_running_whatever_the_launcher_does(h):
    # There is no launcher in this test at all: the daemon counts from what
    # logind says, not from anything the child's session runs.
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)

    h.play(600)

    assert h.used() == 600


def test_an_unlimited_child_is_counted_but_never_locked(h):
    h.policy(mode="unlimited")
    h.service.session_appeared(SESSION)

    h.play(3 * 3600, step=60)

    assert h.used() == 3 * 3600
    assert "Locked" not in h.signal_names()


def test_other_sessions_are_not_tracked(h):
    h.service.session_appeared({**SESSION, "uid": ADMIN.uid})
    h.service.session_appeared({**SESSION, "id": "c1", "class": "greeter"})

    assert h.service.timekeeper.sessions == {}


# --- warnings and time up ----------------------------------------------------


def test_a_daily_child_is_warned_then_locked(h):
    h.policy(mode="daily", daily_minutes=11)
    h.service.session_appeared(SESSION)

    h.play(11 * 60)

    warnings = [s[3][1] for s in h.signals if s[1] == "TimeWarning"]
    assert len(warnings) == 3
    assert ("Access1", "Locked", "(ss)", ("ana", "time_up")) in h.signals


def test_time_set_to_zero_locks_a_session_up_at_once(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.play(5 * 60)
    token = h.call(GREETER, "Parental1", "Unlock", ADULT)

    h.call(GREETER, "Access1", "SetTimeLeft", token, "ana", 0)
    h.play(10)

    assert ("Access1", "Locked", "(ss)", ("ana", "time_up")) in h.signals
    # What was used stays what it was: the adult sees it as it happened.
    assert 5 * 60 <= h.used() <= 5 * 60 + 10


def test_time_set_on_a_session_up_is_what_it_has_from_then(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.play(5 * 60)
    token = h.call(GREETER, "Parental1", "Unlock", ADULT)

    h.call(GREETER, "Access1", "SetTimeLeft", token, "ana", 2)
    assert h.left() == 2 * 60
    h.play(2 * 60)

    assert ("Access1", "Locked", "(ss)", ("ana", "time_up")) in h.signals


def test_the_lock_happens_in_the_right_order(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)

    h.play(60)

    assert h.machine.calls == [
        # A new session never starts on a user manager a lost lock left frozen.
        ("thaw", f"user@{ANA.uid}.service"),
        ("start_locker", "ana"),
        ("switch_to", LOCK_VT),
        ("freeze", "session-3.scope"),
        # The modules run under the child's user manager, outside the
        # session's scope (D32), and are frozen with it.
        ("freeze", f"user@{ANA.uid}.service"),
    ]


def test_locked_time_is_not_counted(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)

    h.play(600)

    assert h.used() == 60


# --- when the lock does not take (D28) -----------------------------------------


def test_a_switch_that_does_not_happen_ends_the_session(h):
    h.policy(mode="daily", daily_minutes=1)
    h.machine.switch_works = False
    h.service.session_appeared(SESSION)

    h.play(60)

    assert ("terminate", SESSION["path"]) in h.machine.calls
    assert ("lock", "failed") in [(a, o) for a, o, _ in h.audit]
    assert "Locked" not in h.signal_names()


def test_a_lock_screen_that_does_not_start_ends_the_session(h):
    h.policy(mode="daily", daily_minutes=1)
    h.machine.locker_starts = False
    h.service.session_appeared(SESSION)

    h.play(60)

    assert ("switch_to", LOCK_VT) not in h.machine.calls
    assert ("terminate", SESSION["path"]) in h.machine.calls


def test_a_lock_screen_systemd_refuses_to_start_ends_the_session(h):
    # Without kidux-session there is no lock screen unit at all. A time limit
    # that cannot lock is not a limit; the session ends instead (D28).
    h.policy(mode="daily", daily_minutes=1)
    h.machine.locker_refused = True
    h.service.session_appeared(SESSION)

    h.play(60)

    assert ("terminate", SESSION["path"]) in h.machine.calls
    assert ("lock", "failed") in [(a, o) for a, o, _ in h.audit]


# --- the lock screen: an adult gives more time ---------------------------------


def test_an_adult_gives_more_time_from_the_lock_screen(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)
    h.machine.calls.clear()

    assert h.call(GREETER, "Access1", "GrantExtraTime", ADULT, "ana", 5) is True

    assert h.machine.calls == [
        ("thaw", f"user@{ANA.uid}.service"),
        ("thaw", "session-3.scope"),
        ("switch_to", CHILD_VT),
        ("wake_input",),
        ("stop_locker", "ana"),
    ]
    assert ("Access1", "Unlocked", "(s)", ("ana",)) in h.signals
    h.play(60)
    assert h.left() == 240


def test_a_wrong_adult_password_gives_nothing_and_is_audited(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)

    assert h.call(GREETER, "Access1", "GrantExtraTime", "a guess", "ana", 60) is False

    assert h.left() == 0
    assert ("grant", "denied") in [(a, o) for a, o, _ in h.audit]


def test_grants_are_audited_with_their_minutes(h):
    # So an adult can see they gave three extra half-hours this week.
    h.policy(mode="manual")
    h.call(GREETER, "Access1", "AuthoriseSession", ADULT, "ana", 30)

    assert ("grant", "ok", {"caller": "_greetd", "child": "ana", "minutes": 30}) in h.audit


@pytest.mark.parametrize("minutes", [0, 24 * 60 + 1])
def test_a_grant_out_of_range_is_refused(h, minutes):
    with pytest.raises(InvalidArgument):
        h.call(GREETER, "Access1", "GrantExtraTime", ADULT, "ana", minutes)


# --- the lock screen: the child ------------------------------------------------


def test_a_child_locks_themselves_and_continues(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.play(300)

    h.call(ANA, "Access1", "Lock")
    assert ("Access1", "Locked", "(ss)", ("ana", "requested")) in h.signals
    h.play(900)   # dinner

    assert h.call(GREETER, "Access1", "ContinueSession", "ana", "ana-pw") is True
    assert h.used() == 300


@pytest.mark.parametrize("reason", ["idle", "lid"])
def test_a_session_left_alone_or_with_its_lid_closed_locks_itself(h, reason):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.play(300)

    h.call(ANA, "Access1", "LockFor", reason)

    assert ("Access1", "Locked", "(ss)", ("ana", reason)) in h.signals
    assert ("lock", "ok", {"child": "ana", "reason": reason}) in h.audit
    h.play(900)
    assert h.used() == 300                     # not counted while locked


def test_a_session_locks_itself_for_no_other_reason(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)

    with pytest.raises(InvalidArgument):
        h.call(ANA, "Access1", "LockFor", "requested")
    assert not h.service.timekeeper.sessions["ana"].locked


def test_a_lock_for_idleness_right_after_continuing_is_a_frozen_timer_s(h):
    # The session's idle timer ran out while it was frozen under the lock
    # screen; it fires as the session thaws, and must not lock it again.
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "Lock")
    assert h.call(GREETER, "Access1", "ContinueSession", "ana", "ana-pw") is True

    with pytest.raises(NoSession):
        h.call(ANA, "Access1", "LockFor", "idle")
    assert not h.service.timekeeper.sessions["ana"].locked
    h.call(ANA, "Access1", "LockFor", "lid")    # the lid is never a timer's
    assert h.service.timekeeper.sessions["ana"].locked


def test_a_lock_for_idleness_later_on_locks(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "Lock")
    assert h.call(GREETER, "Access1", "ContinueSession", "ana", "ana-pw") is True
    h.play(30)

    h.call(ANA, "Access1", "LockFor", "idle")

    assert h.service.timekeeper.sessions["ana"].locked


def test_continuing_gives_the_screen_back_then_wakes_the_input_devices(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.calls.clear()

    assert h.call(GREETER, "Access1", "ContinueSession", "ana", "ana-pw") is True

    # The compositor must have the screen back before its devices are woken,
    # and the lock screen goes only after both.
    assert h.machine.calls == [
        ("thaw", f"user@{ANA.uid}.service"),
        ("thaw", "session-3.scope"),
        ("switch_to", CHILD_VT),
        ("wake_input",),
        ("stop_locker", "ana"),
    ]


def test_continuing_with_the_wrong_password_is_refused(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "Lock")

    assert h.call(GREETER, "Access1", "ContinueSession", "ana", "luis-pw") is False
    assert h.service.timekeeper.sessions["ana"].locked


def test_continuing_with_no_time_left_is_refused_with_its_own_error(h):
    # The screen has to be able to say "your time is up for today", not
    # "wrong password".
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)

    with pytest.raises(NoTimeLeft):
        h.call(GREETER, "Access1", "ContinueSession", "ana", "ana-pw")


def test_the_next_day_the_child_continues_with_a_fresh_allowance(h):
    # A daily child who leaves the session locked overnight simply continues.
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)

    h.clock.advance(18 * 3600)

    assert h.call(GREETER, "Access1", "ContinueSession", "ana", "ana-pw") is True
    assert h.left() == 60


def test_the_adult_password_also_continues(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "Lock")

    assert h.call(GREETER, "Access1", "ContinueSession", "ana", ADULT) is True
    assert ("continue", "ok", {"child": "ana", "by": "adult"}) in h.audit


@pytest.mark.parametrize("method", ["ContinueSession", "EndSession"])
def test_the_adult_password_never_reaches_pam(h, method):
    # PAM would log it as a failed attempt at the child's account, and make
    # the adult wait out pam_faildelay first.
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "Lock")

    assert h.call(GREETER, "Access1", method, "ana", ADULT) is True
    assert h.pam_asked == []


def test_the_childs_own_password_still_goes_to_pam(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "Lock")

    assert h.call(GREETER, "Access1", "ContinueSession", "ana", "ana-pw") is True
    assert h.pam_asked == [("ana", "ana-pw")]


@pytest.mark.parametrize("interface,method,reply", [
    ("Access1", "Usage", (0, 3600)),
    ("Modules1", "List", []),
])
def test_the_trusted_screens_may_ask_about_any_child(h, interface, method, reply):
    # The panel shows each child's time and modules; the scope check that
    # keeps a child to themselves does not apply to the trusted screens.
    h.policy(mode="daily", daily_minutes=60)

    assert h.call(GREETER, interface, method, "ana") == reply
    assert h.call(GREETER, interface, method, "luis") is not None


# --- unlocking so the child can save -------------------------------------------


def test_unlock_to_save_is_not_charged_and_locks_again(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)

    assert h.call(GREETER, "Access1", "UnlockForSaving", ADULT, 2) is True
    assert not h.service.timekeeper.sessions["ana"].locked

    h.play(130)

    assert h.used() == 60
    assert ("Access1", "Locked", "(ss)", ("ana", "grace")) in h.signals


def test_unlock_to_save_is_short(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)

    with pytest.raises(InvalidArgument):
        h.call(GREETER, "Access1", "UnlockForSaving", ADULT, 16)


def test_unlock_to_save_needs_a_locked_session(h):
    with pytest.raises(NoSession):
        h.call(GREETER, "Access1", "UnlockForSaving", ADULT, 5)


# --- the machine going down, the daemon stopping ------------------------------


def test_powering_off_thaws_a_locked_session_first(h):
    # systemd refuses to stop a frozen unit, and a frozen module could not
    # save: both units are thawed, without unlocking, before logind is asked.
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.calls.clear()

    h.call(GREETER, "System1", "Shutdown")

    assert h.machine.calls == [("thaw", f"user@{ANA.uid}.service"), ("thaw", "session-3.scope")]
    assert h.service.logind.powered_off
    assert h.service.timekeeper.sessions["ana"].locked


def test_the_daemon_stopping_thaws_what_it_froze(h):
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.calls.clear()

    h.service.stopping()

    assert h.machine.calls == [("thaw", f"user@{ANA.uid}.service"), ("thaw", "session-3.scope")]


# --- ending ------------------------------------------------------------------


def test_logging_out_from_the_lock_screen_thaws_then_ends(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)
    h.machine.calls.clear()

    assert h.call(GREETER, "Access1", "EndSession", "ana", "ana-pw") is True

    assert h.machine.calls[:3] == [
        ("thaw", f"user@{ANA.uid}.service"),
        ("thaw", "session-3.scope"),
        ("terminate", SESSION["path"]),
    ]


def test_a_session_ended_on_purpose_is_not_taken_for_an_abandoned_one(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)
    assert h.call(GREETER, "Access1", "EndSession", "ana", "ana-pw") is True
    # logind is ending it: closing, until it is gone.
    h.machine.closing.add(SESSION["path"])
    h.machine.calls.clear()

    h.service.tick()

    assert ("stop_scope", "session-3.scope") not in h.machine.calls
    assert not any(entry[0] == "abandoned session ended" for entry in h.audit)


def test_a_locked_session_that_ends_by_itself_takes_its_lock_screen_with_it(h):
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.calls.clear()

    h.service.session_disappeared("3")

    assert ("stop_locker", "ana") in h.machine.calls
    assert not h.machine.locker_up
    # The user manager outlives the session: left frozen, it would hang the
    # child's next session.
    assert ("thaw", f"user@{ANA.uid}.service") in h.machine.calls


def test_a_locked_session_whose_compositor_is_gone_is_thawed_and_ended(h):
    # greetd stopping ends the compositor, and logind cannot stop the frozen scope
    # with the launcher left in it (locker.py, `abandoned`).
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.closing.add(SESSION["path"])
    h.machine.calls.clear()

    h.service.session_appeared({"id": "c7", "path": "/org/freedesktop/login1/session/c7",
                                "uid": GREETER.uid, "class": "greeter", "scope": "",
                                "vtnr": 7})

    # logind has given up on it, so the scope itself is stopped.
    assert h.machine.calls[:3] == [
        ("thaw", f"user@{ANA.uid}.service"),
        ("thaw", "session-3.scope"),
        ("stop_scope", "session-3.scope"),
    ]
    assert ("stop_locker", "ana") in h.machine.calls
    assert any(entry[0] == "abandoned session ended" for entry in h.audit)

    # Until logind says it is gone, it is not ended twice.
    h.machine.calls.clear()
    h.service.tick()
    assert ("stop_scope", "session-3.scope") not in h.machine.calls
    h.service.session_disappeared("3")
    assert h.service.timekeeper.find("3") is None


def test_the_clock_also_notices_an_abandoned_locked_session(h):
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.closing.add(SESSION["path"])
    h.machine.calls.clear()

    h.service.tick()

    assert ("stop_scope", "session-3.scope") in h.machine.calls


def test_a_locked_session_still_whole_is_left_locked(h):
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.calls.clear()

    h.service.tick()
    h.service.session_appeared({"id": "c7", "path": "/org/freedesktop/login1/session/c7",
                                "uid": GREETER.uid, "class": "greeter", "scope": "",
                                "vtnr": 7})

    assert ("stop_scope", "session-3.scope") not in h.machine.calls
    assert h.machine.locker_up


def test_ending_a_session_takes_the_lock_screen_down_even_if_logind_objects(h):
    h.service.session_appeared(SESSION)
    h.service.attention("power_button")
    h.machine.terminate_fails = True
    h.machine.calls.clear()

    try:
        h.service.locker.end(h.service.timekeeper.find("3"))
    except RuntimeError:
        pass

    assert ("stop_locker", "ana") in h.machine.calls


def test_log_out_and_back_in_does_not_reset_the_count(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.play(600)

    h.service.session_disappeared("3")
    h.service.session_appeared({**SESSION, "id": "4", "path": "/s/4", "scope": "session-4.scope"})
    h.play(60)

    assert h.used() == 660


# --- the daemon restarting ---------------------------------------------------


def test_a_daemon_restart_mid_session_loses_at_most_a_tick(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.play(600)

    h.build()
    h.service.session_appeared(SESSION)
    h.play(60)

    assert h.used() == 660


def test_a_daemon_restart_while_locked_locks_again(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)
    h.machine.calls.clear()

    h.build()
    h.service.session_appeared(SESSION)

    assert ("start_locker", "ana") in h.machine.calls
    assert h.service.timekeeper.sessions["ana"].lock == "time_up"


def test_a_session_locked_when_the_computer_went_off_is_not_locked_at_the_next_sign_in(h):
    # The computer suspended, then hung or lost its power, under Ana's
    # locked session; at the next boot she signs in with her password.
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.service.going_to_sleep()
    h.machine.calls.clear()

    h.build()
    h.service.timekeeper.boot_id = "another-boot"
    h.service.session_appeared(SESSION)

    assert ("start_locker", "ana") not in h.machine.calls
    assert h.service.timekeeper.sessions["ana"].lock == "none"


def test_a_state_without_a_boot_counts_as_this_boot_s(h):
    h.policy(mode="daily", daily_minutes=1)
    h.service.session_appeared(SESSION)
    h.play(60)
    _, usage, _ = h.service.timekeeper.load("ana")
    h.service.timekeeper.save("ana", h.service.timekeeper.load("ana")[0],
                              usage.__class__(**{**usage.__dict__, "boot": ""}))
    h.machine.calls.clear()

    h.build()
    h.service.timekeeper.boot_id = "another-boot"
    h.service.session_appeared(SESSION)

    assert ("start_locker", "ana") in h.machine.calls

# --- secure attention (D16) --------------------------------------------------


def test_the_power_button_locks_an_unlocked_session(h):
    h.policy(mode="unlimited")
    h.service.session_appeared(SESSION)

    h.service.attention("power_button")

    assert ("Access1", "Locked", "(ss)", ("ana", "power_button")) in h.signals


def test_the_power_button_with_nobody_signed_in_asks_the_sign_in_screen(h):
    h.service.attention("power_button")

    assert ("Daemon1", "AttentionRequested", "(s)", ("power_button",)) in h.signals


# --- who may ask what ----------------------------------------------------------


def test_a_child_may_see_their_own_time(h):
    h.policy(mode="daily", daily_minutes=60)

    assert h.call(ANA, "Access1", "Usage", "ana") == (0, 3600)


def test_a_child_may_not_see_a_siblings_time(h):
    with pytest.raises(NotAuthorized):
        h.call(ANA, "Access1", "Usage", "luis")


def test_setting_a_policy_needs_a_token(h):
    with pytest.raises(NotUnlocked):
        h.call(ADMIN, "Access1", "SetPolicy", "", "ana", {"mode": "unlimited"})


def test_setting_a_policy_keeps_the_bank(h):
    h.policy(mode="manual", granted_seconds=1800)
    token = h.call(ADMIN, "Parental1", "Unlock", ADULT)

    h.call(ADMIN, "Access1", "SetPolicy", token, "ana", {"mode": "daily", "daily_minutes": 30})

    assert h.call(ADMIN, "Access1", "GetPolicy", "ana") == {
        "mode": "daily", "daily_minutes": 30, "granted_seconds": 1800, "days": [True] * 7,
    }


def test_the_days_are_set_with_the_policy_and_kept_when_not_sent(h):
    # D54. The clock is on a Tuesday; every day but Tuesday.
    token = h.call(ADMIN, "Parental1", "Unlock", ADULT)
    days = [True, False, True, True, True, True, True]

    h.call(ADMIN, "Access1", "SetPolicy", token, "ana",
           {"mode": "daily", "daily_minutes": 30, "days": days})

    assert h.call(ADMIN, "Access1", "GetPolicy", "ana")["days"] == days
    assert h.call(GREETER, "Access1", "CheckAccess", "ana") == ("day_off", 0)
    assert ("policy set", "ok", {"caller": "admin", "child": "ana", "mode": "daily",
                                 "daily_minutes": 30, "days": "1011111"}) in h.audit
    h.call(ADMIN, "Access1", "SetPolicy", token, "ana", {"mode": "unlimited"})
    assert h.call(ADMIN, "Access1", "GetPolicy", "ana")["days"] == days
    assert h.call(GREETER, "Access1", "CheckAccess", "ana") == ("day_off", 0)


def test_an_adult_s_grant_lets_a_child_in_on_a_day_not_ticked(h):
    h.policy(mode="daily", daily_minutes=60, days=(True, False) + (True,) * 5)

    assert h.call(GREETER, "Access1", "AuthoriseSession", ADULT, "ana", 15) is True

    assert h.call(GREETER, "Access1", "CheckAccess", "ana") == ("allowed", 15 * 60)


def test_a_grant_after_the_morning_s_use_on_a_day_unticked_since_gives_its_minutes(h):
    # An unlimited child has used the computer all Tuesday morning when the
    # adult unticks Tuesdays: the session locks as when time runs out, and
    # fifteen minutes given from the lock screen are fifteen minutes.
    h.policy(mode="unlimited")
    h.service.session_appeared(SESSION)
    h.play(3 * 3600, step=600)
    token = h.call(ADMIN, "Parental1", "Unlock", ADULT)
    h.call(ADMIN, "Access1", "SetPolicy", token, "ana",
           {"mode": "unlimited", "days": [True, False] + [True] * 5})
    h.play(60)
    assert ("Access1", "Locked", "(ss)", ("ana", "time_up")) in h.signals

    assert h.call(GREETER, "Access1", "GrantExtraTime", ADULT, "ana", 15) is True

    assert ("Access1", "Unlocked", "(s)", ("ana",)) in h.signals
    assert h.left() == 15 * 60
    h.play(10 * 60)
    assert 4 * 60 <= h.left() <= 5 * 60
    assert h.signal_names().count("Locked") == 1


def test_a_session_up_at_the_reset_hour_into_a_day_not_ticked_is_locked(h):
    # Tuesday evening, no limit; Wednesday is not ticked. At four in the
    # morning the time is spent, as when a daily allowance runs out.
    h.policy(mode="unlimited", days=(True, True, False) + (True,) * 4)
    h.service.session_appeared(SESSION)

    h.play(10 * 3600 + 50 * 60, step=600)
    assert "Locked" not in h.signal_names()
    h.play(20 * 60, step=60)

    assert ("Access1", "Locked", "(ss)", ("ana", "time_up")) in h.signals
    assert h.call(GREETER, "Access1", "CheckAccess", "ana") == ("day_off", 0)


def test_the_bank_cannot_be_written_through_a_policy(h):
    token = h.call(ADMIN, "Parental1", "Unlock", ADULT)

    with pytest.raises(InvalidArgument):
        h.call(ADMIN, "Access1", "SetPolicy", token, "ana",
               {"mode": "manual", "granted_seconds": 10 ** 6})


def test_check_access_for_each_mode(h):
    h.policy("ana", mode="manual")
    h.policy("luis", mode="daily", daily_minutes=0)

    assert h.call(GREETER, "Access1", "CheckAccess", "ana") == ("needs_adult", 0)
    assert h.call(GREETER, "Access1", "CheckAccess", "luis") == ("blocked", 0)

    h.call(GREETER, "Access1", "AuthoriseSession", ADULT, "ana", 20)
    assert h.call(GREETER, "Access1", "CheckAccess", "ana") == ("allowed", 1200)


# --- updates from the panel (daemon.md section 13) --------------------------------


class UpdateRunner:
    def __init__(self, status):
        self.status, self.active, self.started, self.packages = status, False, [], []

    def start_update(self, kind, package=""):
        self.started.append(kind)
        self.packages.append(package)
        self.active = True
        self.status.write_text(f"kidux:job:{kind}\n")

    def update_active(self):
        return self.active

    daily = ("inactive", "success")
    daily_started = 0

    def daily_upgrade_state(self):
        return self.daily

    def start_daily_upgrade(self):
        self.daily_started += 1
        self.daily = ("activating", "success")


@pytest.fixture
def updates(h, tmp_path):
    from kiduxd.updates import Updates

    runner = UpdateRunner(tmp_path / "update.status")
    h.service.updates = Updates(runner, status=runner.status)
    token = h.call(ADMIN, "Parental1", "Unlock", ADULT)
    return runner, token


def test_updates_need_a_token(h, updates):
    with pytest.raises(NotUnlocked):
        h.call(ADMIN, "System1", "CheckUpdates", "")


def test_looking_for_updates_is_allowed_while_a_child_plays(h, updates):
    runner, token = updates
    h.service.session_appeared(SESSION)

    h.call(ADMIN, "System1", "CheckUpdates", token)

    assert runner.started == ["check"]
    assert h.call(GREETER, "System1", "UpdateState")[0] == "checking"


def test_installing_is_refused_while_any_child_has_a_session(h, updates):
    runner, token = updates
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "Lock")

    with pytest.raises(SessionActive):
        h.call(ADMIN, "System1", "ApplyUpdates", token)
    assert runner.started == []


def test_installing_with_nobody_signed_in(h, updates):
    runner, token = updates

    h.call(ADMIN, "System1", "ApplyUpdates", token)

    assert runner.started == ["apply"]
    assert ("update started", "ok") in [(a, o) for a, o, _ in h.audit]


def test_no_session_starts_while_an_update_is_being_installed(h, updates):
    runner, token = updates
    h.policy(mode="unlimited")
    h.call(ADMIN, "System1", "ApplyUpdates", token)

    assert h.call(GREETER, "Access1", "CheckAccess", "ana")[0] == "updating"

    with open(runner.status, "a") as status:
        status.write("kidux:done:updated\n")
    runner.active = False
    h.service.updates.poll()
    assert h.call(GREETER, "Access1", "CheckAccess", "ana")[0] == "allowed"


def test_no_session_starts_while_debian_s_daily_upgrade_runs(h, updates):
    runner, _token = updates
    h.policy(mode="unlimited")
    runner.daily = ("active", "success")

    assert h.call(GREETER, "Access1", "CheckAccess", "ana")[0] == "updating"

    runner.daily = ("inactive", "success")
    assert h.call(GREETER, "Access1", "CheckAccess", "ana")[0] == "allowed"


def test_the_last_child_s_logout_makes_up_a_skipped_daily_upgrade(h, updates):
    runner, _token = updates
    h.service.session_appeared(SESSION)
    runner.daily = ("inactive", "exec-condition")

    h.service.session_disappeared("3")

    assert runner.daily_started == 1


def test_a_logout_after_a_daily_upgrade_that_ran_starts_nothing(h, updates):
    runner, _token = updates
    h.service.session_appeared(SESSION)

    h.service.session_disappeared("3")

    assert runner.daily_started == 0


def test_a_child_may_not_ask_about_updates(h, updates):
    with pytest.raises(AccessDenied):
        h.call(ANA, "System1", "UpdateState")



# --- sleep (D119) ------------------------------------------------------------


def test_a_session_locks_before_the_computer_sleeps(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.play(300)

    h.service.going_to_sleep()

    assert ("Access1", "Locked", "(ss)", ("ana", "sleep")) in h.signals
    h.play(900)
    assert h.used() == 300                     # a closed lid is not a way out


def test_a_session_already_locked_stays_as_it_is_when_the_computer_sleeps(h):
    h.policy(mode="daily", daily_minutes=60)
    h.service.session_appeared(SESSION)
    h.call(ANA, "Access1", "LockFor", "lid")

    h.service.going_to_sleep()

    assert ("Access1", "Locked", "(ss)", ("ana", "sleep")) not in h.signals


def test_sleeping_with_nobody_signed_in_locks_nothing(h):
    h.service.going_to_sleep()

    assert not [s for s in h.signals if s[1] == "Locked"]
