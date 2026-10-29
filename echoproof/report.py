"""Write results/REPORT.md from results/matrix.json."""
import json, pathlib
from collections import defaultdict

def main():
    r = json.loads(pathlib.Path("results/matrix.json").read_text())
    f = lambda xs, m: sum(x[m]["pass"] is False for x in xs)
    L = ["# EchoProof test matrix\n",
         f"{len(r)} runs ({len({x['id'] for x in r})} cases x native voice + aai-jane), TTS-1 -> AssemblyAI Sync STT (Universal-3.5 Pro).",
         "Raw failures were re-transcribed with local Whisper (small); `tts_fault` = both transcribers missed the same value.\n",
         f"**Raw failures: {f(r,'raw')}/{len(r)}. Guarded failures: {f(r,'guarded')}/{len(r)}.**\n",
         "| Category | Runs | Raw fail | Guarded fail |", "|---|---|---|---|"]
    by = defaultdict(list)
    for x in r: by[x["cat"]].append(x)
    for c, xs in by.items(): L.append(f"| {c} | {len(xs)} | {f(xs,'raw')} | {f(xs,'guarded')} |")
    L += ["\n## Every failure\n", "| Case | Voice | Screen shows | Heard (raw) | Verdict | Guarded |", "|---|---|---|---|---|---|"]
    for x in r:
        if x["raw"]["pass"] is False or x["guarded"]["pass"] is False:
            L.append(f"| {x['id']} | {x['voice']} | {x['displayed']} | {x['raw']['heard']} | {x['raw'].get('verdict','')} | {'PASS' if x['guarded']['pass'] else 'FAIL: ' + x['guarded']['heard']} |")
    pathlib.Path("results/REPORT.md").write_text("\n".join(L).replace("\u202e","").replace("\u202c","") + "\n")

if __name__ == "__main__":
    main()
