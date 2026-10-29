from __future__ import annotations
import base64, hashlib, json, os, pathlib, re, time, wave
from dataclasses import dataclass, field, asdict
import requests

from echoproof.guard import guard, check_voice
from echoproof.names import respell, heard_ok
from echoproof.numbers import canon
from echoproof.client import _headers

EVENTS_URL = "https://tts.us.assemblyai.com/v1/speech/events"
STT_URL = "https://sync.assemblyai.com/v1/transcribe"
LANG = {"en": ("english", "en"), "es": ("spanish", "es"), "de": ("german", "de"),
        "fr": ("french", "fr"), "pt": ("portuguese", "pt"), "it": ("italian", "it")}
MONTHS = r"January|February|March|April|May|June|July|August|September|October|November|December"
UNIT_WORDS = {"euro", "euros", "cent", "cents", "centesimi", "céntimos", "centimes", "centavos", "reais",
              "rupees", "dollars", "und", "e", "con", "et", "komma", "virgola", "coma", "virgule", "vírgula",
              "mg", "ml", "g", "µg", "units", "tablet"}
OUT = pathlib.Path(os.environ.get("SAYGUARD_OUT", "receipts"))


@dataclass
class Span:
    text: str
    tokens: tuple[int, int]          # token index range [a, b)
    expect: list[str]                # values the caller must hear
    kind: str
    name: str | None = None          # original spelling for respelled names
    start_ms: int | None = None
    end_ms: int | None = None
    heard: str | None = None
    ok: bool | None = None


@dataclass
class Receipt:
    original: str
    displayed: str
    spoken: str
    locale: str
    changes: list[dict]
    spans: list[Span]
    warnings: list[str] = field(default_factory=list)
    verification: dict | None = None

    def to_dict(self):
        d = asdict(self)
        return d


def _lang(locale: str) -> tuple[str, str]:
    return LANG.get(locale.lower()[:2], LANG["en"])


def _spans(spoken: str, names: dict[str, str]) -> list[Span]:
    toks = spoken.split()
    respelled = {v.lower(): k for k, v in names.items()}
    risky = []
    for i, t in enumerate(toks):
        bare = t.strip(".,;:!?()\"'").lower()
        if re.search(r"\d", t) or re.search(r"[$€£¥₹]", t):
            risky.append((i, "number"))
        elif re.fullmatch(MONTHS, t.strip(".,"), re.I):
            risky.append((i, "date"))
        elif re.search(r"[a-z]\.[a-z]{2,}", bare):
            risky.append((i, "domain"))
        elif bare in respelled:
            risky.append((i, "name"))
    spans, i = [], 0
    while i < len(risky):
        a, kind = risky[i]
        b = a + 1
        j = i + 1
        # glue "1500 Euro und 50 Cent", "March 4, 2026", "2 Komma 5 mg"
        while True:
            while b < len(toks) and toks[b].strip(".,").lower() in UNIT_WORDS and kind in ("number", "date"):
                b += 1
            if j < len(risky) and risky[j][0] == b and risky[j][1] in ("number", "date") and kind in ("number", "date"):
                b += 1; j += 1
                continue
            break
        text = " ".join(toks[a:b]).rstrip(".,;:!?")
        if kind == "name":
            nm = respelled[toks[a].strip(".,;:!?()\"'").lower()]
            spans.append(Span(text, (a, b), [nm], "name", name=nm))
        elif kind == "domain":
            spans.append(Span(text, (a, b), [toks[a].strip(".,;:!?").split(".")[0].lower()], "domain"))
        else:
            c = canon(text)
            exp = re.findall(r"\d+(?:\.\d+)?", c) + re.findall(MONTHS.lower(), c)
            spans.append(Span(text, (a, b), exp, "date" if any(m in c for m in MONTHS.lower().split("|")) else kind))
        i = j
    return spans


def sanitize(text: str, locale: str = "en-us", voice: str | None = None) -> Receipt:
    """Rewrite text so the voice says what the screen shows. Pure, offline, fast."""
    g = guard(text, locale)
    changes = [{"kind": f.kind, "at": f.index, "found": f.char, "why": f.detail} for f in g.findings]
    spoken = g.cleaned
    names = {}
    if locale.lower().startswith("en"):
        from echoproof.names import respell as _r
        import json as _j
        lexf = pathlib.Path(__file__).resolve().parent.parent / "echoproof" / "lexicon.json"
        lex = _j.loads(lexf.read_text()) if lexf.exists() else {}
        names = {k: v for k, v in lex.items() if re.search(rf"\b{re.escape(k)}\b", spoken)}
        for k, v in names.items():
            changes.append({"kind": "name_respelled", "at": spoken.find(k), "found": k, "why": f'TTS-1 mispronounces it; say "{v}"'})
        spoken = _r(spoken, names)
    warnings = []
    if voice:
        w = check_voice(voice, _lang(locale)[0])
        if w:
            warnings.append(w.detail)
    return Receipt(text, g.displayed, spoken, locale, changes, _spans(spoken, names), warnings)


def _tts_events(text: str, voice: str, language: str, sr: int = 24000) -> tuple[bytes, list[dict], float]:
    t0 = time.perf_counter()
    r = requests.post(EVENTS_URL, headers=_headers(), stream=True, timeout=120,
                      json={"text": text, "voice_id": voice, "language": language, "encoding": "pcm_s16le", "sample_rate": sr})
    if r.status_code != 200:
        raise RuntimeError(f"TTS {r.status_code}: {r.text[:300]}")
    pcm, words, ev = bytearray(), [], None
    for line in r.iter_lines(decode_unicode=True):
        if not line or line.startswith(":"):
            continue
        if line.startswith("event:"):
            ev = line[6:].strip()
        elif line.startswith("data:"):
            d = json.loads(line[5:])
            if ev == "Audio":
                pcm += base64.b64decode(d.get("audio") or d.get("data") or "")
            elif ev == "WordBoundaries":
                words = d["words"]
            elif ev == "Error":
                raise RuntimeError(f"TTS error: {d}")
    return bytes(pcm), words, (time.perf_counter() - t0) * 1000


def _wav(pcm: bytes, path: pathlib.Path, sr: int = 24000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)


def _stt(path: pathlib.Path, lang: str) -> tuple[dict, float]:
    t0 = time.perf_counter()
    cfg = json.dumps({"language_codes": [lang], "timestamps": True})
    r = requests.post(STT_URL, headers={**_headers(), "X-AAI-Model": "universal-3-5-pro"},
                      files={"audio": (path.name, path.read_bytes(), "audio/wav"), "config": (None, cfg, "application/json")}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"STT {r.status_code}: {r.text[:300]}")
    return r.json(), (time.perf_counter() - t0) * 1000


def _check(span: Span, heard: str) -> bool:
    if span.kind == "name":
        return heard_ok(span.name, heard)
    h = canon(heard)
    hd = h.replace(" ", "")
    nums = [e for e in span.expect if not e.isalpha()]
    # only well-formed amounts like 1.500,50 / 1,500.50 / 1500,50 (not "1.50050" or "1.500.500")
    money_re = re.compile(r"^(\d{1,3}(?:[.,\u00a0 ]\d{3})+|\d+)[.,]\d{2}$")
    runs = [re.sub(r"\D", "", x) for x in re.findall(r"\d[\d.,]*\d|\d", heard) if money_re.match(x)]
    if nums and len(nums) > 1 and "".join(n.replace(".", "") for n in nums) in runs:
        nums = []  # "1500 Euro und 50 Cent" written back as "1.500,50 Euro"
    for e in [x for x in span.expect if x.isalpha()] + nums:
        if e.isalpha():
            if e not in h.replace(" ", ""):
                return False
        elif not re.search(rf"(?<![\d.]){re.escape(e)}(?![\d]|\.\d)", h) and e not in re.findall(r"\d+(?:\.\d+)?", hd):
            return False
    return True


def verify(r: Receipt, voice: str = "aai-audrey", compare_raw: bool = True, pad_ms: int = 200) -> Receipt:
    """Speak the sanitized text with TTS-1, transcribe it with Sync STT, and check every
    risky span inside its own time window (TTS word timings x STT word timings).
    With compare_raw, also speak the original text so the receipt shows what the caller
    would have heard without SayGuard."""
    tts_lang, stt_lang = _lang(r.locale)
    rid = hashlib.sha256(f"{r.original}|{voice}|{r.locale}".encode()).hexdigest()[:10]
    d = OUT / rid; d.mkdir(parents=True, exist_ok=True)

    pcm, words, tts_ms = _tts_events(r.spoken, voice, tts_lang)
    _wav(pcm, d / "sayguard.wav")
    stt, stt_ms = _stt(d / "sayguard.wav", stt_lang)
    heard_words = stt.get("words", [])
    for s in r.spans:
        ws = [w for w in words[s.tokens[0]:s.tokens[1]] if w["end"] > w["start"]] or words[s.tokens[0]:s.tokens[1]]
        if not ws:
            continue
        s.start_ms, s.end_ms = ws[0]["start"], ws[-1]["end"]
        win = [w["text"] for w in heard_words if w["end"] >= s.start_ms - pad_ms and w["start"] <= s.end_ms + pad_ms]
        s.heard = " ".join(win)
        s.ok = _check(s, s.heard) or _check(s, stt.get("text", ""))  # window first; full text guards against timing drift
        if not _check(s, s.heard):
            s.heard += "  [matched in full transcript]" if s.ok else ""
    v = {"id": rid, "voice": voice, "audio": str(d / "sayguard.wav"), "heard": stt.get("text", ""),
         "tts_ms": round(tts_ms), "stt_ms": round(stt_ms), "audio_ms": stt.get("audio_duration_ms"),
         "passed": all(s.ok for s in r.spans if s.ok is not None)}
    if compare_raw and r.original != r.spoken:
        raw_pcm, _, _ = _tts_events(r.original, voice, tts_lang)
        _wav(raw_pcm, d / "raw.wav")
        raw, _ = _stt(d / "raw.wav", stt_lang)
        v["raw_audio"], v["raw_heard"] = str(d / "raw.wav"), raw.get("text", "")
        v["raw_failed_spans"] = [s.text for s in r.spans if not _check(s, raw.get("text", ""))]
    r.verification = v
    (d / "receipt.json").write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=1))
    (d / "receipt.md").write_text(render(r))
    return r


def render(r: Receipt) -> str:
    v = r.verification or {}
    L = [f"# SayGuard receipt {v.get('id', '')}", "",
         f"- Screen shows: **{r.displayed}**", f"- Agent sent: `{r.original.encode('unicode_escape').decode()}`",
         f"- SayGuard spoke: **{r.spoken}**", ""]
    if r.changes:
        L += ["## Changes", ""] + [f"- `{c['kind']}` {c['found']}: {c['why']}" for c in r.changes] + [""]
    if r.warnings:
        L += ["## Warnings", ""] + [f"- {w}" for w in r.warnings] + [""]
    if v:
        L += ["## Verified by AssemblyAI", "",
              f"TTS-1 voice `{v['voice']}` ({v['tts_ms']} ms) -> Sync STT ({v['stt_ms']} ms). Caller heard: \"{v['heard']}\"", "",
              "| Span | Must hear | Spoken at | Heard there | Result |", "|---|---|---|---|---|"]
        for s in r.spans:
            at = f"{s.start_ms/1000:.2f}-{s.end_ms/1000:.2f}s" if s.start_ms is not None else "-"
            L.append(f"| {s.text} | {', '.join(s.expect)} | {at} | {s.heard or ''} | {'PASS' if s.ok else 'FAIL'} |")
        if "raw_heard" in v:
            L += ["", f"Without SayGuard the caller heard: \"{v['raw_heard']}\"",
                  f"Spans wrong without SayGuard: {', '.join(v['raw_failed_spans']) or 'none'}"]
    return "\n".join(L) + "\n"
