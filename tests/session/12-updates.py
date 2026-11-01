"""Updates from the panel, by keyboard: looked for, found, installed (plan step 9.8).

The package it updates is made in the machine and served from a directory
(`kidux-as canary`); the real archive is never touched. Then the System
page's Advanced settings (D52): Chromium's options, set from the command
line before the panel opened, shown on their page, and saved again from it.

Last, Debian's daily upgrade fenced as the panel's install is (D115), with
a stand-in for it that only leaves a mark and waits, so that nothing needs
to be there to install: under Leo's session it is skipped; when Leo logs
out the daemon starts it; and Leo, signing in while it runs, waits on the
sign-in screen and gets in once it has finished.
"""

import time

from sessionlib import (
    CHILD_PASSWORD,
    Machine,
    active_terminal,
    child_session,
    children_count,
    greeter_log,
    open_panel,
    report,
    root,
    wait,
)

AUDIT = "/home/.kidux/state/audit.log"
DAILY = "apt-daily-upgrade.service"
#: The stand-in's drop-in, beside kidux-base's own, and the mark it leaves.
STAND_IN = "/etc/systemd/system/apt-daily-upgrade.service.d/zz-kidux-test.conf"
RAN = "/var/tmp/daily-upgrade.ran"
#: How long the stand-in takes, long enough for Leo to try to sign in.
STAND_IN_SECONDS = 45


def audit_line(action: str, outcome: str) -> bool:
    lines = root(f"grep '\"action\": \"{action}\"' {AUDIT}").stdout.splitlines()
    return any(f'"outcome": "{outcome}"' in line for line in lines)


def daily(field: str) -> str:
    return root(f"systemctl show -p {field} --value {DAILY}").stdout.strip()


def runs() -> int:
    return len(root(f"cat {RAN} 2>/dev/null").stdout.split())


def sign_in(machine: Machine) -> None:
    """Leo, the first picture, and Leo's password."""
    password = machine.mark()
    machine.key("ret")
    machine.shown("password", password)
    machine.submit(CHILD_PASSWORD)


def log_out(machine: Machine) -> bool:
    """Leo logs out from the lock screen, past Continue and Adult."""
    locked = machine.mark()
    machine.monitor("system_powerdown")
    wait(lambda: active_terminal() == "tty8", 20)
    machine.shown("locked", locked)
    machine.key("tab")
    machine.key("tab")
    asked = machine.mark()
    machine.key("ret")
    machine.shown("child_password", asked)
    choose = machine.submit(CHILD_PASSWORD)
    gone = wait(lambda: child_session() is None, 30)
    machine.shown("choose", choose, 30)
    return gone


def daily_upgrade(machine: Machine) -> None:
    unit = ("[Service]\nExecStartPre=\nExecStart=\n"
            f"ExecStart=/bin/sh -c 'echo ran >> {RAN}; sleep {STAND_IN_SECONDS}'\n")
    root(f"rm -f {RAN} && mkdir -p {STAND_IN.rsplit('/', 1)[0]} "
         f"&& printf '%s' \"{unit}\" > {STAND_IN} && systemctl daemon-reload")
    report("Debian's daily upgrade has kidux-base's condition, beside the test's stand-in",
           "kidux-no-child-session" in daily("ExecCondition")
           and root(f"systemctl cat {DAILY}").stdout.count("zz-kidux-test.conf") == 1,
           root(f"systemctl cat {DAILY}").stdout)

    sign_in(machine)
    signed_in = wait(lambda: child_session() is not None, 30)
    root(f"systemctl start {DAILY}", timeout=120)
    report("with Leo signed in, it is skipped, and nothing of it runs",
           signed_in and daily("Result") == "exec-condition" and runs() == 0,
           daily("Result") + "\n" + root(f"journalctl -b -u {DAILY} --no-pager | tail -5").stdout)

    report("when Leo logs out, the daemon starts it",
           log_out(machine) and wait(lambda: runs() == 1, 30)
           and audit_line("daily upgrade", "started"),
           root(f"journalctl -b -u {DAILY} --no-pager | tail -5").stdout
           + root(f"tail -3 {AUDIT}").stdout)

    # While it runs, Leo's password gets the waiting screen, which goes back
    # to the pictures by itself; once it has finished, Leo gets in.
    waiting = machine.mark()
    sign_in(machine)
    held = (machine.shown("waiting", waiting, 15) and child_session() is None
            and daily("ActiveState") in ("active", "activating"))
    finished = wait(lambda: daily("ActiveState") == "inactive", STAND_IN_SECONDS + 30, 2)
    choose = machine.mark()
    machine.shown("choose", choose, 30)
    sign_in(machine)
    report("Leo, signing in while it runs, waits, and gets in once it has finished",
           held and finished and wait(lambda: child_session() is not None, 30),
           greeter_log())
    report("and the run Leo waited for was the only one", runs() == 1,
           root(f"cat {RAN}").stdout)
    log_out(machine)

    root(f"rm -f {STAND_IN} {RAN} && systemctl daemon-reload")


def suspending(machine: Machine) -> None:
    """The System page's Suspending the computer (D119): the lid's setting
    suspends; Nothing chosen for the lid is written for logind at once."""
    open_panel(machine)
    machine.still()
    for _ in range(5 + children_count() + 3):
        machine.key("shift-tab")
    before = machine.mark()
    machine.key("ret")
    machine.shown("panel_system", before, 10)
    # From the current password, as for Advanced, and one more.
    for _ in range(11):
        machine.key("tab")
    before = machine.mark()
    machine.key("ret")
    shown = machine.shown("panel_power", before, 10)
    machine.screenshot("panel-system-power")
    conf = "/etc/systemd/logind.conf.d/50-kidux-power.conf"
    report("Suspending the computer, beside Advanced, has the lid suspend",
           shown and "HandleLidSwitch=suspend\n" in root(f"cat {conf}").stdout,
           greeter_log() + root(f"cat {conf}").stdout)

    # The lid's list has the focus: its last choice, Nothing.
    machine.key("ret")
    machine.still(2)
    machine.key("end")
    before = machine.mark()
    machine.key("ret")
    machine.shown("panel_power", before, 10)
    report("choosing Nothing for the lid has logind ignore it, at once",
           wait(lambda: "HandleLidSwitch=ignore\n" in root(f"cat {conf}").stdout, 10)
           and root(f"stat -c '%U %a' {conf}").stdout.strip() == "root 644",
           root(f"cat {conf}").stdout + root(f"tail -2 {AUDIT}").stdout)
    root("runuser -u debian -- /usr/local/bin/kidux-as set-config lid_action "
         "'\"sleep\"'")
    before = machine.mark()
    machine.key("esc")                           # the panel closes
    machine.shown("choose", before)


def run(machine: Machine) -> None:
    made = root("/usr/local/bin/kidux-as canary")
    report("a package to update waits in a local repository", made.returncode == 0,
           made.stdout + made.stderr)
    root("runuser -u debian -- /usr/local/bin/kidux-as set-config chromium_flags "
         "'[\"--disable-gpu-compositing\"]'")

    report("the adult panel opens from the sign-in screen", open_panel(machine), greeter_log())
    machine.still()
    # From the first child's name: back past the five controls that give
    # time, every child, Add and Network, to System.
    children = children_count()
    for _ in range(5 + children + 3):
        machine.key("shift-tab")
    before = machine.mark()
    machine.key("ret")
    report("the system page", machine.shown("panel_system", before, 10), greeter_log())
    machine.screenshot("panel-updates-none")

    # From the current password, back past Show, to Look for updates.
    machine.key("shift-tab")
    machine.key("shift-tab")
    machine.key("ret")
    found = wait(lambda: audit_line("update check", "ok"), 180, 2)
    time.sleep(2)                                # the page asks the daemon once a second
    machine.screenshot("panel-updates-found")
    report("looking for updates from the panel finds the one there is", found,
           root(f"tail -3 {AUDIT}").stdout)

    machine.key("shift-tab")
    machine.key("shift-tab")
    machine.key("ret")                           # Install
    time.sleep(2)
    machine.screenshot("panel-updates-progress")
    finished = wait(lambda: audit_line("update finished", "ok"), 300, 2)
    time.sleep(2)                                # the page asks the daemon once a second
    machine.screenshot("panel-updates-done")
    version = root("dpkg-query -W -f='${Version}' kidux-test-canary").stdout.strip()
    report("and installing it from the panel puts it in place", finished and version == "1.1",
           version + "\n" + root(f"tail -3 {AUDIT}").stdout)

    # The page drawn again has the focus on the current password: past the
    # new one twice, Save, language, keyboard, scale, and the two minutes and
    # Set of a computer left alone, to the button under Advanced.
    for _ in range(10):
        machine.key("tab")
    before = machine.mark()
    machine.key("ret")
    shown = machine.shown("panel_advanced", before, 10)
    machine.screenshot("panel-system-advanced")
    report("Advanced, on the System page, shows the pointer's steps and Chromium's options "
           "for this machine",
           shown and root("cat /etc/kidux/chromium-flags").stdout == "--disable-gpu-compositing\n",
           greeter_log())
    saves = int(root(f"grep -c '\"action\": \"config set\"' {AUDIT}").stdout.strip() or 0)
    # From the pointer's speed, past the scroll's, the statistics switch and
    # the options, to Save.
    for _ in range(4):
        machine.key("tab")
    before = machine.mark()
    machine.key("ret")
    machine.shown("panel_advanced", before, 10)
    report("and Save there keeps them, in the file Chromium's starter reads",
           wait(lambda: int(root(f"grep -c '\"action\": \"config set\"' {AUDIT}").stdout.strip()
                            or 0) > saves, 10)
           and root("stat -c '%U %a' /etc/kidux/chromium-flags").stdout.strip() == "root 644"
           and root("cat /etc/kidux/chromium-flags").stdout == "--disable-gpu-compositing\n",
           root(f"tail -2 {AUDIT}").stdout)
    root("runuser -u debian -- /usr/local/bin/kidux-as set-config chromium_flags '[]'")

    # The page drawn again has the focus on the pointer's speed: on to the
    # touchpad's scroll, whose list opens with no step chosen until a key
    # moves in it; Home is its first, Much slower.
    machine.key("tab")
    machine.key("ret")
    machine.still(2)
    machine.key("home")
    before = machine.mark()
    machine.key("ret")
    machine.shown("panel_advanced", before, 10)
    machine.screenshot("panel-system-advanced-scroll")
    report("choosing Much slower for two fingers writes it where a child's session reads it",
           wait(lambda: "<scrollFactor>0.25</scrollFactor>"
                in root("cat /etc/kidux/input.xml").stdout, 10)
           and root("stat -c '%U %a' /etc/kidux/input.xml").stdout.strip() == "root 644",
           root("cat /etc/kidux/input.xml").stdout + root(f"tail -2 {AUDIT}").stdout)
    root("runuser -u debian -- /usr/local/bin/kidux-as set-config scroll_speed 0")

    before = machine.mark()
    machine.key("esc")                           # the panel closes
    machine.shown("choose", before)
    root("rm -f /etc/apt/sources.list.d/kidux-test-canary.list")
    machine.still()

    suspending(machine)
    daily_upgrade(machine)
