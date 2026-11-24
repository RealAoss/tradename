# Vendored from ismatch (https://github.com/RealAoss/ismatch), MIT licence, same
# author. ismatch is not published on PyPI, so tradename carries its own copy.
# Adapted for tradename; do not expect it to stay in sync with upstream.

"""Turn a single name token (Arabic, Hebrew or Latin script) into phonemes.

All three scripts are mapped onto one small shared inventory so that tokens
written in different scripts can be aligned with each other:

* ``C``  consonant            (p = b t θ j h x d ð r z s š ġ f v q k g l m n w y)
* ``V``  vowel                (p = A I U, or E for the ambiguous Latin "e")
* ``W``  "wildcard" vowel     (ayn, hamza, word-initial alef: spelled with any
                               vowel, or not at all, in Latin script)
* ``H``  weak final h         (ta marbuta / final ha: "Fatima" vs "Fatimah")
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache

__all__ = ["Ph", "latin_phonemes", "arabic_phonemes", "hebrew_phonemes", "phonemes", "clean_latin"]


class Ph:
    """One phoneme. Immutable by convention; instances are cached and shared."""

    __slots__ = ("t", "p", "long", "alt", "raw", "di", "src")

    def __init__(self, t, p, src, long=False, alt=None, raw=None, di=None):
        self.t = t        # C / V / W / H
        self.p = p        # phoneme symbol
        self.src = src    # 'la' | 'ar' | 'he'
        self.long = long  # vowel written with a letter in an abjad
        self.alt = alt    # second acceptable vowel reading (final ya / alef maqsura)
        self.raw = raw    # original letter (to tell emphatics apart within a script)
        self.di = di      # Latin digraph that may really be two consonants: ('t', 'h')

    def __repr__(self):
        return self.p if self.t == "C" else f"{self.t}:{self.p}"


# --------------------------------------------------------------------------
# Latin
# --------------------------------------------------------------------------

_LATIN_PRE = {
    "ş": "sh", "š": "sh", "ç": "ch", "č": "ch", "ğ": "gh", "ġ": "gh", "ž": "j",
    "ǧ": "j", "ḫ": "kh", "ẖ": "kh", "ṯ": "th", "ḏ": "dh", "ı": "i", "ß": "ss",
    "æ": "ae", "ø": "o", "ʿ": "3", "ʕ": "3", "ʻ": "3",
}
# "Arabizi" chat alphabet digits. 3 (ayn) is kept and handled by the phonemizer.
_ARABIZI = {"2": "", "5": "kh", "6": "t", "7": "h", "8": "gh", "9": "q"}
_VOWELS = "aeiou"


def clean_latin(token: str) -> str:
    """Lower-case, strip accents and punctuation, expand Arabizi digits."""
    s = token.lower()
    s = s.replace("3'", "gh").replace("7'", "kh")
    s = "".join(_LATIN_PRE.get(c, c) for c in s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    has_alpha = any("a" <= c <= "z" for c in s)
    out = []
    for c in s:
        if "a" <= c <= "z":
            out.append(c)
        elif c.isdigit() and has_alpha:
            out.append("3" if c == "3" else _ARABIZI.get(c, ""))
    return "".join(out)


_DIGRAPHS = {
    "sh": ("š", ("s", "h")),
    "kh": ("x", ("k", "h")),
    "gh": ("ġ", ("g", "h")),
    "th": ("θ", ("t", "h")),
    "dh": ("ð", ("d", "h")),
    "ch": ("š", None),
    "ph": ("f", None),
    "dj": ("j", None),
    "ck": ("k", None),
}
_TRIGRAPHS = {"sch": "š", "tch": "š"}
_SINGLE = {
    "b": "b", "p": "b", "d": "d", "f": "f", "g": "g", "j": "j", "k": "k", "l": "l",
    "m": "m", "n": "n", "q": "q", "r": "r", "s": "s", "t": "t", "v": "v", "z": "z",
    "Y": "y", "W": "w",
}
_LONG_VOWELS = {"ou": "U", "oo": "U", "uu": "U", "ee": "I", "ie": "I", "ii": "I", "aa": "A"}
_SHORT_VOWELS = {"a": "A", "e": "E", "i": "I", "o": "U", "u": "U"}


@lru_cache(maxsize=50_000)
def latin_phonemes(s: str) -> tuple:
    """Phonemes of a cleaned Latin token (see :func:`clean_latin`)."""
    chars = list(s)
    n = len(chars)
    # y / w are consonants only before a vowel; otherwise they are vowels.
    for i, c in enumerate(chars):
        if c in "yw":
            nxt = chars[i + 1] if i + 1 < n else ""
            if nxt == c:
                chars[i] = ""  # doubled glide: Sayyid, Fawwaz
            elif nxt and nxt in _VOWELS:
                chars[i] = c.upper()
            else:
                chars[i] = "i" if c == "y" else "u"
    # "i" between a consonant and a/o/u is the glide y: Rania = Ranya, Ziad = Ziyad
    for i in range(1, n - 1):
        if chars[i] == "i" and chars[i + 1] and chars[i + 1] in "aou" and chars[i - 1] not in _VOWELS + "YW":
            chars[i] = "Y"
    s = "".join(chars)
    n = len(s)

    out = []

    def cons(p, di=None):
        if out and out[-1].t == "C" and out[-1].p == p:
            return  # collapse doubled consonants (Mohammed / Mohamed)
        out.append(Ph("C", p, "la", di=di))

    def vowel(p):
        if out and out[-1].t == "V" and out[-1].p == p:
            return
        out.append(Ph("V", p, "la"))

    i = 0
    while i < n:
        c = s[i]
        two = s[i:i + 2]
        three = s[i:i + 3]
        if c == "3":
            out.append(Ph("W", "ʕ", "la"))
            i += 1
        elif c in _VOWELS:
            if two in _LONG_VOWELS:
                vowel(_LONG_VOWELS[two])
                i += 2
            else:
                vowel(_SHORT_VOWELS[c])
                i += 1
        elif three in _TRIGRAPHS:
            cons(_TRIGRAPHS[three])
            i += 3
        elif two in _DIGRAPHS:
            p, di = _DIGRAPHS[two]
            cons(p, di)
            i += 2
        elif c == "h":
            if i == n - 1 and n > 2 and out and out[-1].t in "VW":
                out.append(Ph("H", "h", "la"))
            else:
                cons("h")
            i += 1
        elif c == "c":
            nxt = s[i + 1] if i + 1 < n else ""
            cons("s" if nxt and nxt in "eiy" else "k")
            i += 1
        elif c == "x":
            cons("k")
            cons("s")
            i += 1
        elif c in _SINGLE:
            cons(_SINGLE[c])
            i += 1
        else:
            i += 1
    return tuple(out)


# --------------------------------------------------------------------------
# Arabic
# --------------------------------------------------------------------------

_AR_CONS = {
    "ب": "b", "پ": "b", "ت": "t", "ث": "θ", "ج": "j", "چ": "š", "ح": "h", "خ": "x",
    "د": "d", "ذ": "ð", "ر": "r", "ز": "z", "ژ": "j", "س": "s", "ش": "š", "ص": "s",
    "ض": "d", "ط": "t", "ظ": "ð", "غ": "ġ", "ف": "f", "ڤ": "v", "ق": "q", "ك": "k",
    "گ": "g", "ل": "l", "م": "m", "ن": "n", "ه": "h",
}
_ALEFS = "اأإآٱ"
_PLAIN_ALEFS = "اآٱ"


@lru_cache(maxsize=50_000)
def arabic_phonemes(s: str) -> tuple:
    """Phonemes of an Arabic-script token with diacritics already removed."""
    n = len(s)
    out = []

    def cons(p, raw):
        if out and out[-1].t == "C" and out[-1].p == p:
            return
        out.append(Ph("C", p, "ar", raw=raw))

    for i, c in enumerate(s):
        prev = s[i - 1] if i else ""
        nxt = s[i + 1] if i + 1 < n else ""
        last = i == n - 1
        # a non-initial alef before/after makes waw / ya a consonant
        after_long_alef = i >= 2 and prev in _PLAIN_ALEFS
        if c in _ALEFS:
            if i == 0:
                out.append(Ph("W", "ʔ", "ar"))
            elif c in _PLAIN_ALEFS:
                out.append(Ph("V", "A", "ar", long=True))
            else:
                out.append(Ph("W", "ʔ", "ar"))
        elif c in "ءؤئ":
            out.append(Ph("W", "ʔ", "ar"))
        elif c == "ع":
            out.append(Ph("W", "ʕ", "ar"))
        elif c == "ى":
            out.append(Ph("V", "A", "ar", long=True, alt="I" if last else None))
        elif c == "ة":
            if last:
                out.append(Ph("V", "A", "ar"))
            else:
                cons("t", c)
        elif c == "و":
            if i == 0 or (nxt and nxt in "اآىةي") or after_long_alef:
                cons("w", c)
            else:
                out.append(Ph("V", "U", "ar", long=True))
        elif c == "ي":
            if (i == 0 and n > 1) or (nxt and nxt in "اآىةو") or after_long_alef:
                cons("y", c)
            else:
                out.append(Ph("V", "I", "ar", long=True, alt="A" if last else None))
        elif c == "ه" and last and n > 2:
            out.append(Ph("H", "h", "ar"))
        elif c in _AR_CONS:
            cons(_AR_CONS[c], c)
    return tuple(out)


# --------------------------------------------------------------------------
# Hebrew (experimental: Arabic names as written in Hebrew script)
# --------------------------------------------------------------------------

_HE_FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
_HE_CONS = {
    "ב": "b", "ג": "g", "ד": "d", "ז": "z", "ח": "h", "ט": "t", "כ": "k", "ל": "l",
    "מ": "m", "נ": "n", "ס": "s", "פ": "f", "צ": "s", "ק": "q", "ר": "r", "ש": "š",
    "ת": "t", "ה": "h",
}
# letter + geresh, the usual way to write Arabic sounds Hebrew lacks
_HE_GERESH = {
    "ג": "j", "ד": "ð", "ז": "j", "ח": "x", "ט": "ð", "כ": "x", "צ": "d",
    "ר": "ġ", "ע": "ġ", "ת": "θ",
}
GERESH = "׳"


@lru_cache(maxsize=50_000)
def hebrew_phonemes(s: str) -> tuple:
    """Phonemes of a Hebrew-script token (niqqud removed, geresh = U+05F3)."""
    s = "".join(_HE_FINALS.get(c, c) for c in s)
    n = len(s)
    out = []

    def cons(p, raw):
        if out and out[-1].t == "C" and out[-1].p == p:
            return
        out.append(Ph("C", p, "he", raw=raw))

    i = 0
    while i < n:
        c = s[i]
        prev = s[i - 1] if i else ""
        nxt = s[i + 1] if i + 1 < n else ""
        last = i == n - 1
        after_alef = i >= 2 and prev == "א"
        if nxt == GERESH and c in _HE_GERESH:
            cons(_HE_GERESH[c], c + GERESH)
            i += 2
            continue
        if c == GERESH:
            i += 1
        elif c == "א":
            out.append(Ph("W", "ʔ", "he") if i == 0 else Ph("V", "A", "he"))
            i += 1
        elif c == "ע":
            out.append(Ph("W", "ʕ", "he"))
            i += 1
        elif c == "ה" and last and n > 2:
            out.append(Ph("H", "h", "he"))
            i += 1
        elif c == "ו":
            if nxt == "ו":
                cons("w", c)
                i += 2
            elif i == 0 or (nxt and nxt in "אה") or after_alef:
                cons("w", c)
                i += 1
            else:
                out.append(Ph("V", "U", "he"))
                i += 1
        elif c == "י":
            if nxt == "י":
                out.append(Ph("V", "I", "he"))
                i += 2
            elif (i == 0 and n > 1) or (nxt and nxt in "או") or after_alef:
                cons("y", c)
                i += 1
            else:
                out.append(Ph("V", "I", "he", alt="A" if last else None))
                i += 1
        elif c in _HE_CONS:
            cons(_HE_CONS[c], c)
            i += 1
        else:
            i += 1
    return tuple(out)


def phonemes(script: str, text: str) -> tuple:
    if script == "ar":
        return arabic_phonemes(text)
    if script == "he":
        return hebrew_phonemes(text)
    return latin_phonemes(text)
