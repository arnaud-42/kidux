"""Kidux's typing lessons, built as Tux Typing's themes (lessons/build.py)."""

import importlib.util
import os
import tomllib
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lessons", PACKAGE / "lessons" / "build.py")
lessons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lessons)


def test_each_language_gets_a_theme_of_its_lessons_named_as_the_list_shows_them(tmp_path):
    lessons.build(tmp_path)

    spanish = sorted(p.name for p in (tmp_path / "kidux-es" / "scripts").iterdir())
    english = sorted(p.name for p in (tmp_path / "kidux-en" / "scripts").iterdir())
    # Spanish has two lessons more, at the end, for the accented vowels.
    assert (len(spanish), len(english)) == (14, 12)
    assert spanish[0] == "Lección 01 - a s d f.xml"
    assert spanish[1] == "Lección 02 - j k l ñ.xml"
    assert spanish[11] == "Lección 12 - x z y punto.xml"
    assert spanish[12:] == ["Lección 13 - á y é.xml", "Lección 14 - í ó y ú.xml"]
    assert english[-1] == "Lesson 12 - x z and stop.xml"


def test_a_theme_has_its_keyboard_table_its_words_and_its_locale(tmp_path):
    lessons.build(tmp_path)

    spanish, english = tmp_path / "kidux-es", tmp_path / "kidux-en"
    assert os.readlink(spanish / "images") == "../espanol/images"
    assert os.readlink(english / "words") == "../../words"
    assert (spanish / "settings.txt").read_text() == "theme_locale_name=es_ES.UTF-8\n"
    # Each table places every key by its US one: the ñ where the US
    # keyboard has the semicolon, an accented vowel on its vowel, and the
    # space by its finger alone.
    table = set((spanish / "keyboard.lst").read_text(encoding="utf-8").splitlines())
    assert {"9|ñ|;", "9|Ñ|:", "5| ", "7|,|,", "8|.|.", "9|-|/",
            "0|á|a", "0|Á|A", "2|é|e", "7|í|i", "8|ó|o", "6|ú|u", "6|Ú|U"} <= table
    table = set((english / "keyboard.lst").read_text(encoding="utf-8").splitlines())
    assert {"0|a|a", "0|A|A", "9|;|;", "5| "} <= table
    assert all(line.startswith("#") or line == "5| " or (len(line) == 5 and line[3] == "|")
               for line in table)


def test_spanish_games_get_kidux_s_word_lists_with_the_ene_and_the_accents(tmp_path):
    lessons.build(tmp_path)

    words = tmp_path / "kidux-es" / "words"
    assert not words.is_symlink()
    lists = {p.name: p.read_text(encoding="utf-8").splitlines() for p in words.iterdir()}
    assert len(lists) == 7
    names = [lines[0] for _, lines in sorted(lists.items())]
    assert names[0] == "Palabras cortas" and names[-2:] == ["Con eñe", "Con tilde"]
    every = {word for lines in lists.values() for word in lines[1:]}
    assert {"MONTAÑA", "NIÑO", "CAMIÓN", "ÁRBOL", "LÁPIZ"} <= every
    assert "MONTANA" not in every
    # The accents only in the last list, as they come at the end of the course.
    accented = set("ÁÉÍÓÚ")
    assert all(not set(word) & accented
               for name, lines in lists.items() if name != "7-tilde.txt" for word in lines[1:])


def test_a_lesson_has_the_shape_tux_typing_s_reader_runs(tmp_path):
    lessons.build(tmp_path)

    first = (tmp_path / "kidux-es" / "scripts" / "Lección 01 - a s d f.xml").read_text()
    lines = first.splitlines()
    assert lines[0].startswith('<script title="Lección 1: a s d f"')
    assert lines[-1] == "</script>"
    # Enter on the first page; P before each of the two practices, each
    # followed by an empty page; Enter on the last.
    assert first.count("<waitforinput/>") == 2
    assert first.count("<waitforchar/>") == 2
    assert "      <prac>asdf fdsa as df sa fd</prac>" in lines
    assert "      <prac>da das fa dada sasa</prac>" in lines
    assert first.count("      <page>\n      </page>") == 2
    # Every text says where it goes, or Tux Typing puts it on the top edge.
    assert all('y="' in line for line in lines if "<text " in line)
    assert "Sigue con la lección 2." in first
    twelfth = (tmp_path / "kidux-es" / "scripts" / "Lección 12 - x z y punto.xml").read_text()
    assert "Sigue con la lección 13." in twelfth
    last = (tmp_path / "kidux-es" / "scripts" / "Lección 14 - í ó y ú.xml").read_text()
    assert "Has terminado todas las lecciones." in last
    assert "      <prac>río león avión tú menú allí</prac>" in last.splitlines()
    english = (tmp_path / "kidux-en" / "scripts" / "Lesson 12 - x z and stop.xml").read_text()
    assert "You have done every lesson." in english


def problems(**changes) -> list:
    source = tomllib.loads((PACKAGE / "lessons" / "es.toml").read_text(encoding="utf-8"))
    source["lesson"][0].update(changes)
    return lessons.check(source, "es.toml")


def test_the_lessons_as_they_are_break_none_of_the_rules():
    for name in ("es.toml", "en.toml"):
        source = tomllib.loads((PACKAGE / "lessons" / name).read_text(encoding="utf-8"))
        assert lessons.check(source, name) == []


@pytest.mark.parametrize("change, said", [
    ({"drill": "asdf fdsa as df sa fd asdf fdsa as df"}, "longer than 36"),
    ({"words": "kilo"}, "not learnt yet"),
    ({"intro": ["Pon los dedos de la mano izquierda sobre la fila del medio"]}, "longer than 44"),
    ({"words": "da & fa"}, "markup"),
])
def test_a_lesson_that_tux_typing_could_not_show_well_fails_the_build(change, said):
    assert any(said in problem for problem in problems(**change)), problems(**change)


def test_a_practice_key_missing_from_the_keyboard_table_fails_the_build():
    # A key the table lacks makes the practice draw a second keyboard.
    source = tomllib.loads((PACKAGE / "lessons" / "es.toml").read_text(encoding="utf-8"))
    source["lesson"][0]["keys"] = "a s d f ¿"
    source["lesson"][0]["drill"] = "asdf ¿"
    assert any("keyboard table lacks" in p for p in lessons.check(source, "es.toml"))


def test_a_practice_key_the_table_does_not_place_fails_the_build(tmp_path, monkeypatch):
    # A key with its finger alone gets no frame and no label on the keyboard.
    short = tmp_path / "short.lst"
    short.write_text("0|a\n0|s|s\n2|d|d\n3|f|f\n5| \n", encoding="utf-8")
    monkeypatch.setattr(lessons, "HERE", tmp_path)
    source = tomllib.loads((PACKAGE / "lessons" / "es.toml").read_text(encoding="utf-8"))
    source.update(keyboard="short.lst", word_lists="")
    source["lesson"] = source["lesson"][:1]
    source["lesson"][0]["words"] = "fa"
    assert any("does not place: ['a']" in p for p in lessons.check(source, "es.toml"))


@pytest.mark.parametrize("words, said", [
    (["Animales", "perro"], "not one word in capitals"),
    (["Animales", "PERRO", "PERRO"], "there twice"),
    (["Animales", "HIPOPOTAMOSAURIO"], "longer than 12"),
    (["Animales", "PINGÜINO"], "keyboard table lacks"),
    (["", "PERRO"], "no name"),
])
def test_a_word_list_the_games_could_not_use_fails_the_build(tmp_path, words, said):
    path = tmp_path / "words-es" / "1-animales.txt"
    path.parent.mkdir()
    path.write_text("\n".join(words) + "\n", encoding="utf-8")
    source = tomllib.loads((PACKAGE / "lessons" / "es.toml").read_text(encoding="utf-8"))
    table = lessons.keyboard_table(source)
    assert any(said in p for p in lessons.check_words(path, table)), lessons.check_words(path, table)


def test_french_lessons_are_for_the_azerty_keyboard(tmp_path):
    lessons.build(tmp_path)

    french = tmp_path / "kidux-fr"
    scripts = sorted(p.name for p in (french / "scripts").iterdir())
    # The ten fingers' twelve, and three for é è, à ç ù and the circumflex.
    assert len(scripts) == 15
    assert scripts[0] == "Leçon 01 - q s d f.xml"
    assert scripts[-1] == "Leçon 15 - accent circonflexe.xml"
    assert (french / "settings.txt").read_text() == "theme_locale_name=fr_FR.UTF-8\n"
    # Tux Typing's French theme has no pictures, so the theme takes none.
    assert not (french / "images").exists()
    # Each key on its US one: the a on the q, the m on the semicolon, the
    # é on the 2, a vowel with a circumflex on its vowel.
    table = set((french / "keyboard.lst").read_text(encoding="utf-8").splitlines())
    assert {"0|a|q", "0|q|a", "1|z|w", "0|w|z", "9|m|;", "9|M|:", "6|,|m",
            "1|é|2", "6|è|7", "8|ç|9", "9|à|0", "9|ù|'", "2|ê|e", "5| "} <= table


def test_french_games_get_kidux_s_word_lists_with_their_accents(tmp_path):
    lessons.build(tmp_path)

    words = tmp_path / "kidux-fr" / "words"
    assert not words.is_symlink()
    lists = {p.name: p.read_text(encoding="utf-8").splitlines() for p in words.iterdir()}
    assert len(lists) == 7
    every = {word for lines in lists.values() for word in lines[1:]}
    assert {"ÉLÉPHANT", "FORÊT", "GARÇON", "OÙ", "ZÈBRE"} <= every
    assert "FEVRIER" not in every and "ELEPHANT" not in every
