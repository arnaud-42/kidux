"""Every path, group and bus name Kidux uses, in one place.

Nothing else in Kidux may spell a path out. Four programs read and write the
same files — the greeter, the lock screen, the launcher and the daemon — and a
path written twice is a path that will eventually disagree with itself.

Every root can be overridden by an environment variable. That is what makes the
tests possible: they point the state root at a temporary directory instead of
at the real one, which is root-owned and holds the family's actual settings.
The overrides are for tests and development only; an installed system sets none
of them.
"""

import os
from pathlib import Path

# --- roots -------------------------------------------------------------------

#: Everything the daemon owns. On /home on purpose: reinstalling the system
#: partition must not lose a family's children, settings or time accounting.
#: Root-owned, group kidux-admin, mode 0750 — no child can read it.
STATE_ROOT = Path(os.environ.get("KIDUX_STATE_ROOT", "/home/.kidux"))

#: Read-only data shipped by our packages: avatars, module metadata, content.
DATA_ROOT = Path(os.environ.get("KIDUX_DATA_ROOT", "/usr/share/kidux"))

#: Compiled translation catalogues.
LOCALE_ROOT = Path(os.environ.get("KIDUX_LOCALE_ROOT", "/usr/share/locale"))

# --- state files -------------------------------------------------------------

#: Schema version, default language and keyboard for the trusted screens,
#: display scale, and the hour the daily counter resets.
CONFIG_FILE = STATE_ROOT / "config.toml"

#: The adult password hash and the GRUB recovery password. Never a child's
#: password: a child's password is their Unix password, in /etc/shadow.
ADULTS_FILE = STATE_ROOT / "adults.toml"

STATE_DIR = STATE_ROOT / "state"

#: Every privileged action, every grant of time, every attempt at the adult
#: password with its outcome. Append-only.
AUDIT_LOG = STATE_DIR / "audit.log"

CHILDREN_DIR = STATE_ROOT / "children"


def child_dir(username: str) -> Path:
    """The directory holding everything Kidux knows about one child.

    Not the child's home directory: their own files stay in /home/<username>
    and Kidux never touches them.
    """
    _reject_path_separators(username)
    return CHILDREN_DIR / username


def child_profile(username: str) -> Path:
    """Display name, language, keyboard, age and avatar."""
    return child_dir(username) / "profile.toml"


def child_access(username: str) -> Path:
    """Access mode, daily allowance and the bank of granted time."""
    return child_dir(username) / "access.toml"


def child_usage(username: str) -> Path:
    """What has been used today, and whether a session is open.

    Flushed every thirty seconds while a session is unlocked, so that a power
    cut, a crash or a deliberate reboot cannot reset a child's daily counter.
    """
    return child_dir(username) / "usage.toml"


def child_modules(username: str) -> Path:
    """Which learning modules an adult has enabled for this child."""
    return child_dir(username) / "modules.toml"


def child_module_settings(username: str) -> Path:
    """What an adult has set in each module for this child (D90), a table
    per module; secrets among it, so root's alone, as the whole directory is."""
    return child_dir(username) / "settings.toml"


# --- shipped data ------------------------------------------------------------

AVATAR_DIR = DATA_ROOT / "avatars"

#: One directory per installed learning module, holding its module.toml and
#: icon.svg (modules.md, section 1).
MODULES_DIR = DATA_ROOT / "modules"

#: Where dpkg lists each installed package's files, `<package>.list`: how a
#: module is told from a folder copied there by hand.
DPKG_INFO = Path(os.environ.get("KIDUX_DPKG_INFO", "/var/lib/dpkg/info"))

#: Kidux's logo and mascot, from the repository's branding/, for every screen
#: that shows them.
LOGO = DATA_ROOT / "branding" / "logo.svg"
MASCOT = DATA_ROOT / "branding" / "mascot.svg"
#: The hourglass beside the time a child has left.
HOURGLASS = DATA_ROOT / "icons" / "hourglass.svg"

# --- the machine's own settings, for programs that do not ask the daemon -------

#: Chromium's flags for this machine's graphics, one a line (D51, D52): the
#: daemon writes it from the panel's Advanced settings, root's and 0644, and
#: kidux-webapp, run as the child, adds them to Chromium's command line.
CHROMIUM_FLAGS = Path(os.environ.get("KIDUX_CHROMIUM_FLAGS", "/etc/kidux/chromium-flags"))

#: The pointer's speed and the touchpad's scroll (pointer.py): the daemon
#: writes it from the panel's Advanced settings, root's and 0644, and a
#: child's session puts it into labwc's configuration when it starts.
INPUT_XML = Path(os.environ.get("KIDUX_INPUT_XML", "/etc/kidux/input.xml"))

#: The identifier this machine adds to every fetch of the package archive
#: while an adult shares usage statistics (kiduxd.statistics, D109): the
#: daemon writes it, root's and 0644, as an apt configuration snippet.
APT_STATISTICS = Path(os.environ.get("KIDUX_APT_STATISTICS",
                                     "/etc/apt/apt.conf.d/61kidux-statistics"))

# --- identities --------------------------------------------------------------

#: Adults. Members may call every method on the daemon. Deliberately not a
#: polkit administrator group: that is sudo, and no child is ever in sudo.
ADMIN_GROUP = "kidux-admin"

#: Children. Members may ask about their own time, list their own modules, lock
#: the screen and turn the machine off. Nothing else.
CHILDREN_GROUP = "kidux-children"

#: The user the trusted screens run as: the sign-in screen, the lock screen and
#: the adult panel. Out of reach of anything a child can run.
GREETER_USER = "_greetd"

# --- the daemon --------------------------------------------------------------

BUS_NAME = "org.kidux.Daemon1"
OBJECT_PATH = "/org/kidux/Daemon1"

#: The gettext domain every Kidux program translates through. One domain, so a
#: word is translated once and reads the same on every screen.
GETTEXT_DOMAIN = "kidux"


def _reject_path_separators(username: str) -> None:
    """Refuse a username that would escape the children directory.

    Usernames come from the adult panel and from D-Bus calls, so they are input,
    not a given. A name containing a slash or a dot-dot would otherwise let a
    caller aim a write anywhere the daemon can reach, and the daemon is root.
    """
    if not username:
        raise ValueError("username must not be empty")
    if "/" in username or "\\" in username or username in (".", ".."):
        raise ValueError(f"invalid username: {username!r}")
