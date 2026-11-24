"""Command line interface:  ``tradename compare | parse | key | search | dedupe``.

Exit codes: 0 match / results found, 1 no match / nothing found, 2 usage or input error.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys

from . import __version__
from .index import CompanyIndex, dedupe
from .match import DEFAULT_THRESHOLD, compare, keys, normalize
from .parse import parse


def _fail(message: str):
    """Usage or input error: exit code 2 (1 means "no match")."""
    print(f"tradename: {message}", file=sys.stderr)
    raise SystemExit(2)


def _read_names(path: str, column):
    """Read names from a text file (one per line) or a CSV / TSV column.

    A column given by name skips the header row; a column given by number
    (or no column at all) reads every row, for files without a header.
    """
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            if column is None and not path.lower().endswith((".csv", ".tsv")):
                return [line.strip() for line in fh if line.strip()]
            dialect = "excel-tab" if path.lower().endswith(".tsv") else "excel"
            rows = list(csv.reader(fh, dialect))
    except OSError as exc:
        _fail(f"cannot read {path!r}: {exc.strerror or exc}")
    except UnicodeDecodeError:
        _fail(f"{path!r} is not UTF-8 text")
    except csv.Error as exc:
        _fail(f"{path!r} is not a valid CSV file: {exc}")
    if not rows:
        return []
    header = rows[0]
    if column is None:
        col = 0
    elif column.isdigit():
        col = int(column)
        if col >= max(len(r) for r in rows):
            _fail(f"column {col} not found; the widest row has {max(len(r) for r in rows)} columns")
    elif column in header:
        col = header.index(column)
    else:
        _fail(f"column {column!r} not found; header is {header}")
    body = rows[1:] if (column is not None and not column.isdigit()) else rows
    return [r[col].strip() for r in body if len(r) > col and r[col].strip()]


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    p = argparse.ArgumentParser(
        prog="tradename", description="Match company names across languages, scripts and legal forms.")
    p.add_argument("--version", action="version", version=f"tradename {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare", help="compare two company names")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("--json", action="store_true")
    c.add_argument("-t", "--threshold", type=float, default=DEFAULT_THRESHOLD)
    c.add_argument("--strict-legal-form", action="store_true",
                   help="names with clearly different legal forms never match")

    q = sub.add_parser("parse", help="show how a name is understood")
    q.add_argument("name")
    q.add_argument("--json", action="store_true")

    k = sub.add_parser("key", help="print the canonical key and the blocking keys of a name")
    k.add_argument("name")
    k.add_argument("--json", action="store_true")

    s = sub.add_parser("search", help="find a company in a file of names")
    s.add_argument("file")
    s.add_argument("query")
    s.add_argument("-c", "--column", help="CSV column: a header name, or a 0-based number for a file without header")
    s.add_argument("-n", "--limit", type=int, default=10)
    s.add_argument("-m", "--min-score", type=float, default=0.7)
    s.add_argument("--json", action="store_true")

    d = sub.add_parser("dedupe", help="group names in a file that refer to the same company")
    d.add_argument("file")
    d.add_argument("-c", "--column", help="CSV column: a header name, or a 0-based number for a file without header")
    d.add_argument("-t", "--threshold", type=float, default=DEFAULT_THRESHOLD)
    d.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "compare":
        m = compare(args.a, args.b, args.threshold, args.strict_legal_form)
        print(_dump(m.to_dict()) if args.json else m.explain())
        return 0 if m.is_match else 1

    if args.cmd == "parse":
        co = parse(args.name)
        if args.json:
            print(_dump(co.to_dict()))
        else:
            lf = co.legal_form
            legal = "-"
            if lf:
                legal = f"{lf.text} = {lf.abbr} [{lf.category}]"
                if lf.countries:
                    legal += f" ({', '.join(lf.countries)})"
            print(f"core         {', '.join(co.core) or '-'}")
            print(f"qualifiers   {', '.join(co.qualifiers) or '-'}")
            print(f"descriptors  {', '.join(co.descriptors) or '-'}")
            print(f"concepts     {', '.join(co.concepts) or '-'}")
            print(f"legal form   {legal}")
            print(f"branch       {co.branch if co.branch is not None else '-'}")
            for label, toks in co.aliases:
                print(f"{label:<12} {' '.join(t.text for t in toks)}")
        return 0

    if args.cmd == "key":
        if args.json:
            print(_dump({"key": normalize(args.name), "blocking_keys": list(keys(args.name))}))
        else:
            print(normalize(args.name))
            print(" ".join(keys(args.name)))
        return 0

    names = _read_names(args.file, args.column)
    if args.cmd == "search":
        hits = CompanyIndex(names).search(args.query, args.limit, args.min_score)
        if args.json:
            print(_dump([{"name": n, "score": round(sc, 4)} for n, sc in hits]))
        else:
            for n, sc in hits:
                print(f"{sc:.2f}  {n}")
        return 0 if hits else 1

    clusters = dedupe(names, args.threshold)
    if args.json:
        print(_dump([[names[i] for i in g] for g in clusters]))
    else:
        for n, g in enumerate(clusters, 1):
            print(f"# group {n}")
            for i in g:
                print(f"  {names[i]}")
        print(f"{len(clusters)} group(s) of likely duplicates among {len(names)} names", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
