# EchoProof

Voice agents show text on screen and speak it out loud. EchoProof checks that the two match before a caller hears it.

## The attack: Trojan Speech

Hidden Unicode can make the screen and the voice disagree:

| Typed text | Screen shows | TTS reads |
|---|---|---|
| `Pay to account \u202e9876\u202c` | 6789 | 9 8 7 6 |
| `p\u0430ypal.com` (Cyrillic a) | paypal.com | garbled |

EchoProof's guard speaks what the user actually sees: it resolves bidi overrides, strips invisible characters, maps look-alike letters, and normalises full-width digits, then logs every finding.

## Results (Oct 29, 2026)

111 runs: 57 cases in all six TTS-1 languages, each spoken by a native catalog voice and the default `aai-jane`.

- Trojan Speech: 32 of 43 raw runs failed; 0 failed after the guard.
- Worst case: the screen shows **$10000**, TTS-1 says **"$1"** (`demo/screen-10000-voice-1.wav`).
- Every raw failure was re-checked by a second transcriber (local Whisper); all 40 were confirmed as speech faults.

Full table: [`results/REPORT.md`](results/REPORT.md).

## How it works

1. Each test case goes through AssemblyAI TTS-1 (`/v1/speech`).
2. The audio is transcribed back with AssemblyAI Sync STT (Universal-3.5 Pro).
3. Critical values (amounts, codes, doses, names) are compared after number normalisation.
4. Every case runs twice: raw and guarded.

## Run

```bash
pip install -r requirements.txt
export ASSEMBLYAI_API_KEY=...
python -m echoproof.run            # full matrix
python -m echoproof.report         # write results/REPORT.md
python -m echoproof.run --only trojan
python -m pytest -q                # offline guard tests
```

Audio and transcripts are cached in `cache/` so reruns cost nothing.

## Safety

All numbers are fake. Findings are reported privately to AssemblyAI.
