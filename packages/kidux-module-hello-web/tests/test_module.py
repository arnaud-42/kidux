"""The reference web application, as the launcher and Chromium will find
it: its manifest read by the one reader (D34), its page in both languages,
its words complete."""

import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

from kidux import modules

PACKAGE = Path(__file__).resolve().parents[1]


def builder():
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("page", str(PACKAGE / "webapp" / "page.py"))
    spec = importlib.util.spec_from_loader("page", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_the_manifest_reads_as_the_launcher_reads_it(tmp_path):
    (tmp_path / "hello-web").mkdir()
    for name in ("module.toml", "icon.svg"):
        shutil.copy(PACKAGE / name, tmp_path / "hello-web" / name)

    web = modules.read("hello-web", root=tmp_path)

    assert web is not None
    assert web.launch == {"webapp": "hello-web"}
    assert (web.i18n_domain, web.memory_max) == ("kidux-module-hello-web", "3G")


def test_the_manifests_version_is_the_packages():
    changelog = (PACKAGE / "debian" / "changelog").read_text().split("\n", 1)[0]
    version = changelog.split("(", 1)[1].split(")", 1)[0]

    assert f'version = "{version}"' in (PACKAGE / "module.toml").read_text()


def test_the_page_holds_every_language_and_its_words(tmp_path):
    locale = tmp_path / "locale" / "es" / "LC_MESSAGES"
    locale.mkdir(parents=True)
    subprocess.run(["msgfmt", "-o", str(locale / "kidux-module-hello-web.mo"),
                    str(PACKAGE / "po" / "es.po")], check=True)
    output = tmp_path / "index.html"

    builder().main(["page.py", str(tmp_path / "locale"), str(PACKAGE / "content"),
                    str(PACKAGE / "webapp" / "index.html.in"), str(output)])

    html = output.read_text()
    data = json.loads(html.split("const PAGES = ", 1)[1].split(";\n", 1)[0])
    assert set(data) == {entry.name for entry in (PACKAGE / "content").iterdir() if entry.is_dir()}
    assert data["fr"]["heading"].startswith("Bonjour")
    assert data["es"]["heading"] == "¡Hola!" and data["en"]["heading"] == "Hello!"
    assert len(data["es"]["paragraphs"]) == 3
    assert data["es"]["words"]["done"] == "Hecho"
    assert data["en"]["words"]["done"] == "Done"
    assert (data["es"]["words"]["save"], data["es"]["words"]["file"]) == ("Guardar", "hola")
    assert "@PAGES@" not in html


def test_the_catalogue_is_complete():
    untranslated = subprocess.run(
        ["msgattrib", "--untranslated", "--only-fuzzy", "--no-obsolete",
         str(PACKAGE / "po" / "es.po")], capture_output=True, text=True, check=True).stdout
    assert [line for line in untranslated.splitlines() if line.startswith('msgid "')
            and line != 'msgid ""'] == []
