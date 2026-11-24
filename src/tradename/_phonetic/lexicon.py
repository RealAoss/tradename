# Vendored from ismatch (https://github.com/RealAoss/ismatch), MIT licence, same
# author. ismatch is not published on PyPI, so tradename carries its own copy.
# Adapted for tradename; do not expect it to stay in sync with upstream.

"""A small curated lexicon of common Arabic names.

Arabic script does not write short vowels, so حسن (Hasan) and حسين (Husayn)
are one vowel letter apart and محمد / محمود share a consonant skeleton.
The lexicon gives the matcher two things rules alone cannot:

1. the *vocalised* reading of an Arabic spelling, so that it can be compared
   with a Latin spelling vowel by vowel;
2. the knowledge that two similar-sounding spellings are **different names**.

Format, one entry per line::

    reading[,reading2] = arabic-spelling [arabic-spelling2 ...]

Readings use plain ASCII. A dot marks a syllable break where two letters
would otherwise be read as a digraph (``fat.hi`` is t + h, not "th").

Contributions are very welcome: adding a line here is the easiest way to
improve matching quality for names from your region.
"""

from __future__ import annotations

from functools import lru_cache

from .distance import similarity, skeleton
from .phonemes import arabic_phonemes, hebrew_phonemes, latin_phonemes

_DATA = """
# --- building blocks -------------------------------------------------------
abd = عبد
allah = الله
ilah = إله
abu = ابو ابي ابا
umm = ام
din = دين
# --- male given names ------------------------------------------------------
muhammad = محمد
ahmad = أحمد
mahmud = محمود
mustafa = مصطفى
hamid = حامد
hamid,humayd = حميد
hamad = حمد
hammad = حماد
hamdan = حمدان
hamdi = حمدي
hamza = حمزة
hamud = حمود
ali = علي
hasan = حسن
husayn = حسين
hasanayn = حسنين
umar = عمر
amr,amru = عمرو
ammar = عمار
amir = عامر
amir = أمير
uthman = عثمان
bakr = بكر
khalid = خالد
khalil = خليل
khalaf = خلف
khalifa = خليفة
walid = وليد
said,sayid = سعيد
saad = سعد
saud = سعود
sayyid = سيد
ibrahim = إبراهيم
ismail = إسماعيل
is.haq = إسحاق اسحق
yaqub = يعقوب
yusuf = يوسف
yunus = يونس
yahya = يحيى
isa = عيسى
musa = موسى
harun = هارون
dawud = داود داوود
sulayman = سليمان
salman = سلمان
salim = سالم
salim = سليم
salam = سلام
salama = سلامة
salih = صالح
salah = صلاح
sabir = صابر
sabri = صبري
subhi = صبحي
samir = سمير
samir = سامر
sami = سامي
samih = سامح
sharif = شريف
shadi = شادي
shakir = شاكر
shukri = شكري
shawqi = شوقي
shaban = شعبان
ramadan = رمضان
rajab = رجب
rashid = راشد
rashid = رشيد
rashad = رشاد
rushdi = رشدي
rida = رضا
ridwan = رضوان
rafiq = رفيق
rafat = رأفت
rami = رامي
ramzi = رمزي
raid = رائد
riyad = رياض
zayd = زيد
ziyad = زياد
zayid = زايد
zakariya = زكريا
zaki = زكي
zuhayr = زهير
zayn = زين
tariq = طارق
talal = طلال
talib = طالب
tahir = طاهر
taha = طه
tawfiq = توفيق
taysir = تيسير
tamim = تميم
tamir = تامر
thabit = ثابت
thamir = ثامر
thair = ثائر
jabir = جابر
jafar = جعفر
jalal = جلال
jamal = جمال
jamil = جميل
jihad = جهاد
jawad = جواد
juma = جمعة
jubran = جبران
jurj = جورج
habib = حبيب
hatim = حاتم
hazim = حازم
husam = حسام
husni = حسني
hilmi = حلمي
hikmat = حكمت
haydar = حيدر
hani = هاني
hashim = هاشم
hisham = هشام
haytham = هيثم
hilal = هلال
hadi = هادي
humam = همام
diya = ضياء
fadi = فادي
fadil = فاضل
fadl = فضل
fahd = فهد
fahmi = فهمي
faris = فارس
faruq = فاروق
fat.hi = فتحي
fawzi = فوزي
faysal = فيصل
fayiz = فايز
fuad = فؤاد
firas = فراس
farid = فريد
faraj = فرج
farhan = فرحان
fawwaz = فواز
qasim = قاسم
qays = قيس
qusay = قصي
kamal = كمال
kamil = كامل
karim = كريم
kazim = كاظم
kinan = كنان
luay = لؤي
lutfi = لطفي
labib = لبيب
majid = ماجد
majid = مجيد
majdi = مجدي
mahir = ماهر
mazin = مازن
malik = مالك
mamduh = ممدوح
mamun = مأمون
mansur = منصور
marwan = مروان
masud = مسعود
mahdi = مهدي
mid.hat = مدحت
munir = منير
mundhir = منذر
mujahid = مجاهد
mukhtar = مختار
murad = مراد
mursi = مرسي
muadh = معاذ
muawiya = معاوية
mutaz = معتز
mutasim = معتصم
muayyad = مؤيد
mumin = مؤمن
muhsin = محسن
muhannad = مهند
mubarak = مبارك
mishal = مشعل
nabil = نبيل
nadir = نادر
nadim = نديم
naim = نعيم
naji = ناجي
najib = نجيب
najm = نجم
nasir = ناصر
nasr = نصر
nasim = نسيم
nawaf = نواف
nayif = نايف
nazih = نزيه
nizar = نزار
numan = نعمان
nur = نور
nuh = نوح
wail = وائل
wajih = وجيه
wasim = وسيم
wisam = وسام
wahid = وحيد
yasir = ياسر
yasin = ياسين
yazid = يزيد
yazan = يزن
ayman = أيمن
ayyub = أيوب
adam = آدم
ad.ham = أدهم
adib = أديب
adil = عادل
adnan = عدنان
akram = أكرم
ala = علاء
amin = أمين
amjad = أمجد
anas = أنس
anwar = أنور
arafat = عرفات
ashraf = أشرف
asad = أسعد
asad = أسد
asim = عاصم
atif = عاطف
awad = عوض
awni = عوني
aziz = عزيز
azmi = عزمي
azzam = عزام
abbas = عباس
abid = عابد
abdu = عبده
ubayd = عبيد
uday = عدي
imad = عماد
imran = عمران
isam = عصام
iyad = إياد
ihab = إيهاب
ilyas = إلياس
idris = إدريس
ihsan = إحسان
islam = إسلام
usama = أسامة
uways = أويس
anis = أنيس
badr = بدر
baha = بهاء
bashir = بشير
bashar = بشار
basim = باسم
basil = باسل
bassam = بسام
bilal = بلال
burhan = برهان
butrus = بطرس
bulus = بولس
hanna = حنا
mikhail = ميخائيل
ghassan = غسان
ghazi = غازي
ghalib = غالب
ghanim = غانم
sufyan = سفيان
sayf = سيف
sultan = سلطان
sinan = سنان
suhayl = سهيل
shihab = شهاب
shafiq = شفيق
safwan = صفوان
sakhr = صخر
sadiq = صادق
siddiq = صديق
saddam = صدام
turki = تركي
khayri = خيري
khattab = خطاب
khamis = خميس
khidr = خضر
# --- family names and name elements ---------------------------------------
masri = مصري
shami = شامي
baghdadi = بغدادي
halabi = حلبي
tamimi = تميمي
hashimi = هاشمي
qurashi = قرشي
najjar = نجار
haddad = حداد
khuri = خوري
khatib = خطيب
sabbagh = صباغ
hariri = حريري
jabbar = جبار
rahman = رحمن رحمان
rahim = رحيم
latif = لطيف
qadir = قادر
halim = حليم
hakim = حكيم
razzaq = رزاق
wahhab = وهاب
ghani = غني
ghaffar = غفار
jalil = جليل
fattah = فتاح
qadhafi = قذافي
husayni = حسيني
sisi = سيسي
hafiz = حافظ
ansari = أنصاري
kurdi = كردي
darwish = درويش
zubi = زعبي
dulaymi = دليمي
jaburi = جبوري
maliki = مالكي
sadr = صدر
shammari = شمري
anzi = عنزي
utaybi = عتيبي
qahtani = قحطاني
ghamdi = غامدي
zahrani = زهراني
dawsari = دوسري
harbi = حربي
mutayri = مطيري
shahri = شهري
thani = ثاني
nahyan = نهيان
maktum = مكتوم
# --- female given names ---------------------------------------------------
fatima = فاطمة
aisha = عائشة
khadija = خديجة
maryam = مريم
zaynab = زينب
ruqayya = رقية
amina = أمينة
amina = آمنة
asma = أسماء
hafsa = حفصة
safiyya = صفية
sumayya = سمية
halima = حليمة
salma = سلمى
salwa = سلوى
samira = سميرة
samar = سمر
sahar = سحر
sara = سارة
suad = سعاد
suha = سهى
suhayr = سهير
sana = سناء
saida = سعيدة
sabah = صباح
safa = صفاء
shayma = شيماء
shadiya = شادية
rana = رنا
raniya = رانيا
rasha = رشا
rim = ريم
rima = ريما
rahma = رحمة
rabab = رباب
raghad = رغد
randa = رندة رندا
rawan = روان
ruba = ربى
zahra = زهراء زهرة
dalal = دلال
daliya = داليا
dina = دينا
dima = ديمة ديما
dua = دعاء
fadwa = فدوى
farah = فرح
farida = فريدة
fatin = فاتن
fayruz = فيروز
ghada = غادة
ghadir = غدير
hala = هالة
hana = هناء
hanan = حنان
hanin = حنين
hiba = هبة
hind = هند
huda = هدى
hayfa = هيفاء
hayat = حياة
iman = إيمان
inas = إيناس
isra = إسراء
ibtisam = ابتسام
ikram = إكرام
ilham = إلهام
intisar = انتصار
jamila = جميلة
jihan = جيهان
jumana = جمانة
karima = كريمة
kawthar = كوثر
lama = لمى
lamis = لميس
latifa = لطيفة
layla = ليلى
lina = لينا
lubna = لبنى
lujayn = لجين
maha = مها
muna = منى
manal = منال
manar = منار
maysa = ميساء
may = مي
malak,malik = ملك
marwa = مروة
nada = ندى
nadiya = نادية
nadin = نادين
nahla = نهلة
najla = نجلاء
najwa = نجوى
nawal = نوال
nura = نورة نورا
nuha = نهى
nisrin = نسرين
rula = رولا رلى
ula = علا
alya = علياء
wafa = وفاء
wala = ولاء
widad = وداد
yasmin = ياسمين
yusra = يسرى
yara = يارا
amal = أمل آمال
amani = أماني
amira = أميرة
arwa = أروى
aya = آية
abir = عبير
afaf = عفاف
ahlam = أحلام
azza = عزة
aziza = عزيزة
basma = بسمة
bushra = بشرى
buthayna = بثينة
tahani = تهاني
taghrid = تغريد
thurayya = ثريا
"""

_AR_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ئ": "ي", "ؤ": "و",
})


def ar_key(s: str) -> str:
    """Fold the spelling variation people do not treat as meaningful."""
    s = s.translate(_AR_FOLD)
    if len(s) > 2 and s.endswith("ء"):
        s = s[:-1]
    return s


@lru_cache(maxsize=None)
def reading_phonemes(reading: str) -> tuple:
    out = []
    for part in reading.split("."):
        out.extend(latin_phonemes(part))
    return tuple(out)


ENTRIES: list = []          # (readings, arabic spellings)
_BY_ARABIC: dict = {}       # folded arabic -> [entry id]
_BY_SKELETON: dict = {}     # consonant skeleton -> [(entry id, phonemes)]
_BY_AR_SKELETON: dict = {}  # same, from the unvocalised Arabic spelling


def _load():
    for line in _DATA.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        left, right = line.split("=")
        readings = tuple(r.strip() for r in left.split(","))
        spellings = tuple(right.split())
        eid = len(ENTRIES)
        ENTRIES.append((readings, spellings))
        for sp in spellings:
            _BY_ARABIC.setdefault(ar_key(sp), []).append(eid)
            seq = arabic_phonemes(sp)
            _BY_AR_SKELETON.setdefault(skeleton(seq), []).append((eid, seq))
        for r in readings:
            seq = reading_phonemes(r)
            _BY_SKELETON.setdefault(skeleton(seq), []).append((eid, seq))


_load()


def arabic_ids(text: str) -> frozenset:
    """Lexicon entries an Arabic spelling may stand for."""
    return frozenset(_BY_ARABIC.get(ar_key(text), ()))


def readings_for(text: str, script: str = "ar") -> tuple:
    """Vocalised readings of an Arabic (or Hebrew) spelling, or ``()`` if unknown."""
    out = []
    for eid in sorted(hebrew_ids(text)) if script == "he" else _BY_ARABIC.get(ar_key(text), ()):
        for r in ENTRIES[eid][0]:
            if r not in out:
                out.append(r)
    return tuple(out)


_RESOLVE_MIN = 0.93
_RESOLVE_MARGIN = 0.02


@lru_cache(maxsize=50_000)
def latin_ids(text: str) -> frozenset:
    """Lexicon entries a Latin spelling confidently stands for (may be empty)."""
    seq = latin_phonemes(text)
    if not seq:
        return frozenset()
    scored = []
    best = 0.0
    for eid, ref in _BY_SKELETON.get(skeleton(seq), ()):
        s = similarity(seq, ref)
        if s >= _RESOLVE_MIN:
            scored.append((s, eid))
            if s > best:
                best = s
    return frozenset(eid for s, eid in scored if s >= best - _RESOLVE_MARGIN)


def _resolve(seq, buckets) -> frozenset:
    if not seq:
        return frozenset()
    scored = []
    best = 0.0
    for eid, ref in buckets.get(skeleton(seq), ()):
        s = similarity(seq, ref)
        if s >= _RESOLVE_MIN:
            scored.append((s, eid))
            if s > best:
                best = s
    return frozenset(eid for s, eid in scored if s >= best - _RESOLVE_MARGIN)


@lru_cache(maxsize=50_000)
def hebrew_ids(text: str) -> frozenset:
    """Lexicon entries a Hebrew-script spelling confidently stands for."""
    return _resolve(hebrew_phonemes(text), _BY_AR_SKELETON)
