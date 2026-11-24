"""Measure the speed of tradename on synthetic data built in memory.

    python bench/speed.py

4,000 invented company names (a family name from the lexicon, one or two
lines of business, a legal form) plus 1,000 planted duplicates: half of them
the same name in the other script, half with another spelling of the legal
form and abbreviated words. Nothing is read from or written to disk.
"""

from __future__ import annotations

import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import dataset  # noqa: E402
import tradename  # noqa: E402
from tradename._phonetic import lexicon  # noqa: E402

BUSINESS = [
    ("Trading", "Trdg.", "للتجارة"), ("Contracting", "Cont.", "للمقاولات"), ("Industries", "Inds.", "للصناعات"),
    ("Investment", "Inv.", "للاستثمار"), ("Transport", "Transport", "للنقل"), ("Insurance", "Ins.", "للتأمين"),
    ("Engineering", "Engg.", "للهندسة"), ("Logistics", "Logistics", "للخدمات اللوجستية"),
    ("Real Estate", "Properties", "العقارية"), ("Foodstuff", "Foods", "للمواد الغذائية"),
    ("Pharmacy", "Pharmacy", "صيدلية"), ("Tourism", "Tours", "للسياحة"), ("Furniture", "Furniture", "للأثاث"),
    ("Plastic", "Plastics", "للبلاستيك"), ("Electronics", "Electronics", "للإلكترونيات"),
]
LEGAL = [("LLC", "L.L.C.", "ذ.م.م"), ("Co. Ltd", "Company Limited", "المحدودة"), ("PJSC", "P.J.S.C.", "ش.م.ع"),
         ("Est.", "Establishment", "مؤسسة"), ("W.L.L.", "WLL", "ذ.م.م")]


def build(n_base=4000, n_dup=1000, seed=7):
    rng = random.Random(seed)
    # readings mark a syllable break with a dot (fat.hi); names are written without it
    people = [(r[0].replace(".", ""), a[0]) for r, a in lexicon.ENTRIES
              if len(r) == 1 and len(a) == 1 and len(r[0]) >= 4]
    names, seen, specs = [], set(), []
    while len(names) < n_base:
        first, last = rng.sample(people, 2)
        biz = rng.sample(BUSINESS, rng.choice((1, 1, 2)))
        legal = rng.choice(LEGAL)
        key = (first[0], last[0], tuple(b[0] for b in biz))
        if key in seen:
            continue
        seen.add(key)
        specs.append((first, last, biz, legal))
        names.append(f"{first[0].title()} Al {last[0].title()} {' & '.join(b[0] for b in biz)} {legal[0]}")
    planted = []
    for k in rng.sample(range(n_base), n_dup):
        first, last, biz, legal = specs[k]
        if len(planted) % 2:
            biz_ar = " و".join(b[2] for b in biz)
            if legal[2] == "مؤسسة":
                dup = f"مؤسسة {first[1]} ال{last[1]} {biz_ar}"
            else:
                dup = f"شركة {first[1]} ال{last[1]} {biz_ar} {legal[2]}"
        else:
            dup = f"{first[0].upper()} AL-{last[0].upper()} {' and '.join(b[1] for b in biz)} {legal[1]}"
        planted.append((k, len(names)))
        names.append(dup)
    return names, planted


def main():
    pairs = [(g[i], g[j]) for g in dataset.GROUPS for i in range(len(g)) for j in range(i + 1, len(g))]
    pairs += [tuple(p) for p in dataset.DISTINCT]
    t0 = time.perf_counter()
    for a, b in pairs:
        tradename.compare(a, b)
    cold = (time.perf_counter() - t0) / len(pairs)
    t0 = time.perf_counter()
    for a, b in pairs:
        tradename.compare(a, b)
    warm = (time.perf_counter() - t0) / len(pairs)
    print(f"compare: {cold * 1000:.2f} ms per pair first time, {warm * 1000:.3f} ms repeated "
          f"({len(pairs)} pairs of the development set)")

    names, planted = build()
    t0 = time.perf_counter()
    index = tradename.CompanyIndex(names)
    print(f"index:   {len(names)} names indexed in {time.perf_counter() - t0:.2f} s")

    queries = [names[j] for _k, j in planted[:200]]
    t0 = time.perf_counter()
    found = 0
    for (k, _j), q in zip(planted, queries):
        hits = index.search_ids(q, limit=5, min_score=tradename.DEFAULT_THRESHOLD)
        found += any(i == k for i, _s in hits)
    dt = (time.perf_counter() - t0) / len(queries)
    print(f"search:  {dt * 1000:.1f} ms per query at min_score 0.85; "
          f"{found} of {len(queries)} planted originals in the top 5")
    t0 = time.perf_counter()
    for q in queries:
        index.search(q)
    dt = (time.perf_counter() - t0) / len(queries)
    print(f"search:  {dt * 1000:.1f} ms per query at the default min_score 0.7 (wider candidate net)")

    t0 = time.perf_counter()
    clusters = tradename.dedupe(names)
    dt = time.perf_counter() - t0
    where = {i: n for n, g in enumerate(clusters) for i in g}
    hit = sum(1 for k, j in planted if k in where and where.get(j) == where[k])
    print(f"dedupe:  {len(names)} names in {dt:.1f} s; {hit} of {len(planted)} planted duplicates grouped; "
          f"{len(clusters)} clusters, largest {max(map(len, clusters), default=0)}")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    main()
