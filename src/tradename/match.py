"""Compare two company names and explain the result.

The score is built from typed tokens (see ``parse.py``):

* the distinctive **core** dominates; it is compared phonetically, across
  scripts, and must agree;
* **qualifiers** and **descriptors** are compared by meaning (translation)
  or by sound (transliteration), whichever fits; a *conflict* between them
  ("Bank" vs "Cement") caps the score below the default threshold;
* the **legal form** matters least: a different one lowers the score a
  little and is reported.

The less distinctive a name is, the stricter the comparison: a name made
only of vocabulary words needs every word to agree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from itertools import islice, product

from ._phonetic import lexicon
from ._phonetic.distance import _KEY as _SKELETON_KEY
from ._phonetic.distance import CONF, similarity, skeleton
from ._phonetic.phonemes import phonemes
from .legal import LegalForm, compatible
from .parse import Company, Token, _initial_options, _initials_match, _marks, parse
from .vocab import ar_key

__all__ = ["Match", "compare", "score", "is_match", "normalize", "keys", "token_similarity", "DEFAULT_THRESHOLD"]

DEFAULT_THRESHOLD = 0.85

_PAIR_MIN = 0.80            # below this two tokens are not the same word
_WEIGHT = {"core": 1.0, "num": 1.0, "init": 0.5, "qual": 0.6, "desc": 0.4}
_WEAK = frozenset({"partners"})   # "& Co." / وشركاه: present or absent at will

_CAP_NO_IDENTITY = 0.45     # nothing identifying agrees
_CAP_CONFLICT = {           # both names have a part the other lacks
    ("core", "core"): 0.55, ("core", "qual"): 0.62, ("core", "desc"): 0.62,
    ("qual", "qual"): 0.72, ("qual", "desc"): 0.76, ("desc", "desc"): 0.72,
}
_CAP_EXTRA_CORE = 0.80      # one name has an extra distinctive word
_CAP_GENERIC = 0.80         # generic-only name with a word that does not agree
_EXTRA_QUAL = 0.95          # one-sided extras next to a matching core
_EXTRA_DESC = 0.93
_EXTRA_MORE = 0.97
_EXTRA_WEAK = 0.99
_LEGAL_DIFFERENT = 0.96
_CAP_STRICT_LEGAL = 0.60
_ALIAS_FACTOR = {"alias": 0.97, "acronym": 0.97, "former name": 0.95}
_INITIALISM_SCORE = 0.88
_DISTINCT_CAP = 0.78
_SAME_FLOOR = 0.9
_JOIN_MIN = 0.88
_JOIN_GAIN = 0.08
_JOIN_SLACK = 2
_JOIN_LONG = 7              # consonants; a longer word can afford to lose its first or last one
_LATIN_VOWEL_CLASS = {"a": 1, "e": 1, "i": 1, "y": 1, "o": 2, "u": 2}
_MAX_TOKENS = 24            # words of a name that are compared
_DIFFERENT_WORD = 0.7      # two spellings that are known not to be one word
_TA_MARBUTA = 0.9
_STRUCTURE = frozenset({"group", "holding", "partners"})   # say how a business is organised, not what it does
_CAP_EXTRA_BUSINESS = 0.82  # "Siemens" vs "Siemens Energy": possibly a subsidiary


@dataclass
class Match:
    """Result of :func:`compare`."""

    score: float
    threshold: float = DEFAULT_THRESHOLD
    core_pairs: list = field(default_factory=list)         # (part of a, part of b, similarity)
    descriptor_pairs: list = field(default_factory=list)   # (part of a, part of b, similarity)
    only_a: list = field(default_factory=list)
    only_b: list = field(default_factory=list)
    legal_a: "LegalForm | None" = None
    legal_b: "LegalForm | None" = None
    legal: str = "unknown"          # 'same' | 'compatible' | 'different' | 'unknown'
    branch_a: "str | None" = None
    branch_b: "str | None" = None
    via: "str | None" = None        # 'alias' | 'acronym' | 'former name' | 'initialism'
    notes: list = field(default_factory=list)

    @property
    def is_match(self) -> bool:
        return self.score >= self.threshold

    @property
    def level(self) -> str:
        s = self.score
        if s >= 0.93:
            return "strong"
        if s >= 0.85:
            return "probable"
        if s >= 0.70:
            return "possible"
        return "no"

    def __bool__(self) -> bool:
        return self.is_match

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "is_match": self.is_match,
            "level": self.level,
            "core_pairs": [{"a": a, "b": b, "score": round(s, 4)} for a, b, s in self.core_pairs],
            "descriptor_pairs": [{"a": a, "b": b, "score": round(s, 4)} for a, b, s in self.descriptor_pairs],
            "only_a": list(self.only_a),
            "only_b": list(self.only_b),
            "legal_form_a": self.legal_a.to_dict() if self.legal_a else None,
            "legal_form_b": self.legal_b.to_dict() if self.legal_b else None,
            "legal_forms": self.legal,
            "branch_a": self.branch_a,
            "branch_b": self.branch_b,
            "via": self.via,
            "notes": list(self.notes),
        }

    def explain(self) -> str:
        lines = [f"score {self.score:.2f}  ({self.level})"]
        for a, b, s in self.core_pairs:
            lines.append(f"  core        {a}  ~  {b}   {s:.2f}")
        for a, b, s in self.descriptor_pairs:
            lines.append(f"  descriptor  {a}  ~  {b}   {s:.2f}")
        if self.legal_a or self.legal_b:
            fa = f"{self.legal_a.text} [{self.legal_a.category}]" if self.legal_a else "(none)"
            fb = f"{self.legal_b.text} [{self.legal_b.category}]" if self.legal_b else "(none)"
            lines.append(f"  legal form  {fa}  ~  {fb}   {self.legal}")
        if self.only_a:
            lines.append("  only in first:  " + ", ".join(self.only_a))
        if self.only_b:
            lines.append("  only in second: " + ", ".join(self.only_b))
        if self.branch_a is not None or self.branch_b is not None:
            lines.append(f"  branch      {self.branch_a or '-'}  |  {self.branch_b or '-'}")
        if self.via:
            lines.append(f"  matched through: {self.via}")
        for n in self.notes:
            lines.append(f"  note: {n}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# one token against another
# --------------------------------------------------------------------------

def _seq(script: str, form: tuple) -> tuple:
    out = []
    for part in form:
        out.extend(phonemes(script, part))
    return tuple(out)


@lru_cache(maxsize=50_000)
def _variants(tok: Token, other_script: str) -> tuple:
    """Phoneme sequences a token may stand for when facing ``other_script``."""
    out = []
    if tok.script not in ("ar", "la"):
        return ()
    for n, form in enumerate(tok.forms):
        if tok.script == "ar" and other_script == "la":
            readings = [lexicon.readings_for(p, "ar") for p in form]
            if all(readings):   # the lexicon of personal names knows the vowels
                for combo in islice(product(*readings), 4):
                    seq = []
                    for r in combo:
                        seq.extend(lexicon.reading_phonemes(r))
                    out.append((n, tuple(seq)))
                if not form[-1].endswith("ة"):
                    continue   # ...but a final ة is also romanised -a / -ah (Hayat / Hayah)
        seq = _seq(tok.script, form)
        if seq:
            out.append((n, seq))
    return tuple(out)


@lru_cache(maxsize=50_000)
def _ids(tok: Token) -> frozenset:
    """Personal names of the lexicon this token is known to stand for."""
    for form in tok.forms:
        part = form[-1]
        ids = lexicon.arabic_ids(part) if tok.script == "ar" else lexicon.latin_ids(part)
        if ids:
            return ids
    return frozenset()


def _flat(tok: Token) -> set:
    if tok.script == "ar":
        return {ar_key("".join(f)) for f in tok.forms}
    return {"".join(f) for f in tok.forms}


def _same_initial(x: str, y: str) -> bool:
    return x[:1] == y[:1] or _LATIN_VOWEL_CLASS.get(x[:1], 0) == _LATIN_VOWEL_CLASS.get(y[:1], -1)


def _phonetic(a: Token, b: Token) -> float:
    if a.script not in ("ar", "la") or b.script not in ("ar", "la"):
        return 1.0 if a.script == b.script and a.forms == b.forms else 0.0
    if a.script == b.script and _flat(a) & _flat(b):
        return 1.0
    best = 0.0
    both_articled = a.full >= 0 and b.full >= 0
    for na, sa in _variants(a, b.script):
        for nb, sb in _variants(b, a.script):
            if both_articled and na == a.full and nb == b.full:
                continue   # two shared articles would inflate the similarity
            s = similarity(sa, sb)
            if s > best:
                best = s
    if a.script == "la" and b.script == "la":
        x, y = "".join(a.forms[0]), "".join(b.forms[0])
        if min(len(x), len(y)) <= 3:
            return 0.0     # short Latin words: exact or nothing
        for p in a.forms:
            for q in b.forms:
                p_, q_ = "".join(p), "".join(q)
                if len(p_) >= 5 and p_[:-1] == q_[:-1] and p_[-2] == "a" and {p_[-1], q_[-1]} == {"t", "h"}:
                    best = max(best, _TA_MARBUTA)   # Hayat / Hayah: two romanisations of one ending
        if not any(_same_initial("".join(p), "".join(q)) for p in a.forms for q in b.forms):
            best = min(best, _DIFFERENT_WORD)
        vx, vy = _LATIN_VOWEL_CLASS.get(x[-1]), _LATIN_VOWEL_CLASS.get(y[-1])
        if vx and vy and vx != vy:
            best = min(best, _DIFFERENT_WORD)   # Rossi / Russo, Maria / Mario
        mx, my = set(_marks(a.text)), set(_marks(b.text))
        if mx and my and not (mx <= my or my <= mx):
            best = min(best, _DIFFERENT_WORD)   # Müller / Möller: both writers were precise
    elif a.script == "ar" and b.script == "ar":
        if not any(ar_key(p[0])[:1] == ar_key(q[0])[:1] for p in a.forms for q in b.forms):
            best = min(best, _DIFFERENT_WORD)   # إعمار / عمار: an extra first letter is not a spelling habit
    if a.kind == "core" and b.kind == "core" and a.compound == b.compound:
        ia, ib = _ids(a), _ids(b)
        if ia and ib:
            if ia.isdisjoint(ib):
                best = min(best, _DISTINCT_CAP)   # known to be different names
            elif ia == ib and len(ia) == 1 and not a.compound:
                best = max(best, _SAME_FLOOR)
    return best


@lru_cache(maxsize=200_000)
def token_similarity(a: Token, b: Token) -> float:
    """Similarity in [0, 1] between two tokens: by meaning, else by sound."""
    if a.concepts and b.concepts:
        return 1.0 if a.concepts & b.concepts else 0.0
    if a.acronym >= 0 and a.acronym == b.acronym:
        return 1.0
    if "num" in (a.kind, b.kind) or "init" in (a.kind, b.kind):
        return 1.0 if a.script == b.script and _flat(a) & _flat(b) else 0.0
    return _phonetic(a, b)


def _join(a: Token, b: Token) -> Token:
    forms = tuple(x + y for x, y in islice(product(a.forms, b.forms), 4))
    return Token("core", a.script, a.text + " " + b.text, forms)


@lru_cache(maxsize=50_000)
def _consonants(tok: Token) -> tuple:
    """Fewest and most strong consonants among the readings of a token."""
    counts, firsts, lasts = [], set(), set()
    for _n, seq in _variants(tok, "la") + _variants(tok, "ar"):
        strong = [ph.p for ph in seq if ph.t == "C" and ph.p not in "wy"]
        counts.append(len(strong))
        firsts.add(strong[0] if strong else "")
        lasts.add(strong[-1] if strong else "")
    if not counts:
        return 0, 99, frozenset({""}), frozenset({""})
    return min(counts), max(counts), frozenset(firsts), frozenset(lasts)


def _alike(xs: frozenset, ys: frozenset) -> bool:
    """Could two consonants (one from each set) be the same sound? ('' and h: cannot tell)."""
    return any(x == y or x in ("", "h") or y in ("", "h") or (x, y) in CONF for x in xs for y in ys)


def _may_join(t: Token, u: Token, v: Token) -> bool:
    """Cheap test: could ``u`` + ``v`` written as one word be the word ``t``?"""
    if not (u.kind == "core" and v.kind == "core" and u.script == v.script and u.script in ("ar", "la")
            and not u.compound and not v.compound):
        return False
    # a joined word that matches has (nearly) the consonants of its two halves,
    # and begins and ends with the same sounds
    (t_lo, t_hi, t_first, t_last), (u_lo, u_hi, u_first, _), (v_lo, v_hi, _, v_last) = \
        _consonants(t), _consonants(u), _consonants(v)
    if not (t_lo - _JOIN_SLACK <= u_hi + v_hi and u_lo + v_lo <= t_hi + _JOIN_SLACK):
        return False
    return t_hi >= _JOIN_LONG or (_alike(t_first, u_first) and _alike(t_last, v_last))


def _merge_split_parts(A: list, B: list) -> list:
    """If one word of A is written as two adjacent words in B, join them.

    Covers Abudawood / Abu Dawood, Binzagr / Bin Zagr, AlMarai / Al Marai.
    """
    B = list(B)
    for t in A:
        if t.kind != "core":
            continue
        j = 0
        while j < len(B) - 1:
            u, v = B[j], B[j + 1]
            if _may_join(t, u, v):
                apart = max(token_similarity(t, u), token_similarity(t, v))
                if apart + _JOIN_GAIN < 1.0:
                    merged = _join(u, v)
                    s = token_similarity(t, merged)
                    if s >= _JOIN_MIN and s > apart + _JOIN_GAIN:
                        B[j:j + 2] = [merged]
                        continue
            j += 1
    return B


def _cannot_match(ca: Company, cb: Company) -> bool:
    """True when :func:`compare` is certain to score at most ``_CAP_EXTRA_CORE``.

    A distinctive word that has no counterpart in the other name caps the
    score, so the full comparison can be skipped. Used by ``dedupe``.
    """
    if ca.aliases or cb.aliases or not ca.tokens or not cb.tokens:
        return False
    if max(len(ca.tokens), len(cb.tokens)) > _MAX_TOKENS:
        return False
    for A, B in ((ca.tokens, cb.tokens), (cb.tokens, ca.tokens)):
        for i, x in enumerate(A):
            if _class(x) != "core" or any(token_similarity(x, y) >= _PAIR_MIN for y in B):
                continue
            # x has no counterpart; could joining words still give it one?
            if any(_may_join(x, B[j], B[j + 1]) for j in range(len(B) - 1)):
                continue
            if any(_may_join(y, A[k], A[k + 1]) for k in (i - 1, i) if 0 <= k < len(A) - 1 for y in B):
                continue
            return not (_initialism(ca, cb) or _initialism(cb, ca))
    return False


# --------------------------------------------------------------------------
# one token list against another
# --------------------------------------------------------------------------

def _assign(S, w):
    """Best one-to-one assignment of rows to columns (order is free)."""
    n, m = len(S), len(S[0]) if S else 0
    if n > 12 or m > 12:   # absurdly long name: greedy is good enough
        cells = sorted(((S[i][j] * w[i][j], -i, -j) for i in range(n) for j in range(m)), reverse=True)
        used_i, used_j, pairs = set(), set(), []
        for v, i, j in cells:
            if -i not in used_i and -j not in used_j and v > 0:
                used_i.add(-i)
                used_j.add(-j)
                pairs.append((-i, -j))
        return sorted(pairs)

    @lru_cache(maxsize=None)
    def best(i: int, mask: int):
        if i == n:
            return 0.0, ()
        top, top_pairs = best(i + 1, mask)
        for j in range(m):
            if not mask & (1 << j):
                v = S[i][j] * w[i][j]
                if v <= 0:
                    continue
                sub, sub_pairs = best(i + 1, mask | (1 << j))
                if v + sub > top + 1e-12:
                    top, top_pairs = v + sub, ((i, j),) + sub_pairs
        return top, top_pairs

    return list(best(0, 0)[1])


def _class(t: Token) -> str:
    if t.kind in ("core", "num"):
        return "core"
    if t.kind == "desc":
        return "weak" if t.concepts and t.concepts <= _WEAK else "desc"
    return "qual"


@dataclass
class _Result:
    score: float = 0.0
    core_pairs: list = field(default_factory=list)
    descriptor_pairs: list = field(default_factory=list)
    only_a: list = field(default_factory=list)
    only_b: list = field(default_factory=list)
    notes: list = field(default_factory=list)


def _compare_tokens(A: tuple, B: tuple) -> _Result:
    res = _Result()
    if not A or not B:
        return res
    if len(A) > _MAX_TOKENS or len(B) > _MAX_TOKENS:
        # not a company name any more; keep the cost bounded
        A, B = A[:_MAX_TOKENS], B[:_MAX_TOKENS]
        res.notes.append(f"very long name: only the first {_MAX_TOKENS} words were compared")
    B = _merge_split_parts(A, B)
    A = _merge_split_parts(B, A)
    n, m = len(A), len(B)
    S = [[0.0] * m for _ in range(n)]
    W = [[0.0] * m for _ in range(n)]
    for i, x in enumerate(A):
        for j, y in enumerate(B):
            s = token_similarity(x, y)
            if s >= _PAIR_MIN:
                S[i][j] = s
                # the small bonus for position keeps the choice stable between equal words
                W[i][j] = max(_WEIGHT[x.kind], _WEIGHT[y.kind]) + 0.001 / (1 + abs(i - j))
    pairs = _assign(S, W)

    used_a, used_b = set(), set()
    num = den = id_num = id_den = 0.0
    core_matched = False
    generic = 0
    for i, j in pairs:
        x, y = A[i], B[j]
        s = S[i][j]
        w = max(_WEIGHT[x.kind], _WEIGHT[y.kind])
        used_a.add(i)
        used_b.add(j)
        num += w * s
        den += w
        if "core" in (_class(x), _class(y)) and (x.concepts or y.concepts):
            # a transliterated generic word (Etisalat ~ اتصالات "telecom") is still generic
            generic += 1
            res.descriptor_pairs.append((x.text, y.text, s))
        elif "core" in (_class(x), _class(y)):
            core_matched = True
            id_num += w * s
            id_den += w
            res.core_pairs.append((x.text, y.text, s))
        else:
            res.descriptor_pairs.append((x.text, y.text, s))
    left_a = [A[i] for i in range(n) if i not in used_a]
    left_b = [B[j] for j in range(m) if j not in used_b]
    res.only_a = [t.text for t in left_a]
    res.only_b = [t.text for t in left_b]
    if not pairs:
        return res

    value = num / den
    if core_matched:
        value = 0.5 * value + 0.5 * id_num / id_den

    ca = {_class(t) for t in left_a} - {"weak"}
    cb = {_class(t) for t in left_b} - {"weak"}
    # a bracketed place ("X (Egypt)") only counts when the other name disagrees
    soft_only = [t for t in left_a + left_b if t.soft]
    if soft_only and not (ca and cb) and all(t.soft for t in (left_a if ca else left_b) if _class(t) != "weak"):
        ca, cb = set(), set()
        value *= _EXTRA_MORE ** len(soft_only)
    has_core = sum(_class(t) == "core" for t in A + B) > generic
    if has_core and not core_matched:
        value = min(value, _CAP_NO_IDENTITY)
        res.notes.append("the distinctive parts of the names do not agree")
    if ca and cb:
        cap = min(_CAP_CONFLICT.get((x, y)) or _CAP_CONFLICT[(y, x)] for x in ca for y in cb)
        value = min(value, cap)
        res.notes.append("each name has a part the other lacks: "
                         + ", ".join(res.only_a) + "  |  " + ", ".join(res.only_b))
    elif ca or cb:
        extra = ca or cb
        left = left_a or left_b
        if "core" in extra:
            value = min(value, _CAP_EXTRA_CORE)
            res.notes.append("one name has an extra distinctive word")
        elif not core_matched:
            value = min(value, _CAP_GENERIC)
            res.notes.append("generic names must agree on every word")
        else:
            first_desc = True
            for t in left:
                c = _class(t)
                if c == "qual":
                    value *= _EXTRA_QUAL
                elif c == "desc":
                    value *= _EXTRA_DESC if first_desc else _EXTRA_MORE
                    first_desc = False
            # a line of business added to a bare name ("Siemens" / "Siemens Energy",
            # "Nestlé" / "Nestlé Waters") usually names a subsidiary or sister company
            shorter = B if left_a else A
            business = [t for t in left if _class(t) == "desc" and not t.concepts <= _STRUCTURE]
            if business and all(_class(t) in ("core", "weak") for t in shorter):
                value = min(value, _CAP_EXTRA_BUSINESS)
                res.notes.append("one name adds a line of business: " + ", ".join(t.text for t in business))
    for t in left_a + left_b:
        if _class(t) == "weak":
            value *= _EXTRA_WEAK
    res.score = max(0.0, min(1.0, value))
    return res


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def _initialism(a: Company, b: Company) -> bool:
    """``a`` is a bare acronym made of the initials of the words of ``b``."""
    if len(a.tokens) != 1 or a.tokens[0].script != "la" or a.tokens[0].kind not in ("core", "init"):
        return False
    acr = a.tokens[0].forms[0][0] if len(a.tokens[0].forms[0]) == 1 else ""
    return len(acr) >= 3 and len(b.words) >= 3 and _initials_match(acr, b.words)


def _compare(ca: Company, cb: Company, threshold: float, strict_legal_form: bool) -> Match:
    best, best_via, best_factor = _Result(), None, 0.0
    va = [(None, ca.tokens)] + list(ca.aliases)
    vb = [(None, cb.tokens)] + list(cb.aliases)
    for la, ta in va:
        for lb, tb in vb:
            factor = min(_ALIAS_FACTOR.get(la, 1.0), _ALIAS_FACTOR.get(lb, 1.0))
            r = _compare_tokens(ta, tb)
            if r.score * factor > best.score * best_factor + 1e-9 or best_factor == 0.0:
                best, best_via, best_factor = r, la or lb, factor
    value = best.score * best_factor
    m = Match(value, threshold, best.core_pairs, best.descriptor_pairs, best.only_a, best.only_b,
              ca.legal_form, cb.legal_form, compatible(ca.legal_form, cb.legal_form),
              ca.branch, cb.branch, best_via, list(best.notes))
    if value < _INITIALISM_SCORE and (_initialism(ca, cb) or _initialism(cb, ca)):
        m.score = value = _INITIALISM_SCORE
        m.via = "initialism"
        m.notes = ["one name is made of the initials of the other; weak evidence"]
    if m.legal == "different":
        m.score = value * _LEGAL_DIFFERENT
        if strict_legal_form:
            m.score = min(m.score, _CAP_STRICT_LEGAL)
        m.notes.append("different legal forms")
    if ca.branch and cb.branch and _branch_similarity(ca.branch, cb.branch) < _PAIR_MIN:
        m.notes.append("different branches")
    return m


def _branch_similarity(a: str, b: str) -> float:
    ta, tb = parse(a).tokens, parse(b).tokens
    return _compare_tokens(ta, tb).score if ta and tb else 0.0


def compare(a: str, b: str, threshold: float = DEFAULT_THRESHOLD, strict_legal_form: bool = False) -> Match:
    """Compare two company names written in Arabic or Latin script.

    >>> compare("شركة الخليج للتجارة والمقاولات ذ.م.م", "Gulf Trading & Contracting Co. LLC").is_match
    True
    >>> compare("Al Rajhi Bank", "Al Rajhi Cement").is_match
    False

    With ``strict_legal_form=True`` two names with clearly different legal
    forms (LLC vs PJSC) never match; by default the difference only lowers
    the score slightly and is reported in ``Match.legal`` and ``Match.notes``.
    """
    a, b = a or "", b or ""
    if a <= b:
        return _compare(parse(a), parse(b), threshold, strict_legal_form)
    m = _compare(parse(b), parse(a), threshold, strict_legal_form)   # one order only: symmetric by construction
    m.core_pairs = [(y, x, s) for x, y, s in m.core_pairs]
    m.descriptor_pairs = [(y, x, s) for x, y, s in m.descriptor_pairs]
    m.only_a, m.only_b = m.only_b, m.only_a
    m.legal_a, m.legal_b = m.legal_b, m.legal_a
    m.branch_a, m.branch_b = m.branch_b, m.branch_a
    m.notes = [_swap_note(n) for n in m.notes]
    return m


def _swap_note(note: str) -> str:
    head = "each name has a part the other lacks: "
    if note.startswith(head) and "  |  " in note:
        x, y = note[len(head):].split("  |  ", 1)
        return head + y + "  |  " + x
    return note


def score(a: str, b: str) -> float:
    """Similarity in [0, 1] between two company names."""
    return compare(a, b).score


def is_match(a: str, b: str, threshold: float = DEFAULT_THRESHOLD, strict_legal_form: bool = False) -> bool:
    """True if two names plausibly refer to the same company."""
    return compare(a, b, threshold, strict_legal_form).is_match


# --------------------------------------------------------------------------
# keys
# --------------------------------------------------------------------------

def _primary(tok: Token) -> tuple:
    """The form of a core token without its article."""
    if tok.script == "la" and tok.full == 0 and len(tok.forms) > 1:
        return tok.forms[1]
    return tok.forms[0]


def _core_key(tok: Token) -> str:
    if tok.script not in ("ar", "la"):
        return tok.forms[0][0].upper()
    if tok.kind in ("num", "init"):
        return "".join(tok.forms[0]).upper()
    return skeleton(_seq(tok.script, _primary(tok)))


def _skeletons(tok: Token) -> list:
    if tok.script not in ("ar", "la") or tok.kind in ("num", "init"):
        return [_core_key(tok)]
    out = []
    for _n, seq in _variants(tok, "la") + _variants(tok, tok.script):
        k = skeleton(seq)
        if k not in out:
            out.append(k)
        if any(ph.di for ph in seq):
            # a Latin digraph may be two letters: Adham is أدهم (d + h), Fathi is فتحي
            letters = []
            for ph in seq:
                for p in (ph.di or (ph.p,)) if ph.t == "C" else ():
                    c = _SKELETON_KEY.get(p)
                    if c and (not letters or letters[-1] != c):
                        letters.append(c)
            k = "".join(letters) or "0"
            if k not in out:
                out.append(k)
    return out


def normalize(name: str) -> str:
    """A canonical, language-neutral key for a company name.

    Vocabulary words become their concept (lower case), the distinctive core
    becomes a consonant skeleton (upper case); legal form, branch, word order
    and noise are dropped. Two spellings of one company usually share the
    key, but the key is lossy: use :func:`compare` to decide.

    >>> normalize("مصرف الراجحي") == normalize("Al Rajhi Bank") == "RKH bank"
    True
    """
    c = parse(name or "")
    cores = sorted(_core_key(t) for t in c.tokens if not t.concepts)
    concepts = sorted({min(t.concepts) for t in c.tokens if t.concepts})
    return " ".join(cores + concepts)


def _joinable(t: Token) -> bool:
    return t.kind == "core" and t.script in ("ar", "la") and not t.compound


def _joined_skeletons(u: Token, v: Token) -> list:
    """Skeletons of two adjacent words written as one (Abu Dawood -> Abudawood)."""
    out = []
    for a in _skeletons(u)[:2]:
        for b in _skeletons(v)[:2]:
            a_, b_ = a.replace("0", ""), b.replace("0", "")
            k = (a_ + (b_[1:] if a_[-1:] == b_[:1] else b_)) or "0"
            if k not in out:
                out.append(k)
    return out


def _token_keys(tokens: tuple, extended: bool) -> list:
    out = []
    cores = [t for t in tokens if not t.concepts]
    quals = [t for t in tokens if t.kind == "qual"]
    for t in cores:
        out.extend(_skeletons(t))
        form = _primary(t)
        if t.script == "la" and t.kind == "core" and len(form[-1]) >= 5 and form[-1].endswith("at"):
            # Hayat is also written Hayah
            out.append(skeleton(_seq("la", form[:-1] + (form[-1][:-1],))))
    for t in tokens:
        if not t.concepts:
            continue
        if t.kind == "qual" or extended or not (cores or quals):
            out.extend(c for c in sorted(t.concepts))
            out.extend(_skeletons(t))   # the other name may transliterate the word (Watania, Lulu)
    if extended:
        for u, v in zip(tokens, tokens[1:]):
            if _joinable(u) and _joinable(v):
                out.extend(_joined_skeletons(u, v))
    return out


def _initial_keys(c: Company) -> list:
    """Keys that bring a bare acronym and the name it abbreviates together (IBM)."""
    out = []
    if len(c.words) >= 3:
        out.extend("=" + o.upper() for o in sorted(_initial_options(c.words)) if 3 <= len(o) <= 8)
    if len(c.tokens) == 1 and c.tokens[0].script == "la" and c.tokens[0].kind in ("core", "init"):
        form = c.tokens[0].forms[0]
        if len(form) == 1 and 3 <= len(form[0]) <= 8:
            out.append("=" + form[0].upper())
    return out


def _keys(c: Company, extended: bool = False) -> tuple:
    out = []
    for toks in [c.tokens] + [t for _l, t in c.aliases]:
        for k in _token_keys(toks, extended):
            if k not in out:
                out.append(k)
    for k in _initial_keys(c):
        if k not in out:
            out.append(k)
    return tuple(out)


def _block_groups(c: Company) -> list:
    """For a strict candidate search: ``(key sets of the distinctive words, all keys)``
    of the name and of each of its aliases."""
    groups = []
    for toks in [c.tokens] + [t for _l, t in c.aliases]:
        sets = []
        for i, t in enumerate(toks):
            if t.kind not in ("core", "num"):
                continue
            ks = set(_token_keys((t,), False))
            for j in (i - 1, i + 1):
                if 0 <= j < len(toks) and _joinable(t) and _joinable(toks[j]):
                    ks.update(_joined_skeletons(*((toks[j], t) if j < i else (t, toks[j]))))
            sets.append(ks)
        groups.append((sets, _token_keys(toks, False)))
    return groups


def keys(name: str) -> tuple:
    """Language-neutral blocking keys for a company name.

    Consonant skeletons (upper case) of the distinctive words, concepts
    (lower case) of the qualifiers, and ``=`` followed by the initials of the
    words (so that IBM meets its long form). Two names that match share at least one
    key in nearly all cases, so the keys can be stored in an indexed database
    column to fetch candidates, which :func:`compare` then scores.

    >>> set(keys("مصرف الراجحي")) & set(keys("Al Rajhi Bank"))
    {'RKH'}
    """
    return _keys(parse(name or ""))
