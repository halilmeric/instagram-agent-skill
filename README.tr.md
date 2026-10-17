# Instagram Ajanı (Türkçe)

Instagram hesabını yöneten 13 Claude skill'i. Ücretsiz, MIT lisanslı, kayıt yok,
API anahtarı yok, bağlanacak bir şey yok.

Bu depo, [Jake Schincariol'un instagram-agent-skill deposunun](https://github.com/Jakeschincariol/instagram-agent-skill)
Türkçeye uyarlanmış bir fork'udur. Orijinal araçlar İngilizce için yazılmıştı;
Türkçe bir metin verdiğinde süreleri, puanları ve uyarıları yanlış çıkıyordu.
Bu sürümde üç skill Türkçeyi kendisi algılıyor ve doğru ölçüyor. İngilizce
metinlerde davranış orijinalle birebir aynı.

**Hiçbir şey sen "evet" demeden paylaşılmaz.** Bu skill'ler yazar, sen paylaşırsın.

## Kurulum

Claude'a şunu yapıştır:

```
https://github.com/halilmeric/instagram-agent-skill

Bu skill'i kur, sonra /ig-reel çalışıyor mu kontrol et.
```

Ya da Claude Code'da kendin kur:

```bash
git clone https://github.com/halilmeric/instagram-agent-skill.git
cp -r instagram-agent-skill/skills/ig-* ~/.claude/skills/
```

Eklenti olarak:

```
/plugin marketplace add halilmeric/instagram-agent-skill
/plugin install instagram-agent
```

Sonra on dakikanı `templates/voice.md` dosyasına ayır. `~/.claude/instagram/voice.md`
olarak kopyalayıp doldur ya da Claude'a kendi Reels'lerinden üçünü gönderip
"voice.md dosyamı bunlardan yaz" de. Her skill bu dosyayı okur; senaryoları
yüksek sesle senin söyleyeceğin için burada her yerden daha önemli.

## 13 skill

| Aşama | Skill | Ne yapar | Türkçe |
| --- | --- | --- | --- |
| Araştır | `/ig-viral` | Nişinde şu an tutan Reels'leri bulur, hangi hook formülünü kullandığını adlandırır, örnek dosyası çıkarır | ✅ |
| Araştır | `/ig-profile` | Profilini 12 başlıkta 100 üzerinden puanlar, bio ve isim alanını yeniden yazar | |
| Araştır | `/ig-audit` | Paylaştıklarına bakar: ne tuttu, neden, neyi bırakmalısın | |
| Planla | `/ig-plan` | Haftalık takvim: ne, hangi formatta, hangi gün | |
| Planla | `/ig-repurpose` | Bir uzun içeriği (video, podcast) bir haftalık Reels ve carousel'e böler | |
| Üret | `/ig-reel` | Fikirden puanlı hook, konuşma metni, ekran yazısı ve saniye saniye zamanlama | ✅ |
| Üret | `/ig-carousel` | Kaydırtan kapak, slayt metinleri, 1080×1350 görseller | |
| Üret | `/ig-story` | Günün story dizisi, hangi çıkartma nerede | |
| Üret | `/ig-caption` | "...devamı" kesimini geçen açıklama, tek çağrı, en fazla üç hashtag | |
| Etkileşim | `/ig-comment` | Başkalarının gönderilerine bot gibi durmayan yorumlar | |
| Etkileşim | `/ig-reply` | Kendi yorumlarına cevaplar, önce cevaplanmaya değenler | |
| Etkileşim | `/ig-dm` | Cevap alan DM'ler ve takip mesajları | |
| Hepsi | `/ig-human` | Yazılan her metni yapay zeka izlerinden temizler ve beş kontrolle puanlar | ✅ |

✅ olmayan skill'ler Türkçe yazabilir, ama kontrollerini İngilizce kurallarla yapar.

## Türkçe uyarlamada neler var

### `/ig-reel`: hook puanı ve zamanlama

- **Süre heceden hesaplanır.** Türkçe sondan eklemeli bir dil: "kaybettiğimizi"
  tek kelime ama altı hece. Kelime saymak yanıltır. Türkçede hece sayısı ünlü
  sayısına eşit olduğu için sayım güvenilirdir. Varsayılan hız saniyede 5,5
  hece; kendini ölçtükten sonra `--sps` ile değiştir.
- **Rakamlar okunduğu gibi sayılır.** "18.000 TL" = "on sekiz bin lira",
  "%40" = "yüzde kırk", "2,5 saat" doğru ölçülür.
- **Eşleşme eklere duyarlıdır.** "kaybet" kökü "kaybettim"i, "eksik" kökü
  "eksiği"ni yakalar. Olumsuzluk fiilin içinden okunur ("yapmadım"). Emir kipi
  cümle sonunda da aranır ("haftada dört saat kazan").
- **Türkçe eleyiciler.** "Selam arkadaşlar", "bu videoda size göstereceğim",
  "kaydırmayı bırak" puanı keser.
- **26 hook formülünün tamamına Türkçe alanlar eklendi:** ad, şablon, örnek,
  ekran yazısı, ne için iyi olduğu, tuzağı. Örnekler çeviri değil, bir Türk
  içerik üreticisinin söyleyeceği gibi yeniden yazıldı.
- Çıktı Türkçedir: GÜÇLÜ / ORTA / ZAYIF.

```bash
python3 skills/ig-reel/hookscore.py hooks.txt            # dil otomatik algılanır
python3 skills/ig-reel/beats.py senaryo.txt --target 25 --sps 6
```

Örnek çıktı:

```
HOOK SIRALAMASI
->  81.4 GÜÇLÜ   Tek bir sözleşme eksiği bana 18.000 TL'ye mal oldu.
    55.8 ORTA    Kimse sana sözleşmesiz işin bedelini söylemiyor.
    54.2 ORTA    Bu iki sayfalık sözleşmeyi çal.
```

### `/ig-human`: Türkçe "yapay zeka kokan kelime" sözlüğü

`skills/ig-human/slop_tr.json`, Türkçe metinde otomatik olarak devreye girer.
İki katmanı vardır, çünkü İngilizcede güvenli olan kelime değiştirme Türkçede
dilbilgisini bozar ("gerçekleştirdim" → "yapdım"):

- **99 sabit kalıp otomatik değişir:** "son derece" → "çok", "bu bağlamda" →
  "bu yüzden", "nihayetinde" → "sonunda", "günümüzün hızla değişen dünyasında"
  → "şu an", "takip etmeyi unutmayın" silinir.
- **46 kök işaretlenir, değiştirilmez:** "gerçekleştirdim", "önemli bir rol
  oynuyor", "potansiyelini ortaya çıkar", "yolculuğum". Her birinin yanında bir
  öneri gelir; cümleyi sen yeniden yazarsın.
- **19 yapı kalıbı uyarı verir:** "sadece X değil, aynı zamanda Y", "hem X hem
  de Y", "Sonuç mu?", "Nasıl mı?", -mektedir / -maktadır, -malısınız, üçlü
  sıralama, video girizgâhı, roket emojisi, hashtag duvarı.
- **"Ses" kontrolü** İngilizce kısaltmalar yerine konuşma dili işaretlerine
  ("yani", "bak", "işte", "bi") ve fiil ekinden okunan kişiye ("yaptım",
  "yapıyorsun") bakar.

```bash
python3 skills/ig-human/humanize.py taslak.txt --report -o temiz.txt
python3 skills/ig-human/detect.py taslak.txt temiz.txt
```

### `/ig-viral`: Türkçe hook'ları tanıma

Toplanan Reels'lerin hook'ları artık Türkçe kurallarla da sınıflandırılır ve
Türkçe kurallarla puanlanır. 26 Türkçe örnek hook'un 26'sı doğru formüle düşüyor.

## Dürüst notlar

- **Ritim kontrolü Türkçede zayıf.** `detect.py`'deki cümle uzunluğu çeşitliliği
  Türkçede güvenilir bir sinyal değil; Türkçe cümleler daha az ama daha uzun
  kelime taşıdığı için doğal bir metin de düşük puan alabilir. Önce diğer dört
  kontrolü düzelt.
- **Puanlar bir kontrol, kehanet değil.** Hook puanı selamlamaları, girizgâhları
  ve somut hiçbir şey içermeyen açılışları yakalar. Hangi videonun tutacağını
  söyleyemez; onu yüzün, kurgun ve sesin belirler.
- **Orijinalden gelen bir hata:** `hooks.json` içindeki 6 İngilizce örnek
  (#7, #8, #11, #12, #14, #19) yanlış formüle sınıflanıyor. Bu, uyarlamadan
  önce de vardı ve henüz düzeltilmedi.

## Lisans ve emek

MIT. Orijinal paket [Jake Schincariol](https://opusjake.ai) tarafından yapıldı.
Türkçe uyarlama [halilmeric](https://github.com/halilmeric) tarafından yapıldı.

---

## For English readers

This fork adds Turkish support to three skills. Language is auto-detected
(`--lang tr` / `--lang en` to force it). English output is byte-for-byte
identical to upstream; this was checked by running old and new versions on
the same inputs.

- `ig-reel/trlang.py` (new): Turkish syllable counting (length is timed in
  syllables, not words), spoken-number expansion ("18.000" = "on sekiz bin"),
  suffix-aware stem matching with consonant softening, in-verb negation,
  clause-final imperatives, Turkish dealbreakers.
- `ig-reel/hookscore.py`, `ig-reel/beats.py`: Turkish mode and Turkish output.
- `ig-reel/hooks.json`: `*_tr` fields on all 26 formulas (name, template,
  example, on-screen line, best for, trap, `match_tr` regex), plus `note_tr`
  and `rules_tr`.
- `ig-human/trhuman.py`, `ig-human/slop_tr.json` (new): Turkish lexicon with
  auto-replaced fixed phrases, flag-only suffixing stems, and Turkish
  structural tells. `humanize.py` and `detect.py` switch to it automatically.
- `ig-viral/swipe.py`: classifies hooks with `match_tr` and scores them in
  Turkish mode.
