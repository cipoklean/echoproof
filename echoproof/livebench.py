"""Run every example on the live page N times and write results/LIVE.md.

python -m echoproof.livebench [--runs 3] [--url https://echoproof-sigma.vercel.app]
Each run is a real AssemblyAI TTS-1 + Sync STT round trip made by the deployed app."""
import argparse, datetime, json, pathlib, time
from concurrent.futures import ThreadPoolExecutor
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--url", default="https://echoproof-sigma.vercel.app")
    ap.add_argument("--from-json", action="store_true", help="rewrite LIVE.md from results/live.json")
    a = ap.parse_args()
    cases = json.loads((ROOT / "space/examples.json").read_text())
    jobs = [(c, i) for c in cases for i in range(a.runs)]

    def go(job):
        c, _ = job
        for attempt in range(4):
            try:
                d = requests.post(a.url + "/api/check", json={"text": c["text"], "locale": c["locale"]}, timeout=170).json()
            except Exception as e:
                d = {"error": str(e)}
            if "429" not in str(d.get("error", "")):
                break
            time.sleep(35)  # TTS-1 allows 50 requests a minute per account
        if "error" in d:
            return {"id": c["id"], "error": d["error"]}
        return {"id": c["id"], "raw_ok": d["raw_ok"], "safe_ok": d["safe_ok"],
                "raw_heard": d["raw"]["heard"], "safe_heard": d["safe"]["heard"],
                "raw_bad": [s["text"] for s in d["spans"] if not s["ok_raw"]],
                "safe_bad": [s["text"] for s in d["spans"] if not s["ok_safe"]],
                "transport": d.get("transport")}

    if a.from_json:
        saved = json.loads((ROOT / "results/live.json").read_text())
        rows, stamp = saved["runs"], saved["when"]
        a.runs = max(sum(r["id"] == c["id"] for r in rows) for c in cases)
    else:
        with ThreadPoolExecutor(3) as p:
            rows = list(p.map(go, jobs))
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        (ROOT / "results/live.json").write_text(json.dumps({"when": stamp, "url": a.url, "runs": rows}, indent=1, ensure_ascii=False))
    ok = [r for r in rows if "error" not in r]
    lines = [f"# Live results ({stamp})", "",
             f"{len(cases)} sentences x {a.runs} runs = {len(rows)} real round trips through {a.url}"
             f" (AssemblyAI TTS-1, then Sync STT). {len(rows) - len(ok)} errored.", "",
             f"- As written: **{sum(not r['raw_ok'] for r in ok)} of {len(ok)}** runs said a value wrong.",
             f"- With SayGuard: **{sum(not r['safe_ok'] for r in ok)} of {len(ok)}**.", "",
             "| Sentence | As written: wrong | With SayGuard: wrong | What the caller heard as written (first run) |",
             "|---|---|---|---|"]
    for c in cases:
        rs = [r for r in ok if r["id"] == c["id"]]
        if not rs:
            continue
        lines.append(f"| {c['why'].rstrip('.')} | {sum(not r['raw_ok'] for r in rs)}/{len(rs)} | "
                     f"{sum(not r['safe_ok'] for r in rs)}/{len(rs)} | {rs[0]['raw_heard'].replace('|', '/')} |")
    lines += ["", "Every transcript is in `results/live.json`."]
    (ROOT / "results/LIVE.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:7]))


if __name__ == "__main__":
    main()
