"""Run the matrix: case x voice x (raw, guarded) -> TTS-1 -> STT -> compare.

Raw failures get a second opinion from local Whisper. If both transcribers miss the
same value, the fault is most likely in the speech itself (TTS-1), not the transcriber.
"""
from __future__ import annotations
import argparse, json, pathlib, re
from concurrent.futures import ThreadPoolExecutor
from .cases import CASES, LANGS
from .client import speak, transcribe
from .guard import guard
from .numbers import canon


def _hit(x: str, h: str) -> bool:
    core = canon(x).replace(" ", "")
    pat = r"(?<!\d)" + r"\s*".join(re.escape(ch) for ch in core) + r"(?!\d)"
    return re.search(pat, h) is not None


def missing(expect: list[str], heard: str) -> list[str]:
    h = canon(heard)
    # "a|b" means either form is fine; digits must match whole numbers, not substrings
    return [e for e in expect if not any(_hit(x, h) for x in e.split("|"))]


def one(c: dict, voice: str) -> dict:
    tts_lang, stt_lang, _ = LANGS[c["lang"]]
    g = guard(c["text"])
    row = {"id": c["id"], "lang": c["lang"], "cat": c["cat"], "voice": voice, "text": c["text"],
           "displayed": g.displayed, "findings": [f.kind for f in g.findings], "expect": c["expect"], "note": c["note"]}
    for mode, text in (("raw", c["text"]), ("guarded", g.cleaned)):
        try:
            wav = speak(text, voice=voice, language=tts_lang)
            heard = transcribe(wav, stt_lang).get("text", "")
            m = missing(c["expect"], heard)
            row[mode] = {"sent": text, "audio": str(wav), "heard": heard, "missing": m, "pass": not m}
        except Exception as e:
            row[mode] = {"sent": text, "error": str(e)[:200], "pass": None}
    return row


def run(only=None, voices="both", second=True, out="results"):
    jobs = []
    for c in CASES:
        if only and only not in (c["id"], c["cat"], c["lang"]):
            continue
        native = LANGS[c["lang"]][2]
        vs = {"native": [native], "default": ["aai-jane"]}.get(voices, list(dict.fromkeys([native, "aai-jane"])))
        jobs += [(c, v) for v in vs]
    with ThreadPoolExecutor(4) as ex:
        rows = list(ex.map(lambda j: one(*j), jobs))
    if second:
        from .second import whisper
        for r in rows:
            if r["raw"].get("pass") is False:
                stt = LANGS[r["lang"]][1]
                w = whisper(pathlib.Path(r["raw"]["audio"]), stt)
                wm = missing(r["expect"], w)
                r["raw"]["whisper"] = w
                r["raw"]["whisper_missing"] = wm
                # both transcribers miss the same value -> speech fault
                r["raw"]["verdict"] = "tts_fault" if set(wm) & set(r["raw"]["missing"]) else "stt_disagree"
    o = pathlib.Path(out); o.mkdir(exist_ok=True)
    (o / "matrix.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    for r in rows:
        raw, gd = r["raw"], r["guarded"]
        f = lambda x: "ERR " if x.get("pass") is None else ("PASS" if x["pass"] else "FAIL")
        print(f"{r['id']:<22} {r['voice']:<14} raw={f(raw)} guarded={f(gd)} {raw.get('verdict','')}  | {raw.get('heard', raw.get('error',''))[:60]}")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--voices", default="both", choices=["both", "native", "default"])
    ap.add_argument("--no-second", action="store_true")
    a = ap.parse_args()
    run(a.only, a.voices, not a.no_second)
