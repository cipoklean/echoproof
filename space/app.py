"""EchoProof bank line: talk to a voice agent built entirely on AssemblyAI
(Sync STT -> LLM Gateway -> SayGuard -> TTS-1 -> Sync STT check)."""
from __future__ import annotations
import base64, io, json, os, pathlib, tempfile, time, wave
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sayguard.core import sanitize, tts, _stt, _check, _lang, _headers, render

LLM_URL = "https://llm-gateway.assemblyai.com/v1/chat/completions"
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma-4-31b")
HERE = pathlib.Path(__file__).parent

# Each record is what the bank's backend holds. Attacker-controlled fields carry the trick;
# the browser renders them exactly as a real banking screen would.
SCENARIOS = {
    "invoice": {"title": "Pay an invoice", "locale": "en-gb", "voice": "aai-audrey", "caller": "UK customer",
                "record": {"Payee": "Aoife Byrne", "Amount": "$\u202e00001\u202c", "Due date": "03/04/2026",
                           "Reference": "INV-2291"},
                "trick": "The invoice amount was written with a hidden right-to-left mark. Screens show $10000; the characters run 0,0,0,0,1.",
                "ask": "Can you confirm the payment I'm about to make?"},
    "clinic": {"title": "Confirm an appointment", "locale": "en-ng", "voice": "aai-audrey", "caller": "Nigerian patient",
               "record": {"Doctor": "Dr Oluwaseun Adeyemi", "Date": "05/06/2026", "Verification code": "\u0663\u0667\u0662\u0669"},
               "trick": "Day-first date for a Nigerian caller, a Yoruba name, and a code typed with Arabic-Indic digits.",
               "ask": "When is my appointment and what's my code?"},
    "pharmacy": {"title": "Prescription refill", "locale": "en-us", "voice": "aai-audrey", "caller": "Pharmacy patient",
                 "record": {"Medicine": "Warfarin", "Dose": "\u00bd tablet twice a day", "Refill code": "\uff11\uff12\uff18\uff14"},
                 "trick": "A half written as the single character \u00bd, and a refill code pasted in full-width digits.",
                 "ask": "How much should I take, and what's my refill code?"},
}

app = FastAPI()
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


@app.get("/api/scenarios")
def scenarios():
    return SCENARIOS


class Turn(BaseModel):
    scenario: str
    sayguard: bool = True
    text: str | None = None
    audio_b64: str | None = None   # 16 kHz mono wav from the browser mic
    history: list[dict] = []


def _llm(sc: dict, history: list[dict], user: str) -> tuple[str, float]:
    sys_prompt = ("You are the phone agent for Northwind Bank. The customer is looking at this record on their screen. "
                  "Answer from the record, copying every value exactly as written in it. Two short sentences, no markdown.\n"
                  "RECORD: " + json.dumps(sc["record"], ensure_ascii=False))
    msgs = [{"role": "system", "content": sys_prompt}] + history[-6:] + [{"role": "user", "content": user}]
    t0 = time.perf_counter()
    r = requests.post(LLM_URL, headers=_headers(), json={"model": LLM_MODEL, "messages": msgs, "max_tokens": 200}, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), (time.perf_counter() - t0) * 1000


def _wav_bytes(pcm: bytes, sr=24000) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)
    return b.getvalue()


def _speak_and_hear(text: str, voice: str, locale: str) -> dict:
    tl, sl = _lang(locale)
    pcm, words, tts_ms, transport = tts(text, voice, tl)
    data = _wav_bytes(pcm)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(data); path = pathlib.Path(f.name)
    heard, stt_ms = _stt(path, sl)
    path.unlink(missing_ok=True)
    return {"audio": base64.b64encode(data).decode(), "words": words, "heard": heard.get("text", ""),
            "heard_words": heard.get("words", []), "tts_ms": round(tts_ms), "stt_ms": round(stt_ms), "transport": transport}


@app.post("/api/turn")
def turn(t: Turn):
    sc = SCENARIOS[t.scenario]
    timings = {}
    user = (t.text or "").strip()
    if t.audio_b64:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(base64.b64decode(t.audio_b64)); path = pathlib.Path(f.name)
        res, timings["caller_stt_ms"] = _stt(path, "en")
        path.unlink(missing_ok=True)
        user = res.get("text", "").strip()
    if not user:
        return JSONResponse({"error": "I didn't catch that."}, status_code=400)
    reply, timings["llm_ms"] = _llm(sc, t.history, user)
    r = sanitize(reply, sc["locale"], sc["voice"])
    text = r.spoken if t.sayguard else r.original
    out = _speak_and_hear(text, sc["voice"], sc["locale"])
    timings["tts_ms"], timings["check_stt_ms"] = out["tts_ms"], out["stt_ms"]
    spans = []
    for s in r.spans:
        row = {"text": s.name or s.text, "kind": s.kind, "expect": s.expect}
        if t.sayguard and out["words"]:
            ws = [w for w in out["words"][s.tokens[0]:s.tokens[1]] if w["end"] > w["start"]]
            if ws:
                a, b = ws[0]["start"], ws[-1]["end"]
                row["at"] = [a, b]
                row["heard"] = " ".join(w["text"] for w in out["heard_words"] if w["end"] >= a - 200 and w["start"] <= b + 200)
        row["ok"] = _check(s, row.get("heard", "")) or _check(s, out["heard"])
        spans.append(row)
    return {"user": user, "reply_raw": r.original, "reply_escaped": r.original.encode("unicode_escape").decode(),
            "spoken": text, "sayguard": t.sayguard, "changes": r.changes if t.sayguard else [],
            "warnings": r.warnings, "spans": spans, "heard": out["heard"], "audio": out["audio"],
            "transport": out["transport"], "timings": timings, "llm": LLM_MODEL,
            "passed": all(x["ok"] for x in spans)}
