"""A session left alone locks itself, and a screen left alone turns off
(D67, phase-3-plan.md step 3.30).

An adult sets a minute to lock and two to turn the screen off, from the
command line as the panel's System page does. Leo signs in and touches
nothing: a minute later the session is locked, the lock screen up, the
audit saying why. Two minutes more on
the lock screen and it turns off; the child's session, frozen, turned
nothing off. A key turns the lock screen on again, Leo continues, and the
timer that ran out while the session was frozen does not lock it again.
Still left alone, a screen asks the daemon to sleep (D119): not while
something holds idleness off, and otherwise the machine sleeps, Leo's
session locked first, and wakes on the lock screen. The settings go back
to five and ten, and Leo logs out.
"""

import time

from sessionlib import (
    CHILD_PASSWORD,
    Machine,
    active_terminal,
    child_session,
    greeter_log,
    journal_count,
    launcher_shown,
    report,
    root,
    wait,
)

AS = "runuser -u debian -- /usr/local/bin/kidux-as"
AUDIT = "/home/.kidux/state/audit.log"


def idle_log() -> str:
    return root("journalctl -b -o cat -t kidux-idle | tail -12").stdout


def audit_says(action: str, reason: str) -> bool:
    lines = root(f"grep '\"action\": \"{action}\"' {AUDIT}").stdout.splitlines()
    return any(f'"reason": "{reason}"' in line for line in lines)


def count(text: str) -> int:
    return journal_count("kidux-idle", text)


def run(machine: Machine) -> None:
    root(f"{AS} set-config idle_lock_minutes 1")
    root(f"{AS} set-config screen_off_minutes 2")

    counting = "swayidle started (tty7, lock 60 s, screen off 120 s, sleep 1200 s)"
    before = count(counting)
    password = machine.mark()
    machine.key("ret")                           # Leo, the first picture
    machine.shown("password", password)
    machine.submit(CHILD_PASSWORD)
    signed_in = wait(lambda: child_session() is not None, 30) and launcher_shown(machine)
    report("Leo signs in, and the session counts a minute to lock and two to turn off",
           signed_in and wait(lambda: count(counting) > before, 20),
           greeter_log() + idle_log())

    # Nothing touched: a minute later the session locks itself.
    locked = machine.mark()
    report("a minute without a touch locks the session",
           wait(lambda: active_terminal() == "tty8", 100, 2)
           and machine.shown("locked", locked, 30) and audit_says("lock", "idle"),
           active_terminal() + "\n" + idle_log())

    # Two minutes more on the lock screen: it turns off. The child's
    # session is frozen, and turns nothing off.
    child_offs = count("screen off (tty7)")
    offs = count("screen off (tty8)")
    report("two minutes without a touch turn the lock screen off",
           wait(lambda: count("screen off (tty8)") > offs, 150, 3), idle_log())
    picture = machine.screenshot("screen-off")
    report("and the child's session, frozen, turned nothing off",
           count("screen off (tty7)") == child_offs, f"{picture}\n" + idle_log())

    # A key turns it on again.
    ons = count("screen on (tty8)")
    machine.key("ctrl")
    report("a key turns the lock screen on again",
           wait(lambda: count("screen on (tty8)") > ons, 15), idle_log())

    # Leo continues: the timer that ran out while the session was frozen
    # does not lock it again, and the count starts afresh.
    started = count("swayidle started (tty7")
    before = machine.mark()
    machine.key("ret")                           # Continue
    machine.shown("child_password", before)
    machine.type(CHILD_PASSWORD + "\n")
    back = wait(lambda: active_terminal() == "tty7", 15)
    time.sleep(15)
    report("Leo continues, and the session is not locked again by a frozen timer",
           back and active_terminal() == "tty7"
           and wait(lambda: count("swayidle started (tty7") > started, 10),
           active_terminal() + "\n" + idle_log())

    # Still left alone, the screen asks the daemon to sleep, as kidux-idle's
    # third timeout does (D119). Nothing while idleness is held off.
    sleep_when_idle = ("busctl call org.kidux.Daemon1 /org/kidux/Daemon1 "
                      "org.kidux.Daemon1.System1 SleepWhenIdle")
    held = root(f"systemd-inhibit --what=idle --why=test sleep 30 & sleep 1; "
                f"{sleep_when_idle}").stdout
    report("a screen left alone while something holds idleness off does not sleep",
           held.strip() == 's ""' and active_terminal() == "tty7", held)
    time.sleep(30)

    # Otherwise the machine sleeps, Leo's session locked first; QEMU's
    # monitor wakes it.
    root(f"({sleep_when_idle} >/dev/null 2>&1 &)", timeout=20)
    asleep = wait(lambda: "suspended" in machine.monitor("info status"), 60, 2)
    machine.monitor("system_wakeup")
    report("otherwise the machine sleeps, the session locked before it",
           asleep and wait(lambda: "PM: suspend exit" in root(
               "journalctl -b -k -o cat | tail -40").stdout, 60, 3)
           and audit_says("lock", "sleep") and active_terminal() == "tty8",
           root("journalctl -b -o cat -t kidux-daemon | tail -5").stdout)
    before = machine.mark()
    machine.key("ctrl")
    machine.shown("locked", before, 30)
    before = machine.mark()
    machine.key("ret")                           # Continue
    machine.shown("child_password", before)
    machine.type(CHILD_PASSWORD + "\n")
    report("and on waking Leo continues with the password",
           wait(lambda: active_terminal() == "tty7", 15), active_terminal())

    # The settings back as they were, and Leo logs out from the lock screen.
    root(f"{AS} set-config idle_lock_minutes 5")
    root(f"{AS} set-config screen_off_minutes 10")
    before = machine.mark()
    machine.monitor("system_powerdown")
    wait(lambda: active_terminal() == "tty8", 20)
    machine.shown("locked", before)
    machine.key("tab")
    machine.key("tab")
    before = machine.mark()
    machine.key("ret")
    machine.shown("child_password", before)
    machine.type(CHILD_PASSWORD + "\n")
    report("Leo logs out from the lock screen", wait(lambda: child_session() is None, 30),
           greeter_log())
