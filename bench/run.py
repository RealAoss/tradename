"""Benchmark tradename against the approaches people usually reach for.

    python bench/run.py            # summary tables
    python bench/run.py --errors   # also list every pair tradename gets wrong

Each set is reported three times: Arabic/English groups, Latin-only groups,
and everything together.

Baselines (each is given its *best possible* threshold on the data it is
measured on, which flatters them; tradename is measured at its fixed default
threshold):

* levenshtein       normalised edit distance on the lower-cased strings
* translit+lev      naive letter-by-letter romanisation of Arabic and
                    Cyrillic, then normalised edit distance
* translit+tokens   same romanisation, then a token-set ratio (shared words
                    are free, word order is ignored)
"""

from __future__ import annotations

import os
import sys
import time
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import dataset  # noqa: E402
import tradename  # noqa: E402

try:
    import blind  # noqa: E402
except ModuleNotFoundError as exc:      # the blind set is written last, by someone else
    if exc.name != "blind":
        raise
    blind = None

_AR = {
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h",
    "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d",
    "ط": "t", "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m",
    "ن": "n", "ه": "h", "و": "w", "ي": "y", "ى": "a", "ة": "a", "ء": "", "ؤ": "u", "ئ": "i",
}
_CY = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ы": "y", "э": "e", "ю": "yu",
    "я": "ya", "ъ": "", "ь": "",
}


def translit(s: str) -> str:
    s = "".join(_AR.get(c, c) for c in s).lower()
    s = "".join(_CY.get(c, c) for c in s)
    s = unicodedata.normalize("NFD", s)
    return " ".join("".join(c if c.isalnum() else " " for c in s if not unicodedata.combining(c)).split())


def lev(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return 1.0 - prev[-1] / max(len(a), len(b))


def token_set(a: str, b: str) -> float:
    """Token-set ratio in the style of fuzzy-matching libraries."""
    ta, tb = set(translit(a).split()), set(translit(b).split())
    common = " ".join(sorted(ta & tb))
    only_a = " ".join(sorted(ta - tb))
    only_b = " ".join(sorted(tb - ta))
    x = (common + " " + only_a).strip()
    y = (common + " " + only_b).strip()
    return max(lev(common, x), lev(common, y), lev(x, y)) if common else lev(x, y)


METHODS = {
    "levenshtein": lambda a, b: lev(a.lower(), b.lower()),
    "translit+lev": lambda a, b: lev(translit(a), translit(b)),
    "translit+tokens": token_set,
    "tradename": tradename.score,
}


def build_pairs(GROUPS, DISTINCT):
    pos, neg = [], [tuple(p) for p in DISTINCT]
    for g in GROUPS:
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                pos.append((g[i], g[j]))
    # first two spellings of each group against the first two of every other group
    for x in range(len(GROUPS)):
        for y in range(x + 1, len(GROUPS)):
            neg.append((GROUPS[x][0], GROUPS[y][0]))
            neg.append((GROUPS[x][1], GROUPS[y][1]))
    return pos, neg


def prf(pos_scores, neg_scores, t):
    tp = sum(s >= t for s in pos_scores)
    fp = sum(s >= t for s in neg_scores)
    fn = len(pos_scores) - tp
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def report(GROUPS, DISTINCT, errors=False):
    pos, neg = build_pairs(GROUPS, DISTINCT)
    print(f"{len(GROUPS)} companies, {len(pos)} same-company pairs, {len(neg)} different-company pairs "
          f"({len(DISTINCT)} of them deliberately confusable)\n")
    print(f"{'method':<17}{'threshold':>10}{'precision':>11}{'recall':>9}{'F1':>8}")
    for name, fn in METHODS.items():
        t0 = time.perf_counter()
        ps = [fn(a, b) for a, b in pos]
        ns = [fn(a, b) for a, b in neg]
        dt = time.perf_counter() - t0
        if name == "tradename":
            t = tradename.DEFAULT_THRESHOLD
            note = "   fixed default"
        else:
            t = max((x / 100 for x in range(5, 101)), key=lambda t: prf(ps, ns, t)[2])
            note = "   best threshold for this data"
        p, r, f = prf(ps, ns, t)
        print(f"{name:<17}{t:>10.2f}{p:>11.3f}{r:>9.3f}{f:>8.3f}{note}")
        if name == "tradename":
            print(f"({len(pos) + len(neg)} pairs scored by tradename in {dt:.1f} s)", file=sys.stderr)
        if name == "tradename" and errors:
            print("\nmissed (same company, scored below threshold):")
            for (a, b), s in zip(pos, ps):
                if s < t:
                    print(f"  {s:.2f}  {a}  |  {b}")
            print("\nfalse alarms (different companies, scored at or above threshold):")
            for (a, b), s in zip(neg, ns):
                if s >= t:
                    print(f"  {s:.2f}  {a}  |  {b}")


def main():
    errors = "--errors" in sys.argv
    sets = [("development set (bench/dataset.py): tuned on", dataset)]
    if blind is not None:
        sets.append(("blind set (bench/blind.py): run once, never tuned on", blind))
    for title, mod in sets:
        parts = []
        for part, g, d in (("Arabic / English", "AR_GROUPS", "AR_DISTINCT"),
                           ("Latin script only", "LATIN_GROUPS", "LATIN_DISTINCT"),
                           ("all together", "GROUPS", "DISTINCT")):
            groups, distinct = getattr(mod, g, None), getattr(mod, d, None)
            if part == "all together" and groups is None and parts:
                groups = [x for _p, gs, _d in parts for x in gs]
                distinct = [x for _p, _g, ds in parts for x in ds]
            if groups:
                parts.append((part, list(groups), list(distinct or [])))
        for part, groups, distinct in parts:
            print(f"== {title} - {part} ==")
            report(groups, distinct, errors)
            print()
    if blind is None:
        print("blind set: bench/blind.py is not present, section skipped")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    main()
