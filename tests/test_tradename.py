import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "bench"))

import tradename  # noqa: E402
from tradename.cli import main as cli  # noqa: E402
from tradename.legal import CATEGORIES, FORMS, compatible  # noqa: E402

CSV = os.path.join(HERE, "companies.csv")      # read-only fixtures; the tests write nothing to disk
TXT = os.path.join(HERE, "companies.txt")


class Base(unittest.TestCase):
    def assertSame(self, a, b):
        m = tradename.compare(a, b)
        self.assertTrue(m.is_match, f"{a!r} vs {b!r} scored {m.score:.2f}\n{m.explain()}")

    def assertDifferent(self, a, b):
        m = tradename.compare(a, b)
        self.assertFalse(m.is_match, f"{a!r} vs {b!r} scored {m.score:.2f}\n{m.explain()}")


class LegalForms(Base):
    def test_english_speaking_forms(self):
        self.assertSame("Acme Widgets Ltd", "Acme Widgets Limited")
        self.assertSame("Acme Widgets Inc.", "Acme Widgets Incorporated")
        self.assertSame("Acme Widgets LLC", "ACME WIDGETS L.L.C.")
        self.assertSame("Royal Dutch Shell plc", "Royal Dutch Shell Public Limited Company")
        self.assertSame("Outback Mining Services Pty Ltd", "Outback Mining Services Proprietary Limited")
        self.assertSame("Sunrise Software Solutions Private Limited", "Sunrise Software Solutions Pvt. Ltd.")
        self.assertSame("Smith Brothers Holdings LLP", "Smith Brothers Holdings L.L.P.")

    def test_continental_forms(self):
        self.assertSame("Siemens AG", "Siemens Aktiengesellschaft")
        self.assertSame("Robert Bosch GmbH", "Robert Bosch Gesellschaft mit beschränkter Haftung")
        self.assertSame("Nestlé S.A.", "Nestle SA")
        self.assertSame("Dupont Logistique SARL", "Dupont Logistique S.à r.l.")
        self.assertSame("Enel S.p.A.", "Enel Società per Azioni")
        self.assertSame("Koninklijke Philips N.V.", "Koninklijke Philips NV")
        self.assertSame("Novo Nordisk A/S", "Novo Nordisk AS")
        self.assertSame("Kowalski Transport Sp. z o.o.", "Kowalski Transport Spółka z ograniczoną odpowiedzialnością")
        self.assertSame("Müller Maschinenbau GmbH & Co. KG", "Mueller Maschinenbau GmbH und Co KG")

    def test_rest_of_the_world(self):
        self.assertSame("Toyota Motor Corporation", "Toyota Motor Kabushiki Kaisha")
        self.assertSame("Grupo Bimbo, S.A.B. de C.V.", "Grupo Bimbo SAB de CV")
        self.assertSame("Bintang Plantation Sdn Bhd", "Bintang Plantation Sendirian Berhad")
        self.assertSame("Temasek Holdings (Private) Limited", "Temasek Holdings Pte Ltd")
        self.assertSame("Koç Holding A.Ş.", "Koc Holding AS")
        self.assertSame("AB Volvo", "Volvo AB")
        self.assertSame("AB Volvo (publ)", "Aktiebolaget Volvo")

    def test_arabic_forms(self):
        self.assertSame("إعمار العقارية ش.م.ع", "Emaar Properties PJSC")
        self.assertSame("شركة الخليج للتجارة ذ.م.م", "Gulf Trading LLC")
        self.assertSame("شركة الخليج للتجارة ذ م م", "شركة الخليج للتجارة ذات مسؤولية محدودة")
        self.assertSame("بيت التمويل الكويتي ش.م.ك.ع", "Kuwait Finance House K.S.C.P.")
        self.assertSame("بنك مسقط ش.م.ع.ع", "Bank Muscat SAOG")

    def test_missing_legal_form_still_matches(self):
        self.assertSame("Siemens", "Siemens AG")
        self.assertSame("Banco Santander, S.A.", "Banco Santander")
        self.assertSame("المراعي", "شركة المراعي")

    def test_parse_reports_the_legal_form(self):
        lf = tradename.parse("Robert Bosch G.m.b.H.").legal_form
        self.assertEqual((lf.abbr, lf.category), ("GmbH", "limited_liability"))
        self.assertIn("DE", lf.countries)
        self.assertEqual(tradename.parse("شركة الصقر للتأمين ش.م.ع").legal_form.category, "public_joint_stock")
        self.assertEqual(tradename.parse("ООО Ромашка").legal_form.abbr, "OOO")
        self.assertIsNone(tradename.parse("Siemens").legal_form)

    def test_ambiguous_abbreviation_inside_a_name_is_not_a_legal_form(self):
        # "SA" and "AS" are words too; they only count at the end or when dotted
        c = tradename.parse("Villa AS Roma Ltd")
        self.assertEqual(c.legal_form.abbr, "Ltd")
        self.assertEqual(c.core, ("Villa", "AS", "Roma"))
        self.assertEqual(tradename.parse("Villa Roma S.A.").legal_form.abbr, "SA")
        self.assertEqual(tradename.parse("Villa Roma SA").legal_form.abbr, "SA")
        self.assertEqual(tradename.parse("AB Volvo").legal_form.abbr, "AB")     # leading, in capitals

    def test_different_legal_forms(self):
        m = tradename.compare("Emaar Properties PJSC", "Emaar Properties LLC")
        self.assertEqual(m.legal, "different")
        self.assertTrue(m.is_match)                 # by default only reported
        self.assertIn("different legal forms", m.notes)
        self.assertLess(m.score, tradename.score("Emaar Properties PJSC", "Emaar Properties PJSC"))
        strict = tradename.compare("Emaar Properties PJSC", "Emaar Properties LLC", strict_legal_form=True)
        self.assertFalse(strict.is_match)
        self.assertFalse(tradename.is_match("Emaar Properties PJSC", "Emaar Properties LLC", strict_legal_form=True))

    def test_compatible_legal_forms(self):
        self.assertEqual(tradename.compare("Acme Widgets Ltd", "Acme Widgets LLC").legal, "same")
        self.assertEqual(tradename.compare("Unilever N.V.", "Unilever PLC").legal, "compatible")
        self.assertEqual(tradename.compare("Acme Widgets Co.", "Acme Widgets Ltd").legal, "unknown")
        self.assertEqual(compatible(None, None), "unknown")

    def test_legal_table_is_well_formed(self):
        self.assertGreater(len(FORMS), 300)
        for category, abbr, countries, spelling, _end_only in FORMS:
            self.assertIn(category, CATEGORIES)
            self.assertTrue(abbr and spelling)
            for cc in countries:
                self.assertEqual(len(cc), 2, spelling)


class Abbreviations(Base):
    def test_abbreviated_words(self):
        self.assertSame("Acme Manufacturing International Ltd", "ACME Mfg. Intl. Limited")
        self.assertSame("Tata Consultancy Services Limited", "Tata Consultancy Svcs Ltd.")
        self.assertSame("Smith Brothers Holdings", "Smith Bros. Hldgs")
        self.assertSame("Al Noor General Trading Est.", "Al-Noor Gen. Trdg. Est")
        self.assertSame("Samsung Electronics Co., Ltd.", "Samsung Electronics Company Limited")

    def test_known_acronyms(self):
        self.assertSame("SABIC", "Saudi Basic Industries Corporation")
        self.assertSame("سابك", "الشركة السعودية للصناعات الأساسية")
        self.assertSame("ADNOC", "شركة بترول أبوظبي الوطنية")
        self.assertSame("QNB", "Qatar National Bank (Q.P.S.C.)")
        self.assertEqual(tradename.compare("SABIC", "Saudi Basic Industries Corporation").via, "acronym")

    def test_acronym_in_brackets(self):
        c = tradename.parse("Saudi Basic Industries Corp. (SABIC)")
        self.assertIn("acronym", [label for label, _ in c.aliases])
        self.assertSame("Saudi Basic Industries Corp. (SABIC)", "SABIC")
        self.assertSame("Bahrain Petroleum Co. (BAPCO)", "بابكو")

    def test_initialism_is_weak_evidence(self):
        m = tradename.compare("IBM", "International Business Machines Corporation")
        self.assertTrue(m.is_match)
        self.assertEqual(m.via, "initialism")
        self.assertEqual(m.level, "probable")
        self.assertDifferent("IBX", "International Business Machines Corporation")
        self.assertDifferent("GE", "General Electric")        # two letters are too little to go on

    def test_an_acronym_spelled_as_a_word_is_a_word(self):
        # KOC is Kuwait Oil Company, but Koç Holding is not "Kuwait Oil Holding"
        self.assertDifferent("Koc Holding", "Kuwait Oil Holding")
        self.assertSame("KOC", "Kuwait Oil Company")


class PunctuationAndOrder(Base):
    def test_ampersand_and_and(self):
        self.assertSame("Johnson & Johnson", "Johnson and Johnson")
        self.assertSame("Procter & Gamble Co.", "Procter and Gamble Company")
        self.assertSame("Marks & Spencer plc", "MARKS AND SPENCER P.L.C.")
        self.assertSame("شركة الخليج للتجارة والمقاولات", "Gulf Trading & Contracting Co.")

    def test_punctuation_case_and_accents(self):
        self.assertSame("Samsung Electronics Co., Ltd.", "SAMSUNG ELECTRONICS CO.,LTD")
        self.assertSame("L'Oréal S.A.", "LOreal SA")
        self.assertSame("Škoda Auto a.s.", "Skoda Auto AS")
        self.assertSame("Hewlett-Packard", "Hewlett Packard")
        self.assertSame("  Siemens   AG ", "Siemens AG")
        self.assertSame("إعمار العقارية", "اعمار العقاريه")
        self.assertSame("مُؤَسَّسَة النُّور للتجارة", "مؤسسة النور للتجارة")

    def test_word_order(self):
        self.assertSame("Bank Muscat", "Muscat Bank")
        self.assertSame("Riyadh Plastic Factory", "Riyadh Factory for Plastic")
        self.assertSame("Grupo Bimbo", "Bimbo Group")
        self.assertSame("الاتحاد للطيران", "طيران الاتحاد")
        self.assertSame("The Savola Group", "Savola Group")

    def test_article_and_joined_words(self):
        for latin in ("Al Rajhi Bank", "Al-Rajhi Bank", "Alrajhi Bank", "AL RAJHI BANK"):
            self.assertSame("مصرف الراجحي", latin)
        self.assertSame("Almarai", "Al Marai")
        self.assertSame("Saudi Binladin Group", "Saudi Bin Laden Group")
        self.assertSame("Abdul Latif Jameel", "عبداللطيف جميل")
        self.assertSame("Abdullatif Jameel", "عبد اللطيف جميل")

    def test_branch_former_name_and_trade_name(self):
        c = tradename.parse("Ali Hassan Al Dosari Contracting Est. - Dammam Branch")
        self.assertEqual(c.branch, "Dammam")
        self.assertSame("Ali Hassan Al Dosari Contracting Est. - Dammam Branch",
                        "مؤسسة علي حسن الدوسري للمقاولات")
        m = tradename.compare("Acme Widgets Ltd (formerly Apex Gadgets Ltd)", "Apex Gadgets Limited")
        self.assertTrue(m.is_match)
        self.assertEqual(m.via, "former name")
        self.assertEqual(tradename.compare("Zenith Marble Works Ltd t/a Marble Palace", "Marble Palace").via, "alias")

    def test_bracketed_place_is_optional(self):
        self.assertSame("Commercial International Bank (Egypt) S.A.E.", "Commercial International Bank")
        self.assertDifferent("Commercial International Bank (Egypt)", "Commercial International Bank (Kuwait)")


class CrossScript(Base):
    def test_arabic_translated_and_transliterated(self):
        self.assertSame("شركة الخليج للتجارة والمقاولات ذ.م.م", "Gulf Trading & Contracting Co. LLC")
        self.assertSame("شركة الخليج للتجارة والمقاولات ذ.م.م", "Al Khaleej Trading and Contracting W.L.L.")
        self.assertSame("مكتبة جرير", "Jarir Bookstore")
        self.assertSame("حديد عز", "Ezz Steel Company S.A.E.")
        self.assertSame("جولدن ستار للتجارة العامة ذ.م.م", "النجمة الذهبية للتجارة العامة")
        self.assertSame("الشركة المتحدة للإلكترونيات", "United Electronics Company")
        self.assertSame("ألمنيوم البحرين", "Aluminium Bahrain")
        self.assertSame("مركز الحياة الطبي", "Al Hayah Medical Center LLC")

    def test_arabic_person_names_inside_company_names(self):
        self.assertSame("شركة محمد عبدالله الشايع وأولاده ذ.م.م", "Mohamed Abdulla Alshaya and Sons Company W.L.L.")
        self.assertSame("مجموعة طلعت مصطفى", "Talat Mustafa Group Holding")
        self.assertSame("صيدلية الشفاء", "Al Shefa Pharmacy")

    def test_cyrillic(self):
        self.assertSame("ООО Ромашка", "Romashka LLC")
        self.assertSame("ПАО Газпром", "Gazprom PJSC")
        self.assertSame("ПАО Газпром", "Public Joint Stock Company Gazprom")
        self.assertDifferent("ПАО Газпром", "PAO Gazprom Neft")

    def test_other_scripts_are_compared_exactly(self):
        self.assertSame("株式会社東芝", "株式会社東芝")
        self.assertDifferent("株式会社東芝", "Toshiba Corporation")

    def test_symmetry(self):
        pairs = [("مصرف الراجحي", "Al Rajhi Bank"), ("Siemens AG", "Siemens Energy AG"),
                 ("IBM", "International Business Machines Corp."), ("Acme Ltd", "Apex Ltd")]
        for a, b in pairs:
            ab, ba = tradename.compare(a, b), tradename.compare(b, a)
            self.assertAlmostEqual(ab.score, ba.score, places=9)
            self.assertEqual(ab.only_a, ba.only_b)
            self.assertEqual(ab.legal_a, ba.legal_b)


class MustNotMatch(Base):
    def test_generic_words_with_a_different_place(self):
        self.assertDifferent("National Bank of Kuwait", "National Bank of Bahrain")
        self.assertDifferent("National Bank of Egypt", "National Bank of Kuwait")
        self.assertDifferent("بنك الكويت الوطني", "بنك البحرين الوطني")
        self.assertDifferent("Dubai Islamic Bank", "Abu Dhabi Islamic Bank")
        self.assertDifferent("Riyadh Plastic Factory", "Jeddah Plastic Factory")

    def test_same_business_different_name(self):
        self.assertDifferent("Gulf Trading LLC", "Emirates Trading LLC")
        self.assertDifferent("Alpha Trading", "Beta Trading")
        self.assertDifferent("الخليج للتجارة", "الإمارات للتجارة")
        self.assertDifferent("Kowalski Transport Sp. z o.o.", "Nowak Transport Sp. z o.o.")
        self.assertDifferent("Acme Manufacturing Ltd", "Apex Manufacturing Ltd")
        self.assertDifferent("Banco Santander SA", "Banco Sabadell SA")

    def test_same_name_different_business(self):
        self.assertDifferent("Al Rajhi Bank", "Al Rajhi Cement")
        self.assertDifferent("مصرف الراجحي", "أسمنت الراجحي")
        self.assertDifferent("مصرف الراجحي", "Al Rajhi Cement")
        self.assertDifferent("Tata Steel Limited", "Tata Power Limited")
        self.assertDifferent("Orascom Construction", "Orascom Telecom")
        self.assertDifferent("National Trading Company", "National Contracting Company")

    def test_generic_names_must_agree_on_every_word(self):
        self.assertDifferent("Arab Bank", "Arab National Bank")
        self.assertDifferent("Gulf Bank", "Gulf International Bank")
        self.assertDifferent("Gulf Trading & Contracting Co. LLC", "Gulf Trading Co. LLC")
        self.assertDifferent("National Food Industries Company", "National Industries Company")
        self.assertDifferent("First National Bank", "First Commercial Bank")

    def test_added_line_of_business_is_a_possible_subsidiary(self):
        for a, b in (("Siemens AG", "Siemens Energy AG"), ("Nestlé S.A.", "Nestlé Waters"),
                     ("Volkswagen AG", "Volkswagen Financial Services AG")):
            m = tradename.compare(a, b)
            self.assertFalse(m.is_match, m.explain())
            self.assertEqual(m.level, "possible")
        # ... while a word about the organisation changes little
        self.assertSame("Zain", "Zain Group")
        self.assertSame("Ingka Holding B.V.", "Ingka B.V.")

    def test_extra_or_different_distinctive_word(self):
        self.assertDifferent("Majid Al Futtaim", "Al-Futtaim Group")
        self.assertDifferent("Johnson & Johnson", "Johnson Controls")
        self.assertDifferent("Abdul Latif Jameel", "Abdul Aziz Jameel")
        self.assertDifferent("Mohammed Al Shaya & Sons", "Ahmed Al Shaya & Sons")
        self.assertDifferent("Goldman Sachs Group", "Goldman Group")
        self.assertDifferent("Smith Brothers Holdings", "Smith Sisters Holdings")

    def test_similar_spellings_that_are_other_words(self):
        self.assertDifferent("Aramex", "Aramco")
        self.assertDifferent("Enel S.p.A.", "Eni S.p.A.")
        self.assertDifferent("Rossi Costruzioni S.r.l.", "Russo Costruzioni S.r.l.")
        self.assertDifferent("Müller Maschinenbau GmbH", "Möller Maschinenbau GmbH")
        self.assertDifferent("إعمار العقارية", "عمار العقارية")
        self.assertDifferent("Al Shifa Pharmacy", "Al Safa Pharmacy")
        self.assertDifferent("Golden Star General Trading LLC", "Silver Star General Trading LLC")

    def test_numbers_are_exact(self):
        self.assertSame("3M Company", "3M Co.")
        self.assertSame("Studio 54 Ltd", "Studio 54 Limited")
        self.assertDifferent("Studio 54 Ltd", "Studio 45 Ltd")
        self.assertDifferent("Channel 4 Ltd", "Channel 5 Ltd")
        self.assertSame("Vision 2030 Est.", "Vision ٢٠٣٠ Est.")


class NormalizeAndKeys(Base):
    def test_normalize_is_language_neutral(self):
        self.assertEqual(tradename.normalize("مصرف الراجحي"), "RKH bank")
        self.assertEqual(tradename.normalize("Al Rajhi Bank"), "RKH bank")
        self.assertEqual(tradename.normalize("AL-RAJHI BANK LLC"), "RKH bank")

    def test_normalize_drops_legal_form_order_and_noise(self):
        self.assertEqual(tradename.normalize("Gulf Trading & Contracting Co. LLC"),
                         tradename.normalize("The Gulf Contracting and Trading Company W.L.L."))
        self.assertEqual(tradename.normalize("Siemens AG"), tradename.normalize("SIEMENS Aktiengesellschaft"))
        self.assertNotEqual(tradename.normalize("Al Rajhi Bank"), tradename.normalize("Al Rajhi Cement"))
        self.assertEqual(tradename.normalize(""), "")

    def test_keys_are_shared_by_matching_names(self):
        self.assertIn("RKH", set(tradename.keys("مصرف الراجحي")) & set(tradename.keys("Al Rajhi Bank")))
        self.assertTrue(set(tradename.keys("ООО Ромашка")) & set(tradename.keys("Romashka LLC")))
        self.assertTrue(set(tradename.keys("IBM")) & set(tradename.keys("International Business Machines Corp.")))
        self.assertTrue(set(tradename.keys("National Bank of Kuwait")) & set(tradename.keys("بنك الكويت الوطني")))
        self.assertEqual(tradename.keys(""), ())

    def test_keys_cover_the_development_set(self):
        import dataset
        missed = total = 0
        for group in dataset.GROUPS:
            for a in group:
                for b in group:
                    if a < b and tradename.is_match(a, b):
                        total += 1
                        missed += not (set(tradename.keys(a)) & set(tradename.keys(b)))
        self.assertGreater(total, 600)
        self.assertLessEqual(missed / total, 0.02)


class Explain(Base):
    def test_explain(self):
        text = tradename.compare("شركة الصقر للتأمين ش.م.ع", "Al Saqr Insurance Company").explain()
        self.assertTrue(text.startswith("score "))
        self.assertIn("core", text)
        self.assertIn("descriptor", text)
        self.assertIn("legal form", text)
        text = tradename.compare("Al Rajhi Bank", "Al Rajhi Cement").explain()
        self.assertIn("only in first:  Bank", text)
        self.assertIn("only in second: Cement", text)

    def test_to_dict_is_json_ready(self):
        m = tradename.compare("Emaar Properties PJSC", "إعمار العقارية")
        d = json.loads(json.dumps(m.to_dict(), ensure_ascii=False))
        self.assertEqual(set(d), {"score", "is_match", "level", "core_pairs", "descriptor_pairs", "only_a", "only_b",
                                  "legal_form_a", "legal_form_b", "legal_forms", "branch_a", "branch_b", "via", "notes"})
        self.assertTrue(d["is_match"])
        self.assertEqual(d["legal_form_a"]["abbr"], "PJSC")
        self.assertIsNone(d["legal_form_b"])
        self.assertEqual(d["core_pairs"][0]["a"], "Emaar")
        json.dumps(tradename.parse("Gulf Trading LLC - Dubai Branch (formerly Gulf Stores)").to_dict())

    def test_levels_threshold_and_bool(self):
        strong = tradename.compare("Siemens AG", "Siemens AG")
        self.assertEqual((strong.score, strong.level, bool(strong)), (1.0, "strong", True))
        weak = tradename.compare("Siemens AG", "Toyota Motor Corporation")
        self.assertEqual((weak.level, bool(weak)), ("no", False))
        m = tradename.compare("Siemens AG", "Siemens Energy AG", threshold=0.8)
        self.assertTrue(m.is_match)
        self.assertEqual(m.threshold, 0.8)
        self.assertEqual(tradename.score("Siemens AG", "Siemens Energy AG"), m.score)
        self.assertEqual(tradename.DEFAULT_THRESHOLD, 0.85)

    def test_parse(self):
        c = tradename.parse("Gulf Trading & Contracting Co. LLC - Dubai Branch")
        self.assertEqual((c.qualifiers, c.descriptors, c.legal_form.abbr, c.branch),
                         (("Gulf",), ("Trading", "Contracting"), "LLC", "Dubai"))
        self.assertEqual(c.concepts, ("gulf", "trading", "contracting"))
        self.assertEqual(tradename.parse("Zenith Marble Works Ltd").core, ("Zenith",))


class Lists(Base):
    NAMES = ["مصرف الراجحي", "Gulf Trading LLC", "Emaar Properties PJSC", "Siemens AG", "Siemens Energy AG",
             "Al Rajhi Cement", "ООО Ромашка"]

    def test_search(self):
        idx = tradename.CompanyIndex(self.NAMES)
        self.assertEqual(len(idx), 7)
        self.assertEqual([n for n, _ in idx.search("Al Rajhi Bank", min_score=0.85)], ["مصرف الراجحي"])
        self.assertEqual(idx.search("إعمار العقارية")[0][0], "Emaar Properties PJSC")
        self.assertEqual(idx.search("Romashka LLC")[0], ("ООО Ромашка", 1.0))
        hits = idx.search("Siemens")
        self.assertEqual([n for n, _ in hits], ["Siemens AG", "Siemens Energy AG"])   # best first
        self.assertGreater(hits[0][1], hits[1][1])
        self.assertEqual(idx.search("Siemens", limit=1), hits[:1])
        self.assertEqual(idx.search("Zzyzx Qwerty Ltd"), [])
        self.assertEqual(idx.search(""), [])

    def test_search_ids_add_and_exhaustive(self):
        idx = tradename.CompanyIndex()
        idx.add("Banco Santander, S.A.", id="V-001")
        idx.add("Acme Widgets Ltd", id="V-002")
        idx.add("شركة الصقر للتأمين ش.م.ع")
        self.assertEqual(idx.search_ids("Banco Santander")[0][0], "V-001")
        self.assertEqual(idx.search_ids("Al Saqr Insurance Co. PSC")[0][0], 2)       # default id: position
        self.assertEqual(idx.search("ACME WIDGETS LIMITED", exhaustive=True), idx.search("ACME WIDGETS LIMITED"))

    def test_search_agrees_with_exhaustive_search(self):
        import dataset
        names = [n for g in dataset.GROUPS for n in g]
        idx = tradename.CompanyIndex(names)
        found = wanted = 0
        for q in names[::7]:
            full = {n for n, _ in idx.search(q, limit=0, min_score=0.85, exhaustive=True)}
            fast = {n for n, _ in idx.search(q, limit=0, min_score=0.85)}
            self.assertLessEqual(fast, full)
            wanted += len(full)
            found += len(fast)
        self.assertGreaterEqual(found / wanted, 0.98)

    def test_dedupe(self):
        names = ["Gulf Trading & Contracting Co. LLC", "Siemens AG", "شركة الخليج للتجارة والمقاولات ذ.م.م",
                 "Zenith Marble Works Ltd", "SIEMENS AKTIENGESELLSCHAFT", "Siemens Energy AG", "Emirates Trading LLC"]
        self.assertEqual(tradename.dedupe(names), [[0, 2], [1, 4]])
        self.assertEqual(tradename.dedupe(names, threshold=0.8), [[0, 2], [1, 4, 5]])
        self.assertEqual(tradename.dedupe([]), [])
        self.assertEqual(tradename.dedupe(["Acme Ltd", "", "Acme Ltd", None]), [[0, 2]])

    def test_dedupe_recovers_the_development_groups(self):
        import dataset
        names = [n for g in dataset.GROUPS for n in g]
        group_of = {n: k for k, g in enumerate(dataset.GROUPS) for n in g}
        clusters = tradename.dedupe(names)
        mixed = [c for c in clusters if len({group_of[names[i]] for i in c}) > 1]
        self.assertEqual(mixed, [])
        self.assertGreaterEqual(len(clusters), len(dataset.GROUPS) - 2)


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = cli(list(args))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_compare(self):
        code, out, _ = self.run_cli("compare", "مصرف الراجحي", "Al Rajhi Bank")
        self.assertEqual(code, 0)
        self.assertIn("score", out)
        code, out, _ = self.run_cli("compare", "Al Rajhi Bank", "Al Rajhi Cement")
        self.assertEqual(code, 1)
        code, out, _ = self.run_cli("compare", "Al Rajhi Bank", "Al Rajhi Cement", "-t", "0.5")
        self.assertEqual(code, 0)

    def test_compare_json_and_strict(self):
        code, out, _ = self.run_cli("compare", "Nestlé S.A.", "Nestle SA", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["is_match"])
        self.assertEqual(data["legal_forms"], "same")
        code, out, _ = self.run_cli("compare", "Emaar Properties PJSC", "Emaar Properties LLC", "--strict-legal-form")
        self.assertEqual(code, 1)
        self.assertIn("different legal forms", out)

    def test_parse(self):
        code, out, _ = self.run_cli("parse", "Gulf Trading & Contracting Co. LLC - Dubai Branch")
        self.assertEqual(code, 0)
        self.assertIn("qualifiers   Gulf", out)
        self.assertIn("branch       Dubai", out)
        code, out, _ = self.run_cli("parse", "شركة الصقر للتأمين ش.م.ع", "--json")
        data = json.loads(out)
        self.assertEqual(data["legal_form"]["abbr"], "PJSC")
        self.assertEqual(data["concepts"], ["insurance"])

    def test_key(self):
        code, out, _ = self.run_cli("key", "مصرف الراجحي")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], "RKH bank")
        code, out, _ = self.run_cli("key", "Al Rajhi Bank", "--json")
        data = json.loads(out)
        self.assertEqual(data["key"], "RKH bank")
        self.assertIn("RKH", data["blocking_keys"])

    def test_search(self):
        code, out, _ = self.run_cli("search", CSV, "Gulf Trading and Contracting", "--column", "name")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 2)        # the English and the Arabic record
        self.assertIn("شركة الخليج للتجارة والمقاولات ذ.م.م", out)
        code, out, _ = self.run_cli("search", CSV, "Siemens", "-c", "name", "-n", "1", "--json")
        self.assertEqual([h["name"] for h in json.loads(out)], ["Siemens AG"])
        code, out, _ = self.run_cli("search", CSV, "Zzyzx Qwerty", "-c", "name")
        self.assertEqual((code, out), (1, ""))
        code, out, _ = self.run_cli("search", TXT, "Santander Bank", "-m", "0.9")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 2)

    def test_dedupe(self):
        code, out, err = self.run_cli("dedupe", CSV, "--column", "name")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("# group"), 4)
        self.assertIn("4 group(s)", err)
        self.assertNotIn("Siemens Energy AG", out)
        self.assertNotIn("Emirates Trading LLC", out)
        code, out, _ = self.run_cli("dedupe", CSV, "-c", "name", "--json")
        groups = json.loads(out)
        self.assertIn(["ООО Ромашка", "Romashka LLC"], groups)
        self.assertIn(["Siemens AG", "SIEMENS AKTIENGESELLSCHAFT"], groups)
        code, out, _ = self.run_cli("dedupe", TXT, "--json")
        self.assertEqual(json.loads(out), [["Banco Santander, S.A.", "Banco Santander SA"]])

    def test_errors(self):
        code, out, err = self.run_cli("dedupe", os.path.join(HERE, "no-such-file.csv"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)
        code, out, err = self.run_cli("search", CSV, "Siemens", "--column", "nosuch")
        self.assertEqual(code, 2)
        self.assertIn("not found", err)
        code, out, err = self.run_cli("search", CSV, "Siemens", "--column", "9")
        self.assertEqual(code, 2)
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        code, out, err = self.run_cli("--version")
        self.assertEqual((code, out.strip()), (0, f"tradename {tradename.__version__}"))


class EdgeCases(Base):
    def test_empty_and_none(self):
        for a, b in (("", ""), ("", "Siemens AG"), ("   ", "Siemens AG"), (None, "Siemens AG"), (None, None),
                     ("...", "---"), ("&", "Siemens")):
            m = tradename.compare(a, b)
            self.assertEqual(m.score, 0.0)
            self.assertFalse(m.is_match)
            self.assertIsInstance(m.explain(), str)
        self.assertEqual(tradename.parse("").tokens, ())
        self.assertEqual(tradename.normalize(None), "")
        self.assertEqual(tradename.keys(None), ())

    def test_only_a_legal_form(self):
        c = tradename.parse("LLC")
        self.assertEqual(c.legal_form.abbr, "LLC")
        self.assertEqual(c.core, ())
        self.assertDifferent("LLC", "Siemens LLC")
        self.assertDifferent("شركة", "Siemens AG")
        self.assertDifferent("Ltd", "Inc")
        self.assertIsInstance(tradename.compare("LLC", "L.L.C.").score, float)
        self.assertIsInstance(tradename.keys("GmbH"), tuple)

    def test_digits_only(self):
        self.assertSame("1234", "1234")
        self.assertDifferent("1234", "1235")
        self.assertDifferent("1234 Ltd", "Siemens Ltd")

    def test_very_long_input(self):
        long_a = " ".join(f"Alpha{chr(97 + i % 26)}{chr(97 + i // 26)}beta" for i in range(400)) + " Ltd"
        long_b = long_a.replace("Ltd", "Limited")
        m = tradename.compare(long_a, long_b)
        self.assertTrue(m.is_match)
        self.assertTrue(any("very long name" in n for n in m.notes))
        self.assertFalse(tradename.is_match(long_a, "Siemens AG"))
        self.assertIsInstance(tradename.keys(long_a), tuple)
        self.assertEqual(tradename.dedupe([long_a, long_b, "Siemens AG"]), [[0, 1]])
        self.assertEqual(tradename.compare("x" * 5000, "x" * 5000).score, 1.0)
        self.assertEqual(tradename.compare("ش" * 3000, "y" * 3000).is_match, False)

    def test_odd_characters(self):
        for name in ("Acme\tWidgets\nLtd", "Acme Widgets Ltd ‏", "«Acme» Widgets, Ltd.", "Acme_Widgets Ltd",
                     "ACME WIDGETS LTD", "Acme Widgets (Ltd)", "Acme Widgets Ltd﻿"):
            self.assertSame(name, "Acme Widgets Ltd")
        for junk in ("()", "(((", "[]]", "\x00", "\\", "/", "💥", "A/S", "t/a", "formerly", "(formerly)"):
            self.assertIsInstance(tradename.compare(junk, "Acme Widgets Ltd").score, float)
            self.assertIsInstance(tradename.normalize(junk), str)
            self.assertIsInstance(tradename.parse(junk).to_dict(), dict)

    def test_deterministic_and_bounded(self):
        import dataset
        for a, b in dataset.DISTINCT[:40]:
            s = tradename.score(a, b)
            self.assertEqual(s, tradename.score(a, b))
            self.assertTrue(0.0 <= s <= 1.0)
        for g in dataset.GROUPS[:20]:
            self.assertEqual(tradename.score(g[0], g[0]), 1.0)


class Benchmark(unittest.TestCase):
    def test_development_set_does_not_regress(self):
        import dataset
        import run
        pos, neg = run.build_pairs(dataset.GROUPS, dataset.DISTINCT)
        ps = [tradename.score(a, b) for a, b in pos]
        ns = [tradename.score(a, b) for a, b in neg]
        p, r, _f = run.prf(ps, ns, tradename.DEFAULT_THRESHOLD)
        self.assertGreaterEqual(p, 0.99)
        self.assertGreaterEqual(r, 0.99)


if __name__ == "__main__":
    unittest.main()
