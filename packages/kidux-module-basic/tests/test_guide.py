"""The guide beside the machine (D84; docs/dev/basic.md): its page built
with every language's words and chapters, its four conventions, its
drawings, and every listing of it a program that runs on wwwBASIC."""

import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
CONTENT = PACKAGE / "content"
# wwwBASIC as the package build copies it, or where WWWBASIC says.
WWWBASIC = Path(os.environ.get("WWWBASIC", PACKAGE / "build" / "wwwbasic" / "wwwbasic.mjs"))


def builder():
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("page", str(PACKAGE / "webapp" / "page.py"))
    spec = importlib.util.spec_from_loader("page", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def node():
    return os.environ.get("NODE") or shutil.which("node") or shutil.which("nodejs")


def test_every_language_has_the_same_chapters():
    english = sorted(path.name for path in (CONTENT / "en").glob("*.md"))
    assert english
    for language in CONTENT.iterdir():
        assert sorted(path.name for path in language.glob("*.md")) == english, language.name


def test_the_page_holds_every_language_its_words_and_its_chapters(tmp_path):
    locale = tmp_path / "locale" / "es" / "LC_MESSAGES"
    locale.mkdir(parents=True)
    subprocess.run(["msgfmt", "-o", str(locale / "kidux-module-basic.mo"),
                    str(PACKAGE / "po" / "es.po")], check=True)
    output = tmp_path / "index.html"

    builder().main(["page.py", str(tmp_path / "locale"), str(CONTENT), str(PACKAGE / "drawings"),
                    str(PACKAGE / "webapp" / "index.html.in"), str(output)])

    html = output.read_text()
    data = json.loads(html.split("const PAGES = ", 1)[1].split(";\n", 1)[0])
    assert set(data) == {entry.name for entry in CONTENT.iterdir() if entry.is_dir()}
    assert data["es"]["words"]["run"] == "Ejecutar" and data["en"]["words"]["run"] == "Run"
    assert len(data["es"]["chapters"]) == len(data["en"]["chapters"]) >= 1
    for language in data.values():
        for chapter in language["chapters"]:
            number = int(chapter["slug"].split("-", 1)[0])
            assert chapter["title"].startswith(f"{number}. ")
            assert chapter["html"].startswith(f"<h1>{number}. ")
            assert "KEPT" not in chapter["html"] and ":::" not in chapter["html"]
            assert "```" not in chapter["html"]
    assert "@PAGES@" not in html


def test_the_guide_s_five_conventions(tmp_path):
    words = {"typeIn": "Type it in for me", "adult": "For the adult"}
    heading, html = builder().chapter(
        "# A chapter\n\nWords.\n\n> [point] Look **here**.\n\n"
        "```basic keys=Leo,Enter\n10 INPUT \"NAME? \"; N$\n20 PRINT N$ < 3\n```\n\n"
        "![A penguin](mascot.svg)\n\n::: adult\nFor *you*.\n:::\n\n"
        "::: type-in\nThe button *types*.\n:::\n",
        PACKAGE / "drawings", words)

    assert heading == "A chapter"
    assert '<div class="listing"><pre>10 INPUT &quot;NAME? &quot;; N$\n20 PRINT N$ &lt; 3\n</pre>' in html
    assert '<button type="button" class="type-in">Type it in for me</button>' in html
    assert "keys=" not in html
    assert '<div class="bubble"><svg aria-hidden="true"' in html and "<strong>here</strong>" in html
    assert '<figure class="drawing"><svg role="img" aria-label="A penguin"' in html
    assert '<details class="adult"><summary>For the adult</summary><p>For <em>you</em>.</p></details>' in html
    assert '<div class="type-in-note"><p>The button <em>types</em>.</p></div>' in html


def test_every_drawing_a_chapter_names_is_there():
    for chapter in CONTENT.glob("*/*.md"):
        for name in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", chapter.read_text()):
            assert (PACKAGE / "drawings" / name).is_file(), f"{chapter}: {name}"


def listings():
    page = builder()
    for chapter in sorted(CONTENT.glob("*/*.md")):
        for number, listing in enumerate(page.listings(page.body(chapter)), 1):
            yield pytest.param(listing, id=f"{chapter.parent.name}/{chapter.stem}#{number}")


@pytest.mark.skipif(not WWWBASIC.is_file(), reason="wwwBASIC is built only in a package build")
@pytest.mark.parametrize("listing", listings())
def test_every_listing_of_the_guide_runs(listing, tmp_path):
    program = tmp_path / "listing.bas"
    program.write_text(listing["code"] + "\n")
    ran = subprocess.run([node(), str(PACKAGE / "tests" / "run-basic.js"), str(WWWBASIC), "--one",
                          str(program), *listing["keys"]], capture_output=True, text=True, timeout=60)
    result = json.loads(ran.stdout)

    if listing["mistake"]:
        # A listing wrong on purpose: BASIC stops before it prints anything.
        assert result["error"] and not result["text"], f"{listing['code']}\n{result}"
        return
    assert result["error"] is None, f"{listing['code']}\n{result}"
    assert result["ended"] or listing["forever"], f"it did not end: {listing['code']}\n{result}"


def test_type_in_for_me_switched_off_hides_the_buttons_and_what_speaks_of_them():
    # D90: the adult's setting reaches the page as ?type_in=0.
    template = (PACKAGE / "webapp" / "index.html.in").read_text()
    style = (PACKAGE / "webapp" / "style.css").read_text()

    assert '.get("type_in") === "0"' in template and 'classList.add("no-type-in")' in template
    assert ".no-type-in .type-in, .no-type-in .type-in-note { display: none; }" in style
    for language in ("en", "es", "fr"):
        assert "::: type-in" in (CONTENT / language / "01-hello.md").read_text()

