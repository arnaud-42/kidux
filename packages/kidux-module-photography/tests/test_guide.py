"""The guide (docs/dev/photography.md): its page built with every language's
words and chapters, its seven conventions, every drawing and photograph it
names there, and every photograph credited, small enough and without the
camera's metadata."""

import importlib.machinery
import importlib.util
import json
import re
import struct
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
CONTENT = PACKAGE / "content"
DRAWINGS = PACKAGE / "drawings"
PICTURES = PACKAGE / "pictures"
LICENCES = {"CC0-1.0", "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-2.0",
            "CC-BY-SA-3.0", "CC-BY-SA-4.0", "public-domain", "GPL-3.0-or-later"}
NAMED = re.compile(r"!\[[^\]]*\]\(([a-z0-9-]+\.(?:svg|jpg))(?: \"[^\"]*\")?\)")


def builder():
    sys.dont_write_bytecode = True
    loader = importlib.machinery.SourceFileLoader("page", str(PACKAGE / "webapp" / "page.py"))
    spec = importlib.util.spec_from_loader("page", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def chapters():
    return sorted(CONTENT.glob("*/*.md"))


def listed() -> dict:
    with (PICTURES / "pictures.toml").open("rb") as file:
        return tomllib.load(file)


def jpeg_size(path: Path) -> tuple[int, int]:
    """A JPEG's width and height, from its frame header."""
    data = path.read_bytes()
    assert data[:2] == b"\xff\xd8", f"{path.name} is not a JPEG"
    at = 2
    while at < len(data):
        marker, length = data[at + 1], struct.unpack(">H", data[at + 2:at + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[at + 5:at + 9])
            return width, height
        at += 2 + length
    raise AssertionError(f"{path.name} has no frame header")


def test_every_language_has_the_same_chapters():
    english = sorted(path.name for path in (CONTENT / "en").glob("*.md"))
    assert english
    for language in CONTENT.iterdir():
        assert sorted(path.name for path in language.glob("*.md")) == english, language.name


def test_the_page_holds_every_language_its_words_and_its_chapters(tmp_path):
    locale = tmp_path / "locale" / "es" / "LC_MESSAGES"
    locale.mkdir(parents=True)
    subprocess.run(["msgfmt", "-o", str(locale / "kidux-module-photography.mo"),
                    str(PACKAGE / "po" / "es.po")], check=True)
    output = tmp_path / "index.html"

    builder().main(["page.py", str(tmp_path / "locale"), str(CONTENT), str(DRAWINGS),
                    str(PICTURES), str(PACKAGE / "webapp" / "index.html.in"), str(output)])

    html = output.read_text()
    data = json.loads(html.split("const PAGES = ", 1)[1].split(";\n", 1)[0])
    assert set(data) == {entry.name for entry in CONTENT.iterdir() if entry.is_dir()}
    assert data["es"]["words"]["next"] == "Siguiente" and data["en"]["words"]["next"] == "Next"
    assert data["es"]["words"]["title"] == "Fotografía"
    assert len(data["es"]["chapters"]) == len(data["en"]["chapters"]) >= 1
    for language in data.values():
        for chapter in language["chapters"]:
            number = int(chapter["slug"].split("-", 1)[0])
            assert chapter["title"].startswith(f"{number}. ")
            assert chapter["html"].startswith(f"<h1>{number}. ")
            assert "KEPT" not in chapter["html"] and ":::" not in chapter["html"]
            assert "![" not in chapter["html"]
    assert "@PAGES@" not in html
    # Every photograph says its size, so that the page keeps its room.
    assert re.search(r'<img src=\\"pictures/[a-z0-9-]+\.jpg\\" alt=\\"[^"]*\\" width=\\"\d+\\" height=\\"\d+\\"', html)


def test_the_guide_s_seven_conventions():
    page = builder()
    words = {key: text for key, text in page.WORDS.items()}
    pictures = {"cat.jpg": {"author": "Ana Example", "licence": "CC-BY-SA-4.0",
                            "source": "https://commons.wikimedia.org/wiki/File:A_cat_%28sleeping%29.jpg"},
                "dog.jpg": {"author": "generated", "licence": "GPL-3.0-or-later"},
                "old.jpg": {"author": "Niépce", "licence": "public-domain"},
                "cut.jpg": {"author": "Bo Example", "licence": "CC-BY-2.0", "made": "cropped"}}
    heading, html = page.chapter(
        "# A chapter\n\nWords.\n\n> [point] Look **here**.\n\n"
        "::: try\n1. Hold it.\n2. Press.\n:::\n\n"
        "::: camera\nThe dial (manual, p. 8).\n:::\n\n"
        "::: adult\nFor *you*.\n:::\n\n"
        "![A penguin](mascot.svg)\n\n"
        "![A cat](cat.jpg \"thirds\")\n\n"
        "::: compare\n![A dog](dog.jpg)\n\n![Old](old.jpg)\n\n![The chick](mascot.svg)\n:::\n\n"
        "![Cut](cut.jpg)\n",
        DRAWINGS, words, pictures)

    assert heading == "A chapter"
    assert '<div class="bubble"><svg aria-hidden="true"' in html and "<strong>here</strong>" in html
    assert '<section class="try"><h3>Try it</h3><ol>' in html
    assert ('<section class="camera"><h3>On the Olympus XZ-2</h3><p class="others">Other '
            'cameras have the same thing under other names') in html
    assert '<details class="adult"><summary>For the adult</summary><p>For <em>you</em>.</p></details>' in html
    assert '<figure class="drawing"><svg role="img" aria-label="A penguin"' in html
    assert ('<figure class="photo thirds"><div class="frame"><img src="pictures/cat.jpg" '
            'alt="A cat" loading="lazy"></div><figcaption>A cat'
            '<span class="credit">Photo: Ana Example, CC BY-SA 4.0</span>'
            '<span class="source">https://commons.wikimedia.org/wiki/File:A_cat_(sleeping).jpg</span>') in html
    assert '<div class="compare"><figure class="photo">' in html
    assert '<span class="credit">Picture made by a computer</span>' in html
    assert '<span class="credit">Photo: Niépce, public domain</span>' in html
    assert '<span class="credit">Photo: Bo Example, CC BY 2.0, edited</span>' in html
    assert '<svg role="img" aria-label="The chick"' in html and "<figcaption>The chick</figcaption>" in html
    assert "<p><figure" not in html


def test_every_drawing_and_photograph_a_chapter_names_is_there():
    for chapter in chapters():
        for name in NAMED.findall(chapter.read_text()):
            folder = DRAWINGS if name.endswith(".svg") else PICTURES
            assert (folder / name).is_file(), f"{chapter}: {name}"


def test_every_photograph_is_credited_and_every_credit_is_of_a_photograph_shown():
    credited = listed()
    named = {name for chapter in chapters() for name in NAMED.findall(chapter.read_text())
             if name.endswith(".jpg")}
    assert named <= set(credited), named - set(credited)
    assert set(credited) <= named, set(credited) - named
    for name, entry in credited.items():
        assert entry.get("licence") in LICENCES, name
        assert entry.get("author") and entry.get("source"), name
        if entry["author"] == "generated":
            assert entry["licence"] == "GPL-3.0-or-later" and entry.get("model"), name
            assert (PICTURES / "prompts" / f"{name[:-4]}.txt").is_file(), name
        elif entry["licence"] != "GPL-3.0-or-later":
            assert entry["source"].startswith(("https://commons.wikimedia.org/wiki/File:",
                                                "https://www.flickr.com/photos/")), name


def test_every_photograph_is_small_and_has_no_metadata():
    for picture in PICTURES.glob("*.jpg"):
        width, height = jpeg_size(picture)
        assert max(width, height) <= 1400, picture.name
        assert picture.stat().st_size < 400_000, picture.name
        data = picture.read_bytes()
        assert b"Exif\x00\x00" not in data and b"http://ns.adobe.com/xap" not in data, picture.name


def test_every_photograph_not_kiduxs_is_in_debian_copyright():
    copyright_ = (PACKAGE / "debian" / "copyright").read_text()
    for name, entry in listed().items():
        if entry["licence"] != "GPL-3.0-or-later":
            assert f"Files: pictures/{name}\n" in copyright_, name


@pytest.mark.parametrize("chapter", chapters(), ids=lambda path: f"{path.parent.name}/{path.stem}")
def test_a_chapter_has_its_box_for_the_adult_and_its_camera_box_names_the_manual(chapter):
    text = chapter.read_text()
    assert "::: adult\n" in text
    for box in re.findall(r"^::: camera\n(.*?)\n:::$", text, re.M | re.S):
        assert re.search(r"\((?:manual|manual de la cámara|manuel), p(?:p)?\. \d+", box), chapter.name


@pytest.mark.parametrize("chapter", chapters(), ids=lambda path: f"{path.parent.name}/{path.stem}")
def test_a_comparison_holds_two_to_four_pictures(chapter):
    for box in re.findall(r"^::: compare\n(.*?)\n:::$", chapter.read_text(), re.M | re.S):
        assert 2 <= len(NAMED.findall(box)) <= 4, chapter.name
