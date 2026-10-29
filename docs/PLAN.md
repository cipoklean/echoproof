# EchoProof build plan (Oct 30 - Nov 7, 2026)

Product: EchoProof = "what the caller hears matches what the screen shows", built on AssemblyAI.
Sanitizer name: TBD (candidates: SayGuard, SpeakSafe, VoiceLint). Benchmark: EchoBench.

Pipeline: Universal-Streaming STT (caller) -> agent LLM -> SANITIZER (rewrite + receipt) -> TTS-1 (word timings) -> Sync STT spot-check of risky spans only -> caller.

Deliverables:
1. Library: sanitize(text, locale, voice) -> spoken text + receipt; verify(text) -> round-trip check of risky spans via TTS word timings + Sync STT.
2. Drop-in: Pipecat (or LiveKit) processor in front of AssemblyAI TTS.
3. Demo agent "bank payment line": same reply with/without EchoProof, raw vs guarded audio, receipt panel. Hosted (HF Space).
4. EchoBench: 63 cases / 122 runs, 6 languages, published report.
5. 2-min video + README with honest limits.

Days: Oct 30-31 library + receipts; Nov 1-2 verify (word timings + spot-check); Nov 3-4 Pipecat processor + demo agent; Nov 5 hosted demo; Nov 6 video + README; Nov 7 submit before 11:00 PT.
