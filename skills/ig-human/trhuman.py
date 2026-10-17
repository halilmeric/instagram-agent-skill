#!/usr/bin/env python3
"""
trhuman.py - humanize.py ve detect.py için Türkçe desteği.

Dil otomatik algılanır. Türkçe metinde:
  - sözlük slop_tr.json'dan gelir (görünmez karakter ve tipografi listesi ortak),
  - kalıplar Türkçe küçük harfe çevrilmiş metinde aranır (I -> ı, İ -> i),
  - ek almayan kalıplar otomatik değişir, ek alan kökler önerisiyle işaretlenir,
  - VOICE kontrolü İngilizce kısaltmalar yerine konuşma dili işaretlerine ve
    fiil eklerinden okunan kişiye bakar.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LEX_TR = os.path.join(HERE, "slop_tr.json")

TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
HINT_WORDS = {
    "ve", "bir", "bu", "şu", "için", "ama", "çok", "daha", "değil", "gibi",
    "şimdi", "artık", "yok", "ben", "sen", "biz", "siz", "ile", "ki", "hiç",
    "neden", "nasıl", "sonra", "önce", "kadar", "oldu", "olan",
}
UPPER = "A-ZÇĞİÖŞÜÂÎÛ"
LOWER = "a-zçğıöşüâîû"
WORD_RE = re.compile(rf"[{UPPER}{LOWER}0-9'’]+")
PROPER_RE = re.compile(rf"(?<![.!?]\s)(?<!^)\b[{UPPER}][{LOWER}]{{2,}}\b", re.MULTILINE)

# Konuşma dili işaretleri: yazıda az, ağızda çok.
COLLOQUIAL = {
    "yani", "işte", "bak", "bakın", "hani", "valla", "vallahi", "cidden",
    "resmen", "harbiden", "aynen", "mesela", "bi", "şey", "abi", "ya",
    "tamam", "peki", "hadi", "oha", "bile", "zaten", "hiç", "baya", "bayağı",
    "falan", "filan", "napıyorsun", "naber", "noldu", "değil mi",
}
PERSON_WORDS = {
    "ben", "benim", "bana", "beni", "bende", "benden", "biz", "bizim", "bize",
    "bizi", "sen", "senin", "sana", "seni", "sende", "senden", "siz", "sizin",
    "size", "sizi", "kendim", "kendin",
}
# Fiil ekinden okunan birinci ve ikinci şahıs: yaptım, yapıyorum, yapıyorsun...
PERSON_RE = re.compile(
    r"(?:d[ıiuü]m|t[ıiuü]m|d[ıiuü]k|t[ıiuü]k|yorum|yoruz|yorsun|yorsunuz"
    r"|[ae]c[ae]ğ[ıi]m|[ae]c[ae]ks[ıi]n|d[ıiuü]n|t[ıiuü]n|d[ıiuü]n[ıiuü]z"
    r"|m[ae]l[ıi]s[ıi]n|[ae]b[ıi]l[ıi]rs[ıi]n|ırım|irim|urum|ürüm)$")


def lower(text):
    """Türkçe küçük harf, uzunluğu korur: I -> ı, İ -> i."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def detect(text, lang="auto"):
    if lang in ("tr", "en"):
        return lang
    if any(c in TR_CHARS for c in text):
        return "tr"
    toks = set(re.findall(r"\w+", lower(text)))
    return "tr" if toks & HINT_WORDS else "en"


def load(path=LEX_TR):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def words(text):
    return WORD_RE.findall(text)


def _phrase_re(find):
    body = re.escape(find).replace(r"\ ", r"\s+")
    return re.compile(r"(?<!\w)" + body + r"(?!\w)")


def _stem_re(find):
    body = re.escape(find).replace(r"\ ", r"\s+")
    return re.compile(r"(?<!\w)" + body + r"\w*")


def slop_hits(text, lex):
    """Ek almayan kalıplar ve ek alan kökler için (bulunan, sayı) listesi."""
    low = lower(text)
    found = []
    for entry in lex["words"] + lex["phrases"]:
        n = len(_phrase_re(entry["find"]).findall(low))
        if n:
            found.append((entry["find"], n))
    for entry in lex.get("stems", []):
        n = len(_stem_re(entry["find"]).findall(low))
        if n:
            found.append((entry["find"], n))
    return found


def match_case(src, repl):
    if not repl:
        return repl
    if src.isupper() and len(src) > 1:
        return repl.upper().replace("i", "İ")
    if src[0].isupper():
        first = "İ" if repl[0] == "i" else ("I" if repl[0] == "ı" else repl[0].upper())
        return first + repl[1:]
    return repl


def replace_phrases(text, lex):
    """Ek almayan kalıpları değiştir. Eşleşme küçük harfli kopyada aranır,
    değişiklik aynı konumda asıl metne uygulanır (lower() uzunluğu korur)."""
    hits = []
    entries = sorted(lex["phrases"] + lex["words"], key=lambda e: len(e["find"]), reverse=True)
    for entry in entries:
        pattern = _phrase_re(entry["find"])
        spans = [m.span() for m in pattern.finditer(lower(text))]
        if not spans:
            continue
        hits.append({"find": entry["find"], "replace": entry["replace"] or "(silindi)",
                     "count": len(spans), "family": entry["family"]})
        for a, b in reversed(spans):
            text = text[:a] + match_case(text[a:b], entry["replace"]) + text[b:]
    return text, hits


def flag_stems(text, lex):
    low = lower(text)
    out = []
    for entry in lex.get("stems", []):
        found = _stem_re(entry["find"]).findall(low)
        if found:
            out.append({"find": entry["find"], "suggest": entry["suggest"],
                        "count": len(found), "seen": sorted(set(found))[:3],
                        "family": entry["family"]})
    return out


def scan_structures(text, lex):
    low = lower(text)
    flags = []
    for s in lex["structures"]:
        try:
            pattern = re.compile(s["regex"], re.MULTILINE)
        except re.error:
            continue
        found = pattern.findall(text if s.get("raw") else low)
        if found:
            flags.append({"id": s["id"], "name": s["name"], "count": len(found), "fix": s["fix"]})
    return flags


def voice_counts(text):
    """(konuşma dili işareti, kişi işareti) sayıları."""
    low = lower(text)
    toks = [re.split(r"['’]", t)[0] for t in words(low)]
    colloquial = sum(1 for t in toks if t in COLLOQUIAL)
    colloquial += len(re.findall(r"\bdeğil mi\b", low))
    person = sum(1 for t in toks if t in PERSON_WORDS or (len(t) > 3 and PERSON_RE.search(t)))
    return colloquial, person
