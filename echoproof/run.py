"""Run every case raw and guarded: text -> TTS-1 -> STT -> compare."""
from __future__ import annotations
import argparse, json, pathlib
from .cases import CASES
from .client import speak, transcribe
from .guard import guard
from .numbers import canon


def check(expect: list[str], heard: str) -> list[str]:
    h = canon(heard).replace(" ", "")
    return [e for e in expect if canon(e).replace(" ", "") not in h]


def run(only: str | None = None, out: str = "results") -> list[dict]:
    rows = []
    for c in CASES:
        if only and only not in (c["id"], c["cat"]):
            continue
        lang, stt = c.get("lang", "english"), c.get("stt", "en")
        g = guard(c["text"])
        row = {"id": c["id"], "cat": c["cat"], "text": c["text"], "displayed": g.displayed,
               "findings": [f.__dict__ for f in g.findings], "expect": c["expect"], "note": c.get("note", "")}
        for mode, text in (("raw", c["text"]), ("guarded", g.cleaned)):
            try:
                heard = transcribe(speak(text, language=lang), stt).get("text", "")
                missing = check(c["expect"], heard)
                row[mode] = {"sent": text, "heard": heard, "missing": missing, "pass": not missing}
            except Exception as e:  # keep going; record the error
                row[mode] = {"sent": text, "error": str(e), "pass": False}
        rows.append(row)
        r, gd = row["raw"], row["guarded"]
        print(f"{c['id']:<18} raw={'PASS' if r['pass'] else 'FAIL'}  guarded={'PASS' if gd['pass'] else 'FAIL'}  heard: {r.get('heard', r.get('error'))[:70]}")
    o = pathlib.Path(out); o.mkdir(exist_ok=True)
    (o / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    raw_fail = sum(not r["raw"]["pass"] for r in rows)
    g_fail = sum(not r["guarded"]["pass"] for r in rows)
    print(f"\n{len(rows)} cases | raw failures: {raw_fail} | guarded failures: {g_fail}")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="case id or category")
    a = ap.parse_args()
    run(a.only)
