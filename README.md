# tradename

**Match company names across spellings, legal forms, abbreviations, word order and scripts.**
`Samsung Electronics Co., Ltd.` = `SAMSUNG ELECTRONICS COMPANY LIMITED`,
`شركة الخليج للتجارة والمقاولات ذ.م.م` = `Gulf Trading & Contracting Co. LLC`,
but `National Bank of Kuwait` ≠ `National Bank of Bahrain`.

Pure Python, zero dependencies, works offline.

```python
>>> import tradename
>>> tradename.is_match("Samsung Electronics Co., Ltd.", "SAMSUNG ELECTRONICS COMPANY LIMITED")
True
>>> tradename.is_match("شركة الخليج للتجارة والمقاولات ذ.م.م", "Gulf Trading & Contracting Co. LLC")
True
>>> tradename.is_match("ПАО Газпром", "Gazprom PJSC")
True
>>> tradename.is_match("National Bank of Kuwait", "National Bank of Bahrain")
False
>>> tradename.is_match("Al Rajhi Bank", "Al Rajhi Cement")
False
>>> print(tradename.compare("Siemens Aktiengesellschaft", "Siemens Energy AG").explain())
score 0.82  (possible)
  core        Siemens  ~  Siemens   1.00
  legal form  Aktiengesellschaft [joint_stock]  ~  AG [joint_stock]   same
  only in second: Energy
  note: one name adds a line of business: Energy
```

## Why this exists

The same company is written differently in every system that stores it: with
or without its legal form, with the legal form spelled out or abbreviated,
with "Trading" shortened to "Trdg.", with the words in another order, in
capitals, in Arabic. Comparing these names as plain strings fails in both
directions:

- **KYC and onboarding** cannot tell that the customer on the application is
  the company already on file under a slightly different name.
- **Vendor and customer master data** fill up with duplicates, so one
  supplier has three records, three payment histories and three credit
  limits.
- **Sanctions and watch-list screening** either misses a listed entity whose
  name was romanised differently, or buries analysts in false hits because
  every name containing "Trading" or "International" looks alike to a generic
  fuzzy matcher.
- **Invoice and payment matching** cannot link "ACME Mfg. Intl. Limited" on an
  invoice to "Acme Manufacturing International Ltd" in the ledger.

Generic string similarity gets company names wrong because it treats every
word alike. In a company name the words are not alike: "Ltd" carries almost no
identity, "Trading" a little, "Gulf" more, and the distinctive word carries
nearly all of it. `tradename` types each word first and scores afterwards. It
is a small library you can read in an afternoon and drop into any pipeline.

## What it understands

| Phenomenon | Example |
|---|---|
| Legal forms, spelled out or abbreviated | Siemens AG ↔ Siemens Aktiengesellschaft · Acme Widgets Ltd ↔ Acme Widgets Limited |
| Dots, spacing and case in legal forms | L.L.C. / LLC / L L C · `ذ.م.م` / `ذ م م` · S.à r.l. / SARL |
| A missing legal form | Banco Santander, S.A. ↔ Banco Santander |
| Legal forms across languages | `إعمار العقارية ش.م.ع` ↔ Emaar Properties PJSC · ПАО Газпром ↔ Gazprom PJSC · Toyota Motor Corp. ↔ Toyota Motor Kabushiki Kaisha |
| Abbreviated business words | Acme Manufacturing International Ltd ↔ ACME Mfg. Intl. Limited |
| `&` / and, punctuation, accents | Johnson & Johnson ↔ Johnson and Johnson · Nestlé S.A. ↔ Nestle SA · Koç Holding A.Ş. ↔ Koc Holding AS |
| Word order | Bank Muscat ↔ Muscat Bank · Grupo Bimbo ↔ Bimbo Group |
| Translated business words (Arabic ↔ English) | `مكتبة جرير` ↔ Jarir Bookstore · `حديد عز` ↔ Ezz Steel |
| Transliterated names (Arabic ↔ Latin) | `مصرف الراجحي` ↔ Al Rajhi Bank / Al-Rajhi Bank / Alrajhi Bank |
| A word translated in one name, transliterated in the other | `شركة الخليج للتجارة` ↔ Gulf Trading ↔ Al Khaleej Trading |
| Joined or split words | Almarai ↔ Al Marai · Saudi Binladin Group ↔ Saudi Bin Laden Group |
| Known acronyms | SABIC ↔ Saudi Basic Industries Corporation · `سابك` |
| An acronym in brackets | Saudi Basic Industries Corp. (SABIC) ↔ SABIC |
| Initials (weak evidence, reported as such) | IBM ↔ International Business Machines Corp. |
| Former names and trade names | Acme Widgets Ltd (formerly Apex Gadgets Ltd) ↔ Apex Gadgets Limited · "t/a", "d/b/a" |
| Branch markers and bracketed places | "... - Dammam Branch" · Commercial International Bank (Egypt) S.A.E. ↔ Commercial International Bank |
| Cyrillic legal forms and names | ООО Ромашка ↔ Romashka LLC |

It knows 447 spellings of about 80 legal forms from some 60 jurisdictions
(the Gulf and the wider Arab world, the English-speaking world, most of
Europe, Russia, Turkey, Japan, Malaysia, Singapore, Mexico, Brazil ...) and
264 business concepts with their English and Arabic spellings and
abbreviations.

And, just as important, what it refuses to merge:

| Different companies | Why they are hard |
|---|---|
| National Bank of Kuwait ≠ National Bank of Bahrain | every word but one is shared |
| Gulf Trading LLC ≠ Emirates Trading LLC | same business, same legal form |
| Al Rajhi Bank ≠ Al Rajhi Cement | same family name, different business |
| Arab Bank ≠ Arab National Bank | a name of generic words must agree on every word |
| Siemens AG ≠ Siemens Energy AG | an added line of business usually names a subsidiary |
| Majid Al Futtaim ≠ Al-Futtaim Group | one extra distinctive word |
| Johnson & Johnson ≠ Johnson Controls | shared first word |
| Aramex ≠ Aramco · Enel ≠ Eni | similar spelling, another word |
| Rossi Costruzioni S.r.l. ≠ Russo Costruzioni S.r.l. | one vowel apart |
| Studio 54 Ltd ≠ Studio 45 Ltd | numbers are compared exactly |

A pair that is refused is not thrown away. The first five pairs above score
between 0.72 and 0.82, which `Match.level` calls `possible`, so a review
queue can still see them; the others score 0.62 or less.

## How it works

1. **Tokenise** the name. Dotted or spaced single letters become one word
   (`L.L.C.` → `llc`); brackets, "formerly ..." and "t/a ..." are split off as
   aliases; a branch marker is removed and reported.
2. **Type every word**:
   - a **legal form**, looked up in a table of forms by jurisdiction and
     mapped to one of 13 categories (limited liability, joint stock, public
     joint stock, partnership ...);
   - a **descriptor** (what the company does: trading, bank, steel) or a
     **qualifier** (national, gulf, a country, a city), looked up in a
     vocabulary that maps English and Arabic spellings to one concept;
   - the distinctive **core**: whatever is left.
3. **Compare** word against word. Vocabulary words are compared by meaning,
   so a word matches its translation. Core words are compared by sound with
   a weighted phonetic edit distance, so a word matches its transliteration
   and its spelling variants. Words are assigned to each other in the best
   possible way, whatever their order.
4. **Score.** The core dominates and must agree. A conflict between
   descriptors or qualifiers ("Bank" against "Cement") caps the score below
   the threshold. The less distinctive a name is, the stricter the rule: a
   name made only of vocabulary words needs every word to agree. A different
   legal form lowers the score a little and is reported; with
   `strict_legal_form=True` it prevents a match.

No machine learning, no model download: the result is deterministic and every
score can be explained (`Match.explain()`).

The phonetic core (phonemes, weighted edit distance and a lexicon of 461
Arabic personal names, which appear in many company names) is shared with
[ismatch](https://github.com/RealAoss/ismatch), a library for matching
personal names; a copy is vendored in `src/tradename/_phonetic`.

## Accuracy

`python bench/run.py` compares `tradename` with the approaches people usually
reach for. Each baseline gets the **best possible threshold for that data**;
`tradename` uses its fixed default (0.85).

Development set (`bench/dataset.py`, tuned on): 104 companies, 677
same-company pairs and 10,843 different-company pairs, 131 of them
deliberately confusable.

| Part | Pairs | Method | Precision | Recall | F1 |
|---|---|---|---|---|---|
| All together | 11,520 | Levenshtein | 0.583 | 0.482 | 0.528 |
| | | Transliterate + Levenshtein | 0.587 | 0.539 | 0.562 |
| | | Transliterate + token-set ratio | 0.710 | 0.560 | 0.626 |
| | | **tradename** | **0.996** | **0.996** | **0.996** |
| Arabic / English | 4,441 | Transliterate + token-set ratio | 0.518 | 0.446 | 0.479 |
| | | **tradename** | 0.993 | 0.993 | 0.993 |
| Latin script only | 1,913 | Transliterate + token-set ratio | 0.841 | 0.897 | 0.868 |
| | | **tradename** | 1.000 | 1.000 | 1.000 |

Blind set (written by someone who had not seen the engine, run once, never
tuned on):

`bench/blind.py`: 118 companies, 880 same-company pairs and 14,142
different-company pairs, 336 of them deliberately confusable.

| Part | Pairs | Method | Precision | Recall | F1 |
|---|---|---|---|---|---|
| All together | 15,022 | Levenshtein | 0.624 | 0.500 | 0.555 |
| | | Transliterate + Levenshtein | 0.652 | 0.515 | 0.575 |
| | | Transliterate + token-set ratio | 0.716 | 0.556 | 0.626 |
| | | **tradename** | **0.981** | **0.774** | **0.865** |
| Arabic / English | 3,381 | Transliterate + token-set ratio | 0.625 | 0.343 | 0.443 |
| | | **tradename** | 0.997 | 0.769 | 0.868 |
| Latin script only | 4,751 | Transliterate + token-set ratio | 0.771 | 0.808 | 0.789 |
| | | **tradename** | 0.965 | 0.780 | 0.862 |

**This is the number to believe, and it is much lower than the development
one.** On names it has never seen, `tradename` is rarely wrong when it says
"same company" (precision 0.98) but misses about one true match in four. The
matcher was not changed after this run; `python bench/run.py --errors` prints
every wrong pair. The misses fall into a few families:

- **Brand names and acronyms that are not derivable from the legal name**
  (`Mobily` for Etihad Etisalat, `Omantel` for Oman Telecommunications
  Company, `BBK`, `QIC`, `DP World` for Dubai Ports World, `Maroc Telecom` for
  Itissalat Al-Maghrib). Linking these needs an alias table, which this
  library does not ship.
- **Joined versus split brand words** (`EgyptAir` / `Egypt Air`, `Tunisair` /
  `Tunis Air`, `Mashreqbank` / `Mashreq Bank`, `flynas` / `Fly Nas`).
- **Brand names transliterated into Arabic** that are not in the vocabulary
  (`سوناطراك` / Sonatrach, `بلو أوشن` / Blue Ocean).
- **A bare name against the same name with "Group" or a line of business**
  (`Qatar Airways` / `Qatar Airways Group Q.C.S.C.`, `Royal Jordanian` /
  `Royal Jordanian Airlines`) scores 0.80, just under the threshold, by
  design: see Limitations.

Read these numbers with care:

- **The development numbers are optimistic.** The set was written by the
  project authors, and the matcher was tuned on it until the numbers above
  came out. Before that tuning the same set scored precision 0.987 and recall
  0.973. Treat the development rows as a regression test, not as an
  evaluation. Only a blind row is an honest estimate.
- **The sets were written, not collected.** The names of real companies are
  used as the authors remember them from public sources; the variants are
  made up, and nothing was checked against a company registry. Real data
  will be messier.
- **A name match is not a legal-entity match.** Two different legal entities
  can carry the same name (in different countries, or one after the other),
  and one entity can trade under several names. Combine the score with a
  registration number, a tax number, a country or an address before merging
  records or blocking a payment.
- If you have labelled pairs of company names from a real system and can
  share them (or just the aggregate results), please open an issue. That is
  the most valuable contribution this project can receive.

Speed on a laptop, single thread, Python 3.14 (`python bench/speed.py`): a
comparison takes about 0.2 ms the first time and 0.04 ms once the words have
been seen. Indexing 5,000 names takes 1.2 s. Searching that index takes about
3 ms per query at `min_score=0.85` and about 26 ms at the default
`min_score=0.7`, which casts a wider net. De-duplicating the 5,000 names takes
about 5 s. The data is synthetic: 4,000 invented names plus 1,000 planted
duplicates, half of them in the other script; all 1,000 were found.

## Install

```bash
pip install git+https://github.com/RealAoss/tradename
```

or clone the repository and run `pip install .`. Python 3.10+.

## Usage

### Compare two names

```python
>>> m = tradename.compare("Al Saqr Insurance Co. PSC", "شركة الصقر للتأمين ش.م.ع")
>>> m.is_match           # score >= threshold (default 0.85)
True
>>> m.level              # 'strong' | 'probable' | 'possible' | 'no'
'strong'
>>> m.core_pairs
[('Saqr', 'الصقر', 0.9900990099009901)]
>>> m.descriptor_pairs
[('Insurance', 'للتأمين', 1.0)]
>>> m.legal              # 'same' | 'compatible' | 'different' | 'unknown'
'compatible'
>>> m.legal_a.abbr, m.legal_b.abbr
('PSC', 'PJSC')
>>> print(m.explain())
score 0.99  (strong)
  core        Saqr  ~  الصقر   0.99
  descriptor  Insurance  ~  للتأمين   1.00
  legal form  PSC [private_joint_stock]  ~  شمع [public_joint_stock]   compatible
```

`m.to_dict()` gives the same information ready for JSON. `m.via` says when
the match went through an `'alias'`, a `'former name'`, an `'acronym'` or an
`'initialism'`.

```python
>>> tradename.score("Tata Consultancy Services Limited", "Tata Consultancy Svcs Ltd.")
1.0
>>> tradename.score("Tata Steel Limited", "Tata Power Limited")
0.72
>>> tradename.is_match("Emaar Properties PJSC", "Emaar Properties LLC")
True
>>> tradename.is_match("Emaar Properties PJSC", "Emaar Properties LLC", strict_legal_form=True)
False
>>> tradename.compare("IBM", "International Business Machines Corp.").via
'initialism'
```

Choosing a threshold: `0.85` balances both error types. For anything that
blocks a customer or a payment (sanctions, fraud), keep a human in the loop
and treat `possible` (0.70-0.85) as "needs review", never as a decision.

### See how a name is understood

```python
>>> c = tradename.parse("Gulf Trading & Contracting Co. LLC - Dubai Branch")
>>> c.qualifiers, c.descriptors, c.concepts
(('Gulf',), ('Trading', 'Contracting'), ('gulf', 'trading', 'contracting'))
>>> c.legal_form.abbr, c.legal_form.category, c.branch
('LLC', 'limited_liability', 'Dubai')
>>> tradename.parse("Müller Maschinenbau GmbH & Co. KG").legal_form
LegalForm(abbr='GmbH & Co. KG', category='limited_partnership', categories=('limited_partnership',), countries=('DE', 'AT'), text='GmbH & Co KG')
>>> tradename.parse("Zenith Marble Works Pty Ltd").core
('Zenith',)
```

### Search a list

```python
>>> idx = tradename.CompanyIndex(["مصرف الراجحي", "Gulf Trading LLC", "Siemens AG", "Siemens Energy AG"])
>>> idx.add("Banco Santander, S.A.", id="V-0042")
>>> idx.search("Al Rajhi Bank")
[('مصرف الراجحي', 1.0)]
>>> idx.search("Siemens")
[('Siemens AG', 1.0), ('Siemens Energy AG', 0.82)]
>>> idx.search_ids("Banco Santander")
[('V-0042', 1.0)]
```

`search(query, limit=10, min_score=0.7, exhaustive=False)` finds candidates
through blocking keys; `exhaustive=True` scores every stored name instead.

### Find duplicates

```python
>>> names = ["Gulf Trading & Contracting Co. LLC", "Siemens AG", "شركة الخليج للتجارة والمقاولات ذ.م.م",
...          "SIEMENS AKTIENGESELLSCHAFT", "Siemens Energy AG"]
>>> tradename.dedupe(names)          # indexes into names
[[0, 2], [1, 3]]
```

Matching is transitive (single linkage): review large clusters before merging
records.

### Keys for databases

```python
>>> tradename.normalize("مصرف الراجحي")
'RKH bank'
>>> tradename.normalize("Al-Rajhi Bank LLC")
'RKH bank'
>>> tradename.keys("مصرف الراجحي")
('RKH', 'LRKH')
>>> tradename.keys("Al Rajhi Bank")
('RKH', '=ARB')
```

`normalize` gives one canonical, language-neutral key per name: concepts in
lower case, a consonant skeleton of the core in upper case; legal form, word
order and noise are dropped. `keys` gives several blocking keys (skeletons,
concepts of qualifiers, and `=` followed by the initials). Store them in an
indexed column to fetch candidates with plain SQL, then score the candidates
with `compare`. Both are lossy: they find candidates, they do not decide.

### Command line

```console
$ tradename compare "شركة الخليج للتجارة والمقاولات ذ.م.م" "Gulf Trading & Contracting Co. LLC"
score 1.00  (strong)
  descriptor  الخليج  ~  Gulf   1.00
  descriptor  للتجارة  ~  Trading   1.00
  descriptor  والمقاولات  ~  Contracting   1.00
  legal form  ذمم [limited_liability]  ~  LLC [limited_liability]   same

$ tradename parse "Gulf Trading & Contracting Co. LLC - Dubai Branch"
core         -
qualifiers   Gulf
descriptors  Trading, Contracting
concepts     gulf, trading, contracting
legal form   LLC = LLC [limited_liability] (AE, SA, KW, QA, BH, OM, JO, EG, US)
branch       Dubai

$ tradename key "مصرف الراجحي"
RKH bank
RKH LRKH

$ tradename search tests/companies.csv "Siemens" --column name
1.00  Siemens AG
1.00  SIEMENS AKTIENGESELLSCHAFT
0.82  Siemens Energy AG

$ tradename dedupe tests/companies.csv --column name
# group 1
  Gulf Trading & Contracting Co. LLC
  شركة الخليج للتجارة والمقاولات ذ.م.م
# group 2
  Siemens AG
  SIEMENS AKTIENGESELLSCHAFT
# group 3
  Samsung Electronics Co., Ltd.
  Samsung Electronics Company Limited
# group 4
  ООО Ромашка
  Romashka LLC
4 group(s) of likely duplicates among 11 names
```

Every command takes `--json`. `compare` takes `--threshold` and
`--strict-legal-form`. `search` and `dedupe` read a text file with one name
per line, or a CSV / TSV file with `--column` (a header name, or a 0-based
number for a file without a header row). Exit codes: `0` match or results
found, `1` no match or nothing found, `2` usage or input error.
`python -m tradename` works the same way.

## Limitations

Be aware of these before relying on a score:

- **A name is not a legal entity** (see above). The library never looks
  anything up; it only compares strings.
- **Translation is built in for Arabic and English only.** Business words in
  other languages are matched when they happen to be in the vocabulary
  (Banco, Banque, Grupo) or sound alike (Telekom / Telecom); otherwise they
  are treated as distinctive words. "Banco do Brasil" against "Bank of
  Brazil" scores 0.92 only because Brasil and Brazil sound alike.
- **Scripts other than Latin, Arabic and Cyrillic are compared exactly.**
  `株式会社東芝` does not match "Toshiba Corporation". Cyrillic is
  romanised letter by letter with Russian values.
- **Synonyms in the vocabulary cannot be told apart.** Petroleum and oil are
  one concept, so "Kuwait Petroleum Corporation" and "Kuwait Oil Company",
  two different companies, score 1.00. The same holds for bank / banking,
  shipping / marine / navigation and similar groups.
- **Near-identical distinctive words** can be merged: "Almarai" and
  "Al Marri" score 0.96.
- **A bare name against the same name with a line of business** is held just
  below the threshold: "Emaar" against "Emaar Properties" scores 0.82, like
  "Siemens" against "Siemens Energy". The library cannot know which of the
  two is a subsidiary. Lower the threshold to 0.8 if your data prefers
  recall here.
- **A name of generic words must agree on every word**, even when one of
  them is a transliteration that works as a brand: "Nakheel" against
  "Nakheel Properties" scores 0.80.
- **Word order is ignored**, so "Imran Al Ramadan Logistics" and "Ramadan Al
  Imran Logistics" score 1.00.
- **Typing errors are not modelled.** The phonetic comparison tolerates
  doubled letters and vowel variation ("Widgetts"), not swapped or wrong
  consonants: "Mircosoft Corporation" does not match "Microsoft Corporation".
- **Rebrands and nicknames are unknown** unless the name itself says
  "formerly": Facebook / Meta, Federal Express / FedEx, PwC. Initials need at
  least three letters, so "GE" does not match "General Electric", and only
  26 acronyms (Gulf companies) are built in.
- **Legal forms were compiled from general knowledge**, not from each
  jurisdiction's statutes. Categories are coarse, and some abbreviations mean
  different things in different countries (`ش.م.م` is a joint-stock company
  in Egypt and a limited liability company in Lebanon and Oman).
- **Blocking can miss.** `CompanyIndex.search` and `dedupe` only score
  candidates that share a key. On the development set the keys reach every
  pair that `compare` matches, but the keys were tuned on that set; an
  unusual spelling can slip through. Use `exhaustive=True` when a list is
  small and a miss is expensive.
- Only the first 24 words of a name are compared.

## Contributing

The easiest high-impact contributions are a line in
[`src/tradename/legal.py`](src/tradename/legal.py) (a legal form of your
jurisdiction) or in [`src/tradename/vocab.py`](src/tradename/vocab.py) (a
business word, an abbreviation, a known acronym). See
[CONTRIBUTING.md](CONTRIBUTING.md).

```bash
python -m unittest discover -s tests     # tests
python bench/run.py --errors             # benchmark and every wrong pair
```

## License

MIT
