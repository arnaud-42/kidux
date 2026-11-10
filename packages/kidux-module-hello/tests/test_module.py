"""The reference module, as the launcher and the panel will find it: its
manifest read by the one reader (D34), its catalogue complete, its page in
both languages."""

import importlib.machinery
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from kidux import modules

PACKAGE = Path(__file__).resolve().parents[1]


def program():
    # Nothing is written beside the program: bin/ is what the package installs.
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("hello", str(PACKAGE / "bin" / "kidux-module-hello"))
    spec = importlib.util.spec_from_loader("hello", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_the_manifest_reads_as_the_launcher_reads_it(tmp_path):
    (tmp_path / "hello").mkdir()
    for name in ("module.toml", "icon.svg"):
        shutil.copy(PACKAGE / name, tmp_path / "hello" / name)

    hello = modules.read("hello", root=tmp_path)

    assert hello is not None
    assert (hello.name, hello.description) == ("[Test] Hello", "A first page to read, and a button to press.")
    assert hello.launch == {"exec": "/usr/libexec/kidux-module-hello"}
    assert hello.i18n_domain == "kidux-module-hello"
    assert (hello.min_age, hello.max_age, hello.memory_max) == (4, 8, "1G")
    assert hello.icon == str(tmp_path / "hello" / "icon.svg")


def test_the_manifests_version_is_the_packages():
    changelog = (PACKAGE / "debian" / "changelog").read_text().split("\n", 1)[0]
    version = changelog.split("(", 1)[1].split(")", 1)[0]

    assert f'version = "{version}"' in (PACKAGE / "module.toml").read_text()


def test_the_catalogue_is_complete_and_holds_the_manifests_words():
    catalogue = PACKAGE / "po" / "es.po"
    untranslated = subprocess.run(
        ["msgattrib", "--untranslated", "--only-fuzzy", "--no-obsolete", str(catalogue)],
        capture_output=True, text=True, check=True).stdout
    text = catalogue.read_text()

    assert [line for line in untranslated.splitlines() if line.startswith('msgid "')
            and line != 'msgid ""'] == []
    for words in ("Hello", "A first page to read, and a button to press.", "Done"):
        assert f'msgid "{words}"' in text


def test_the_page_is_the_childs_language_or_english():
    hello = program()
    content = PACKAGE / "content"

    heading, paragraphs = hello.page("es", content)
    assert heading == "¡Hola!"
    assert len(paragraphs) == 3 and "source_sha256" not in " ".join(paragraphs)
    assert hello.page("fr", content)[0].startswith("Bonjour")
    assert hello.page("de", content) == hello.page("en", content)
    assert hello.page("en", content)[0] == "Hello!"


def test_the_language_comes_from_the_session(monkeypatch):
    hello = program()
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    assert hello.language() == "en"
    monkeypatch.setenv("LANG", "es_ES.UTF-8")
    assert hello.language() == "es"
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    assert hello.language() == "es"
