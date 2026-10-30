"""Cut each recorded scene (drop the page load and the wait for AssemblyAI), lay the voiceover
and the run's own audio on it, and join everything into echoproof-demo.mp4."""
import json, pathlib, subprocess, wave

B = pathlib.Path(__file__).parent / "build"
OUT = pathlib.Path(__file__).parent / "echoproof-demo.mp4"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
AUDIO = {  # scene: [(file, event or seconds, label shown while it plays)]
    "s1": [("vo_s1a", 0.2, None), ("s1_raw", "play_raw", "Caller hears it as written"), ("vo_s1b", "s1b", None),
           ("s1_safe", "play_safe", "Caller hears it with SayGuard")],
    "s2": [("vo_s2", 0.3, None)],
    "s3": [("vo_s3a", 0.2, None), ("s3_raw", "play_raw", "As written (my cloned voice)"),
           ("s3_safe", "play_safe", "With SayGuard (my cloned voice)"), ("vo_s3b", "s3b", None)],
    "s4": [("vo_s4", 0.3, None)],
    "s5": [("vo_s5", 0.3, None)],
    "s6": [("vo_s6", 0.3, None)],
}


def dur(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def scene(name):
    ev = json.loads((B / f"{name}.json").read_text())
    lead, end = ev["lead"], ev["end"]
    if "cut_from" in ev:
        a0, a1 = lead, lead + ev["cut_from"]
        b0, b1 = lead + ev["cut_from"] + ev["cut_len"], lead + end + ev["cut_len"]
        v = (f"[0:v]trim={a0}:{a1},setpts=PTS-STARTPTS[va];[0:v]trim={b0}:{b1},setpts=PTS-STARTPTS[vb];"
             f"[va][vb]concat=n=2:v=1:a=0[vc]")
    else:
        v = f"[0:v]trim={lead}:{lead + end},setpts=PTS-STARTPTS[vc]"
    inputs, parts, labels = ["-i", str(B / f"{name}.webm")], [], []
    for i, (f, at, label) in enumerate(AUDIO[name], start=1):
        t = ev[at] if isinstance(at, str) else at
        inputs += ["-i", str(B / f"{f}.wav")]
        gain = "1.0" if f.startswith("vo_") else "1.15"
        parts.append(f"[{i}:a]aresample=48000,volume={gain},adelay={int(t * 1000)}:all=1[a{i}]")
        if label:
            labels.append((label, t, t + dur(B / f"{f}.wav")))
    n = len(parts)
    draw = "".join(
        f",drawtext=fontfile={FONT}:text='{lab}':x=40:y=h-80:fontsize=30:fontcolor=white:box=1:boxcolor=0x4f46e5@0.92:"
        f"boxborderw=16:enable='between(t,{s:.2f},{e:.2f})'" for lab, s, e in labels)
    fade_out = max(0.0, end - 0.3)
    fc = (v + f";[vc]fps=30,scale=1280:720,format=yuv420p{draw},fade=t=in:d=0.25,fade=t=out:st={fade_out:.2f}:d=0.3[v];"
          + ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(1, n + 1))
          + f"amix=inputs={n}:normalize=0:duration=longest,apad,atrim=0:{end:.2f}[a]")
    out = B / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                    "-ar", "48000", "-t", f"{end:.2f}", str(out)], check=True)
    return out


if __name__ == "__main__":
    outs = [scene(n) for n in AUDIO if (B / f"{n}.json").exists()]
    (B / "list.txt").write_text("".join(f"file '{o.name}'\n" for o in outs))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(B / "list.txt"),
                    "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", str(OUT)], check=True)
    print(OUT)
