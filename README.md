# EchoProof

**What the caller hears matches what the screen shows.**

Voice agents put text on a screen and speak it aloud. When the two disagree, the caller acts on the voice: the screen says $10000, the voice says "$1". EchoProof finds those gaps with real AssemblyAI audio, and **SayGuard** closes them before the words are spoken.

**Try it live:** https://echoproof-sigma.vercel.app
Pick a sentence or type your own (up to 1,000 characters). The page speaks it twice through AssemblyAI TTS-1 (as written, and after SayGuard), transcribes both with AssemblyAI Sync STT, and checks every risky value: amounts, account numbers, dates, codes, doses, names, emails, links. Nothing is pre-recorded; every click is a fresh round trip.

## Live results

Every example on the page, run 3 times each against the deployed app: see [`results/LIVE.md`](results/LIVE.md), with every transcript in [`results/live.json`](results/live.json). Rerun it yourself with `python -m echoproof.livebench --runs 3`.

Oct 29, 2026: 16 sentences x 3 runs = 48 real round trips, 0 errors.

- **As written: 45 of 48 runs** had a value the caller heard wrong.
- **With SayGuard: 2 of 48.** Both misses are shown in the file: account 6789 transcribed as "$67.89", and Oluwaseun heard as "Oluwaseyan".

What the caller heard without SayGuard, straight from those runs:

| On screen | Caller heard |
|---|---|
| Approved the payment of $10000 (hidden right-to-left mark) | "Approved the payment of $1." |
| Log in to paypal.com (Cyrillic а) | "Log in to passchaipal.com" |
| Your code is ٣٧٢٩ (Arabic-Indic digits) | "Your code is ba ba ba." |
| Take ½ tablet | "Take Nerve Tablet." |
| Send the receipt to k.nwosu-eze@unn.edu.ng | "k.nwosu-easy@un.edu.ng" |
| Oluwaseun and Seyi have confirmed | "Oluwasun and Seyi have confirmed." |
| Your appointment is on 04/03/2026 (UK caller) | "March 4th, 2026" |

## What SayGuard does

- **Hidden characters:** resolves right-to-left overrides, strips invisible marks, maps look-alike letters (Cyrillic, Greek, full-width) and foreign digits to what the reader actually sees.
- **Dates by locale:** 03/04/2026 is March 4 in the US and 3 April in the UK and Nigeria; TTS-1 reads it the US way for everyone, so SayGuard writes it out for the caller's locale.
- **Money and numbers:** Indian lakh grouping, European "1.500,50 €", fractions and superscripts become plain spoken words.
- **Names:** TTS-1 has no pronunciation lexicon, so SayGuard respells names it mispronounces (Oluwaseun, Aoife, Niamh) using respellings an unprimed transcriber heard correctly.
- **Emails and links:** real words are said, everything else is spelled ("front dot desk underscore 2 at S-T-M-A-R-Y-S dash clinic dot org").
- **Receipt for every check:** what changed and why, both audio files, what the caller heard, and the time window each value was spoken in.

## Honest limits

The checker never hides a miss: if a value comes back wrong with SayGuard, the page marks it red. Known soft spots from real runs:

- Spelled emails and links inside long passages are usually right but not always (a link in a 1,000-character reminder came back right in 2 of 3 runs).
- Some names still fail after respelling now and then (Oluwaseun heard as "Oluwaseyan" in 1 of 3 live runs; "chiamaka" as "chamaka").
- A bare 4-digit account number can be transcribed as money ("6789" as "$67.89") in 1 of 3 runs; the checker counts that as wrong.
- The built-in English voices mangle German words; SayGuard flags any built-in voice speaking another language (`check_voice`). The native voices are fine.
- The live page runs on one AssemblyAI key, which allows 50 TTS-1 requests a minute.

## Use SayGuard in an agent

```python
from sayguard import sanitize, verify
r = sanitize(agent_reply, locale="en-gb", voice="aai-audrey")  # offline, instant
speak(r.spoken)                       # safe to say aloud
r = verify(r, voice="aai-audrey")     # optional: TTS-1 + Sync STT check per risky value
```

```
python -m sayguard "Transfer $‮00001‬ to Aoife on 03/04/2026" --locale en-gb
```

**Pipecat:** `sayguard/pipecat.py` has `SayGuardProcessor`, which sits between the LLM and AssemblyAI TTS and guards each sentence as it streams. `examples/pipecat_proof.py` runs a real pipeline; its output is in [`demo/pipecat/`](demo/pipecat).

## Built on AssemblyAI

- **TTS-1** speaks every sentence (WebSocket on the live page).
- **Sync STT (Universal-3.5 Pro)** is the caller's ear: it transcribes what TTS-1 actually said, with word timings used to find each value in the audio.
- The benchmark matrix (`python -m echoproof.run`, report in [`results/REPORT.md`](results/REPORT.md)) covers 63 cases across all six TTS-1 languages.

## Run it

```bash
pip install -r requirements.txt
export ASSEMBLYAI_API_KEY=...
uvicorn space.app:app            # the tester page on localhost:8000
python -m echoproof.livebench    # live results against the deployed page
python -m echoproof.run          # full benchmark matrix
python -m pytest -q tests        # checker and guard tests
```

All account numbers, names and emails in the examples are made up.
