#!/usr/bin/env python3
"""
beats.py - turn a Reel script into a timed beat sheet before you record it.

Estimates how long each line takes to say, stacks them into timecodes, and
flags the four things that kill a Reel in the edit: a hook that runs past the
three-second mark, a beat long enough for the viewer to leave, a run of lines
with nothing concrete in them, and a total length that does not match what you
said you were making.

The timings are an estimate from word count at a words-per-minute rate. They
are close enough to plan an edit and not a substitute for recording it. Set
your own rate with --wpm once you have timed yourself reading a script out
loud: most people land between 150 and 200, and the default here is 165.

Türkçe: dil otomatik algılanır (ya da --lang tr). Türkçede süre kelimeden
değil heceden hesaplanır, çünkü sondan eklemeli bir dilde kelime uzunluğu çok
değişir. Rakamlar okunduğu gibi sayılır ("18.000" = "on sekiz bin"). Varsayılan
hız saniyede 5.5 hece; kendini ölçtükten sonra --sps ile ayarla. Notlar
Türkçe yazılır.

Usage
  python3 beats.py script.txt
  python3 beats.py script.txt --target 30
  python3 beats.py script.txt --wpm 185 --target 45
  python3 beats.py senaryo.txt --lang tr --sps 6 --target 30
  pbpaste | python3 beats.py -
  python3 beats.py script.txt --json
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trlang  # noqa: E402

WORD_RE = re.compile(r"[A-Za-z0-9$%'’-]+")
SENT_RE = re.compile(r"[^.!?]+[.!?]*")
CONCRETE_RE = re.compile(r"\$\s?\d|\b\d[\d,.]*\b|(?<!^)\b[A-Z][a-z]{2,}\b", re.MULTILINE)
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "that", "this", "it", "is", "are", "was", "were", "be", "been",
    "you", "your", "i", "my", "me", "we", "our", "they", "them", "he", "she",
    "so", "just", "not", "no", "do", "did", "does", "have", "has", "had",
    "will", "can", "at", "as", "by", "from", "out", "up", "off", "one", "all",
}

HOOK_WINDOW = 3.0        # seconds. Past this, the thumb has already decided.
MAX_BEAT = 4.0           # seconds on one idea with no change on screen.
ABSTRACT_RUN = 3         # beats in a row with nothing checkable in them.
TR_SPS = 5.5             # Türkçe konuşma hızı, hece/saniye.


def words(text):
    # "$18,000" is one word when it is spoken, so it is one word here too.
    return WORD_RE.findall(re.sub(r"(?<=\d),(?=\d)", "", text))


def pretty(token):
    """Put the thousands separator back for display."""
    return re.sub(r"(\d)(?=(\d{3})+$)", r"\1,", token)


def tc(seconds):
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:04.1f}"


class English:
    code = "en"

    def __init__(self, wpm):
        self.rate = wpm / 60.0          # words per second

    def units(self, text):
        return len(words(text))

    def concrete(self, text):
        return len(CONCRETE_RE.findall(text))

    def loop(self, first, last):
        a = {w.lower() for w in words(first) if w.lower() not in STOPWORDS}
        b = {w.lower() for w in words(last) if w.lower() not in STOPWORDS}
        return sorted(pretty(w) for w in a & b)


class Turkish:
    code = "tr"

    def __init__(self, sps):
        self.rate = sps                 # syllables per second

    def units(self, text):
        return trlang.syllables(text)

    def concrete(self, text):
        nums, propers, spoken = trlang.concrete(text)
        return len(nums) + len(propers) + len(spoken)

    def loop(self, first, last):
        def keys(text):
            out = {}
            for w in trlang.words(text):
                b = trlang.base(w)
                if b and b not in trlang.STOPWORDS and len(b) > 1:
                    out.setdefault(trlang.stem_key(w), b)
            return out
        a, b = keys(first), keys(last)
        return sorted(re.sub(r"(\d)(?=(\d{3})+$)", r"\1.", a[k]) for k in a.keys() & b.keys())


def split_beats(raw, lang):
    """One line is one beat, unless a line is too long to be one."""
    beats = []
    for line in [l.strip() for l in raw.splitlines()]:
        if not line:
            continue
        if lang.units(line) / lang.rate <= MAX_BEAT * 1.5:
            beats.append(line)
            continue
        # Long paragraph: break it at sentence ends so the timings mean
        # something, and let the report say it was split.
        parts = [p.strip() for p in SENT_RE.findall(line) if p.strip()]
        buf = ""
        for part in parts:
            candidate = (buf + " " + part).strip()
            if buf and lang.units(candidate) / lang.rate > MAX_BEAT:
                beats.append(buf)
                buf = part
            else:
                buf = candidate
        if buf:
            beats.append(buf)
    return beats


MSG = {
    "en": {
        "hook_flag": "hook runs {d:.1f}s, past the {w:.0f}s mark",
        "hook_note": "Beat 1 takes {d:.1f}s to say. Cut it to {n} words or fewer, or the hook "
                     "lands after the decision has been made.",
        "hook_abstract": "Beat 1 has no number and no name in it. Hooks without something "
                         "checkable are the ones that get scrolled.",
        "beat_flag": "{d:.1f}s on one beat",
        "long_note": "Beat(s) {b} run past {m:.0f}s. Either split the line or change what is on "
                     "screen inside it. A static frame is where people leave.",
        "abstract_note": "Beats {a}-{b} have nothing concrete in them. "
                         "Put a number, a name or a price in one of them.",
        "loop_yes": "Loops: the last beat repeats \"{w}\" from the hook. "
                    "Second watches are free reach.",
        "loop_no": "No loop. The last beat shares no word with the hook, so the video "
                   "ends flat. Echoing one word from beat 1 is the cheapest replay you get.",
        "on_target": "Length is on target ({t:.1f}s against {g}s).",
        "over": "{d:.1f}s over target. Cut about {n} words.",
        "under": "{d:.1f}s under target. Either add {n} words or shoot it short. "
                 "Short is usually right.",
        "empty": "empty script",
    },
    "tr": {
        "hook_flag": "hook {d:.1f}sn sürüyor, {w:.0f}sn sınırını geçiyor",
        "hook_note": "Beat 1'i söylemek {d:.1f}sn sürüyor. {n} heceye ya da daha azına indir, "
                     "yoksa hook karar verildikten sonra yetişir.",
        "hook_abstract": "Beat 1'de sayı da isim de yok. Kontrol edilebilir bir şey içermeyen "
                         "hook'lar kaydırılıp geçilenlerdir.",
        "beat_flag": "tek beat'te {d:.1f}sn",
        "long_note": "Beat {b} {m:.0f}sn'yi geçiyor. Cümleyi böl ya da içinde ekrandaki "
                     "görüntüyü değiştir. Sabit kare, izleyicinin çıktığı yerdir.",
        "abstract_note": "Beat {a}-{b} arasında somut hiçbir şey yok. "
                         "Birine sayı, isim ya da fiyat koy.",
        "loop_yes": "Döngü var: son beat hook'taki \"{w}\" {k} tekrarlıyor. "
                    "İkinci izlenme bedava erişimdir.",
        "loop_no": "Döngü yok. Son beat hook'la hiçbir kelime paylaşmıyor, video düz biter. "
                   "Beat 1'den tek bir kelimeyi yankılamak en ucuz tekrar izlenmedir.",
        "on_target": "Süre hedefte ({t:.1f}sn, hedef {g}sn).",
        "over": "Hedefin {d:.1f}sn üzerinde. Yaklaşık {n} hece kes.",
        "under": "Hedefin {d:.1f}sn altında. Ya {n} hece ekle ya da kısa çek. "
                 "Kısa olan genelde doğrudur.",
        "empty": "senaryo boş",
    },
}


def fmt_target(t):
    return f"{t:g}"


def analyse(raw, wpm=165, target=None, lang="auto", sps=TR_SPS):
    code = trlang.detect(raw, lang)
    L = Turkish(sps) if code == "tr" else English(wpm)
    M = MSG[code]
    beats = split_beats(raw, L)
    if not beats:
        return None

    rows, clock = [], 0.0
    for i, text in enumerate(beats):
        units = L.units(text)
        dur = units / L.rate
        row = {
            "n": i + 1,
            "start": round(clock, 2),
            "dur": round(dur, 2),
            "words": len(trlang.words(text)) if code == "tr" else units,
            "text": text,
            "concrete": L.concrete(text),
            "label": "",
            "flags": [],
        }
        if code == "tr":
            row["syllables"] = units
        rows.append(row)
        clock += dur
    total = clock

    # Label the structural positions a Reel is actually built around.
    for r in rows:
        if r["n"] == 1 or r["start"] + r["dur"] <= HOOK_WINDOW:
            r["label"] = "HOOK"
    rows[-1]["label"] = "CTA" if rows[-1]["label"] != "HOOK" else "HOOK/CTA"
    half = total / 2
    for r in rows:
        if not r["label"] and r["start"] <= half < r["start"] + r["dur"]:
            r["label"] = "MID"

    notes = []
    if rows[0]["dur"] > HOOK_WINDOW:
        rows[0]["flags"].append(M["hook_flag"].format(d=rows[0]["dur"], w=HOOK_WINDOW))
        notes.append(M["hook_note"].format(d=rows[0]["dur"], n=int(HOOK_WINDOW * L.rate)))
    if rows[0]["concrete"] == 0:
        notes.append(M["hook_abstract"])

    for r in rows:
        if r["dur"] > MAX_BEAT:
            r["flags"].append(M["beat_flag"].format(d=r["dur"]))
    long_beats = [r["n"] for r in rows if r["dur"] > MAX_BEAT]
    if long_beats:
        notes.append(M["long_note"].format(b=", ".join(map(str, long_beats)), m=MAX_BEAT))

    run, start = 0, None
    for r in rows:
        if r["concrete"] == 0:
            run += 1
            start = start if start is not None else r["n"]
            if run == ABSTRACT_RUN:
                notes.append(M["abstract_note"].format(a=start, b=r["n"]))
        else:
            run, start = 0, None

    # Does the last line hand you back to the first one?
    loop = L.loop(rows[0]["text"], rows[-1]["text"])
    if loop:
        notes.append(M["loop_yes"].format(w=", ".join(loop[:3]),
                                          k="kelimesini" if len(loop) == 1 else "kelimelerini"))
    else:
        notes.append(M["loop_no"])

    if target:
        delta = total - target
        if abs(delta) <= target * 0.1:
            notes.append(M["on_target"].format(t=total, g=fmt_target(target) if code == "tr" else target))
        elif delta > 0:
            notes.append(M["over"].format(d=delta, n=int(delta * L.rate)))
        else:
            notes.append(M["under"].format(d=-delta, n=int(-delta * L.rate)))

    result = {
        "wpm": wpm, "target": target,
        "total_seconds": round(total, 2),
        "total_words": sum(r["words"] for r in rows),
        "beats": rows,
        "notes": notes,
    }
    if code == "tr":
        result = {"lang": "tr", "sps": sps, **result,
                  "total_syllables": sum(r["syllables"] for r in rows)}
        result.pop("wpm")
    return result


def render(a, out=sys.stdout):
    if a.get("lang") == "tr":
        head = (f"BEAT SHEET  ·  {a['total_words']} kelime, {a['total_syllables']} hece  ·  "
                f"~{a['total_seconds']:.1f}sn, saniyede {a['sps']:g} hece"
                + (f"  ·  hedef {fmt_target(a['target'])}sn" if a["target"] else ""))
        unit = "sn"
    else:
        head = (f"BEAT SHEET  ·  {a['total_words']} words  ·  ~{a['total_seconds']:.1f}s "
                f"at {a['wpm']:g} wpm" + (f"  ·  target {a['target']}s" if a["target"] else ""))
        unit = "s"
    print("\n" + head, file=out)
    print("=" * max(len(head), 72), file=out)
    for r in a["beats"]:
        label = f"{r['label']:<8}" if r["label"] else " " * 8
        print(f"  {tc(r['start'])}  {r['dur']:4.1f}{unit:<2} {label}{r['text']}"
              if unit == "sn" else
              f"  {tc(r['start'])}  {r['dur']:4.1f}s  {label}{r['text']}", file=out)
        for f in r["flags"]:
            print(f"  {'':>6}  {'':>5}  {'':<8}^ {f}", file=out)
    print("-" * max(len(head), 72), file=out)
    for n in a["notes"]:
        print(f"  - {n}", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Time a Reel script into a beat sheet.")
    ap.add_argument("input", nargs="?", default="-", help="script file, or - for stdin")
    ap.add_argument("--wpm", type=float, default=165, help="speaking rate (default 165)")
    ap.add_argument("--sps", type=float, default=TR_SPS,
                    help="Türkçe konuşma hızı, hece/saniye (varsayılan 5.5)")
    ap.add_argument("--lang", choices=["auto", "en", "tr"], default="auto",
                    help="script language (default: auto-detect)")
    ap.add_argument("--target", type=float, help="target length in seconds")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    a = analyse(raw, wpm=args.wpm, target=args.target, lang=args.lang, sps=args.sps)
    if not a:
        print(MSG[trlang.detect(raw, args.lang)]["empty"], file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    sys.exit(0)


if __name__ == "__main__":
    main()
