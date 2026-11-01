"""config.toml: the settings that belong to the machine rather than to a child."""

from dataclasses import dataclass

from kidux import paths, state

DEFAULTS = {
    "default_language": "en_US.UTF-8",
    "default_keyboard": "us",
    # 0 is automatic, until an adult chooses one (kidux.screen, D49).
    "display_scale": 0.0,
    "reset_hour": 4,
    # A session left alone locks after this many minutes, and the adult
    # panel closes (D67); the screen turns off after the second.
    "idle_lock_minutes": 5,
    "screen_off_minutes": 10,
    # How long an adult's *Unlock to save* gives a child whose time is up.
    # The panel does not offer it; the session tests set it to 1, so as not
    # to wait five minutes.
    "save_minutes": 5,
    "setup_complete": False,
    # Set once a language has been chosen for the machine, by the first-run
    # wizard or the panel: it is how the wizard, restarted to apply the
    # keyboard, knows it is past its first two steps.
    "language_chosen": False,
    # Chromium's flags for this machine's graphics (advanced.py, D52).
    "chromium_flags": [],
    # The pointer's speed and the touchpad's scroll, a step from -2 to 2
    # each (kidux.pointer).
    "pointer_speed": 0,
    "scroll_speed": 0,
    # Whether every fetch of the package archive carries an identifier of
    # this machine's, so that the archive's logs count it as one machine
    # (statistics.py, D109), and the identifier, made the first time it is
    # needed and kept for good.
    "apt_statistics": True,
    "apt_statistics_id": "",
    # What closing the lid does, what a computer still left alone this many
    # minutes after its last touch does, and how long a computer that sleeps
    # and then turns off saving sleeps first, which no page offers (power.py,
    # D119). A machine whose config.toml predates them takes these.
    "lid_action": "sleep_then_hibernate",
    "idle_action": "sleep_then_hibernate",
    "idle_sleep_minutes": 20,
    "hibernate_delay_seconds": 60,
}


@dataclass
class Config:
    default_language: str
    default_keyboard: str
    display_scale: float
    reset_hour: int
    idle_lock_minutes: int
    screen_off_minutes: int
    save_minutes: int
    setup_complete: bool
    language_chosen: bool
    chromium_flags: list
    pointer_speed: int
    scroll_speed: int
    apt_statistics: bool
    apt_statistics_id: str
    lid_action: str
    idle_action: str
    idle_sleep_minutes: int
    hibernate_delay_seconds: int

    @classmethod
    def load(cls) -> "Config":
        document = state.read(paths.CONFIG_FILE, "config", default=DEFAULTS)
        merged = {**DEFAULTS, **document}
        return cls(**{key: merged[key] for key in DEFAULTS})

    def save(self) -> None:
        state.write(paths.CONFIG_FILE, self.as_dict(), "config")

    def as_dict(self) -> dict:
        return {key: getattr(self, key) for key in DEFAULTS}
