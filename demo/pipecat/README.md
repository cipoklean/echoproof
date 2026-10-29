# SayGuard inside a real Pipecat pipeline

`python examples/pipecat_proof.py` streams an LLM reply in five chunks (the Trojan amount is split
across two of them) through `SayGuardProcessor` into AssemblyAI TTS-1, captures the audio, and asks
AssemblyAI Sync STT what the caller heard.

| | Text that reached TTS-1 | Caller heard |
|---|---|---|
| SayGuard off | `Confirming your payment of $\u202e00001\u202c to Aoife Byrne on 03/04/2026.` | "Confirming your payment of **$1** to **Afa** Burn on **March 4th**, 2026." |
| SayGuard on | `Confirming your payment of $10000 to Eefa Byrne on 3 April 2026.` | "Confirming your payment of **$10,000** to EFA Burn on **3 April** 2026." |

Audio: `sayguard-off.wav`, `sayguard-on.wav`. Raw data: `result.json`.

TTS here runs through AssemblyAI's OpenAI-compatible HTTP route because the sandbox it was recorded
in drops outbound WebSocket frames. `SAYGUARD_TTS_TRANSPORT=ws` uses Pipecat's native
`AssemblyAITTSService`; SayGuard sits in the same place either way.
