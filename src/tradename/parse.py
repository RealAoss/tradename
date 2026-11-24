"""Split a company name into typed tokens.

A company name mixes parts that vary independently between languages:

* a **legal form** (LLC, ذ.م.م, GmbH) - recognised from ``legal.py``;
* **descriptors** and **qualifiers** (Trading, للتجارة, National, الوطنية)
  that are *translated* - recognised from ``vocab.py``;
* a distinctive **core** (Al Rajhi, الراجحي) that is *transliterated* - what
  is left, prepared here for phonetic comparison;
* noise: connectors, the article, branch markers, "(formerly ...)".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from functools import lru_cache

from . import legal as _legal
from . import vocab as _vocab
from ._phonetic.phonemes import clean_latin
from .legal import LegalForm
from .vocab import ar_key

__all__ = ["Token", "Company", "parse"]


@dataclass(frozen=True)
class Token:
    """One meaningful part of a company name."""

    kind: str                     # 'core' | 'desc' | 'qual' | 'legal' | 'num' | 'init'
    script: str                   # 'ar' | 'la' | 'xx' (anything else: compared exactly)
    text: str                     # as written
    forms: tuple = ()             # readings for phonetic comparison; each a tuple of parts
    concepts: frozenset = frozenset()   # vocabulary concepts (desc / qual)
    compound: bool = False        # an Abd- compound (Abdul Latif)
    full: int = -1                # index of the form that still carries an attached article
    place: bool = False           # a country or city
    soft: bool = False            # a bracketed place: "X (Egypt)"
    legal: "LegalForm | None" = None
    acronym: int = -1             # row of the known-acronym table, if any


@dataclass(frozen=True)
class Company:
    """A parsed company name. See :func:`parse`."""

    original: str
    tokens: tuple                 # content tokens, in order (no legal forms, no noise)
    legal_tokens: tuple           # every legal-form token found
    legal_form: "LegalForm | None"   # the most informative one
    branch: "str | None"          # "Dubai" for "... - Dubai Branch"; "" if unnamed
    aliases: tuple = ()           # ((label, tokens), ...): trade name, former name, acronym
    words: tuple = ()             # every word of the main name, normalised (for initialisms)

    @property
    def core(self) -> tuple:
        """The distinctive, transliterated part of the name."""
        return tuple(t.text for t in self.tokens if t.kind in ("core", "num", "init"))

    @property
    def descriptors(self) -> tuple:
        """Generic business words, as written."""
        return tuple(t.text for t in self.tokens if t.kind == "desc")

    @property
    def qualifiers(self) -> tuple:
        """Qualifiers and places (National, Gulf, Kuwait), as written."""
        return tuple(t.text for t in self.tokens if t.kind == "qual")

    @property
    def concepts(self) -> tuple:
        """Language-neutral concepts of the descriptors and qualifiers."""
        out = []
        for t in self.tokens:
            for c in sorted(t.concepts):
                if c not in out:
                    out.append(c)
        return tuple(out)

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "core": list(self.core),
            "descriptors": list(self.descriptors),
            "qualifiers": list(self.qualifiers),
            "concepts": list(self.concepts),
            "legal_form": self.legal_form.to_dict() if self.legal_form else None,
            "branch": self.branch,
            "aliases": [{"type": label, "name": " ".join(t.text for t in toks)}
                        for label, toks in self.aliases],
        }


# --------------------------------------------------------------------------
# characters and words
# --------------------------------------------------------------------------

_STRIP = re.compile(
    "[\u064b-\u065f\u0670\u06d6-\u06ed\u0640"            # Arabic diacritics + tatweel
    "\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]"     # zero width / bidi
)
_AR_MAP = str.maketrans({
    "ک": "ك", "ی": "ي", "ے": "ي", "ۀ": "ه", "ہ": "ه", "ھ": "ه", "ە": "ه", "گ": "ك", "ڤ": "ف", "پ": "ب", "چ": "ج",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4", "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
})
_AR_LETTER = re.compile("[\u0621-\u064a\u066e-\u06d3]")
_CY_LETTER = re.compile("[\u0400-\u04ff]")
_OTHER_LETTER = re.compile("[^\\W\\d_a-zA-Z\u00c0-\u024f]")
_CY_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y",
    "ь": "", "э": "e", "ю": "yu", "я": "ya", "і": "i", "ї": "yi", "є": "ye", "ґ": "g",
}
_SCAN = re.compile(
    r"(?P<sep>[,;:،؛|–—]|(?<=\s)-(?=\s)|(?<=\s)-$|^-(?=\s))"
    r"|(?P<w>[^\s,;:\\/|()\[\]{}<>\"“”«»_،؛–—]+)"
)


@dataclass(frozen=True)
class _Word:
    raw: str        # as written
    script: str     # 'ar' | 'la' | 'cy' | 'num' | 'xx'
    key: str        # lookup key
    text: str       # text for phonetic comparison
    abbr: bool = False   # written as dotted / spaced single letters (L.L.C.)
    sep: bool = False    # a separator (comma, dash, bracket) stands before it


def _one_word(raw: str, abbr: bool, sep: bool):
    if _AR_LETTER.search(raw):
        text = "".join(c for c in raw if _AR_LETTER.match(c))
        return _Word(raw, "ar", ar_key(text), text, abbr, sep)
    if raw.isdigit():
        return _Word(raw, "num", raw, raw, False, sep)
    if _CY_LETTER.search(raw):
        low = "".join(c for c in raw.lower() if _CY_LETTER.match(c))
        return _Word(raw, "cy", low, clean_latin("".join(_CY_MAP.get(c, c) for c in low)), abbr, sep)
    if _OTHER_LETTER.search(raw):
        return _Word(raw, "xx", raw.casefold(), "", abbr, sep)
    if raw == "&" or raw == "+":
        return _Word(raw, "la", "and", "", False, sep)
    if any(c.isdigit() for c in raw):
        low = "".join(c for c in raw.lower() if c.isalnum())
        return _Word(raw, "xx", low, "", abbr, sep) if low else None
    text = clean_latin(raw)
    if not text:
        return None
    return _Word(raw, "la", text, text, abbr, sep)


def _words(text: str, known_abbr=None) -> list:
    """Tokenise. Dotted or spaced single letters become one word (L.L.C. -> llc)."""
    out = []
    sep = False
    for m in _SCAN.finditer(text):
        if m.group("sep"):
            sep = True
            continue
        chunk = m.group("w").replace("'", "").replace("’", "").replace("`", "").replace("ʼ", "")
        chunk = chunk.replace("&", " & ").replace("+", " & ")
        for piece in chunk.split():
            for part in piece.split("-"):
                trailing = part.endswith(".")
                bits = [b for b in part.split(".") if b]
                if not bits:
                    continue
                if len(bits) > 1 and all(len(b) == 1 for b in bits):
                    bits, abbr = ["".join(bits)], True
                else:
                    abbr = len(bits) > 1 or (trailing and len(bits[0]) == 1)
                for b in bits:
                    w = _one_word(b, abbr, sep)
                    if w is not None:
                        out.append(w)
                        sep = False
    return _merge_letters(out, known_abbr)


def _merge_letters(words: list, known_abbr) -> list:
    """Join runs of single letters: "L L C" -> llc, "ذ م م" -> ذمم, "M H" -> mh."""
    out = []
    i, n = 0, len(words)
    while i < n:
        w = words[i]
        if len(w.key) == 1 and w.script in ("ar", "la", "cy"):
            j = i
            while j < n and len(words[j].key) == 1 and words[j].script == w.script and (j == i or not words[j].sep):
                j += 1
            merged = None
            if known_abbr is not None and w.script == "la":
                # "X A/S": keep a known abbreviation at the end of the run apart
                for s in range(i + 1, j - 1):
                    whole = "".join(x.key for x in words[i:j])
                    if "".join(x.key for x in words[s:j]) in known_abbr and whole not in known_abbr:
                        j = s
                        break
            for k in range(j, i + 1, -1):
                key = "".join(x.key for x in words[i:k])
                if known_abbr is None or key in known_abbr or (w.script == "la" and k == j):
                    merged = _Word(" ".join(x.raw for x in words[i:k]) if not w.abbr else "".join(x.raw for x in words[i:k]),
                                   w.script, key, "".join(x.text for x in words[i:k]), True, w.sep)
                    out.append(merged)
                    i = k
                    break
            if merged is not None:
                continue
        out.append(w)
        i += 1
    return out


# --------------------------------------------------------------------------
# lookup tables
# --------------------------------------------------------------------------

_MAX_PHRASE = 6
_LEGAL: dict = {}        # first key -> [(keys, entry)]
_LEGAL_ENTRIES: dict = {}
_VOCAB: dict = {}        # first key -> [(keys, concepts)]
_VOCAB_ENTRIES: dict = {}
_ACR_LATIN: dict = {}
_ACR_ARABIC: dict = {}
_SPECIFICITY = {c: i for i, c in enumerate((
    "company", "corporation", "joint_stock", "limited_liability", "sole_proprietorship",
    "general_partnership", "limited_partnership", "limited_liability_partnership", "cooperative",
    "public_joint_stock", "private_joint_stock", "single_owner", "free_zone",
))}


def _bare(w: "_Word") -> str:
    # only a real article: إلكترونيات / ألمنيوم fold to "ال..." but carry none
    return w.key[2:] if w.text.startswith("ال") and len(w.key) >= 4 else w.key


def _plain_latin(raw: str) -> str:
    """Letters of a Latin word with the diacritics simply dropped (Koç -> koc)."""
    s = unicodedata.normalize("NFD", raw.lower().replace("ı", "i").replace("ß", "ss").replace("ø", "o")
                              .replace("æ", "ae").replace("ł", "l").replace("đ", "d"))
    return "".join(c for c in s if "a" <= c <= "z")


def _marks(raw: str) -> tuple:
    """The letters of a word that carry a diacritic (ü, ö, é ...), in order."""
    if raw.isascii():
        return ()
    return tuple(c for c in unicodedata.normalize("NFC", raw.lower()) if c.isalpha() and not c.isascii())


def _build():
    for category, abbr, countries, spelling, end_only in _legal.FORMS:
        keys = tuple(w.key for w in _words(spelling))
        if not keys or len(keys) > _MAX_PHRASE:
            raise ValueError(f"legal form {spelling!r} cannot be used")
        e = _LEGAL_ENTRIES.get(keys)
        if e is None:
            e = _LEGAL_ENTRIES[keys] = {"abbr": abbr, "cats": [], "cc": [], "end": False}
            _LEGAL.setdefault(keys[0], []).append((keys, e))
        if category not in e["cats"]:
            e["cats"].append(category)
        for c in countries:
            if c not in e["cc"]:
                e["cc"].append(c)
        e["end"] = e["end"] or end_only
    for table, script in ((_vocab.LATIN, "la"), (_vocab.ARABIC, "ar")):
        for concept, spelling in table:
            keys = tuple(_bare(w) if script == "ar" else w.key for w in _words(spelling))
            if not keys or len(keys) > _MAX_PHRASE:
                raise ValueError(f"vocabulary spelling {spelling!r} cannot be used")
            e = _VOCAB_ENTRIES.get(keys)
            if e is None:
                e = _VOCAB_ENTRIES[keys] = set()
                _VOCAB.setdefault(keys[0], []).append((keys, e))
            e.add(concept)
    for row, (latin, arabic, _en, _ar) in enumerate(_vocab.ACRONYMS):
        _ACR_LATIN[latin] = row
        for a in arabic:
            _ACR_ARABIC[a] = row


_build()
_KNOWN_ABBR = {k[0] for k in _LEGAL_ENTRIES if len(k) == 1} | {k[0] for k in _VOCAB_ENTRIES if len(k) == 1 and len(k[0]) <= 4}
for _lst in list(_LEGAL.values()) + list(_VOCAB.values()):
    _lst.sort(key=lambda item: -len(item[0]))


def _legal_cands(w: _Word) -> tuple:
    if w.script == "ar" and w.key.startswith("و") and len(w.key) > 3:
        return (w.key, w.key[1:])
    return (w.key,)


@lru_cache(maxsize=50_000)
def _vocab_cands_ar(key: str) -> tuple:
    out = [key]
    bases = [key]
    if key.startswith("و") and len(key) > 3:
        bases.append(key[1:])
        out.append(key[1:])
    for b in bases:
        for p in ("ال", "لل", "بال", "ل"):
            if b.startswith(p) and len(b) - len(p) >= 2:
                c = b[len(p):]
                if c not in out:
                    out.append(c)
    return tuple(out)


def _vocab_cands(w: _Word) -> tuple:
    if w.script == "ar":
        return _vocab_cands_ar(w.key)
    if w.script != "la":
        return (w.key,)
    out = [w.key]
    if len(w.key) > 3 and w.key.endswith("s"):
        out.append(w.key[:-1])
    if len(w.key) >= 5 and w.key.startswith(("al", "el")):   # attached article: Alkhaleej
        out.append(w.key[2:])
    return tuple(out)


def _match_at(words, cands, i, table):
    """Longest phrase of ``table`` starting at word ``i``: (length, entry, picked) or None."""
    n = len(words)
    best = None
    for c in cands[i]:
        for keys, entry in table.get(c, ()):
            L = len(keys)
            if best is not None and L <= best[0]:
                break
            if i + L > n:
                continue
            picked = [c]
            for k in range(1, L):
                if keys[k] not in cands[i + k]:
                    break
                picked.append(keys[k])
            else:
                best = (L, entry, tuple(picked))
    return best


# --------------------------------------------------------------------------
# the structure of Arabic names (adapted from ismatch.parse)
# --------------------------------------------------------------------------

_ARTICLES = {"la": {"al", "el", "il", "ul"}, "ar": {"ال"}}
_ASSIMILATED = {
    "as": "s", "es": "s", "ash": "sh", "esh": "sh", "ad": "d", "ed": "d", "adh": "dh",
    "an": "n", "en": "n", "ar": "r", "er": "r", "at": "t", "et": "t", "ath": "th",
    "az": "z", "ez": "z",
}
_PARTICLES = {"la": {"bin", "ibn", "ben", "bn"}, "ar": {"بن", "ابن"}}
_CONNECTORS = {
    "la": {"and", "the", "of", "for", "in", "at", "by", "to", "de", "du", "des", "la", "le", "les",
           "et", "und", "del", "di", "do", "da", "dos", "das", "von", "van", "der", "den", "fuer", "fur", "pour"},
    "ar": {"و", "في", "من", "ذات", "ال", "لل"},
}
_ALLAH_AR = {"الله", "اللة", "لله"}
_ALEF_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})
_ABD_LINK = re.compile(r"(?:a|e|u|o|ou)(l|r|sh|s|n|z|dh|d|th|t)")
_ABUL = re.compile(r"ab(?:u|ou|o|i)l()(.*)")
_ABD_ALLAH = re.compile(r"l?[aeo]?h?")
_SUN_ATTACHED = re.compile(r"^[ae](?:(sh)sh|([sdnrtz])\2)")


def _strip_article(text: str) -> str:
    if text.translate(_ALEF_FOLD) in _ALLAH_AR:
        return "الله"
    if text.startswith("ال") and len(text) >= 4:
        return text[2:]
    return text


def _abd_latin(tok: str):
    r = tok[3:]
    if r == "":
        return ("link", "")
    m = _ABD_LINK.fullmatch(r)
    if m:
        return ("link", m.group(1))
    if re.fullmatch(r"[aeiou]+", r):
        return None
    x = re.sub(r"^[aeiou]{1,2}", "", r)
    if x != r and x.startswith("l"):
        x = x[1:]
        if _ABD_ALLAH.fullmatch(x):
            return ("joined", "allah")
    if len(x) < 3:
        return None
    return ("joined", x)


def _acronym(w: _Word) -> int:
    if w.script == "la":
        return _ACR_LATIN.get(w.key, -1)
    if w.script == "ar":
        return _ACR_ARABIC.get(w.key, -1)
    return -1


def _core_tokens(run: list, followed: "str | None") -> list:
    """Tokens for a run of words that are neither legal forms nor vocabulary.

    ``followed`` is the script of the word right after the run (or None), so
    that an article at the end of the run ("Al" + Khaleej) can be dropped.
    """
    tokens = []
    words = [(("la" if w.script == "cy" else w.script), w.text, w.raw, w) for w in run]
    n = len(words)
    i = 0
    had_article = False
    while i < n:
        script, text_, raw, w = words[i]
        nxt = words[i + 1] if i + 1 < n else None
        nxt_script = nxt[0] if nxt is not None else followed

        if script == "num":
            tokens.append(Token("num", "xx", raw, ((w.key,),)))
            i += 1
            continue
        if script == "xx":
            tokens.append(Token("core", "xx", raw, ((w.key,),)))
            i += 1
            continue
        key = text_ if w.script == "cy" else w.key
        if key in _CONNECTORS[script]:
            had_article = had_article or key == "ال"
            i += 1
            continue
        if nxt_script == script:
            if key in _ARTICLES[script]:
                had_article = True
                i += 1
                continue
            if script == "la" and nxt is not None and text_ in _ASSIMILATED and nxt[1].startswith(_ASSIMILATED[text_]):
                had_article = True
                i += 1
                continue
            if key in _PARTICLES[script] and nxt is not None:
                i += 1
                continue

        # --- Abd compounds ---------------------------------------------------
        second = None
        consumed = 1
        if script == "la" and text_.startswith("abd"):
            kind = _abd_latin(text_)
            if kind and kind[0] == "joined":
                second = kind[1]
            elif kind and nxt is not None and nxt[0] == "la":
                j = i + 1
                link = kind[1]
                if words[j][1] in _ARTICLES["la"] and j + 1 < n:
                    j += 1
                    link = ""
                cand = words[j][1]
                if link in ("", "l") or cand.startswith(link):
                    if link in ("", "l") and cand.startswith(("al", "el")) and len(cand) >= 5 and text_ == "abd":
                        cand = cand[2:]
                    second = "allah" if re.fullmatch(r"[aeu]?l+a+h?", cand) else cand
                    consumed = j - i + 1
                    raw = " ".join(x[2] for x in words[i:j + 1])
        elif script == "ar" and text_.startswith("عبد"):
            rest = text_[3:]
            if rest == "" and nxt is not None and nxt[0] == "ar":
                j = i + 1
                explicit = False
                if words[j][3].key in _ARTICLES["ar"] and j + 1 < n:
                    j += 1
                    explicit = True
                cand = words[j][1]
                stripped = _strip_article(cand)
                if explicit or stripped != cand or cand.translate(_ALEF_FOLD) in _ALLAH_AR:
                    second = stripped
                    consumed = j - i + 1
                    raw = " ".join(x[2] for x in words[i:j + 1])
            elif rest.translate(_ALEF_FOLD) in _ALLAH_AR:
                second = "الله"
            elif rest.startswith("ال") and len(rest) >= 4:
                second = rest[2:]
            elif rest in ("ربه", "رب"):
                second = rest
        if second is not None:
            head = "abd" if script == "la" else "عبد"
            tokens.append(Token("core", script, raw, ((head, second),), compound=True))
            had_article = False
            i += consumed
            continue

        abul = _ABUL.fullmatch(text_) if script == "la" else None
        if abul and not abul.group(2) and nxt is not None and nxt[0] == "la":
            tokens.append(Token("core", "la", raw, (("abu",),)))
            had_article = True
            i += 1
            continue

        # --- ordinary word ---------------------------------------------------
        if len(text_) == 1:
            tokens.append(Token("init", script, raw, ((text_,),)))
        elif w.abbr and script == "la" and len(text_) <= 4:
            tokens.append(Token("init", script, raw, ((text_,),), acronym=_acronym(w)))
        else:
            forms = [(text_,)]
            full = -1
            if script == "la":
                if not had_article:
                    if text_.startswith(("al", "el")) and len(text_) >= 5:
                        forms.append((text_[2:],))
                        full = 0
                    elif abul and len(abul.group(2)) >= 3:
                        forms.append(("abu", abul.group(2)))
                    else:
                        m = _SUN_ATTACHED.match(text_)
                        if m and len(text_) >= 6:
                            forms.append((text_[2:] if not m.group(1) else text_[3:],))
                if text_.startswith("bin") and len(text_) >= 6:
                    forms.append((text_[3:],))
                if w.script == "la":
                    plain = _plain_latin(raw)   # Koç is also written Koc, Škoda Skoda
                    if plain and plain != text_:
                        forms.append((plain,))
            else:
                base = text_
                if base.startswith("و") and len(base) >= 4 and i > 0:
                    forms.append((base[1:],))
                    base = base[1:]
                if not had_article:
                    bare = _strip_article(base)
                    if bare != base:
                        forms.insert(0, (bare,))
                        full = 1
                    else:
                        k = base.find("ال", 2)   # نورالدين = نور + الدين
                        if k >= 2:
                            rest = _strip_article(base[k:])
                            if rest != base[k:] and len(rest) >= 3:
                                forms.append((base[:k], rest))
            tokens.append(Token("core", script, raw, tuple(dict.fromkeys(forms)), full=full, acronym=_acronym(w)))
        had_article = False
        i += 1
    return tokens


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

_FORMER = re.compile(
    r"\b(?:formerly\s+known\s+as|previously\s+known\s+as|formerly|previously|f\.?k\.?a\.?|f/k/a)(?![\w])[\s:.]*",
    re.I)
_FORMER_AR = re.compile(r"(?:المعروفة\s+سابقا\s+باسم|المعروفة\s+سابقا\s+ب|سابقا)")
_TRADE = re.compile(
    r"(?:\b(?:t/a|d/b/a|dba|trading\s+as|doing\s+business\s+as|also\s+known\s+as|a\.k\.a\.?|aka)(?![\w])"
    r"|المعروفة\s+باسم|المعروف\s+باسم|والمعروفة\s+ب)[\s:.]*",
    re.I)
_PAREN = re.compile(r"[(\[（]([^()\[\]（）]*)[)\]）]")
_BRANCH_AR = "فرع"


def _tokens_of(text: str) -> tuple:
    """Tokenise and type one name: (tokens, legal tokens, branch, words)."""
    words = _words(text, _KNOWN_ABBR)
    n = len(words)
    lcands = [_legal_cands(w) for w in words]
    vcands = [_vocab_cands(w) for w in words]

    # 1. legal forms and vocabulary, longest phrase first
    items = []          # [kind, words, payload]
    i = 0
    while i < n:
        w = words[i]
        hit_l = _match_at(words, lcands, i, _LEGAL) if w.script in ("ar", "la", "cy") else None
        hit_v = _match_at(words, vcands, i, _VOCAB) if w.script in ("ar", "la") else None
        if hit_l and (not hit_v or hit_l[0] >= hit_v[0]):
            items.append(["legal", words[i:i + hit_l[0]], hit_l[1]])
            i += hit_l[0]
        elif hit_v:
            items.append(["vocab", words[i:i + hit_v[0]], hit_v])
            i += hit_v[0]
        else:
            items.append(["word", [w], None])
            i += 1

    # 2. branch markers
    branch = None
    for idx, (kind, ws, _p) in enumerate(items):
        if kind != "word":
            continue
        key = ws[0].key
        if key == _BRANCH_AR and ws[0].script == "ar":
            if idx == 0:
                branch = ""
                del items[0]
            elif len(items) - idx <= 5:
                branch = " ".join(w.raw for it in items[idx + 1:] for w in it[1])
                del items[idx:]
            break
        if ws[0].script == "la" and (key in ("branch", "branches") or (key == "br" and idx == len(items) - 1 and idx > 0)):
            if idx + 1 < len(items) and items[idx + 1][1][0].key == "of":
                branch = ""
                del items[idx:idx + 2]
                break
            start = idx
            found_sep = False
            while start > 0 and idx - start < 4:
                prev = items[start - 1]
                if prev[0] == "legal":
                    break
                start -= 1
                if prev[1][0].sep:
                    found_sep = True
                    break
            if not found_sep:
                start = idx
                while start > 0 and idx - start < 2 and items[start - 1][0] == "vocab" and any(
                        _vocab.CONCEPTS[c] == "p" for c in items[start - 1][2][1]):
                    start -= 1
            if start == 0:           # never swallow the whole name
                start = idx
            branch = " ".join(w.raw for it in items[start:idx] for w in it[1])
            items[start:] = items[idx + 1:]
            break

    # 3. an ambiguous legal form (SA, AS, AG ...) only counts when dotted or final
    for idx, (kind, ws, entry) in enumerate(items):
        if kind == "legal" and entry["end"] and not (len(ws) == 1 and ws[0].abbr):
            final = idx > 0 and all(it[0] == "legal" for it in items[idx + 1:])
            # ... or leads the name in capitals before a proper name ("AB Volvo")
            leading = idx == 0 and len(items) > 1 and ws[0].raw.isupper() and items[1][0] == "word"
            if not final and not leading:
                items[idx] = ["word", ws, None]
    flat = []
    for it in items:
        if it[0] == "word" and len(it[1]) > 1:
            flat.extend(["word", [w], None] for w in it[1])
        else:
            flat.append(it)
    items = flat

    # 4. build tokens
    tokens, legal_tokens = [], []
    i, n = 0, len(items)
    while i < n:
        kind, ws, payload = items[i]
        if kind == "legal":
            form = LegalForm(payload["abbr"], payload["cats"][0],
                             tuple(payload["cats"]), tuple(payload["cc"]), " ".join(w.raw for w in ws))
            legal_tokens.append(Token("legal", "la" if ws[0].script == "cy" else ws[0].script, form.text,
                                      (tuple(w.text for w in ws),), legal=form))
            i += 1
        elif kind == "vocab":
            L, concepts, picked = payload
            parts = []
            for w, p in zip(ws, picked):
                cut = len(w.key) - len(p) if w.script == "ar" or w.key.endswith(p) else 0
                parts.append(w.text[cut:] if cut > 0 else w.text)
            kinds = {_vocab.CONCEPTS[c] for c in concepts}
            tokens.append(Token("desc" if kinds == {"d"} else "qual", ws[0].script, " ".join(w.raw for w in ws),
                                (tuple(p for p in parts if p),), frozenset(concepts), place="p" in kinds,
                                acronym=_acronym(ws[0]) if L == 1 else -1))
            i += 1
        else:
            j = i
            while j < n and items[j][0] == "word":
                j += 1
            followed = None
            if j < n:
                s = items[j][1][0].script
                followed = "la" if s == "cy" else s
            tokens.extend(_core_tokens([it[1][0] for it in items[i:j]], followed))
            i = j
    return tuple(tokens), tuple(legal_tokens), branch, tuple(w.key for w in words)


def _prepare(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _STRIP.sub("", text).translate(_AR_MAP)
    return text.replace("\u00a0", " ")


def _best_legal(legal_tokens):
    best = None
    for t in legal_tokens:
        if best is None or _SPECIFICITY[t.legal.category] > _SPECIFICITY[best.category]:
            best = t.legal
    return best


def _is_initialism(candidate: tuple, words: tuple) -> bool:
    if len(candidate) != 1 or len(words) < 2:
        return False
    c = candidate[0]
    if c.script != "la" or c.kind not in ("core", "init") or len(c.forms[0]) != 1:
        return False
    return _initials_match(c.forms[0][0], words)


def _initials_match(acr: str, words: tuple) -> bool:
    """True if ``acr`` is made of the first letters of ``words`` (small words optional)."""
    if not 2 <= len(acr) <= 8 or len(words) < len(acr):
        return False
    return acr in _initial_options(words)


def _initial_options(words: tuple) -> set:
    """The acronyms the words of a Latin-script name can be shortened to."""
    full = [w for w in words if w and w[0].isalpha() and w.isascii()]
    if len(full) != len(words):
        return set()
    strict = [w for w in full if w not in _CONNECTORS["la"] and w not in _ARTICLES["la"]]
    options = {"".join(w[0] for w in strict), "".join(w[0] for w in full)}
    while strict and (strict[-1],) in _LEGAL_ENTRIES:
        strict = strict[:-1]
        options.add("".join(w[0] for w in strict))
    options.discard("")
    return options


@lru_cache(maxsize=50_000)
def parse(name: str) -> Company:
    """Parse a company name.

    >>> c = parse("Gulf Trading & Contracting Co. LLC - Dubai Branch")
    >>> c.qualifiers, c.descriptors, c.legal_form.abbr, c.branch
    (('Gulf',), ('Trading', 'Contracting'), 'LLC', 'Dubai')
    """
    original = name
    text = _prepare(name or "")
    aliases = []
    pending = []    # bracketed single words: an acronym / trade name, or just part of the name
    bracketed = []  # other bracketed text, kept in the name

    def bracket(m):
        inner = m.group(1).strip()
        if not inner:
            return " "
        f = _FORMER.search(inner) or _FORMER_AR.search(inner)
        if f:
            other = (inner[:f.start()] + " " + inner[f.end():]).strip()
            if other:
                aliases.append(("former name", other))
            return " "
        t = _TRADE.match(inner)
        if t:
            aliases.append(("alias", inner[t.end():]))
            return " "
        ws = _words(inner, _KNOWN_ABBR)
        if len(ws) == 1 and len(ws[0].key) > 1 and ws[0].script in ("la", "ar", "cy"):
            w = ws[0]
            if (w.key,) not in _LEGAL_ENTRIES and not any((c,) in _VOCAB_ENTRIES for c in _vocab_cands(w)) \
                    or _acronym(w) >= 0:
                pending.append(inner)
                return f" , \ue000{len(pending) - 1}\ue000 , "
        bracketed.append(inner)
        return f" , {inner} , "

    prev = None
    while prev != text:
        prev = text
        text = _PAREN.sub(bracket, text)
    text = text.replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ")

    f = _FORMER.search(text)
    if f and text[:f.start()].strip():
        aliases.append(("former name", text[f.end():]))
        text = text[:f.start()]
    t = _TRADE.search(text)
    if t and text[:t.start()].strip():
        aliases.append(("alias", text[t.end():]))
        text = text[:t.start()]

    # a bracketed single word is an acronym / trade name when it is made of the
    # initials of the name or is a known acronym; otherwise it is part of the name
    marker = re.compile("\ue000(\\d+)\ue000")
    words = _tokens_of(marker.sub(" ", text))[3]
    out_aliases = []
    keep = set()
    for k, inner in enumerate(pending):
        toks = _tokens_of(inner)[0]
        if toks and words and (_is_initialism(toks, words) or toks[0].acronym >= 0):
            out_aliases.append(("acronym", toks))
        else:
            keep.add(k)
    text = marker.sub(lambda m: pending[int(m.group(1))] if int(m.group(1)) in keep else " ", text)

    tokens, legal_tokens, branch, words = _tokens_of(text)
    if bracketed and len(tokens) > 1:
        # "X (Egypt)", "X (Middle East) Ltd": a bracketed place is a soft hint,
        # often left out of the same company's name elsewhere
        soft = {" ".join(inner.split()) for inner in bracketed}
        tokens = tuple(replace(t, soft=True) if t.place and t.text in soft else t for t in tokens)
        if all(t.soft for t in tokens):
            tokens = tuple(replace(t, soft=False) for t in tokens)
    if not tokens and legal_tokens:
        # a name made only of legal words ("شركة", "The Company"): compare them as words
        tokens = tuple(Token("desc", t.script, t.text, t.forms, frozenset({"legal:" + t.legal.category}))
                       for t in legal_tokens)
    for label, other in aliases:
        toks = _tokens_of(other)[0]
        if toks:
            out_aliases.append((label, toks))
    # a known acronym stands for its expansion (SABIC = Saudi Basic Industries Corporation)
    # when it is the whole name, or stands out in capitals in a mixed-case name;
    # "Koc Holding" and "Alba Trading" are ordinary words
    mixed_case = original != original.upper()
    for group in [tokens] + [toks for _l, toks in out_aliases]:
        for k, tok in enumerate(group):
            if tok.acronym >= 0 and (len(group) == 1 or (tok.script == "la" and mixed_case and tok.text.isupper())):
                rest = group[:k] + group[k + 1:]
                _la, _ar, en, ar = _vocab.ACRONYMS[tok.acronym]
                for expansion in (en, ar):
                    out_aliases.append(("acronym", _tokens_of(_prepare(expansion))[0] + rest))
                break
    seen = {tokens}
    unique = []
    for label, toks in out_aliases:
        if toks not in seen:
            seen.add(toks)
            unique.append((label, toks))
    return Company(original, tokens, legal_tokens, _best_legal(legal_tokens), branch, tuple(unique[:6]), words)
