"""SayGuard: make what a voice agent says match what its screen shows.

    from sayguard import sanitize, verify
    r = sanitize("Transfer $\u202e00001\u202c now", locale="en-us")
    r.spoken      # "Transfer $10000 now"  (what the screen shows)
    r.changes     # every rewrite, with the reason
    v = verify(r, voice="aai-audrey")   # speaks it with TTS-1, checks each risky span with Sync STT
"""
from .core import sanitize, verify, Receipt  # noqa: F401
