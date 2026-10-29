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


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_DOMAIN_WORDS = {"com", "org", "net", "co", "uk", "ng", "edu", "gov", "io", "mail", "info", "ac", "us",
                 "app", "dev", "yahoo", "gmail", "outlook", "hotmail", "icloud", "proton"}
_SEP_WORDS = {".": "dot", "_": "underscore", "-": "dash", "+": "plus"}


_WORDS = None


def _common_word(w: str) -> bool:
    global _WORDS
    if _WORDS is None:
        f = pathlib.Path(__file__).with_name("words.txt")
        _WORDS = set(f.read_text().split()) if f.exists() else set()
    return len(w) >= 4 and w.lower() in _WORDS


def say_email(addr: str) -> str:
    """jo.smith_92@mail.co.uk -> "J-O dot smith underscore 92 at mail dot co dot uk".
    Spelled letters stop TTS-1 turning "jo" into "joe" or "eze" into "easy"."""
    local, domain = addr.split("@", 1)
    out = []
    for side, part_s in (("local", local), ("domain", domain)):
        if side == "domain":
            out.append("at")
        for part in re.split(r"([._+-])", part_s):
            if not part:
                continue
            if part in _SEP_WORDS:
                out.append(_SEP_WORDS[part])
            elif part.isdigit():
                out.append(" ".join(part) if len(part) > 2 else part)
            elif (side == "domain" and part.lower() in _DOMAIN_WORDS) or _common_word(part):
                out.append(part.lower())  # real words are said; spelling them made STT drift
            else:
                out.append("-".join(part.upper()))
    return " ".join(out)


def heard_email(heard: str) -> str:
    """Fold a transcript's spoken or spelled email back into one compact lowercase string."""
    h = " " + heard.lower() + " "
    for w, c in ((" at ", "@"), (" dot ", "."), (" underscore ", "_"), (" dash ", "-"), (" hyphen ", "-"), (" plus ", "+")):
        h = h.replace(w, c)
    h = re.sub(r"\b([a-z0-9])[-,\s]+(?=[a-z0-9]\b)", r"\1", h)  # J-O / J, O / J O -> jo
    return re.sub(r"\s*([@._+-])\s*", r"\1", h)


def _spans(spoken: str, names: dict[str, str], emails: list[tuple[str, str]] = ()) -> list[Span]:
    toks = spoken.split()
    respelled = {v.lower(): k for k, v in names.items()}
    risky, taken, email_spans = [], set(), []
    for addr, said in emails:
        st = said.split()
        for a in range(len(toks) - len(st) + 1):
            if [t.rstrip(".,;:!?") for t in toks[a:a + len(st)]] == st and a not in taken:
                taken.update(range(a, a + len(st)))
                email_spans.append(Span(addr, (a, a + len(st)), ["email:" + addr.lower()], "email", name=addr))
                break
    for i, t in enumerate(toks):
        if i in taken:
            continue
        bare = t.strip(".,;:!?()\"'").lower()
        if re.search(r"\d", t) or re.search(r"[$€£¥₹]", t):
            risky.append((i, "number"))
        elif re.fullmatch(MONTHS, t.strip(".,"), re.I) and any(
                re.search(r"\d", x) for x in toks[max(0, i - 1):i + 2]):  # "May 10", not "we may switch"
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
            fr = re.findall(r"\d+/\d+", text)
            rest = re.sub(r"\b(\d{1,2}):00\b", r"\1", re.sub(r"\d+/\d+", " ", text))  # 8:00 PM == 8 PM
            # canon each token on its own so "10, 2025" stays two numbers, but keep
            # number groups that canon must join ("1,500.50", "1.500,50") within one token
            c = " ".join(canon(tok) for tok in rest.split())
            nums = [re.sub(r"\.0+$", "", n) for n in re.findall(r"\d+(?:\.\d+)?", c)]  # $35.00 is heard as $35
            exp = fr + nums + re.findall(MONTHS.lower(), c)
            cur = [w for sym, w in (("$", "dollar"), ("€", "euro"), ("£", "pound"), ("₹", "rupee"))
                   if sym in text or w in text.lower()]
            exp += [f"cur:{w}" for w in cur]
            m = re.match(r"^[-\u2212](\d+)", text)
            if m:
                exp.append("neg:" + m.group(1))  # "-5°C" must not be heard as "5°C"
            spans.append(Span(text, (a, b), exp, "date" if any(m in c for m in MONTHS.lower().split("|")) else kind))
        i = j
    return sorted(spans + email_spans, key=lambda x: x.tokens[0])


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
    emails = []
    if locale.lower().startswith("en"):
        for addr in dict.fromkeys(EMAIL_RE.findall(spoken)):
            said = say_email(addr)
            emails.append((addr, said))
            changes.append({"kind": "email_spelled", "at": spoken.find(addr), "found": addr,
                            "why": f'TTS-1 guesses at addresses; spell it: "{said}"'})
            spoken = spoken.replace(addr, said)
    warnings = []
    if voice:
        w = check_voice(voice, _lang(locale)[0])
        if w:
            warnings.append(w.detail)
    return Receipt(text, g.displayed, spoken, locale, changes, _spans(spoken, names, emails), warnings)


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


async def _tts_ws_async(text: str, voice: str, language: str, sr: int = 24000):
    import websockets
    url = f"wss://tts.us.assemblyai.com/v1/ws?voice_id={voice}&language={language}&sample_rate={sr}&encoding=pcm_s16le"
    pcm, words = bytearray(), []
    async with websockets.connect(url, additional_headers=_headers(), open_timeout=10) as ws:
        first = json.loads(await ws.recv())
        if first["type"] == "Error":
            raise RuntimeError(f"TTS ws: {first}")
        await ws.send(json.dumps({"type": "Generate", "text": text}))
        await ws.send(json.dumps({"type": "Flush"}))
        await ws.send(json.dumps({"type": "Terminate"}))
        async for raw in ws:
            m = json.loads(raw)
            if m["type"] == "Audio":
                pcm += base64.b64decode(m["audio"])
            elif m["type"] == "WordBoundaries":
                words = m["words"]
            elif m["type"] == "Termination":
                break
            elif m["type"] == "Error":
                raise RuntimeError(f"TTS ws: {m}")
    return bytes(pcm), words


def tts(text: str, voice: str, language: str, sr: int = 24000) -> tuple[bytes, list[dict], float, str]:
    """TTS-1 with word timings. WebSocket by default (SAYGUARD_TTS_TRANSPORT=ws|http);
    falls back to the HTTP events route if the network blocks WebSocket frames."""
    import asyncio
    t0 = time.perf_counter()
    if os.environ.get("SAYGUARD_TTS_TRANSPORT", "ws") == "ws":
        try:
            pcm, words = asyncio.run(asyncio.wait_for(_tts_ws_async(text, voice, language, sr), 20))
            if pcm:
                return pcm, words, (time.perf_counter() - t0) * 1000, "websocket"
        except Exception:
            pass
    pcm, words, ms = _tts_events(text, voice, language, sr)
    return pcm, words, (time.perf_counter() - t0) * 1000, "http"


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
    if span.kind == "email":
        return span.name.lower() in heard_email(heard)
    for e in [x for x in span.expect if x.startswith("cur:")]:
        w = e[4:]; sym = {"dollar": "$", "euro": "€", "pound": "£", "rupee": "₹"}[w]
        if sym not in heard and w not in heard.lower():
            return False
    for e in [x for x in span.expect if x.startswith("neg:")]:
        n = e[4:]
        if not re.search(rf"(?:[-\u2212]\s?|minus\s|negative\s){n}(?!\d)", heard, re.I):
            return False
    span = Span(span.text, span.tokens, [x for x in span.expect if not x.startswith(("cur:", "neg:"))], span.kind, span.name)
    heard = heard.replace("^", " to the power of ")
    heard = re.sub(r"(\d)\.00?(?!\d)", r"\1", heard)  # "$35.00" == "$35"
    heard = re.sub(r"\b(\d{1,2}):00\b", r"\1", heard)
    for h in (canon(heard), " ".join(canon(t) for t in heard.split())):
        if _match(span, heard, h):
            return True
    return False


def _match(span: Span, heard: str, h: str) -> bool:
    # h is the heard text canonicalised whole ("555 0132" joins) or token by token ("4, 2026" stays apart)
    hd = h.replace(" ", "")
    nums = [e for e in span.expect if not e.isalpha()]
    # only well-formed amounts like 1.500,50 / 1,500.50 / 1500,50 (not "1.50050" or "1.500.500")
    money_re = re.compile(r"^(\d{1,3}(?:[.,\u00a0 ]\d{3})+|\d+)[.,]\d{2}$")
    runs = [re.sub(r"\D", "", x) for x in re.findall(r"\d[\d.,]*\d|\d", heard) if money_re.match(x)]
    if nums and len(nums) > 1 and "".join(n.replace(".", "") for n in nums) in runs:
        nums = []  # "1500 Euro und 50 Cent" written back as "1.500,50 Euro"
    joined = "".join(n.replace(".", "") for n in nums if "/" not in n)
    runs_alnum = [re.sub(r"\D", "", x) for x in re.findall(r"[0-9A-Za-z]*\d[0-9A-Za-z]*", heard)]
    runs_alnum += [re.sub(r"\D", "", x) for x in re.findall(r"\+?\d[\d ()-]*\d", heard)]  # +44 207 946 0958
    if len(nums) > 1 and len(joined) >= 6 and joined in runs_alnum:
        nums = [n for n in nums if "/" in n]  # grouped digits run together: "GB29 5678 1234" -> "GB2956781234"
    fracs = [x for x in nums if "/" in x]
    nums = [x for x in nums if "/" not in x]
    for f in fracs:
        a, b = f.split("/")
        words = {"2": "half", "3": "third", "4": "quarter"}
        if f not in heard and not (a == "1" and words.get(b, "@") in heard.lower()):
            return False
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

    pcm, words, tts_ms, transport = tts(r.spoken, voice, tts_lang)
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
         "tts_ms": round(tts_ms), "tts_transport": transport, "stt_ms": round(stt_ms), "audio_ms": stt.get("audio_duration_ms"),
         "passed": all(s.ok for s in r.spans if s.ok is not None)}
    if compare_raw and r.original != r.spoken:
        raw_pcm, _, _, _ = tts(r.original, voice, tts_lang)
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
              f"TTS-1 voice `{v['voice']}` over {v.get('tts_transport','http')} ({v['tts_ms']} ms) -> Sync STT ({v['stt_ms']} ms). Caller heard: \"{v['heard']}\"", "",
              "| Span | Must hear | Spoken at | Heard there | Result |", "|---|---|---|---|---|"]
        for s in r.spans:
            at = f"{s.start_ms/1000:.2f}-{s.end_ms/1000:.2f}s" if s.start_ms is not None else "-"
            L.append(f"| {s.text} | {', '.join(s.expect)} | {at} | {s.heard or ''} | {'PASS' if s.ok else 'FAIL'} |")
        if "raw_heard" in v:
            L += ["", f"Without SayGuard the caller heard: \"{v['raw_heard']}\"",
                  f"Spans wrong without SayGuard: {', '.join(v['raw_failed_spans']) or 'none'}"]
    return "\n".join(L) + "\n"
