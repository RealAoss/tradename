"""Legal forms of companies, by jurisdiction, mapped to a few categories.

Format of ``_DATA``, one legal form per line::

    category | CANONICAL | countries | spelling ; spelling ; ...

* ``category`` is one of :data:`CATEGORIES`.
* ``CANONICAL`` is the abbreviation reported by :func:`tradename.parse`.
* ``countries`` are ISO 3166 alpha-2 codes where the form is used ("*" when
  it is generic or used in many places).
* Each spelling is written the way it appears in a name. Dots, case and
  spacing between single letters do not matter: ``L.L.C.``, ``LLC`` and
  ``L L C`` are one spelling, and so are ``ذ.م.م`` and ``ذ م م``.
* A spelling that starts with ``!`` is too ambiguous to be trusted in the
  middle of a name (``SA``, ``AS``, ``AG`` ...). It is only read as a legal
  form when it is written with dots or stands at the end of the name.

The same spelling may be listed under two categories when its meaning
depends on the country: ``ش.م.م`` is a joint-stock company in Egypt
(S.A.E.) and a limited liability company in Oman and Lebanon.

See CONTRIBUTING.md before adding a line.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["LegalForm", "CATEGORIES", "compatible", "FORMS"]

CATEGORIES = (
    "limited_liability",              # LLC, Ltd, GmbH, SARL, ذ.م.م
    "joint_stock",                    # SA, AG, JSC, S.p.A., مساهمة
    "public_joint_stock",             # PLC, PJSC, ش.م.ع
    "private_joint_stock",            # closed / private JSC, ش.م.خ
    "corporation",                    # Inc, Corp
    "general_partnership",
    "limited_partnership",
    "limited_liability_partnership",
    "single_owner",                   # one-person company, ش.ش.و
    "sole_proprietorship",            # Est., مؤسسة
    "free_zone",                      # FZE, FZCO, FZ-LLC, DMCC
    "cooperative",
    "company",                        # "Company", "Co.", شركة: says nothing
)

# Categories that are close enough not to count as a disagreement.
_FAMILIES = (
    {"joint_stock", "public_joint_stock", "private_joint_stock", "corporation"},
    {"limited_liability", "single_owner", "free_zone"},
    {"single_owner", "sole_proprietorship"},
    {"general_partnership", "limited_partnership", "limited_liability_partnership"},
)

_DATA = """
# ---------------------------------------------------------------- generic
company | Co | * | Co ; Company ; Companies ; Coy ; Cie ; Compagnie ; Compania ; Companhia ; Société ; Societe ; Ste ; Sociedad ; Societa ; شركة ; الشركة ; شركات
limited_liability | Ltd | * | Ltd ; Limited ; Ltee ; Limitee ; Limitada ; المحدودة ; محدودة ; المحدوده ; ليمتد
limited_liability | LLC | AE,SA,KW,QA,BH,OM,JO,EG,US | LLC ; L.L.C ; Limited Liability Company ; With Limited Liability ; ذ.م.م ; ذات مسؤولية محدودة ; ذات مسئولية محدودة ; ذات المسؤولية المحدودة ; ذات المسئولية المحدودة ; شركة ذات مسؤولية محدودة ; شركة ذات مسئولية محدودة ; محدودة المسؤولية ; محدودة المسئولية
joint_stock | JSC | * | JSC ; J.S.C ; Joint Stock Company ; Joint Stock ; Joint-Stock Company ; Shareholding Company ; مساهمة ; المساهمة ; شركة مساهمة ; ش.م ; شركة المساهمة
public_joint_stock | PJSC | AE,* | PJSC ; P.J.S.C ; Public Joint Stock Company ; Public Joint Stock ; Public Shareholding Company ; ش.م.ع ; مساهمة عامة ; شركة مساهمة عامة ; المساهمة العامة
private_joint_stock | PrJSC | AE,* | PrJSC ; Pr.J.S.C ; Private Joint Stock Company ; Private Joint Stock ; Private Shareholding Company ; ش.م.خ ; مساهمة خاصة ; شركة مساهمة خاصة ; المساهمة الخاصة
private_joint_stock | CJSC | SA,* | CJSC ; C.J.S.C ; Closed Joint Stock Company ; Closed Joint Stock ; مساهمة مقفلة ; شركة مساهمة مقفلة ; مساهمة مغلقة ; شركة مساهمة مغلقة ; المساهمة المقفلة
general_partnership | GP | * | General Partnership ; Partnership ; تضامن ; شركة تضامن ; تضامنية ; شركة تضامنية ; شركة التضامن
limited_partnership | LP | * | LP ; L.P ; Limited Partnership ; توصية بسيطة ; شركة توصية بسيطة ; التوصية البسيطة ; توصية بالأسهم ; شركة توصية بالأسهم
limited_liability_partnership | LLP | GB,US,IN,SG | LLP ; L.L.P ; Limited Liability Partnership
sole_proprietorship | Est | AE,SA,KW,QA,BH,OM,JO | Est ; Establishment ; Estab ; Estb ; Individual Establishment ; Sole Establishment ; Sole Proprietorship ; Sole Proprietor ; Sole Trader ; مؤسسة ; المؤسسة ; مؤسسة فردية ; المؤسسة الفردية ; منشأة فردية
corporation | Est | * | مؤسسة ; المؤسسة
cooperative | Coop | * | Cooperative ; Co-operative ; Cooperative Society ; Co-operative Society ; جمعية تعاونية ; الجمعية التعاونية ; تعاونية ; التعاونية
# ---------------------------------------------- Arab countries, by country
single_owner | SPC | BH,KW,OM,AE,QA | SPC ; S.P.C ; Single Person Company ; One Person Company ; Single Owner ; Single Owner LLC ; Sole Proprietorship LLC ; One Person Company LLC ; ش.ش.و ; شركة الشخص الواحد ; الشخص الواحد ; شركة شخص واحد ; ش.ش.و ذ.م.م ; ذ.م.م ش.ش.و
joint_stock | SAE | EG | SAE ; S.A.E ; Egyptian Joint Stock Company ; Egyptian Joint Stock ; ش.م.م ; شركة مساهمة مصرية ; مساهمة مصرية
limited_liability | LLC | OM,LB | ش.م.م
limited_liability | SARL | EG,MA,DZ,TN | ش.ذ.م.م
joint_stock | SJSC | SA | SJSC ; Saudi Joint Stock Company ; Saudi Joint Stock ; شركة مساهمة سعودية ; مساهمة سعودية
joint_stock | KSC | KW | KSC ; K.S.C ; SAK ; S.A.K ; Kuwaiti Shareholding Company ; Kuwait Shareholding Company ; ش.م.ك ; شركة مساهمة كويتية ; مساهمة كويتية
public_joint_stock | KSCP | KW | KSCP ; K.S.C.P ; SAKP ; S.A.K.P ; KSC Public ; KSC P ; ش.م.ك.ع ; شركة مساهمة كويتية عامة ; مساهمة كويتية عامة
private_joint_stock | KSCC | KW | KSCC ; K.S.C.C ; SAKC ; S.A.K.C ; KSC Closed ; KSC C ; ش.م.ك.م ; شركة مساهمة كويتية مقفلة ; مساهمة كويتية مقفلة ; ش.م.ك مقفلة
joint_stock | BSC | BH | BSC ; B.S.C ; Bahraini Shareholding Company ; ش.م.ب ; شركة مساهمة بحرينية ; مساهمة بحرينية
private_joint_stock | BSC(c) | BH | BSC C ; BSC Closed ; BSCC ; ش.م.ب.م ; ش.م.ب مقفلة ; شركة مساهمة بحرينية مقفلة ; مساهمة بحرينية مقفلة
limited_liability | WLL | BH,QA,KW | WLL ; W.L.L ; With Limited Liability
joint_stock | SAL | LB | !SAL ; S.A.L ; ش.م.ل ; شركة مساهمة لبنانية ; مساهمة لبنانية
joint_stock | QSC | QA | QSC ; Q.S.C ; Qatari Shareholding Company ; ش.م.ق ; شركة مساهمة قطرية ; مساهمة قطرية
public_joint_stock | QPSC | QA | QPSC ; Q.P.S.C ; Qatari Public Shareholding Company ; ش.م.ع.ق ; شركة مساهمة عامة قطرية ; مساهمة عامة قطرية ; شركة مساهمة قطرية عامة
private_joint_stock | QPJSC | QA | QPJSC ; Q.P.J.S.C ; QCSC ; Q.C.S.C ; Qatari Private Joint Stock Company ; ش.م.خ.ق ; ش.م.ق.خ ; شركة مساهمة خاصة قطرية ; شركة مساهمة قطرية خاصة
public_joint_stock | SAOG | OM | SAOG ; S.A.O.G ; ش.م.ع.ع ; شركة مساهمة عمانية عامة ; مساهمة عمانية عامة
private_joint_stock | SAOC | OM | SAOC ; S.A.O.C ; ش.م.ع.م ; شركة مساهمة عمانية مقفلة ; مساهمة عمانية مقفلة
public_joint_stock | PLC | JO | م.ع.م ; شركة مساهمة عامة محدودة ; مساهمة عامة محدودة ; المساهمة العامة المحدودة
private_joint_stock | PSC | JO,AE | PSC ; P.S.C ; م.خ.م ; شركة مساهمة خاصة محدودة ; مساهمة خاصة محدودة ; المساهمة الخاصة المحدودة
joint_stock | SPA | DZ | ش.ذ.أ ; شركة ذات أسهم ; ذات أسهم
free_zone | FZE | AE | FZE ; F.Z.E ; Free Zone Establishment ; م.م.ح ; مؤسسة منطقة حرة
free_zone | FZCO | AE | FZCO ; FZ CO ; FZC ; F.Z.C ; F.Z.CO ; Free Zone Company ; ش.م.ح ; شركة منطقة حرة
free_zone | FZ-LLC | AE | FZ LLC ; FZLLC ; FZ L.L.C ; Free Zone LLC ; Free Zone Limited Liability Company ; منطقة حرة ذ.م.م ; م.م.ح ذ.م.م ; ش.م.ح ذ.م.م ; منطقة حرة
free_zone | DMCC | AE | DMCC ; D.M.C.C ; م.د.م.س
free_zone | FZ | AE | FZ ; Free Zone ; JAFZA ; DAFZA
# ------------------------------------------------- English-speaking world
public_joint_stock | PLC | GB,IE,* | PLC ; P.L.C ; Public Limited Company ; Public Limited
corporation | Inc | US,CA,PH | Inc ; Incorporated ; Incorporation
corporation | Corp | US,CA,* | Corp ; Corporation ; Corpn
limited_liability | Pty Ltd | AU,ZA | Pty Ltd ; Pty Limited ; Proprietary Limited ; Pty ; (Pty) Ltd
limited_liability | Pvt Ltd | IN,PK,LK,BD,NP | Pvt Ltd ; Pvt Limited ; Private Limited ; Pvt ; P Ltd ; (Pvt) Ltd ; (Private) Limited
limited_liability | Pte Ltd | SG | Pte Ltd ; Pte Limited ; Private Limited ; Pte
limited_liability | Sdn Bhd | MY | Sdn Bhd ; Sendirian Berhad ; Sdn
public_joint_stock | Bhd | MY | Bhd ; Berhad
limited_liability | Co Ltd | CN,KR,TH,JP,TW,VN | Co Ltd ; Company Limited ; Co Limited
# --------------------------------------------------------------- Europe
limited_liability | GmbH | DE,AT,CH | GmbH ; G.m.b.H ; Gesellschaft mit beschränkter Haftung ; mbH
limited_liability | UG | DE | !UG ; UG haftungsbeschränkt ; Unternehmergesellschaft
joint_stock | AG | DE,AT,CH | !AG ; Aktiengesellschaft
limited_partnership | KG | DE,AT | !KG ; Kommanditgesellschaft
limited_partnership | GmbH & Co. KG | DE,AT | GmbH & Co KG ; GmbH und Co KG ; GmbH Co KG ; AG & Co KG ; GmbH & Co KGaA ; AG & Co KGaA ; KGaA
general_partnership | OHG | DE | OHG ; Offene Handelsgesellschaft
joint_stock | SA | FR,ES,BE,CH,LU,PT,PL,RO,GR,BR,AR,MA,TN | !SA ; S.A ; Société Anonyme ; Societe Anonyme ; Sociedad Anónima ; Sociedad Anonima ; Sociedade Anônima ; Sociedade Anonima
joint_stock | SAS | FR | !SAS ; S.A.S ; SASU ; Société par Actions Simplifiée ; Societe par Actions Simplifiee
limited_liability | SARL | FR,LU,CH,MA,DZ,TN,LB | SARL ; S.A.R.L ; S.à r.l ; Sàrl ; EURL ; SARL AU ; Société à Responsabilité Limitée ; Societe a Responsabilite Limitee
general_partnership | SNC | FR,IT | SNC ; S.N.C ; Société en Nom Collectif ; Societe en Nom Collectif
joint_stock | SpA | IT | S.p.A ; !SPA ; Società per Azioni ; Societa per Azioni
limited_liability | Srl | IT,RO | Srl ; S.r.l ; Società a Responsabilità Limitata ; Societa a Responsabilita Limitata
limited_liability | SL | ES | !SL ; S.L ; SLU ; S.L.U ; Sociedad Limitada ; S.R.L
limited_liability | BV | NL,BE | !BV ; B.V ; BVBA ; Besloten Vennootschap
joint_stock | NV | NL,BE | !NV ; N.V ; Naamloze Vennootschap
joint_stock | AB | SE,FI | !AB ; Aktiebolag ; Aktiebolaget ; AB publ ; publ
joint_stock | SE | EU | !SE ; Societas Europaea
joint_stock | A/S | DK | A/S ; Aktieselskab
limited_liability | ApS | DK | ApS ; Anpartsselskab
limited_liability | AS | NO,EE | !AS ; Aksjeselskap
public_joint_stock | ASA | NO | ASA ; Allmennaksjeselskap
limited_liability | Oy | FI | !Oy ; Osakeyhtiö ; Osakeyhtio
public_joint_stock | Oyj | FI | Oyj
limited_liability | Sp. z o.o. | PL | Sp z o.o ; Sp zoo ; Spółka z ograniczoną odpowiedzialnością ; Spolka z ograniczona odpowiedzialnoscia ; Spolka z o.o
joint_stock | SA | PL | Spółka Akcyjna ; Spolka Akcyjna
limited_liability | s.r.o. | CZ,SK | s.r.o ; spol s r.o ; spol s.r.o
joint_stock | a.s. | CZ,SK | a.s ; akciová společnost ; akciova spolecnost
limited_liability | OOO | RU,BY | OOO ; ООО ; Общество с ограниченной ответственностью
joint_stock | AO | RU | !AO ; АО ; Акционерное общество
public_joint_stock | PAO | RU | PAO ; ПАО ; OAO ; ОАО ; Публичное акционерное общество
private_joint_stock | ZAO | RU | ZAO ; ЗАО
limited_liability | TOV | UA | TOV ; ТОВ ; Товариство з обмеженою відповідальністю
joint_stock | A.Ş. | TR | A.Ş ; A.S ; Anonim Şirketi ; Anonim Sirketi ; Anonim Şirket
limited_liability | Ltd. Şti. | TR | Ltd Şti ; Ltd Sti ; Limited Şirketi ; Limited Sirketi
# ------------------------------------------------- Asia and the Americas
joint_stock | K.K. | JP | K.K ; !KK ; Kabushiki Kaisha ; Kabushiki Gaisha
limited_liability | G.K. | JP | G.K ; !GK ; Godo Kaisha ; Godo Gaisha
joint_stock | S.A. de C.V. | MX | S.A de C.V ; SA de CV ; S.A.B de C.V ; SAB de CV ; S.A.P.I de C.V ; SAPI de CV
limited_liability | S. de R.L. de C.V. | MX | S de R.L de C.V ; S de RL de CV ; S de R.L ; S de RL
limited_liability | Ltda | BR,PT,CO,CL | Ltda ; Lda ; Limitada
"""


@dataclass(frozen=True)
class LegalForm:
    """A legal form recognised in a name."""

    abbr: str            # canonical abbreviation, e.g. "LLC"
    category: str        # the most specific category, see CATEGORIES
    categories: tuple    # every category the spelling may stand for
    countries: tuple     # ISO codes where the form is used; () if generic
    text: str = ""       # the form as written in the name

    def to_dict(self) -> dict:
        return {"text": self.text, "abbr": self.abbr, "category": self.category,
                "categories": list(self.categories), "countries": list(self.countries)}


def compatible(a: "LegalForm | None", b: "LegalForm | None") -> str:
    """Relation between two legal forms.

    ``"same"``, ``"compatible"`` (e.g. Ltd / LLC, JSC / PJSC), ``"different"``
    or ``"unknown"`` when a side has no informative legal form.
    """
    if a is None or b is None or a.category == "company" or b.category == "company":
        return "unknown"
    ca, cb = set(a.categories), set(b.categories)
    if ca & cb:
        return "same"
    for fam in _FAMILIES:
        if ca & fam and cb & fam:
            return "compatible"
    return "different"


# (category, abbr, countries, spelling, end_only) rows, parsed lazily by parse.py
# because turning a spelling into tokens needs the tokeniser.
FORMS: list = []


def _load():
    for line in _DATA.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        category, abbr, countries, spellings = (x.strip() for x in line.split("|"))
        if category not in CATEGORIES:
            raise ValueError(f"unknown legal category {category!r}")
        cc = tuple(c for c in countries.split(",") if c != "*")
        for sp in spellings.split(";"):
            sp = sp.strip()
            if not sp:
                continue
            end_only = sp.startswith("!")
            FORMS.append((category, abbr, cc, sp.lstrip("!"), end_only))


_load()
