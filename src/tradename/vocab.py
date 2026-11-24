"""Business vocabulary that gets *translated* between Arabic and English.

Format of ``_DATA``, one concept per line::

    concept : kind | latin spellings | arabic spellings

* ``kind`` is ``p`` for a place (country or city; matched like a qualifier),
  ``d`` for a descriptor (what the company does or is: trading,
  bank, group, holding) or ``q`` for a qualifier (national, international,
  gulf, a country, a city, a colour). Qualifiers carry more identity than
  descriptors: "Gulf Bank" and "National Bank" differ only in a qualifier.
* Spellings are separated by ``;`` and may be several words long.
* Latin spellings include English words, their abbreviations (``trdg``) and
  common *transliterations* of the Arabic word (``khaleej`` for الخليج).
* Arabic spellings are written without the article. The parser strips
  ``ال`` / ``لل`` / ``و`` / ``بال`` by itself, so ``تجارة`` also covers
  ``التجارة``, ``للتجارة`` and ``والتجارة``. List plural and adjective forms
  explicitly. Arabic spellings also include English words written in Arabic
  letters (``جروب`` = group).

A spelling may appear under two concepts (عمان is both Oman and Amman).

Known acronyms and trade names live in ``_ACRONYMS``::

    LATIN ; arabic | English expansion | Arabic expansion
"""

from __future__ import annotations

__all__ = ["CONCEPTS", "LATIN", "ARABIC", "ACRONYMS", "ar_key"]

_DATA = """
# ------------------------------------------------------------ what it does
trading : d | trading ; trade ; trdg ; trd ; tradg ; traders ; trader ; commerce ; commercial ; coml ; tijara ; tijarah ; tijaria ; tijariya ; tijari | تجارة ; تجارية ; تجاري ; متاجرة ; تريدنج ; تريدنغ ; تريدينج ; تريدينغ
general : d | general ; gen ; genl ; public | عامة ; عام ; عمومية ; جنرال
contracting : d | contracting ; contractors ; contractor ; cont ; contg ; contr ; contrg | مقاولات ; مقاولون ; مقاولين ; مقاول ; كونتراكتنج
construction : d | construction ; constructions ; constr ; const ; constn ; building ; buildings ; builders ; bldg | إنشاءات ; إنشاء ; إنشائية ; بناء ; تشييد ; مباني ; عمران ; كونستركشن
industries : d | industries ; industry ; industrial ; inds ; ind ; indl ; indus ; manufacturing ; manufacturers ; manufacture ; mfg ; mfrs ; sinaat ; sinaiya | صناعات ; صناعة ; صناعية ; صناعي ; تصنيع ; اندستريز
factory : d | factory ; factories ; fty ; plant ; mill ; mills ; works | مصنع ; مصانع ; معمل ; معامل
group : d | group ; grp ; gp ; groupe ; grupo ; gruppo | مجموعة ; جروب ; قروب ; غروب ; كروب
holding : d | holding ; holdings ; hldg ; hldgs ; hold | قابضة ; هولدنج ; هولدنغ ; هولدينج ; هولدينغ
investment : d | investment ; investments ; invest ; inv ; invt ; investing ; investors | استثمار ; استثمارات ; استثمارية ; استثماري ; انفستمنت
real_estate : d | real estate ; realestate ; realty ; properties ; property ; estates ; estate ; akaria ; aqaria ; aqar ; akar ; aqarat ; akarat | عقارية ; عقارات ; عقار ; عقاري ; أملاك ; بروبرتيز
development : d | development ; developments ; dev ; devt ; developers ; developer ; developing | تطوير ; تنمية ; تطويرية ; تنموية ; مطورون ; تعمير ; ديفلوبمنت
transport : d | transport ; transportation ; transports ; transporting ; haulage ; trucking ; carriers | نقل ; نقليات ; مواصلات ; ترانسبورت
shipping : d | shipping ; marine ; maritime ; navigation ; freight ; cargo ; forwarding | شحن ; ملاحة ; ملاحية ; بحرية ; شيبنج ; شيبينج ; كارجو ; مارين
logistics : d | logistics ; logistic | لوجستية ; لوجستيات ; لوجستيك ; لوجستي ; لوجستكس ; إمداد
services : d | services ; service ; svcs ; svc ; serv ; srvcs | خدمات ; خدمة ; خدمية ; سيرفيسز ; سيرفيسيز ; سيرفيس ; سيرفس
import : d | import ; imports ; importers ; importing ; imp | استيراد ; مستوردون
export : d | export ; exports ; exporters ; exporting ; exp | تصدير ; مصدرون
foodstuff : d | foodstuff ; foodstuffs ; food stuff ; food stuffs ; food ; foods ; provisions | مواد غذائية ; أغذية ; غذائية ; غذاء ; أطعمة ; فود ; فودز
catering : d | catering ; caterers | تموين ; تموينات ; إعاشة
pharmacy : d | pharmacy ; pharmacies ; drugstore ; drug store | صيدلية ; صيدليات
pharma : d | pharma ; pharmaceutical ; pharmaceuticals ; pharm ; drugs ; medicines | أدوية ; دواء ; دوائية ; صيدلانية ; فارما ; فارماسيوتيكال
hospital : d | hospital ; hospitals ; hosp | مستشفى ; مستشفيات ; مشفى
medical : d | medical ; med ; healthcare ; health care ; health ; medicare | طبية ; طبي ; صحية ; صحة ; رعاية صحية ; ميديكال
clinic : d | clinic ; clinics ; polyclinic | عيادة ; عيادات ; مستوصف
laboratory : d | laboratory ; laboratories ; lab ; labs | مختبر ; مختبرات
bank : d | bank ; banking ; banque ; banco ; bk ; banca | بنك ; مصرف ; بنوك ; مصرفية ; مصارف
insurance : d | insurance ; assurance ; ins ; insur ; reinsurance | تأمين ; تأمينات ; تأمينية ; إعادة تأمين
takaful : d | takaful ; takafol | تكافل ; تكافلي
exchange : d | exchange ; exch ; money exchange ; forex ; money changers | صرافة ; صيرفة ; صرافين
finance : d | finance ; financial ; financing ; fin ; financials ; financiere | تمويل ; مالية ; مالي ; تمويلية ; فاينانس
capital : d | capital | كابيتال ; رأس المال ; مال
brokerage : d | brokerage ; brokers ; broker ; securities | وساطة ; أوراق مالية ; سمسرة
technology : d | technology ; technologies ; tech ; techno ; teknoloji | تقنية ; تقنيات ; تكنولوجيا ; تكنولوجي ; تكنولوجية ; تكنولوجيز ; تك ; تيك
technical : d | technical ; technic ; technique | فنية ; فني ; تكنيكال
engineering : d | engineering ; engg ; eng ; engrg ; engineers ; engrs | هندسية ; هندسة ; هندسي ; مهندسون ; إنجنيرنج
consulting : d | consulting ; consultants ; consultancy ; consultant ; consultancies ; consult ; advisory ; advisors ; advisers | استشارات ; استشارية ; استشاري ; استشاريون ; مستشارون ; كونسلتنج
petroleum : d | petroleum ; oil ; oils ; petrol ; petro ; pétrole ; petrole | بترول ; نفط ; بترولية ; نفطية ; زيوت ; زيت ; بتروليوم ; بترو
gas : d | gas ; gases ; gaz | غاز ; غازات
energy : d | energy ; power ; energies | طاقة ; باور ; إنرجي ; انيرجي ; طاقات
electric : d | electric ; elektrik ; electrical ; electricity ; elect ; elec ; electricals | كهرباء ; كهربائية ; كهربائي ; كهربائيات ; إلكتريك ; إليكتريك ; إلكتريك
electronics : d | electronics ; electronic | إلكترونيات ; إلكترونية ; إلكتروني
water : d | water ; waters | مياه ; ماء
bookstore : d | bookstore ; bookstores ; book store ; bookshop ; library ; stationery | مكتبة ; مكتبات ; قرطاسية
warehousing : d | warehousing ; warehouses ; warehouse ; storage | مخازن ; تخزين ; مستودعات ; مخزن
retail : d | retail ; retailing ; retailers | تجزئة ; بيع بالتجزئة ; ريتيل
store : d | stores ; store ; shop ; shops ; shoppe | متاجر ; متجر ; محلات ; محل ; ستور ; ستورز ; شوب
market : d | market ; markets ; mart ; supermarket ; supermarkets ; hypermarket ; hypermarkets ; souk ; souq | أسواق ; سوق ; ماركت ; سوبرماركت ; سوبر ماركت ; هايبرماركت ; هايبر ماركت ; مارت
mall : d | mall ; malls | مول ; مولات
center : d | center ; centre ; ctr ; centers ; centres | مركز ; مراكز ; سنتر
plaza : d | plaza | بلازا
tower : d | tower ; towers | برج ; أبراج ; تاور ; تاورز
telecom : d | telecom ; telecommunications ; telecommunication ; telecoms ; communications ; communication ; comms | اتصالات ; تليكوم ; تيليكوم
media : d | media | إعلام ; إعلامية ; ميديا
advertising : d | advertising ; advertisement ; adv ; advt ; publicity | دعاية ; إعلان ; إعلانات
marketing : d | marketing ; mktg | تسويق ; تسويقية ; ماركتنج
printing : d | printing ; press ; printers ; print | طباعة ; مطبعة ; مطابع
publishing : d | publishing ; publishers ; publications | نشر ; منشورات
distribution : d | distribution ; distributors ; distributor ; dist ; distr ; distributing | توزيع ; موزعون
tourism : d | tourism ; tours ; tourist ; tour | سياحة ; سياحية ; سياحي ; تورز
travel : d | travel ; travels | سفر ; سفريات ; ترافل
hotel : d | hotel ; hotels ; hospitality ; resort ; resorts | فندق ; فنادق ; فندقية ; ضيافة ; أوتيل ; منتجع ; منتجعات
restaurant : d | restaurant ; restaurants | مطعم ; مطاعم
cafe : d | cafe ; coffee ; cafeteria ; coffeeshop | مقهى ; كافيه ; كوفي ; قهوة ; كافتيريا
bakery : d | bakery ; bakeries | مخبز ; مخابز ; أفران
sweets : d | sweets ; confectionery ; pastry ; pastries | حلويات
motors : d | motors ; motor ; automotive ; auto ; automobiles ; automobile ; cars ; car ; vehicles | سيارات ; موتورز ; موتور ; أوتو ; مركبات
spare_parts : d | spare parts ; spares ; parts | قطع غيار
garage : d | garage ; workshop | ورشة ; كراج ; ورش
rental : d | rental ; rent ; leasing ; lease ; rent a car | تأجير ; إيجار ; ليسنج
agriculture : d | agriculture ; agricultural ; agri ; agro ; farms ; farm ; farming | زراعة ; زراعية ; زراعي ; مزارع ; مزرعة
dairy : d | dairy ; dairies | ألبان
poultry : d | poultry | دواجن
fisheries : d | fisheries ; fish ; seafood | أسماك
meat : d | meat ; meats | لحوم
dates : d | dates | تمور
cement : d | cement ; ciment | أسمنت ; إسمنت
steel : d | steel ; iron | حديد ; صلب ; فولاذ ; ستيل
aluminium : d | aluminium ; aluminum | ألمنيوم ; ألومنيوم
glass : d | glass | زجاج
plastic : d | plastic ; plastics | بلاستيك ; لدائن
chemicals : d | chemical ; chemicals ; chem | كيماويات ; كيميائية ; كيماوية ; كيميائيات
petrochemicals : d | petrochemical ; petrochemicals ; petrochem | بتروكيماويات ; بتروكيماوية ; بتروكيميائيات
fertilizers : d | fertilizers ; fertilizer ; fertilisers | أسمدة
paints : d | paints ; paint ; coatings | دهانات ; أصباغ
paper : d | paper | ورق
packaging : d | packaging ; packing | تعبئة ; تغليف
textiles : d | textile ; textiles ; garments ; clothing ; fashion ; fashions ; readymade garments | نسيج ; منسوجات ; ملابس ; أزياء ; أقمشة ; غزل
furniture : d | furniture ; furnishings ; furnishing | أثاث ; مفروشات
wood : d | timber ; wood ; woodworks | أخشاب ; خشب
marble : d | marble | رخام
ceramics : d | ceramics ; ceramic | سيراميك ; خزف
cables : d | cables ; cable | كابلات ; كيبل
pipes : d | pipes ; pipe | أنابيب ; مواسير
mining : d | mining ; mines | تعدين ; مناجم
minerals : d | minerals ; mineral ; metals ; metal | معادن ; معدنية
jewellery : d | jewellery ; jewelry ; jewellers ; jewelers ; jewels | مجوهرات ; جواهر
equipment : d | equipment ; equipments ; equip ; eqpt ; machinery ; machines | معدات ; آلات ; أجهزة ; تجهيزات
supplies : d | supplies ; supply ; suppliers | توريدات ; توريد ; لوازم ; مستلزمات ; إمدادات
materials : d | materials ; material ; matls | مواد
tools : d | tools ; hardware | أدوات ; عدد
maintenance : d | maintenance ; maint | صيانة
cleaning : d | cleaning | تنظيف ; نظافة
security : d | security ; guards | أمن ; حراسة ; حراسات ; أمنية ; سيكيوريتي
safety : d | safety | سلامة
projects : d | projects ; project ; enterprises ; enterprise ; ent ; ventures | مشاريع ; مشروعات ; مشروع
management : d | management ; mgmt ; mgt ; managing | إدارة
education : d | education ; educational | تعليم ; تعليمية ; تربية
training : d | training | تدريب
school : d | school ; schools | مدرسة ; مدارس
university : d | university ; univ | جامعة
college : d | college | كلية
academy : d | academy | أكاديمية
institute : d | institute ; institution | معهد
law : d | law ; legal ; advocates ; attorneys ; lawyers | محاماة ; محامون ; قانونية ; قانون
accounting : d | accounting ; accountants ; auditors ; audit ; auditing | محاسبة ; محاسبون ; تدقيق ; مراجعة ; مدققون
design : d | design ; designs ; decor ; decoration ; interiors | تصميم ; تصاميم ; ديكور ; ديزاين
computer : d | computer ; computers | كمبيوتر ; حاسب ; حاسوب ; حاسبات
software : d | software | برمجيات ; سوفتوير ; سوفت وير
digital : d | digital | رقمية ; رقمي ; ديجيتال
information : d | information ; info | معلومات
networks : d | networks ; network | شبكات ; شبكة
data : d | data | بيانات ; داتا
solutions : d | solutions ; solution ; solns ; soln | حلول ; سوليوشنز
systems : d | systems ; system ; sys | أنظمة ; نظم ; سيستمز ; سيستم
airlines : d | airlines ; airways ; airline ; air lines ; air ; aviation | طيران ; خطوط جوية ; جوية ; إيرلاينز
airport : d | airport ; airports | مطار ; مطارات
port : d | ports ; port ; harbour ; harbor | ميناء ; موانئ
sport : d | sports ; sport | رياضة ; رياضية ; رياضي ; سبورت
club : d | club | نادي
beauty : d | beauty ; salon ; cosmetics | تجميل ; صالون ; كوزمتكس
perfumes : d | perfumes ; perfume ; fragrances | عطور ; عطورات ; عطر
optics : d | optics ; optical ; opticians | بصريات ; نظارات
products : d | products ; product | منتجات
environment : d | environment ; environmental | بيئة ; بيئية
recruitment : d | recruitment ; manpower ; human resources ; staffing | استقدام ; توظيف ; موارد بشرية ; عمالة ; قوى عاملة
agencies : d | agencies ; agency ; agents | وكالات ; وكالة ; توكيلات ; وكلاء
office : d | office ; bureau | مكتب ; مكاتب
house : d | house | بيت ; دار ; هاوس
association : d | association ; society ; assn | جمعية ; رابطة
authority : d | authority | هيئة ; سلطة
organization : d | organization ; organisation ; org | منظمة
ministry : d | ministry | وزارة
basic : d | basic | أساسية ; أساسي
brothers : d | brothers ; bros ; bro ; freres ; frères ; hermanos | إخوان ; أخوان ; إخوانه ; إخوة ; أخوة ; أشقاء ; شقيقه
sons : d | sons ; son ; fils | أولاده ; أبناؤه ; أبنائه ; أبناءه ; أولاد ; أبناء ; أولادهم ; أبنه ; نجله ; أنجاله
partners : d | partners ; partner ; associates ; and co ; and company ; et cie ; und co | شركاه ; شركاؤه ; شركائه ; شركاءه ; شركاهم ; شركاؤهم ; شريكه ; شركاء ; شركاها
star : q | star ; stars | نجمة ; نجم ; نجوم ; ستار ; ستارز
plus : q | plus | بلس
gold : q | gold | ذهب ; جولد ; غولد ; قولد
golden : q | golden | ذهبي ; ذهبية ; جولدن ; غولدن
silver : q | silver | فضة ; فضي ; فضية ; سيلفر
diamond : q | diamond ; diamonds | ألماس ; ماسة ; ماس ; دايموند
# ------------------------------------------------------------- qualifiers
international : q | international ; intl ; intnl ; internl ; int ; internacional ; internationale ; global ; worldwide ; world ; dawlia ; dawliya ; alamia ; alamiya ; alamiah | دولية ; دولي ; عالمية ; عالمي ; عالم ; إنترناشيونال ; إنترناشونال ; انترناشيونال ; انترناشونال ; جلوبال ; غلوبال
national : q | national ; natl ; nat ; nationale ; nacional ; watania ; wataniya ; wataniah ; watani ; ahli ; ahlia ; ahliya ; ahlia ; ahlya | وطنية ; وطني ; أهلية ; أهلي ; ناشيونال ; ناشونال
united : q | united ; utd ; unified ; mottahida ; muttahida ; mutahida ; motaheda ; mottaheda | متحدة ; متحد ; موحدة ; يونايتد
modern : q | modern ; haditha ; hadeetha | حديثة ; حديث ; عصرية ; عصري ; مودرن
arab : q | arab ; arabian ; arabia ; arabic ; arabe | عربية ; عربي ; عرب ; أرابيان ; أرابيا
gulf : q | gulf ; khaleej ; khalij ; khaleeji ; khaliji ; khaleejia ; khaleejiya ; khalijia | خليج ; خليجية ; خليجي ; جلف ; غلف ; قلف
middle_east : q | middle east ; mideast ; mid east ; middleeast | شرق أوسط ; ميدل إيست
east : q | east ; eastern ; orient ; oriental ; sharq ; sharqia ; sharqiya ; mashreq ; mashriq | شرق ; شرقية ; شرقي ; مشرق
west : q | west ; western ; gharbia | غرب ; غربية ; غربي
north : q | north ; northern ; shamal | شمال ; شمالية ; شمالي
south : q | south ; southern ; janoub | جنوب ; جنوبية ; جنوبي
central : q | central ; markazi | مركزي ; مركزية ; وسطى
islamic : q | islamic ; islami ; islamia ; islamique | إسلامي ; إسلامية
first : q | first ; oula ; ula ; awwal | أول ; أولى
new : q | new | جديد ; جديدة ; نيو
green : q | green | أخضر ; خضراء ; جرين ; غرين
blue : q | blue | أزرق ; زرقاء ; بلو
red : q | red | أحمر ; حمراء
white : q | white | أبيض ; بيضاء ; وايت
black : q | black | أسود ; سوداء ; بلاك
royal : q | royal | ملكي ; ملكية ; رويال
crescent : q | crescent ; hilal ; helal | هلال
union : q | union ; etihad ; ittihad ; ittehad ; itihad | اتحاد ; يونيون
oasis : q | oasis ; waha | واحة
palm : q | palm ; palms ; nakheel ; nakhil | نخيل ; نخلة
pearl : q | pearl ; pearls | لؤلؤة ; لؤلؤ
desert : q | desert ; sahara | صحراء
sea : q | sea | بحر
city : q | city | مدينة ; سيتي
future : q | future ; mustaqbal | مستقبل
vision : q | vision | رؤية ; فيجن
pioneers : q | pioneers ; pioneer ; rowad ; ruwad | رواد ; رائد ; رائدة
elite : q | elite | نخبة
ideal : q | ideal | مثالي ; مثالية
advanced : q | advanced | متقدمة ; متطورة ; متقدم ; متطور
integrated : q | integrated | متكاملة ; متكامل
specialized : q | specialized ; specialised ; specialist ; specialists ; speciality ; specialty | متخصصة ; متخصص ; تخصصي ; تخصصية
professional : q | professional ; professionals ; pro | محترف ; محترفون ; مهنية ; مهني
smart : q | smart | ذكية ; ذكي ; سمارت
express : q | express ; fast ; speedy | سريع ; سريعة ; إكسبرس
quality : q | quality | جودة
private : q | private | خاصة ; خاص
great : q | great ; grand ; greater | كبرى ; كبير ; كبيرة ; عظمى ; جراند
nile : q | nile | نيل
# --------------------------------------------------------------- countries
saudi : p | saudi ; saudi arabia ; saudi arabian ; ksa ; saudia ; saoudite | سعودية ; سعودي ; مملكة عربية سعودية ; عربية سعودية
emirates : p | emirates ; emirati ; emirate ; uae ; united arab emirates ; emarat ; emaratia | إمارات ; إماراتية ; إماراتي ; إمارات عربية متحدة
kuwait : p | kuwait ; kuwaiti ; koweit | كويت ; كويتية ; كويتي
qatar : p | qatar ; qatari | قطر ; قطرية ; قطري
bahrain : p | bahrain ; bahraini | بحرين ; بحرينية ; بحريني
oman : p | oman ; omani | عمان ; عمانية ; عماني
egypt : p | egypt ; egyptian ; misr ; masr ; egypte | مصر ; مصرية ; مصري
jordan : p | jordan ; jordanian | أردن ; أردنية ; أردني
lebanon : p | lebanon ; lebanese ; liban ; libanaise ; libanais | لبنان ; لبنانية ; لبناني
syria : p | syria ; syrian | سوريا ; سورية ; سوري
iraq : p | iraq ; iraqi | عراق ; عراقية ; عراقي
palestine : p | palestine ; palestinian | فلسطين ; فلسطينية ; فلسطيني
yemen : p | yemen ; yemeni | يمن ; يمنية ; يمني
libya : p | libya ; libyan | ليبيا ; ليبية ; ليبي
tunisia : p | tunisia ; tunisian ; tunis ; tunisie ; tunisienne | تونس ; تونسية ; تونسي
algeria : p | algeria ; algerian ; algerie ; algerienne ; algiers ; alger | جزائر ; جزائرية ; جزائري
morocco : p | morocco ; moroccan ; maroc ; marocaine ; marocain | مغرب ; مغربية ; مغربي
sudan : p | sudan ; sudanese | سودان ; سودانية ; سوداني
turkey : p | turkey ; turkish ; turkiye ; turk | تركيا ; تركية ; تركي
iran : p | iran ; iranian | إيران ; إيرانية ; إيراني
india : p | india ; indian | هند ; هندية ; هندي
pakistan : p | pakistan ; pakistani | باكستان ; باكستانية ; باكستاني
china : p | china ; chinese | صين ; صينية ; صيني
japan : p | japan ; japanese | يابان ; يابانية ; ياباني
britain : p | british ; britain ; uk ; united kingdom ; england ; english | بريطانيا ; بريطانية ; بريطاني ; مملكة متحدة ; إنجليزية
america : p | american ; america ; usa ; united states ; americas | أمريكا ; أمريكية ; أمريكي ; أميركية ; أميركي ; أميركا ; ولايات متحدة
france : p | france ; french ; francaise ; français ; francais | فرنسا ; فرنسية ; فرنسي
germany : p | germany ; german ; deutschland ; deutsche | ألمانيا ; ألمانية ; ألماني
italy : p | italy ; italian ; italia | إيطاليا ; إيطالية ; إيطالي
spain : p | spain ; spanish ; espana | إسبانيا ; إسبانية ; إسباني
swiss : p | swiss ; switzerland ; suisse | سويسرا ; سويسرية ; سويسري
europe : p | europe ; european ; euro | أوروبا ; أوروبية ; أوروبي
africa : p | africa ; african ; afrique | أفريقيا ; أفريقية ; أفريقي
asia : p | asia ; asian ; asiatic | آسيا ; آسيوية ; آسيوي
# ------------------------------------------------------------------ cities
dubai : p | dubai | دبي
abu_dhabi : p | abu dhabi ; abudhabi ; abu dhabi emirate | أبوظبي ; أبو ظبي
sharjah : p | sharjah | شارقة
ajman : p | ajman | عجمان
ras_al_khaimah : p | ras al khaimah ; ras al khaima ; rak ; ras alkhaimah | رأس الخيمة
fujairah : p | fujairah | فجيرة
riyadh : p | riyadh ; riyad | رياض
jeddah : p | jeddah ; jidda ; jedda ; jiddah | جدة
makkah : p | makkah ; mecca ; makka | مكة ; مكة مكرمة
dammam : p | dammam | دمام
khobar : p | khobar | خبر
doha : p | doha | دوحة
manama : p | manama | منامة
muscat : p | muscat | مسقط
cairo : p | cairo ; le caire | قاهرة
alexandria : p | alexandria ; alex | إسكندرية
giza : p | giza | جيزة
amman : p | amman | عمان
beirut : p | beirut ; beyrouth | بيروت
damascus : p | damascus ; damas | دمشق
aleppo : p | aleppo | حلب
baghdad : p | baghdad | بغداد
basra : p | basra ; basrah | بصرة
erbil : p | erbil ; arbil | أربيل
jerusalem : p | jerusalem ; quds | قدس
gaza : p | gaza | غزة
sanaa : p | sanaa | صنعاء
aden : p | aden | عدن
tripoli : p | tripoli | طرابلس
benghazi : p | benghazi | بنغازي
casablanca : p | casablanca | دار بيضاء ; كازابلانكا
rabat : p | rabat | رباط
khartoum : p | khartoum | خرطوم
london : p | london | لندن
"""

_ACRONYM_DATA = """
SABIC ; سابك | Saudi Basic Industries Corporation | الشركة السعودية للصناعات الأساسية
ADNOC ; أدنوك | Abu Dhabi National Oil Company | شركة بترول أبوظبي الوطنية
ENOC ; اينوك | Emirates National Oil Company | شركة بترول الإمارات الوطنية
DEWA ; ديوا | Dubai Electricity and Water Authority | هيئة كهرباء ومياه دبي
STC | Saudi Telecom Company | شركة الاتصالات السعودية
QNB | Qatar National Bank | بنك قطر الوطني
NBK | National Bank of Kuwait | بنك الكويت الوطني
NBE | National Bank of Egypt | البنك الأهلي المصري
NBB | National Bank of Bahrain | بنك البحرين الوطني
CIB | Commercial International Bank | البنك التجاري الدولي
KOC | Kuwait Oil Company | شركة نفط الكويت
KPC | Kuwait Petroleum Corporation | مؤسسة البترول الكويتية
KFH ; بيتك | Kuwait Finance House | بيت التمويل الكويتي
ADCB | Abu Dhabi Commercial Bank | بنك أبوظبي التجاري
ADIB | Abu Dhabi Islamic Bank | مصرف أبوظبي الإسلامي
DIB | Dubai Islamic Bank | بنك دبي الإسلامي
FAB | First Abu Dhabi Bank | بنك أبوظبي الأول
SNB | Saudi National Bank | البنك الأهلي السعودي
QIB | Qatar Islamic Bank | مصرف قطر الإسلامي
BAPCO ; بابكو | Bahrain Petroleum Company | شركة نفط البحرين
ALBA ; ألبا | Aluminium Bahrain | ألمنيوم البحرين
EGA | Emirates Global Aluminium | الإمارات العالمية للألمنيوم
PDO | Petroleum Development Oman | تنمية نفط عمان
EGPC | Egyptian General Petroleum Corporation | الهيئة المصرية العامة للبترول
SEC | Saudi Electricity Company | الشركة السعودية للكهرباء
MAADEN ; معادن | Saudi Arabian Mining Company | شركة التعدين العربية السعودية
"""

_AR_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ئ": "ي", "ؤ": "و",
})


def ar_key(s: str) -> str:
    """Fold the Arabic spelling variation people do not treat as meaningful."""
    s = s.translate(_AR_FOLD)
    if len(s) > 2 and s.endswith("ء"):
        s = s[:-1]
    return s


CONCEPTS: dict = {}   # concept -> kind ('d' | 'q' | 'p')
LATIN: list = []      # (concept, spelling)
ARABIC: list = []     # (concept, spelling)
ACRONYMS: list = []   # (latin keys, arabic keys, english expansion, arabic expansion)


def _load():
    for line in _DATA.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        head, latin, arabic = (x.strip() for x in line.split("|"))
        concept, kind = (x.strip() for x in head.split(":"))
        if kind not in ("d", "q", "p"):
            raise ValueError(f"bad kind in vocabulary line: {line}")
        if concept in CONCEPTS:
            raise ValueError(f"duplicate concept {concept!r}")
        CONCEPTS[concept] = kind
        LATIN.extend((concept, s.strip()) for s in latin.split(";") if s.strip())
        ARABIC.extend((concept, s.strip()) for s in arabic.split(";") if s.strip())
    for line in _ACRONYM_DATA.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        keys, en, ar = (x.strip() for x in line.split("|"))
        keys = [k.strip() for k in keys.split(";")]
        ACRONYMS.append((keys[0].lower(), tuple(ar_key(k) for k in keys[1:]), en, ar))


_load()
