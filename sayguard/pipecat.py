"""SayGuard as a Pipecat processor. Put it between your LLM and AssemblyAITTSService:

    pipeline = Pipeline([transport.input(), stt, user_agg, llm,
                         SayGuardProcessor(locale="en-gb", on_receipt=print),
                         tts, transport.output(), assistant_agg])

LLM tokens stream in pieces, so a Trojan amount like "$\u202e00001\u202c" can arrive split
across chunks. The processor holds text until a sentence ends, sanitizes the whole
sentence, then passes it on. Everything else flows through untouched.
"""
from __future__ import annotations
import re
from typing import Callable

from pipecat.frames.frames import (Frame, LLMTextFrame, LLMFullResponseEndFrame, TTSSpeakFrame,
                                   InterruptionFrame)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from .core import sanitize, Receipt

_END = re.compile(r"(?<!\d)[.!?](?=\s)|\n")  # sentence end, not a decimal point


class SayGuardProcessor(FrameProcessor):
    def __init__(self, locale: str = "en-us", voice: str | None = None, enabled: bool = True,
                 on_receipt: Callable[[Receipt], None] | None = None, **kw):
        super().__init__(**kw)
        self.locale, self.voice, self.enabled, self.on_receipt = locale, voice, enabled, on_receipt
        self._buf = ""

    def _clean(self, text: str) -> str:
        if not self.enabled or not text.strip():
            return text
        r = sanitize(text, self.locale, self.voice)
        if self.on_receipt:
            self.on_receipt(r)
        # keep the chunk's surrounding whitespace so TTS aggregation still sees spaces
        lead = text[: len(text) - len(text.lstrip())]
        tail = text[len(text.rstrip()):]
        return lead + r.spoken + tail

    async def _flush(self, direction):
        if self._buf:
            text, self._buf = self._buf, ""
            await self.push_frame(LLMTextFrame(self._clean(text)), direction)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMTextFrame) and direction == FrameDirection.DOWNSTREAM:
            self._buf += frame.text
            while (m := _END.search(self._buf)):
                cut = m.end()
                sentence, self._buf = self._buf[:cut], self._buf[cut:]
                await self.push_frame(LLMTextFrame(self._clean(sentence)), direction)
            return
        if isinstance(frame, TTSSpeakFrame):
            frame = TTSSpeakFrame(self._clean(frame.text))
        elif isinstance(frame, LLMFullResponseEndFrame):
            await self._flush(direction)
        elif isinstance(frame, InterruptionFrame):
            self._buf = ""
        await self.push_frame(frame, direction)
