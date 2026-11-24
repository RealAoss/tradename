"""Search and de-duplicate lists of company names without comparing every pair."""

from __future__ import annotations

from .match import (_CAP_EXTRA_CORE, DEFAULT_THRESHOLD, _block_groups, _cannot_match, _initial_keys, _keys,
                    compare)
from .parse import parse

__all__ = ["CompanyIndex", "dedupe"]


class CompanyIndex:
    """An in-memory index of company names that can be searched in any script.

    >>> idx = CompanyIndex(["مصرف الراجحي", "Gulf Trading LLC", "Emaar Properties PJSC"])
    >>> [name for name, _ in idx.search("Al Rajhi Bank")]
    ['مصرف الراجحي']
    """

    def __init__(self, names=()):
        self._names: list = []
        self._parsed: list = []
        self._ids: list = []
        self._buckets: dict = {}    # blocking key -> positions
        for name in names:
            self.add(name)

    def __len__(self) -> int:
        return len(self._names)

    def add(self, name: str, id=None) -> None:
        """Add a name. ``id`` is returned by :meth:`search_ids` (default: position)."""
        pos = len(self._names)
        parsed = parse(name or "")
        self._names.append(name)
        self._parsed.append(parsed)
        self._ids.append(pos if id is None else id)
        for k in _keys(parsed, extended=True):
            self._buckets.setdefault(k, []).append(pos)

    def _candidates(self, name: str, strict: bool = False) -> list:
        """Stored names sharing a blocking key with ``name``.

        ``strict`` is for scores above ``_CAP_EXTRA_CORE``, which need every
        distinctive word to have a counterpart: a candidate must then share
        keys with two distinctive words of the name (with the only one if
        there is just one).
        """
        parsed = parse(name or "")
        seen = set()
        if not strict:
            for k in _keys(parsed):
                seen.update(self._buckets.get(k, ()))
            return sorted(seen)
        for k in _initial_keys(parsed):
            seen.update(self._buckets.get(k, ()))
        for sets, every in _block_groups(parsed):
            if not sets:      # a name of generic words only
                for k in every:
                    seen.update(self._buckets.get(k, ()))
                continue
            counts: dict = {}
            for ks in sets:
                hit = set()
                for k in ks:
                    hit.update(self._buckets.get(k, ()))
                for pos in hit:
                    counts[pos] = counts.get(pos, 0) + 1
            need = min(2, len(sets))
            seen.update(pos for pos, n in counts.items() if n >= need)
        return sorted(seen)

    def _search(self, query, limit, min_score, exhaustive):
        skip = min_score > _CAP_EXTRA_CORE
        cands = range(len(self._names)) if exhaustive else self._candidates(query, strict=skip)
        hits = []
        parsed = parse(query or "")
        for pos in cands:
            if skip and _cannot_match(parsed, self._parsed[pos]):
                continue
            s = compare(query, self._names[pos]).score
            if s >= min_score:
                hits.append((s, pos))
        hits.sort(key=lambda h: (-h[0], h[1]))
        return hits[:limit] if limit else hits

    def search(self, query: str, limit: int = 10, min_score: float = 0.7, exhaustive: bool = False) -> list:
        """Return ``[(name, score), ...]`` best first.

        Candidates are found through blocking keys, which is fast but can miss
        an unusual spelling; pass ``exhaustive=True`` to score every stored name.
        """
        return [(self._names[p], s) for s, p in self._search(query, limit, min_score, exhaustive)]

    def search_ids(self, query: str, limit: int = 10, min_score: float = 0.7, exhaustive: bool = False) -> list:
        """Like :meth:`search` but returns ``[(id, score), ...]``."""
        return [(self._ids[p], s) for s, p in self._search(query, limit, min_score, exhaustive)]


def dedupe(names, threshold: float = DEFAULT_THRESHOLD) -> list:
    """Group names that refer to the same company.

    Returns a list of clusters, each a list of indexes into ``names``; only
    clusters with two or more members are returned. Matching is transitive
    (single linkage), so review large clusters before merging records.
    """
    names = list(names)
    index = CompanyIndex(names)
    parent = list(range(len(names)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    skip = threshold > _CAP_EXTRA_CORE
    for i, name in enumerate(names):
        for j in index._candidates(name, strict=skip):
            if j == i:
                continue
            ri, rj = find(i), find(j)
            if ri == rj or (skip and _cannot_match(index._parsed[i], index._parsed[j])):
                continue
            if compare(name or "", names[j] or "").score >= threshold:
                parent[max(ri, rj)] = min(ri, rj)
    groups: dict = {}
    for pos in range(len(names)):
        groups.setdefault(find(pos), []).append(pos)
    return [g for g in groups.values() if len(g) > 1]
