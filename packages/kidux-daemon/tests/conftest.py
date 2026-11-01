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
    importlib.reload(paths)
    yield state_root
    monkeypatch.undo()
    importlib.reload(paths)


@pytest.fixture
def fast_hasher():
    """argon2 with the cost turned right down: correctness, not strength, is tested."""
    return argon2.PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
