"""Minimal AssemblyAI TTS-1 + Sync STT client with on-disk caching."""
from __future__ import annotations
import hashlib, json, os, pathlib, time
import requests

TTS_URL = "https://tts.us.assemblyai.com/v1/speech"
STT_URL = "https://sync.assemblyai.com/v1/transcribe"
CACHE = pathlib.Path(os.environ.get("ECHOPROOF_CACHE", "cache"))
_s = requests.Session()


def _headers() -> dict:
    key = os.environ.get("ASSEMBLYAI_API_KEY", "")
    return {"Authorization": key} if key else {}


def _key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:20]


def speak(text: str, voice: str = "aai-jane", language: str = "english") -> pathlib.Path:
    path = CACHE / "audio" / f"{_key(text, voice, language)}.wav"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"text": text, "voice_id": voice, "language": language, "container": "wav", "stream": False}
    for attempt in range(4):
        r = _s.post(TTS_URL, json=body, headers=_headers(), timeout=120)
        if r.status_code in (429, 503):
            time.sleep(int(r.headers.get("Retry-After", 2)) + attempt)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"TTS {r.status_code}: {r.text[:300]}")
        path.write_bytes(r.content)
        return path
    raise RuntimeError("TTS retries exhausted")


def transcribe(wav: pathlib.Path, lang: str = "en", keyterms: list[str] | None = None) -> dict:
    tag = "-kt" + _key(*keyterms)[:8] if keyterms else ""
    path = CACHE / "stt" / f"{wav.stem}-{lang}{tag}.json"
    if path.exists():
        return json.loads(path.read_text())
    path.parent.mkdir(parents=True, exist_ok=True)
    conf = {"language_codes": [lang], "timestamps": True}
    if keyterms:
        conf["keyterms_prompt"] = keyterms
    cfg = json.dumps(conf)
    for attempt in range(4):
        r = _s.post(STT_URL, headers={**_headers(), "X-AAI-Model": "universal-3-5-pro"},
                    files={"audio": (wav.name, wav.read_bytes(), "audio/wav"),
                           "config": (None, cfg, "application/json")}, timeout=120)
        if r.status_code in (429, 503):
            time.sleep(int(r.headers.get("Retry-After", 2)) + attempt)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"STT {r.status_code}: {r.text[:300]}")
        data = r.json()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
        return data
    raise RuntimeError("STT retries exhausted")
