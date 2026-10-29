import argparse, sys
from .core import sanitize, verify, render

ap = argparse.ArgumentParser(prog="sayguard")
ap.add_argument("text")
ap.add_argument("--locale", default="en-us")
ap.add_argument("--voice", default="aai-audrey")
ap.add_argument("--offline", action="store_true", help="sanitize only, no API calls")
a = ap.parse_args()
r = sanitize(a.text, a.locale, a.voice)
if not a.offline:
    r = verify(r, a.voice)
sys.stdout.write(render(r))
