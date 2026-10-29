"""SayGuard live tester. Every result is real: the text goes to AssemblyAI TTS-1 twice
(as written, and after SayGuard), and AssemblyAI Sync STT reports what a caller hears."""
from __future__ import annotations
import base64, io, json, pathlib, tempfile, wave
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sayguard.core import sanitize, tts, _stt, _check, _lang

HERE = pathlib.Path(__file__).parent
EXAMPLES = json.loads((HERE / "examples.json").read_text())
VOICES = {"en": "aai-audrey", "es": "aai-constanza", "de": "aai-jorg", "fr": "aai-donatien",
          "pt": "aai-benicio", "it": "aai-jane"}
MAX_CHARS = 1000

app = FastAPI()
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES, "voices": VOICES}


class Check(BaseModel):
    text: str
    locale: str = "en-us"
    voice: str | None = None


def _show_hidden(t: str) -> str:
    """Make invisible and direction characters visible; leave °, ½, ₹ and accents as they are."""
    import unicodedata
    return "".join(f"\\u{ord(ch):04x}" if unicodedata.category(ch) in ("Cf", "Cc", "Co", "Zl", "Zp")
                   or (unicodedata.category(ch) == "Zs" and ch != " ") else ch for ch in t)


def _wav(pcm: bytes, sr=24000) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)
    return b.getvalue()


def _speak_and_hear(text: str, voice: str, locale: str) -> dict:
    tl, sl = _lang(locale)
    pcm, words, tts_ms, transport = tts(text, voice, tl)
    data = _wav(pcm)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(data); path = pathlib.Path(f.name)
    try:
        heard, stt_ms = _stt(path, sl)
    finally:
        path.unlink(missing_ok=True)
    return {"audio": base64.b64encode(data).decode(), "words": words, "heard": heard.get("text", ""),
            "heard_words": heard.get("words", []), "tts_ms": round(tts_ms), "stt_ms": round(stt_ms),
            "transport": transport}


@app.post("/api/check")
def check(c: Check):
    try:
        return _check_text(c)
    except Exception as e:  # show the real reason instead of a bare 500
        if "429" in str(e):
            return JSONResponse({"error": "Too many people testing at once: AssemblyAI TTS-1 allows 50 voice requests a minute on this key. Try again in about 30 seconds."}, status_code=429)
        return JSONResponse({"error": f"{type(e).__name__}: {str(e)[:200]}"}, status_code=502)


def _check_text(c: Check):
    text = c.text.strip()
    if not text:
        return JSONResponse({"error": "Type or pick a sentence first."}, status_code=400)
    if len(text) > MAX_CHARS:
        return JSONResponse({"error": f"Keep it under {MAX_CHARS} characters."}, status_code=400)
    lang = c.locale.lower()[:2]
    voice = c.voice or VOICES.get(lang, "aai-audrey")
    r = sanitize(text, c.locale, voice)
    with ThreadPoolExecutor(2) as pool:
        raw_f = pool.submit(_speak_and_hear, r.original, voice, c.locale)
        safe_f = pool.submit(_speak_and_hear, r.spoken, voice, c.locale) if r.spoken != r.original else None
        raw = raw_f.result()
        safe = safe_f.result() if safe_f else raw
    spans = []
    for s in r.spans:
        row = {"text": s.name or s.text, "kind": s.kind,
               "expect": [e[4:] + "s" if e.startswith("cur:") else e for e in s.expect]}
        if safe["words"]:
            ws = [w for w in safe["words"][s.tokens[0]:s.tokens[1]]
                  if w.get("end") is not None and w.get("start") is not None and w["end"] > w["start"]]
            if ws:
                a, b = ws[0]["start"], ws[-1]["end"]
                row["at"] = [a, b]
                row["heard_safe"] = " ".join(w["text"] for w in safe["heard_words"]
                                             if w.get("end", -1) >= a - 200 and w.get("start", 10**9) <= b + 200)
        row["ok_safe"] = _check(s, row.get("heard_safe", "")) or _check(s, safe["heard"])
        row["ok_raw"] = _check(s, raw["heard"])
        spans.append(row)
    strip = lambda d: {k: v for k, v in d.items() if k not in ("words", "heard_words")}
    return {"text": r.original, "escaped": _show_hidden(r.original),
            "displayed": r.displayed, "spoken": r.spoken, "unchanged": r.spoken == r.original,
            "changes": r.changes, "warnings": r.warnings, "spans": spans, "voice": voice, "locale": c.locale,
            "raw": strip(raw), "safe": strip(safe),
            "raw_ok": all(x["ok_raw"] for x in spans), "safe_ok": all(x["ok_safe"] for x in spans)}
