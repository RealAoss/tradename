# Contributing

Thank you for helping. No setup is needed beyond Python 3.10+; the project has
no dependencies.

```bash
python -m unittest discover -s tests     # must pass
python bench/run.py --errors             # shows every pair the matcher gets wrong
python bench/speed.py                    # speed on 5,000 synthetic names
```

## Add a legal form (most useful)

Open `src/tradename/legal.py` and add a line to `_DATA`, or a spelling to an
existing line:

```
category | CANONICAL | countries | spelling ; spelling ; ...
```

- `category` is one of `CATEGORIES` at the top of the file
  (`limited_liability`, `joint_stock`, `public_joint_stock` ...). Pick the
  closest one; the categories are deliberately coarse.
- `CANONICAL` is the abbreviation that `tradename.parse` reports.
- `countries` are ISO 3166 alpha-2 codes, or `*` for a generic form.
- Write each spelling the way it appears in a name. Dots, case and spaces
  between single letters do not matter: `L.L.C`, `LLC` and `L L C` are one
  spelling.
- Start a spelling with `!` when it is also an ordinary word or a common pair
  of initials (`!SA`, `!AS`, `!AG`). It is then read as a legal form only at
  the end of a name or when written with dots.
- If a spelling means different things in different countries, list it on
  two lines; the parser then keeps both readings.

Forms from Africa, South and South-East Asia, Latin America and the Nordic
and Baltic countries are thin or missing. Every line helps.

## Add a business word, an abbreviation or an acronym

Open `src/tradename/vocab.py`:

```
concept : kind | latin spellings | arabic spellings
```

- `kind` is `d` for a descriptor (what the company does or is: trading,
  bank, group), `q` for a qualifier (national, gulf, golden) or `p` for a
  place.
- Latin spellings include the English word, its abbreviations (`trdg`), and
  common transliterations of the Arabic word (`khaleej`).
- Arabic spellings are written **without the article**; list plural and
  adjective forms explicitly.
- Put two words on one line only if a company would use either for the same
  thing. Words on one line can never tell two companies apart: that is why
  "Kuwait Petroleum Corporation" and "Kuwait Oil Company" currently match.
- Known acronyms go in `_ACRONYM_DATA`:
  `LATIN ; arabic | English expansion | Arabic expansion`.

Only Arabic and English are translated today. Vocabulary for another
language would be a larger change; please open an issue first.

## Report a wrong result

Open an issue with the two names, what you expected, and the output of:

```bash
tradename compare "name one" "name two"
tradename parse "name one"
```

Use public or invented company names in issues, tests and data sets, never
names from a customer file.

## Change the matcher

- Add the failing pairs to `bench/dataset.py` first, then fix.
- Prefer a general rule over a special case for one company.
- Precision comes first. A change that makes two different companies match
  ("National Bank of X" / "National Bank of Y") is a regression even if
  recall improves.
- **Never tune against `bench/blind.py`.** That file is written by someone
  who has not read the engine, and is run once. If a change is motivated by a
  pair in it, move the pair to `dataset.py` and note it in the changelog, so
  the blind numbers stay honest.
- Keep the library dependency-free and compatible with Python 3.10.
- `src/tradename/_phonetic` is vendored from
  [ismatch](https://github.com/RealAoss/ismatch). Fix phonetic bugs there
  first when they are not specific to company names.

## Real-world data

Labelled pairs of company names from a real system (even a few hundred)
would improve this project more than anything else. If you cannot share
data, sharing the precision / recall you measured is still valuable.
