"""Real Pipecat pipeline: streamed LLM tokens -> [SayGuardProcessor] -> AssemblyAITTSService.
Captures the audio the caller would hear, then asks AssemblyAI Sync STT what was said.

    python examples/pipecat_proof.py        # runs with SayGuard off, then on
"""
import asyncio, json, os, pathlib, sys, wave
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from pipecat.frames.frames import (EndFrame, LLMFullResponseEndFrame, LLMFullResponseStartFrame,
                                   LLMTextFrame, TTSAudioRawFrame)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.assemblyai.tts import AssemblyAITTSService
from pipecat.services.openai.tts import OpenAITTSService

from sayguard.core import _stt

# Only needed behind an HTTP proxy whose username contains ':' (websockets asserts on it).
import base64, websockets.proxy as _wp
_wp.build_authorization_basic = lambda u, pw: "Basic " + base64.b64encode(f"{u}:{pw}".encode()).decode()
from sayguard.pipecat import SayGuardProcessor

# What an LLM produces after reading an attacker-written invoice: the amount field
# holds U+202E so the screen shows $10000 while the characters run 0,0,0,0,1.
REPLY = "Confirming your payment of $\u202e00001\u202c to Aoife Byrne on 03/04/2026. Shall I send it?"
CHUNKS = ["Confirming your ", "payment of $\u202e00", "001\u202c to Aoife", " Byrne on 03/0", "4/2026. Shall I send it?"]
SR = 24000
OUT = pathlib.Path("demo/pipecat")


class Sink(FrameProcessor):
    def __init__(self):
        super().__init__(); self.pcm = bytearray(); self.last = None

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, TTSAudioRawFrame):
            self.pcm += frame.audio
            self.last = asyncio.get_event_loop().time()
        await self.push_frame(frame, direction)


class Tap(FrameProcessor):
    """Records the text that reaches TTS."""
    def __init__(self, texts):
        super().__init__(); self.texts = texts

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMTextFrame):
            self.texts.append(frame.text)
        await self.push_frame(frame, direction)


async def run(enabled: bool):
    receipts, texts = [], []
    key = os.environ.get("ASSEMBLYAI_API_KEY", "")
    if os.environ.get("SAYGUARD_TTS_TRANSPORT", "http") == "ws":
        # AssemblyAI's native Pipecat service (WebSocket). Same place in the pipeline.
        tts = AssemblyAITTSService(api_key=key, sample_rate=SR, settings=AssemblyAITTSService.Settings(voice="aai-audrey"))
    else:
        # AssemblyAI TTS-1 through its documented OpenAI-compatible HTTP route, for networks
        # that block outbound WebSocket frames (like the sandbox this was first run in).
        tts = OpenAITTSService(api_key=key, base_url="https://tts.us.assemblyai.com/v1/openai",
                               sample_rate=SR, settings=OpenAITTSService.Settings(voice="alloy", model="assemblyai-tts-en"))
    sink = Sink()
    guard = SayGuardProcessor(locale="en-gb", enabled=enabled, on_receipt=receipts.append)
    task = PipelineTask(Pipeline([guard, Tap(texts), tts, sink]),
                        params=PipelineParams(audio_out_sample_rate=SR))
    await task.queue_frames([LLMFullResponseStartFrame(), *[LLMTextFrame(c) for c in CHUNKS],
                             LLMFullResponseEndFrame()])

    async def end_when_quiet():  # stop once audio has started and then gone quiet for 2 s
        loop = asyncio.get_event_loop(); t0 = loop.time()
        while loop.time() - t0 < 60:
            await asyncio.sleep(0.25)
            if sink.last and loop.time() - sink.last > 2:
                break
        await task.queue_frame(EndFrame())

    await asyncio.gather(PipelineRunner(handle_sigint=False).run(task), end_when_quiet())
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"sayguard-{'on' if enabled else 'off'}.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(sink.pcm))
    heard, ms = _stt(path, "en")
    return {"sayguard": enabled, "text_sent_to_tts": "".join(texts), "audio": str(path),
            "audio_seconds": round(len(sink.pcm) / 2 / SR, 2), "caller_heard": heard.get("text"),
            "changes": [c for r in receipts for c in r.changes]}


async def main():
    results = [await run(False), await run(True)]
    (OUT / "result.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    for r in results:
        print(f"\nSayGuard {'ON ' if r['sayguard'] else 'OFF'} | sent to TTS: {r['text_sent_to_tts'].encode('unicode_escape').decode()}")
        print(f"             | caller heard: {r['caller_heard']}  ({r['audio_seconds']}s)")

if __name__ == "__main__":
    asyncio.run(main())
