"""Vercel entrypoint for the EchoProof bank line (the app lives in space/app.py)."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent / "space"))
from app import app  # noqa: E402,F401
