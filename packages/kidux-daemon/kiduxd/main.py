"""kidux-daemon's entry point: wire the real machine to the service, run the loop."""

import argparse
import signal
import sys

from gi.repository import Gio, GLib

from kidux import log, paths

from .accounts import SystemAccounts
from .attention import Chords, InputWatcher
from .bus import BusObject
from .gate import Gate, PolkitAuthority
from .locker import Locker
from .logind import SessionWatcher, SleepGuard, SystemLogind
from .machine import SystemMachine
from .network import Network
from .service import Service
from .updates import Updates
from . import statistics
from .config import Config

#: How often idle adult-panel tokens are swept. The timeout itself is minutes,
#: so a minute of slack is invisible; the check on every use is exact.
TOKEN_SWEEP_SECONDS = 60


def build(connection: Gio.DBusConnection, accounts=None, logind=None, authority=None,
          machine=None):
    """The daemon, wired to `connection`. Tests pass fakes for the machine."""
    accounts = accounts or SystemAccounts()
    logind = logind or SystemLogind(connection)
    authority = authority or PolkitAuthority(connection)
    machine = machine or SystemMachine(connection)

    bus_object: BusObject | None = None

    def emit(interface, signal_name, signature, args):
        if bus_object is not None:
            bus_object.emit(interface, signal_name, signature, args)

    service = Service(
        gate=Gate(authority, accounts),
        accounts=accounts,
        logind=logind,
        locker=Locker(machine, log.audit),
        emit=emit,
        updates=Updates(machine, emit=emit, audit=log.audit),
        modules_offered=machine.modules_offered,
        network=Network(audit=log.audit),
        kidux_packages=machine.kidux_packages,
    )
    bus_object = BusObject(connection, service)
    return service, bus_object


def serve(
    connection: Gio.DBusConnection,
    service: Service,
    bus_object: BusObject,
    *,
    watch_sessions: bool = True,
    watch_input: bool = True,
) -> int:
    logger = log.get_logger("daemon")
    loop = GLib.MainLoop()
    outcome = {"code": 0}

    # The usage-statistics snippet as config.toml has it (statistics.py): first
    # boot writes it on a new machine, and this writes it on one upgraded from
    # before the setting existed. Never before first boot, whose mark the
    # config file is.
    if paths.CONFIG_FILE.exists():
        try:
            statistics.apply(Config.load())
        except Exception:
            logger.exception("could not apply the usage statistics setting")

    bus_object.register()

    # --- the clock: one timer, re-armed after every tick for as long as the
    # next warning or time-up needs, and sooner whenever something changes.
    timer = {"source": 0}

    def schedule(delay: float) -> None:
        if timer["source"]:
            GLib.source_remove(timer["source"])
        timer["source"] = GLib.timeout_add(max(100, int(delay * 1000)), run_tick)

    def run_tick() -> bool:
        timer["source"] = 0
        try:
            delay = service.tick()
        except Exception:
            logger.exception("tick failed")
            delay = 30.0
        if not timer["source"]:
            schedule(delay)
        return GLib.SOURCE_REMOVE

    service.on_timing_changed = lambda: schedule(0.1)
    schedule(1.0)

    # --- an update job: its status file, read twice a second while it runs.
    watching = {"source": 0}

    def watch_update() -> None:
        if watching["source"] or service.updates is None:
            return

        def poll() -> bool:
            try:
                running = service.updates.poll()
            except Exception:
                logger.exception("could not read the update's status")
                running = True
            if not running:
                watching["source"] = 0
            return GLib.SOURCE_CONTINUE if running else GLib.SOURCE_REMOVE

        watching["source"] = GLib.timeout_add(500, poll)

    service.on_update_started = watch_update
    if service.updates is not None and service.updates.resume():
        watch_update()

    # --- sessions, from logind -------------------------------------------------
    if watch_sessions:
        def appeared(info):
            try:
                service.session_appeared(info)
            except Exception:
                logger.exception("could not track session %s", info.get("id"))

        def disappeared(session_id):
            try:
                service.session_disappeared(session_id)
            except Exception:
                logger.exception("could not stop tracking session %s", session_id)

        watcher = SessionWatcher(connection, appeared, disappeared)
        watcher.start()
        for info in watcher.existing():
            appeared(info)

    # --- a child's session locks before the computer sleeps (D119) -------------
    if watch_sessions:
        def going_to_sleep():
            service.going_to_sleep()

        SleepGuard(connection, going_to_sleep).start()

    # --- the power button and Ctrl+Alt+Escape ------------------------------------
    if watch_input:
        def attention(source):
            try:
                service.attention(source)
            except Exception:
                logger.exception("could not answer %s", source)

        InputWatcher(Chords(attention)).start()

    def on_lost(connection, name):
        logger.error("lost the name %s, or never got it; exiting", name)
        outcome["code"] = 1
        loop.quit()

    Gio.bus_own_name_on_connection(
        connection,
        paths.BUS_NAME,
        Gio.BusNameOwnerFlags.NONE,
        lambda *args: logger.info("serving %s", paths.BUS_NAME),
        on_lost,
    )

    def sweep():
        service.expire_tokens()
        return GLib.SOURCE_CONTINUE

    GLib.timeout_add_seconds(TOKEN_SWEEP_SECONDS, sweep)

    def stop(*_args) -> bool:
        service.stopping()
        loop.quit()
        return GLib.SOURCE_REMOVE

    for signum in (signal.SIGTERM, signal.SIGINT):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signum, stop)

    loop.run()
    return outcome["code"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kidux-daemon")
    parser.add_argument("--debug", action="store_true", help="log everything")
    arguments = parser.parse_args(argv)

    log.setup("daemon", debug=arguments.debug)
    connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    service, bus_object = build(connection)
    return serve(connection, service, bus_object)


if __name__ == "__main__":
    sys.exit(main())
