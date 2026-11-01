"""Every test gets its own state root and data root, never the machine's.

`kidux.paths` reads its roots from the environment when it is imported, and
every module reads `paths.X` when it is called, so setting the environment and
reloading the module in place is enough to point the whole daemon somewhere
else.
"""

import importlib

import argon2
import pytest

from kidux import paths

LANGUAGES = {"en_US.UTF-8", "es_ES.UTF-8"}

AVATAR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" aria-label="x">'
    '<circle cx="5" cy="5" r="5"/></svg>'
)


@pytest.fixture(autouse=True)
def roots(tmp_path, monkeypatch):
    state_root = tmp_path / "state"
    data_root = tmp_path / "data"
    (data_root / "avatars").mkdir(parents=True)
    for name in ("fox", "owl", "star"):
        (data_root / "avatars" / f"{name}.svg").write_text(AVATAR_SVG)
    (data_root / "locales").write_text(
        "# test\n" + "".join(f"{lang} UTF-8\n" for lang in sorted(LANGUAGES))
    )

    monkeypatch.setenv("KIDUX_STATE_ROOT", str(state_root))
    monkeypatch.setenv("KIDUX_DATA_ROOT", str(data_root))
    # For a daemon started in a subprocess, which reads it when it imports
    # kiduxd.updates: the machine's own, under /run/kidux, is root's.
    monkeypatch.setenv("KIDUX_UPDATE_STATUS", str(tmp_path / "update.status"))
    monkeypatch.setenv("KIDUX_CHROMIUM_FLAGS", str(tmp_path / "etc" / "chromium-flags"))
    monkeypatch.setenv("KIDUX_INPUT_XML", str(tmp_path / "etc" / "input.xml"))
    monkeypatch.setenv("KIDUX_APT_STATISTICS", str(tmp_path / "etc" / "61kidux-statistics"))
    monkeypatch.setenv("KIDUX_LOGIND_POWER", str(tmp_path / "etc" / "logind-power.conf"))
    monkeypatch.setenv("KIDUX_SLEEP_POWER", str(tmp_path / "etc" / "sleep-power.conf"))
    # A computer with Secure Boot off and a swap partition, unless a test
    # writes them otherwise.
    (tmp_path / "lockdown").write_text("[none] integrity confidentiality\n")
    (tmp_path / "swaps").write_text("Filename\tType\tSize\tUsed\tPriority\n"
                                    "/dev/sda2 partition\t1000\t0\t-1\n")
    monkeypatch.setenv("KIDUX_LOCKDOWN", str(tmp_path / "lockdown"))
    monkeypatch.setenv("KIDUX_SWAPS", str(tmp_path / "swaps"))
    (tmp_path / "resume").write_text("8:2\n")
    (tmp_path / "cmdline").write_text("BOOT_IMAGE=/boot/vmlinuz root=UUID=x ro quiet\n")
    monkeypatch.setenv("KIDUX_RESUME", str(tmp_path / "resume"))
    monkeypatch.setenv("KIDUX_CMDLINE", str(tmp_path / "cmdline"))
    importlib.reload(paths)
    yield state_root
    monkeypatch.undo()
    importlib.reload(paths)


@pytest.fixture
def fast_hasher():
    """argon2 with the cost turned right down: correctness, not strength, is tested."""
    return argon2.PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
