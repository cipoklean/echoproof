"""Second, independent transcriber (local faster-whisper) to separate TTS faults from STT faults."""
from __future__ import annotations
import json, pathlib, wave
import numpy as np

_model = None


def _load(path: pathlib.Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        sr, n = w.getframerate(), w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    if sr != 16000:  # linear resample (avoids PyAV)
        x = np.linspace(0, len(a), int(len(a) * 16000 / sr), endpoint=False)
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    return a


def whisper(path: pathlib.Path, lang: str) -> str:
    global _model
    out = path.parent.parent / "whisper" / f"{path.stem}-{lang}.json"
    if out.exists():
        return json.loads(out.read_text())["text"]
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = _model.transcribe(_load(path), language=lang, beam_size=5)
    text = " ".join(s.text.strip() for s in segs)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"text": text}, ensure_ascii=False))
    return text
