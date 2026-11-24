# Vendored from ismatch (https://github.com/RealAoss/ismatch), MIT licence, same
# author. ismatch is not published on PyPI, so tradename carries its own copy.
# Adapted for tradename; do not expect it to stay in sync with upstream.

"""Weighted phonetic edit distance between two phoneme sequences.

The costs encode how Arabic names actually vary when they are written down:

* short vowels are not written in Arabic / Hebrew, so a Latin vowel facing a
  gap in an abjad costs almost nothing, while a *written* long vowel does;
* consonants that are routinely confused in romanisation are cheap to swap
  (q/k/g, j/g, th/t/s, dh/d/z, kh/h ...);
* ayn, hamza and an initial alef behave as a wildcard vowel against Latin;
* a Latin digraph such as "th" may really be two consonants (Fat-hi).
"""

from __future__ import annotations

INF = 99.0
_SEMI = ("w", "y")

_CONF_PAIRS = {
    ("θ", "t"): 0.3, ("θ", "s"): 0.3, ("θ", "ð"): 0.2,
    ("ð", "d"): 0.25, ("ð", "z"): 0.2,
    ("j", "g"): 0.25, ("g", "ġ"): 0.2, ("q", "k"): 0.25, ("q", "g"): 0.25,
    ("ġ", "q"): 0.5, ("k", "x"): 0.4, ("h", "x"): 0.4, ("q", "x"): 0.6,
    ("š", "s"): 0.5, ("š", "x"): 0.5, ("š", "j"): 0.5, ("s", "z"): 0.4,
    ("f", "v"): 0.3, ("w", "v"): 0.2, ("b", "v"): 0.4, ("k", "g"): 0.7,
    ("t", "d"): 0.6, ("j", "y"): 0.5, ("j", "z"): 0.5, ("ġ", "r"): 0.6,
    ("m", "n"): 0.7,
}
CONF = {}
for (_a, _b), _c in _CONF_PAIRS.items():
    CONF[(_a, _b)] = _c
    CONF[(_b, _a)] = _c

# Hebrew writers often drop the geresh, so these pairs are near-equal there.
_HE_SOFT = {frozenset(p) for p in (("h", "x"), ("k", "x"), ("g", "j"), ("š", "s"), ("d", "ð"), ("t", "θ"))}

_FINAL = 0.8
_E_COST = {"A": 0.05, "I": 0.05, "U": 0.2}


def del_cost(x, other_src: str) -> float:
    t = x.t
    if t == "C":
        return 0.5 if x.p in _SEMI else 1.0
    if t == "V":
        if x.src == "la":
            return 0.2 if other_src == "la" else 0.03
        if x.src == "ar":
            return 0.5 if x.long else 0.1
        return 0.25
    if t == "W":
        if x.p == "ʕ" and x.src != "la" and other_src == x.src:
            return 0.8
        return 0.1
    return 0.1  # H


def _vowel_sub(x, y) -> float:
    a, b = x.p, y.p
    if a == b:
        return 0.0
    if x.alt == b or y.alt == a:
        return 0.15
    if a == "E":
        return _E_COST[b]
    if b == "E":
        return _E_COST[a]
    if x.src == "la" and y.src == "la":
        return 0.3
    return 0.4


def sub_cost(x, y) -> float:
    tx, ty = x.t, y.t
    if tx == "C" and ty == "C":
        if x.p == y.p:
            if x.raw and y.raw and x.raw != y.raw and x.src == y.src:
                return 0.4  # same script, different letter (س / ص)
            return 0.0
        c = CONF.get((x.p, y.p))
        if c is None:
            return INF
        if x.src == y.src and x.src != "la":
            return 0.5 if c <= 0.25 else 1.0  # same script: a different letter, not a romanisation choice
        if (x.src == "he" or y.src == "he") and frozenset((x.p, y.p)) in _HE_SOFT:
            return min(c, 0.15)
        return c
    if tx == "V" and ty == "V":
        return _vowel_sub(x, y)
    if tx == "W" or ty == "W":
        w, o = (x, y) if tx == "W" else (y, x)
        same_abjad = w.src == o.src and w.src != "la"
        if o.t == "W":
            if w.p == o.p:
                return 0.0
            return 0.5 if same_abjad else 0.0
        if o.t == "V":
            return 0.5 if (w.p == "ʕ" and same_abjad) else 0.0
        if o.t == "C":
            return 0.1 if o.p in _SEMI else INF
        return 0.3
    if tx == "H" or ty == "H":
        h, o = (x, y) if tx == "H" else (y, x)
        if o.t == "H":
            return 0.0
        if o.t == "V":
            return 0.05
        if o.p == "h":
            return 0.05
        return 0.5 if o.p == "x" else INF
    c, v = (x, y) if tx == "C" else (y, x)
    if c.p == "y" and v.p in "IE":
        return 0.1
    if c.p == "w" and v.p == "U":
        return 0.1
    return INF


def _two_for_one(x, y1, y2) -> float:
    """Latin digraph ``x`` (e.g. "th") read as two consonants ``y1 y2`` (t + h)."""
    if not (y2.t == "H" or (y2.t == "C" and y2.p == "h")):
        return INF
    if y1.t != "C":
        return INF
    first = x.di[0]
    if y1.p == first:
        return 0.1
    c = CONF.get((first, y1.p))
    if c is not None and c <= 0.3:
        return 0.1 + c
    return INF


def _del_costs(seq, other_src):
    """Return ``(deletion costs, weights)`` for a sequence.

    The weights (context-free) normalise the distance; the deletion costs add
    what the position of a phoneme tells us.
    """
    weights = [del_cost(x, other_src) for x in seq]
    out = list(weights)
    n = len(seq)
    if other_src == "la" and seq[0].src == "la":
        for i, x in enumerate(seq):
            before_vowel = i + 1 < n and (seq[i + 1].t == "V" or seq[i + 1].p in _SEMI)
            if x.t == "V":
                # the weak half of a diphthong (Hussain / Husin, Aisha / Ayesha)
                if (i > 0 and seq[i - 1].p in _SEMI) or (before_vowel and x.p in "AE"):
                    out[i] = 0.1
            elif x.p in _SEMI and 0 < i < n - 1 and seq[i - 1].t == "V" and seq[i + 1].t == "V":
                out[i] = 0.15  # glide between vowels (Sayeed / Saeed)
    if n >= 3:
        last = seq[-1]
        if last.t == "V":
            if last.src == "la" and last.p == "E" and n >= 4 and seq[-2].t == "C":
                out[-1] = 0.05  # silent final -e of French-style spellings (Hocine)
            else:
                out[-1] = _FINAL  # a final vowel is often all that marks a feminine name
        elif last.t == "H" and last.src != "la":
            out[-1] = _FINAL
    return out, weights


def distance(a, b):
    """Return ``(distance, weight_a, weight_b)`` for two non-empty sequences."""
    sa, sb = a[0].src, b[0].src
    n, m = len(a), len(b)
    da, wa = _del_costs(a, sb)
    db, wb = _del_costs(b, sa)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        D[i][0] = D[i - 1][0] + da[i - 1]
    row0 = D[0]
    for j in range(1, m + 1):
        row0[j] = row0[j - 1] + db[j - 1]
    for i in range(1, n + 1):
        x = a[i - 1]
        row, up = D[i], D[i - 1]
        for j in range(1, m + 1):
            y = b[j - 1]
            best = up[j] + da[i - 1]
            c = row[j - 1] + db[j - 1]
            if c < best:
                best = c
            s = sub_cost(x, y)
            if s < INF:
                c = up[j - 1] + s
                if c < best:
                    best = c
            if x.di and j >= 2:
                s = _two_for_one(x, b[j - 2], y)
                if s < INF:
                    c = up[j - 2] + s
                    if c < best:
                        best = c
            if y.di and i >= 2:
                s = _two_for_one(y, a[i - 2], x)
                if s < INF:
                    c = D[i - 2][j - 1] + s
                    if c < best:
                        best = c
            row[j] = best
    return D[n][m], sum(wa), sum(wb)


def similarity(a, b) -> float:
    """Similarity in [0, 1] between two phoneme sequences."""
    if not a or not b:
        return 1.0 if (not a and not b) else 0.0
    d, wa, wb = distance(a, b)
    w = max(wa, wb)
    if w <= 0:
        return 1.0 if d == 0 else 0.0
    return max(0.0, 1.0 - d / w)


_KEY = {
    "b": "B", "f": "F", "v": "F", "t": "T", "θ": "T", "d": "D", "ð": "D", "z": "D",
    "s": "S", "š": "C", "j": "K", "g": "K", "ġ": "K", "q": "K", "k": "K", "x": "X",
    "h": "H", "l": "L", "m": "M", "n": "N", "r": "R",
}


def skeleton(seq) -> str:
    """Coarse consonant skeleton, used as a blocking key ("MHMD")."""
    out = []
    for x in seq:
        if x.t == "C":
            k = _KEY.get(x.p)
            if k and (not out or out[-1] != k):
                out.append(k)
    return "".join(out) or "0"
