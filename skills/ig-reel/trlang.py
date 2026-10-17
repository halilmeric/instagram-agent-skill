#!/usr/bin/env python3
"""
trlang.py - hookscore.py ve beats.py için Türkçe dil desteği.

İngilizce sürüm süreyi kelime sayısından tahmin ediyor. Türkçe sondan eklemeli
bir dil: "kaybettiğimizi" tek kelime ama altı hece. Bu yüzden Türkçede süre
heceden hesaplanır. Türkçede hece sayısı ünlü sayısına eşittir, bu da sayımı
güvenilir kılar. Rakamlar okunduğu gibi sayılır: "18.000" -> "on sekiz bin",
dört hece.

Kelime eşlemesi eklere duyarlıdır: "kaybet" kökü "kaybettim", "kaybettiğim"
kelimelerini de yakalar; "beş" sayısı "beşte", "beşe" hallerini yakalar.
"""

import re

UPPER = "A-ZÇĞİÖŞÜÂÎÛ"
LOWER = "a-zçğıöşüâîû"
VOWELS = set("aeıioöuüâîûAEIİOÖUÜÂÎÛ")
TR_CHARS = set("çğıöşüÇĞİÖŞÜ")

# Yalnızca Türkçede geçen sık kelimeler. Bir tanesi bile metni Türkçe yapar.
HINT_WORDS = {
    "ve", "bir", "bu", "şu", "için", "ama", "çok", "daha", "değil", "gibi",
    "şimdi", "artık", "yok", "ben", "sen", "biz", "siz", "ile", "ki", "hiç",
    "neden", "nasıl", "sonra", "önce", "kadar", "oldu", "olan",
}

WORD_RE = re.compile(r"[$%₺€]?\d+(?:,\d+)+[\w'’]*|[\w$%₺€'’-]+")
NUMBER_RE = re.compile(
    r"[₺$€]\s?\d[\d.,]*"                                 # ₺500, $40
    r"|%\s?\d[\d,]*"                                     # %50
    r"|\b\d[\d.,]*\s?(?:%|₺|tl\b|lira|dolar|bin\b|k\b|x\b|kat"
    r"|saat|dakika|dk\b|saniye|sn\b|gün|hafta|ay\b|yıl|sene)?",
    re.IGNORECASE)
PROPER_RE = re.compile(rf"(?<!^)\b[{UPPER}][{LOWER}]{{2,}}\b", re.MULTILINE)
HASHTAG_RE = re.compile(r"(?:^|\s)#\w+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")

# Bir kökün arkasından gelebilecek kısa ekler. Uzun köklerde (4+ harf) her
# devam kabul edilir; kısa köklerde yalnızca bu listedekiler.
SUFFIXES = {
    "e", "a", "ye", "ya", "i", "ı", "u", "ü", "yi", "yı", "yu", "yü",
    "de", "da", "te", "ta", "den", "dan", "ten", "tan",
    "in", "ın", "un", "ün", "nin", "nın", "nun", "nün",
    "le", "la", "yle", "yla", "ler", "lar", "lerce", "larca", "lerde", "larda",
    "ce", "ca", "li", "lı", "lu", "lü", "lik", "lık", "luk", "lük",
    "dir", "dır", "tir", "tır", "dur", "dür", "tur", "tür",
    "im", "ım", "um", "üm", "imiz", "ımız", "umuz", "ümüz", "ken",
    "si", "sı", "su", "sü", "inci", "ıncı", "uncu", "üncü",
    "nci", "ncı", "ncu", "ncü", "er", "ar", "şer", "şar",
}
# Başka anlamı da olan kısa sayılar: yalnızca tam eşleşmede sayılır.
EXACT_ONLY = {"on", "ay", "yüz", "altı", "bin", "sır"}

ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]

SPOKEN_NUMBERS = {
    "sıfır", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz",
    "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen",
    "doksan", "yüz", "bin", "milyon", "milyar", "düzine", "yarım", "buçuk",
    "çeyrek", "binlerce", "yüzlerce", "milyonlarca",
}
MONEY_WORDS = {
    "lira", "tl", "dolar", "euro", "avro", "kuruş", "para", "maaş", "kira",
    "ciro", "gelir", "kâr", "kar", "zarar", "borç", "fatura", "fiyat",
    "milyoner", "yüzde", "zam", "indirim", "bütçe", "kazanç", "ücret",
}
UNIT_WORDS = {"saat", "dakika", "saniye", "gün", "hafta", "yıl", "sene"}

# Ortaya bir şey koyan kelimeler: kayıp, hata, yasak, sır, karşıtlık.
STAKES = {
    "asla", "hiç", "hiçbir", "kimse", "yanlış", "hata", "kaybet", "kayıp",
    "maliyet", "pahalı", "bedava", "ücretsiz", "ödedi", "ödedim", "ödeyip",
    "kovul", "istifa", "bırak", "sildim", "silin", "yasak", "yasadışı",
    "nefret", "israf", "boşa", "dolandır", "yalan", "gerçek", "sır", "gizli",
    "çaldı", "çalın", "önce", "yerine", "ama", "fakat", "ancak", "oysa",
    "sorun", "problem", "risk", "tehlike", "uyarı", "pişman", "keşke",
    "hâlâ", "hala", "zaten", "sadece", "yalnızca", "olmadan", "aslında",
    "değil", "yok", "bitti", "battı", "batır", "iflas", "kazan", "kazandı",
    "ilk", "kestim", "kesti", "durdur", "bedel", "korku", "kork", "kötü",
    "berbat", "rezil", "mahvet", "mahvol", "başarısız", "reddet", "reddedil",
    "kandır", "kaçır", "kaçırdı", "unut", "yasakla", "vazgeç",
    "karşı", "rağmen", "neden", "niye", "kimse", "herkes", "eksik",
    "boşuna", "zorunda", "mecbur", "şikayet", "kriz", "ceza",
}
# Tek kelimeyle yakalanamayan bedel kalıpları.
STAKE_PHRASES_RE = re.compile(r"(?i)\bmal ol|\bcebimden|\bel(?:imden)? çık|\byüzüne bak")
# Türkçede olumsuzluk fiilin içindedir: yap-ma-dım, bil-mi-yor.
NEGATION_RE = re.compile(
    r"..(?:m[ae]d[ıiuü]|m[ıiuü]yor|m[ae]z\b|m[ae]m[ıiuü]ş|m[ae]y[ae]c[ae]k|m[ae]m[ae]l[ıi])")

# İlk saniyeyi boşa harcayan açılışlar.
WEAK_OPENERS = [
    "selam", "selamlar", "merhaba", "herkese", "hepinize", "arkadaşlar",
    "dostlar", "evet", "tamam", "peki", "bugün", "şimdi", "aslında", "yani",
    "bakın", "bak", "dinleyin", "dinle", "öncelikle", "şöyle", "hani",
    "bu videoda", "bu video", "bugünkü", "size", "sana", "biliyor musun",
    "biliyor musunuz", "hiç düşündün", "hiç düşündünüz", "bir şey",
    "bir gün", "bu bir", "bu konu", "şunu", "bilmiyorum", "bence",
]

# Komut kipleri. Türkçede fiil sonda olduğu için ilk ve son kelimeye bakılır.
IMPERATIVES = {
    "çal", "kopyala", "sil", "dene", "izle", "oku", "kaydet", "kullan", "kur",
    "yap", "yaz", "gönder", "al", "başla", "bırak", "kontrol", "dur",
    "durdur", "unut", "bak", "sakla", "paylaş", "yorumla", "dinle", "öğren",
    "yapma", "silme", "alma", "deneme", "kullanma", "harcama", "ödeme",
    "atla", "geç", "tıkla", "takip", "düşün", "hesapla", "sor", "söyle",
    "kazan", "biriktir", "yükle", "indir", "ekle", "çıkar", "değiştir",
}
SECOND_PERSON = {
    "sen", "siz", "senin", "sizin", "sana", "size", "seni", "sizi", "sende",
    "sizde", "senden", "sizden", "kendin", "kendine", "kendini",
}
SECOND_PERSON_RE = re.compile(
    r"(?:yorsun|yorsunuz|d[ıiuü]n|t[ıiuü]n|d[ıiuü]n[ıiuü]z|t[ıiuü]n[ıiuü]z"
    r"|m[ae]l[ıi]s[ıi]n|m[ae]l[ıi]s[ıi]n[ıi]z|[ae]b[ıi]l[ıi]rs[ıi]n|[ae]c[ae]ks[ıi]n"
    r"|ırsın|irsin|ursun|ürsün)$")
FIRST_PERSON = {
    "ben", "benim", "bana", "beni", "bende", "benden", "biz", "bizim",
    "bize", "bizi", "bizde", "bizden", "kendim", "kendimi",
}
FIRST_PERSON_RE = re.compile(
    r"(?:d[ıiuü]m|t[ıiuü]m|d[ıiuü]k|t[ıiuü]k|yorum|yoruz|[ae]c[ae]ğ[ıi]m"
    r"|m[ıiuü]ş[ıiuü]m|r[ıiuü]m|ırım|irim|urum|ürüm)$")

STOPWORDS = {
    "ve", "ile", "bir", "bu", "şu", "o", "da", "de", "mi", "mı", "mu", "mü",
    "ki", "ben", "sen", "biz", "siz", "onlar", "için", "gibi", "çok", "daha",
    "ama", "en", "ne", "her", "hiç", "ya", "veya", "ise", "olarak", "kadar",
    "sonra", "önce", "şimdi", "artık", "değil", "var", "yok", "bunu", "şunu",
    "onu", "benim", "senin", "bana", "sana", "beni", "seni", "oldu", "olan",
}

DEALBREAKERS = [
    (re.compile(r"(?i)^\s*(?:kaydırmayı bırak|kaydırma|geçme|sakın geçme|dur dur)"),
     "\"Kaydırma\" diye açılıyor. Dikkat istemek, onu henüz hak etmediğini gösterir."),
    (re.compile(r"(?i)\b(?:bu videoda|bugünkü videoda|bu reels'?te|bu reel'?da"
                r"|size (?:\w+ )?göstereceğim|sana (?:\w+ )?göstereceğim|anlatacağım)\b"),
     "Video girizgâhı. Sil ve doğrudan vaatle aç."),
    (re.compile(r"(?i)^\s*(?:selam|merhaba|herkese merhaba|selamlar|arkadaşlar|hoş geldin)"),
     "Selamlama. Kimse akışa selamlanmak için gelmedi."),
    (HASHTAG_RE,
     "Hook'ta hashtag var. Hashtag'in yeri açıklamanın altı, o da gerekirse."),
    (EMOJI_RE,
     "Hook'ta emoji var. Hook boyutundaki ekran yazısında ya kelimeye ya emojiye yer var, ikisine değil."),
]


def lower(text):
    """Türkçe küçük harf: I -> ı, İ -> i."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def detect(text, lang="auto"):
    if lang in ("tr", "en"):
        return lang
    if any(c in TR_CHARS for c in text):
        return "tr"
    toks = set(re.findall(r"\w+", lower(text)))
    return "tr" if toks & HINT_WORDS else "en"


def words(text):
    # Türkçede binlik ayırıcı noktadır: "18.000" konuşulurken tek sayıdır.
    text = re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", text)
    return [w for w in WORD_RE.findall(text) if w.strip("-'’")]


def base(token):
    """Küçük harfe çevir, kesme işaretinden sonraki eki at: Notion'da -> notion."""
    return re.split(r"['’]", lower(token))[0].strip("-")


SOFTEN = {"k": "ğ", "p": "b", "t": "d", "ç": "c"}


def matches(token, stems):
    """Eklere duyarlı eşleme: kök tam eşleşir ya da ekle devam eder."""
    t = base(token)
    if t in stems:
        return True
    for s in stems:
        if s in EXACT_ONLY:
            continue
        # Ünsüz yumuşaması: eksik -> eksiği, kitap -> kitabı, git -> gidiyor
        forms = [s]
        if s[-1] in SOFTEN and len(s) >= 4:
            forms.append(s[:-1] + SOFTEN[s[-1]])
        for f in forms:
            if not t.startswith(f):
                continue
            rest = t[len(f):]
            if (f == s and len(s) >= 4) or rest in SUFFIXES or (f != s and rest):
                return True
    return False


def number_words(n):
    if n == 0:
        return "sıfır"
    parts = []
    for value, name in ((10**9, "milyar"), (10**6, "milyon"), (1000, "bin")):
        q, n = divmod(n, value)
        if q:
            parts.append("bin" if value == 1000 and q == 1 else f"{number_words(q)} {name}")
    h, n = divmod(n, 100)
    if h:
        parts.append("yüz" if h == 1 else f"{ONES[h]} yüz")
    t, o = divmod(n, 10)
    if t:
        parts.append(TENS[t])
    if o:
        parts.append(ONES[o])
    return " ".join(parts)


def vowel_count(text):
    return sum(1 for c in text if c in VOWELS)


SYMBOL_WORDS = (("%", "yüzde"), ("₺", "lira"), ("$", "dolar"), ("€", "avro"))


def token_syllables(token):
    t = token.strip("-'’")
    if not t:
        return 0
    total = 0
    for sym, word in SYMBOL_WORDS:
        if sym in t:
            total += vowel_count(word)
            t = t.replace(sym, "")
    if not t:
        return total
    m = re.match(r"^(\d+)(?:,(\d+))?(.*)$", t)
    if m:
        total += vowel_count(number_words(int(m.group(1)[:12])))
        if m.group(2):
            total += 2 + vowel_count(number_words(int(m.group(2)[:12])))  # virgül
        rest = m.group(3).lstrip("'’.")
        if lower(rest) == "k":
            total += 1                                               # bin
        elif rest:
            total += max(1, vowel_count(rest))
        return total
    v = vowel_count(t)
    if v == 0:
        # Kısaltma: PDF, TL, dk. Harf harf okunur, harf başına bir hece.
        return total + max(1, len(t))
    return total + v


def syllables(text):
    return sum(token_syllables(w) for w in words(text))


def concrete(text):
    """Kontrol edilebilir şeyler: rakam, isim, okunan sayı, para."""
    nums = [n.strip() for n in NUMBER_RE.findall(text) if n.strip()]
    propers = set(PROPER_RE.findall(text))
    rest = NUMBER_RE.sub(" ", text)          # rakamla birlikte sayılanı tekrar sayma
    spoken = [w for w in words(rest)
              if not re.match(r"[\d$₺€%]", w)
              and (matches(w, SPOKEN_NUMBERS) or matches(w, MONEY_WORDS))]
    return nums, propers, spoken


def stem_key(token):
    """Döngü karşılaştırması için kaba kök: ilk beş harf."""
    t = base(token)
    return t[:5] if len(t) > 5 else t
