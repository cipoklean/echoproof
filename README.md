# EchoProof

Voice agents show text on screen and speak it out loud. EchoProof checks that the two match before a caller hears it.

## The attack: Trojan Speech

Hidden Unicode can make the screen and the voice disagree:

| Typed text | Screen shows | TTS reads |
|---|---|---|
| `Pay to account \u202e9876\u202c` | 6789 | 9 8 7 6 |
| `p\u0430ypal.com` (Cyrillic a) | paypal.com | garbled |

EchoProof's guard speaks what the user actually sees: it resolves bidi overrides, strips invisible characters, maps look-alike letters, and normalises full-width digits, then logs every finding.

## How it works

1. Each test case goes through AssemblyAI TTS-1 (`/v1/speech`).
2. The audio is transcribed back with AssemblyAI Sync STT (Universal-3.5 Pro).
3. Critical values (amounts, codes, doses, names) are compared after number normalisation.
4. Every case runs twice: raw and guarded.

## Run

```bash
pip install -r requirements.txt
export ASSEMBLYAI_API_KEY=...
python -m echoproof.run            # all cases
python -m echoproof.run --only trojan
python -m pytest -q                # offline guard tests
```

Audio and transcripts are cached in `cache/` so reruns cost nothing.

## Safety

All numbers are fake. Findings are reported privately to AssemblyAI.
