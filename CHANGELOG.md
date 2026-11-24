# Changelog

## 0.1.0

First release.

- `compare`, `score`, `is_match`: comparison of company names across legal
  forms, abbreviations, word order and scripts (Latin, Arabic, Cyrillic),
  with an explainable result (`Match.explain()`, `Match.to_dict()`).
- `parse`: the legal form, descriptors, qualifiers, distinctive core, branch
  and aliases of a name.
- `CompanyIndex` and `dedupe` for searching and de-duplicating lists.
- `normalize` and `keys`: language-neutral canonical and blocking keys.
- `tradename` command line tool: `compare`, `parse`, `key`, `search`,
  `dedupe`.
- 447 spellings of about 80 legal forms from some 60 jurisdictions, 264
  business concepts in English and Arabic, 26 known acronyms.
- Phonetic core and lexicon of Arabic personal names vendored from
  [ismatch](https://github.com/RealAoss/ismatch).
- Benchmark (`bench/run.py`) with a development set and three baselines, and
  a speed benchmark (`bench/speed.py`).
- Blind set (`bench/blind.py`) written without access to the matcher and run
  once: precision 0.981, recall 0.774. The misses are listed in the README.
