"""Small text helpers for German: folding, slugs, word matching."""
from __future__ import annotations

import re
import unicodedata

_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def fold(s: str | None) -> str:
    """Case- and umlaut-insensitive key: 'Thüringen' and 'thueringen' fold equal."""
    if not s:
        return ""
    s = s.translate(_FOLD).casefold()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def slug(s: str, max_len: int = 60) -> str:
    s = fold(s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:max_len].rstrip("-") or "doc"


_WORD = re.compile(r"[0-9A-Za-zÄÖÜäöüß]+")


def words(s: str) -> list[str]:
    return [fold(w) for w in _WORD.findall(s or "")]


def contains_phrase(text_words: list[str], phrase: str) -> bool:
    """True if the folded words of `phrase` occur consecutively in text_words.
    A phrase word ending in '*' matches any word with that prefix."""
    pw = phrase.split()
    pw = [fold(w) for w in pw]
    if not pw:
        return False
    n = len(pw)
    for i in range(len(text_words) - n + 1):
        ok = True
        for j, p in enumerate(pw):
            t = text_words[i + j]
            if p.endswith("*"):
                if not t.startswith(p[:-1]):
                    ok = False
                    break
            elif t != p:
                ok = False
                break
        if ok:
            return True
    return False


def operator_forms(infinitive: str) -> set[str]:
    """Surface forms of a German operator verb as used in task texts:
    'berechnen' -> berechnen, berechne, berechnet; 'skizzieren' -> skizziere, ..."""
    inf = fold(infinitive)
    forms = {inf}
    stem = inf[:-2] if inf.endswith("en") else inf[:-1] if inf.endswith("n") else inf
    forms |= {stem, stem + "e", stem + "t", stem + "et"}
    return {f for f in forms if len(f) >= 4}
