"""Record the demo from the live page: real runs, real audio. Writes build/<scene>.webm,
build/<scene>.json (events in seconds) and build/<scene>_raw.wav / _safe.wav from the run."""
import base64, json, os, pathlib, sys, time, urllib.parse, wave
from playwright.sync_api import sync_playwright

B = pathlib.Path(__file__).parent / "build"
URL = "https://echoproof-sigma.vercel.app"
VO = json.loads((B / "vo_dur.json").read_text())
u = urllib.parse.urlparse(os.environ["HTTPS_PROXY"])
PROXY = {"server": f"http://{u.hostname}:{u.port}", "username": urllib.parse.unquote(u.username or ""),
         "password": urllib.parse.unquote(u.password or "")}


def wav_dur(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


class Scene:
    def __init__(self, p, name):
        self.name = name
        self.ctx = p.chromium.launch(proxy=PROXY, args=["--autoplay-policy=no-user-gesture-required"]).new_context(
            viewport={"width": 1280, "height": 720}, ignore_https_errors=True, record_video_dir=str(B / "raw"),
            record_video_size={"width": 1280, "height": 720})
        self.page = self.ctx.new_page()
        self.vstart = self.t0 = time.monotonic()
        self.ev = {}
        self.gap = 0.0
        self.resp = None
        self.page.on("response", self._on)

    def _on(self, r):
        if "/api/check" in r.url:
            try:
                self.resp = r.json()
            except Exception:
                pass

    def now(self):  # time on the final, cut timeline
        return time.monotonic() - self.t0 - self.gap

    def mark(self, k):
        self.ev[k] = round(self.now(), 2)
        if k in ("play_raw", "play_safe"):  # move the on-page player too (the sound is mixed in later)
            el = "rawA" if k == "play_raw" else "safeA"
            self.page.evaluate(f"(()=>{{const a=document.getElementById('{el}');a.muted=true;a.currentTime=0;a.play()}})()")

    def hold_until(self, t):
        while self.now() < t:
            time.sleep(0.05)

    def open(self):
        self.page.goto(URL, timeout=60000)
        self.page.wait_for_selector(".chip")
        self.page.add_style_tag(content="html{scroll-behavior:smooth;zoom:1.42}")
        self.page.wait_for_timeout(400)
        self.t0 = time.monotonic()  # timeline starts once the page is ready
        self.ev["lead"] = round(self.t0 - self.vstart, 2)

    def run(self, chip_text=None, voice=None):
        if voice:
            self.page.select_option("#voice", voice)
        if chip_text:
            self.page.locator(".chip", has_text=chip_text).first.click()
            self.page.evaluate("window.scrollTo({top:0})")
            self.page.wait_for_timeout(900)
        self.mark("click")
        real_click = time.monotonic()
        self.page.click("#go")
        self.page.wait_for_function("document.getElementById('go') && !document.getElementById('go').disabled", timeout=170000)
        self.page.wait_for_timeout(250)
        self.gap += time.monotonic() - real_click - 0.6  # cut the wait, keep 0.6 s of spinner
        self.ev["cut_from"] = round(real_click - self.t0 + 0.3, 2)
        self.ev["cut_len"] = round(self.gap, 2)
        self.mark("result")
        d = self.resp
        for side in ("raw", "safe"):
            (B / f"{self.name}_{side}.wav").write_bytes(base64.b64decode(d[side]["audio"]))
        json.dump({k: d[k] for k in ("raw_ok", "safe_ok", "spans", "spoken") if k in d} |
                  {"raw_heard": d["raw"]["heard"], "safe_heard": d["safe"]["heard"]},
                  open(B / f"{self.name}_result.json", "w"), indent=1, ensure_ascii=False)
        return d

    def scroll_to(self, sel, block="center"):
        self.page.evaluate(f"document.querySelector('{sel}').scrollIntoView({{behavior:'smooth',block:'{block}'}})")

    def glide(self, px, secs):
        steps = max(1, int(secs / 0.05))
        for _ in range(steps):
            self.page.mouse.wheel(0, px / steps)
            time.sleep(0.05)

    def close(self):
        self.mark("end")
        vid = self.page.video
        self.ctx.close()
        pathlib.Path(vid.path()).rename(B / f"{self.name}.webm")
        (B / f"{self.name}.json").write_text(json.dumps(self.ev))


def s1(p):
    s = Scene(p, "s1"); s.open()
    s.page.locator(".chip", has_text="10000").first.click(); s.page.evaluate("window.scrollTo({top:0})")
    s.hold_until(1.6); s.run()
    s.scroll_to("#out", "start"); 
    s.hold_until(max(VO["s1a"] + 0.4, s.now() + 1.2)); s.mark("play_raw")
    s.hold_until(s.ev["play_raw"] + wav_dur(B / "s1_raw.wav") + 0.5); s.mark("s1b")
    s.hold_until(s.ev["s1b"] + VO["s1b"] + 0.3); s.mark("play_safe")
    s.hold_until(s.ev["play_safe"] + wav_dur(B / "s1_safe.wav") + 0.8); s.close()


def s2(p):
    s = Scene(p, "s2"); s.open()
    s.hold_until(0.8); s.glide(1100, VO["s2"] * 0.75); s.hold_until(VO["s2"] + 0.6); s.close()


def s3(p):
    s = Scene(p, "s3"); s.open()
    s.page.select_option("#voice", "cipoklean-voice")
    s.page.locator(".chip", has_text="paypal").first.click(); s.page.evaluate("window.scrollTo({top:0})")
    s.hold_until(2.5); s.run()
    s.scroll_to("#out", "start")
    s.hold_until(max(VO["s3a"] + 0.4, s.now() + 1.0)); s.mark("play_raw")
    s.hold_until(s.ev["play_raw"] + wav_dur(B / "s3_raw.wav") + 0.4); s.mark("play_safe")
    s.hold_until(s.ev["play_safe"] + wav_dur(B / "s3_safe.wav") + 0.5); s.mark("s3b")
    s.scroll_to("#chk", "start")
    s.hold_until(s.ev["s3b"] + VO["s3b"] + 0.6); s.close()


def s4(p):
    s = Scene(p, "s4"); s.open()
    s.page.locator(".chip", has_text="Okafor").first.click(); s.page.evaluate("window.scrollTo({top:0})")
    s.hold_until(1.5); s.run()
    s.scroll_to("#chk", "start"); s.hold_until(s.now() + 1.2)
    left = max(2.0, VO["s4"] + 0.8 - s.now())
    s.glide(1400, left * 0.8); s.hold_until(VO["s4"] + 0.8); s.close()


def s5(p):
    s = Scene(p, "s5")
    s.page.goto("https://github.com/cipoklean/echoproof/blob/main/results/LIVE.md", timeout=60000)
    s.page.wait_for_timeout(1500)
    s.page.add_style_tag(content="#repos-file-tree,[aria-label='File Tree Navigation'],nav[aria-label*='File'],div[class*='FileTree'],div[data-testid*='tree']{display:none!important}")
    s.page.evaluate("document.querySelector('article.markdown-body')?.scrollIntoView({block:'start'})")
    s.page.wait_for_timeout(800); s.t0 = time.monotonic(); s.ev["lead"] = round(s.t0 - s.vstart, 2)
    s.hold_until(1.0); s.glide(450, VO["s5"] * 0.6); s.hold_until(VO["s5"] + 0.6); s.close()


def s6(p):
    s = Scene(p, "s6"); s.open(); s.hold_until(VO["s6"] + 1.8); s.close()


if __name__ == "__main__":
    want = sys.argv[1:] or ["s1", "s2", "s3", "s4", "s5", "s6"]
    with sync_playwright() as p:
        for n in want:
            globals()[n](p); print("recorded", n, flush=True)
