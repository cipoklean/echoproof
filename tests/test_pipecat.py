import asyncio
import pytest
pytest.importorskip("pipecat")
from pipecat.frames.frames import LLMTextFrame, LLMFullResponseEndFrame
from pipecat.processors.frame_processor import FrameDirection
from sayguard.pipecat import SayGuardProcessor


def test_split_trojan_reassembled():
    out = []
    p = SayGuardProcessor(locale="en-gb")
    async def push(frame, direction=FrameDirection.DOWNSTREAM):
        out.append(frame)
    p.push_frame = push
    async def go():
        for c in ["Pay $\u202e00", "001\u202c on 03/0", "4/2026. Ok?"]:
            await _feed(p, LLMTextFrame(c))
        await _feed(p, LLMFullResponseEndFrame())
    asyncio.run(go())
    text = "".join(f.text for f in out if isinstance(f, LLMTextFrame))
    assert text == "Pay $10000 on 3 April 2026. Ok?"


async def _feed(p, frame):
    # bypass FrameProcessor base bookkeeping; exercise SayGuard's own logic
    from pipecat.processors.frame_processor import FrameProcessor
    orig = FrameProcessor.process_frame
    async def noop(self, f, d): pass
    FrameProcessor.process_frame = noop
    try:
        await p.process_frame(frame, FrameDirection.DOWNSTREAM)
    finally:
        FrameProcessor.process_frame = orig
