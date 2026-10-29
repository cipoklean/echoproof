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

122 runs: 63 cases in all six TTS-1 languages, each spoken by a native catalog voice and the default `aai-jane`.

- Trojan Speech: 32 of 43 raw runs failed; 0 failed after the guard.
- Worst case: the screen shows **$10000**, TTS-1 says **"$1"** (`demo/screen-10000-voice-1.wav`).
- Dates: TTS-1 reads English 03/04/2026 as March 4 for everyone. UK and Nigerian callers lose; the guard spells the date out by locale (4 raw failures, 0 guarded). Spanish, German, French, Portuguese and Italian already read day-first.
- Names: TTS-1 has no pronunciation lexicon, so `python -m echoproof.names` searches respellings (Aoife -> Eefa, Niamh -> Neev, Xochitl -> Socheel, Siân -> Sharn) and keeps the ones an unprimed transcriber hears as the right sound. Names went from 4 failures to 0. Priming STT with the name as a keyterm is useless as a check: it "heard" every raw name correctly, even mispronounced ones.
- Money: Indian lakh grouping (₹1,50,000 was spoken "$105,000") and "1.500,50 Euro" (the default voice said "1.500.500") are rewritten into plain spoken form. Money went from 3 failures to 0.
- The one guarded failure left is the default voice mangling German words ("Nehmen Sie" -> "Namen C"). EchoProof flags any built-in voice speaking a language other than English (`check_voice`); the native German voice gets the same sentence right.
- Every raw failure was re-checked by a second transcriber (local Whisper); each was confirmed as speech faults.

Full table: [`results/REPORT.md`](results/REPORT.md).

**Try it live:** https://echoproof-sigma.vercel.app — talk to a bank voice agent built entirely on AssemblyAI (Sync STT → LLM Gateway → SayGuard → TTS-1 over WebSocket → Sync STT check) and flip SayGuard off to hear the difference.

## SayGuard: use it in an agent

```python
from sayguard import sanitize, verify
r = sanitize(agent_reply, locale="en-gb", voice="aai-audrey")  # offline, instant
speak(r.spoken)                       # what the screen shows, safe to say
r = verify(r, voice="aai-audrey")     # optional: TTS-1 word timings + Sync STT check per risky span
```

```
python -m sayguard "Transfer $‮00001‬ to Aoife on 03/04/2026" --locale en-gb
```

Every call writes a receipt: what changed and why, the real audio, what AssemblyAI heard inside each risky span's time window, and what the caller would have heard without SayGuard. Real ones: [`demo/receipts/`](demo/receipts/README.md).

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
python -m echoproof.names          # learn name respellings -> echoproof/lexicon.json
python -m echoproof.run --only trojan
python -m pytest -q                # offline guard tests
```

Audio and transcripts are cached in `cache/` so reruns cost nothing.

## Safety

All numbers are fake. Findings are reported privately to AssemblyAI.
