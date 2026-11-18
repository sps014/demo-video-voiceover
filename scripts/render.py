# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""Render demo.mp4 from edit_list.json, script.json, voice/*.wav and freezes.txt in WORKDIR.

    python render.py WORKDIR            # final, 1920 wide -> WORKDIR/demo.mp4
    python render.py WORKDIR --preview  # 960 wide, fast encode -> WORKDIR/demo-preview.mp4

Rendered pieces are cached in WORKDIR/work*/; only changed pieces are re-encoded.

Timing: every segment gets an output length (keep = real time with still stretches inside it
squeezed to 1 s; fast = 1.5 s; drop = gone). Each line owns the segments from its own up to
the next line's; if its voice does not fit, the fast segments in that window are slowed
first, then the last frame of the window is held. Segments play in list order; wherever the
footage jumps (dropped or reordered) there is a 0.25 s crossfade. Sped-up stretches carry a "Processing... (sped up)" label.
"""

from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import common

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    sys.exit(__doc__)
HERE = Path(args[0]).expanduser().resolve()
SOURCE = str(HERE / "source.mov")
PREVIEW = "--preview" in sys.argv
WIDTH = 960 if PREVIEW else 1920
FPS = 30
FAST = 1.5  # seconds a sped-up wait plays in
SQUEEZE = 2.0  # stills longer than this inside a kept segment ...
SQUEEZED = 1.0  # ... play in this long
LEAD, GAP = 0.3, 0.9  # silence before a line, and least silence after it
XFADE = 0.25
HOLD_MAX = 2.0  # most a window is held on its last frame before the line should be shortened
RATE = 24000

edl = json.loads((HERE / "edit_list.json").read_text())
script = json.loads((HERE / "script.json").read_text())
freezes = [tuple(map(float, ln.split())) for ln in (HERE / "freezes.txt").read_text().split("\n") if ln.strip()]
work = HERE / ("work-preview" if PREVIEW else "work")
work.mkdir(exist_ok=True)


def voice(line_id: str) -> np.ndarray:
    with wave.open(str(HERE / "voice" / f"{line_id}.wav")) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    loud = np.flatnonzero(np.abs(a) > 400)
    if len(loud):
        a = a[max(loud[0] - int(0.05 * RATE), 0) : loud[-1] + int(0.15 * RATE)]
    return a


# --- pieces: (source start, source end, output length, label) ---------------------------------


def pieces_of(seg: dict) -> list[list]:
    s, e = seg["start"], seg["end"]
    if seg["mode"] == "fast":
        return [[s, e, FAST, True]]
    out, t = [], s
    for a, b in freezes:
        a, b = max(a, s), min(b, e)
        if b - a > SQUEEZE:
            if a > t:
                out.append([t, a, a - t, False])
            out.append([a, b, SQUEEZED, False])
            t = b
    if e > t:
        out.append([t, e, e - t, False])
    return out


segs = [dict(sg, pieces=pieces_of(sg)) for sg in edl["segments"] if sg["mode"] != "drop"]
index = {sg["id"]: k for k, sg in enumerate(segs)}
missing = [ln["at"] for ln in script["lines"] if ln["at"] != "end" and ln["at"] not in index]
if missing:
    sys.exit(f"script.json lines point at segments that are missing or dropped: {missing}")
if [index[ln["at"]] for ln in script["lines"] if ln["at"] != "end"] != sorted(index[ln["at"]] for ln in script["lines"] if ln["at"] != "end"):
    sys.exit("script.json lines must follow the segment order of edit_list.json")
for k, sg in enumerate(segs):  # a crossfade wherever the footage jumps (dropped or reordered)
    sg["xfade_in"] = k > 0 and abs(segs[k - 1]["end"] - sg["start"]) > 0.05

lines = [dict(ln, audio=voice(ln["id"])) for ln in script["lines"]]
body = [ln for ln in lines if ln["at"] != "end"]
closing = [ln for ln in lines if ln["at"] == "end"]
starts = [index[ln["at"]] for ln in body]
warnings = []
for n, ln in enumerate(body):
    window = segs[starts[n] : starts[n + 1] if n + 1 < len(starts) else len(segs)]
    need = LEAD + len(ln["audio"]) / RATE + GAP
    have = sum(p[2] for sg in window for p in sg["pieces"]) - XFADE * sum(sg["xfade_in"] for sg in window[1:])
    short = need - have
    fast = [p for sg in window for p in sg["pieces"] if p[3] or (p[1] - p[0]) > p[2] + 1e-6]
    room = sum((p[1] - p[0]) - p[2] for p in fast)
    if short > 0 and room > 0:
        take = min(short, room)
        for p in fast:
            p[2] += take * ((p[1] - p[0]) - p[2]) / room
        short -= take
    if short > 0:
        window[-1]["hold"] = short
        if short > HOLD_MAX:
            warnings.append(f"{ln['id']} needs {short:.1f}s of hold; shorten it")
segs[-1]["hold"] = segs[-1].get("hold", 0) + sum(LEAD + len(c["audio"]) / RATE + 1.5 for c in closing)

# --- output timeline --------------------------------------------------------------------------

t = 0.0
for k, sg in enumerate(segs):
    if sg["xfade_in"]:
        t -= XFADE
    sg["out_start"] = t
    sg["out_len"] = sum(p[2] for p in sg["pieces"]) + sg.get("hold", 0)
    t += sg["out_len"]
total = t

# --- label ------------------------------------------------------------------------------------

label = work / "label.png"
scale = WIDTH / 1920
font = common.font(int(30 * scale))
text = "Processing...  (sped up)"
tw = int(font.getlength(text))
img = Image.new("RGBA", (tw + int(48 * scale), int(56 * scale)), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=int(16 * scale), fill=(20, 24, 33, 215))
d.text((int(24 * scale), int(10 * scale)), text, font=font, fill=(255, 255, 255, 255))
img.save(label)

# --- video pieces -----------------------------------------------------------------------------


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        sys.exit("ffmpeg failed:\n" + "\n".join(r.stderr.splitlines()[-15:]))


def build(f: Path, key: str, cmd: list[str]) -> None:
    """Run cmd to make f unless f was already built from the same key."""
    k = f.with_suffix(".key")
    if f.exists() and k.exists() and k.read_text() == key:
        return
    k.unlink(missing_ok=True)
    run(cmd)
    k.write_text(key)


enc = ["-c:v", "libx264", "-preset", "veryfast" if PREVIEW else "medium", "-crf", "26" if PREVIEW else "18", "-pix_fmt", "yuv420p"]
files = []
for sg in segs:
    parts = []
    for n, (s, e, out_len, lab) in enumerate(sg["pieces"]):
        f = work / f"{sg['id']}_{n}.mp4"
        factor = out_len / (e - s)
        vf = f"setpts=(PTS-STARTPTS)*{factor:.6f},fps={FPS},scale={WIDTH}:-2:flags=lanczos"
        last = n == len(sg["pieces"]) - 1
        if last and sg.get("hold"):
            vf += f",tpad=stop_mode=clone:stop_duration={sg['hold']:.3f}"
        cmd = ["ffmpeg", "-y", "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", SOURCE]
        if lab:
            m = int(28 * scale)
            cmd += ["-i", str(label), "-filter_complex", f"[0:v]{vf}[v];[v][1:v]overlay={m}:H-h-{m}[o]", "-map", "[o]"]
        else:
            cmd += ["-vf", vf]
        cmd = [*cmd, "-an", *enc, "-r", str(FPS), str(f)]
        build(f, " ".join(cmd), cmd)
        parts.append(f)
    out = work / f"{sg['id']}.mp4"
    lst = work / f"{sg['id']}.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    build(out, lst.read_text() + "".join(p.with_suffix(".key").read_text() for p in parts),
          ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    files.append(out)
    print(f"{sg['id']}: {sg['out_len']:.1f}s", flush=True)


def length(f: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    return float(r.stdout)


# Join: plain concat inside runs, crossfade where footage was dropped.
inputs, graph, cur, offset = [], [], None, 0.0
for k, (sg, f) in enumerate(zip(segs, files)):
    inputs += ["-i", str(f)]
    n = k
    graph.append(f"[{n}:v]settb=AVTB,setpts=PTS-STARTPTS[v{n}]")
    if cur is None:
        cur, offset = f"[v{n}]", length(f)
        continue
    if sg["xfade_in"]:
        graph.append(f"{cur}[v{n}]xfade=transition=fade:duration={XFADE}:offset={offset - XFADE:.3f},settb=AVTB[j{n}]")
        offset += length(f) - XFADE
    else:
        graph.append(f"{cur}[v{n}]concat=n=2:v=1:a=0,settb=AVTB[j{n}]")
        offset += length(f)
    cur = f"[j{n}]"

# --- narration track --------------------------------------------------------------------------

track = np.zeros(int((offset + 0.5) * RATE), dtype=np.float32)
real = []  # each segment's actual start after encoding, for placing the lines
t = 0.0
for k, (sg, f) in enumerate(zip(segs, files)):
    if k and sg["xfade_in"]:
        t -= XFADE
    real.append(t)
    t += length(f)
for n, ln in enumerate(body):
    at = int((real[starts[n]] + LEAD) * RATE)
    track[at : at + len(ln["audio"])] += ln["audio"][: max(len(track) - at, 0)]
end_at = t - sum(LEAD + len(c["audio"]) / RATE + 1.5 for c in closing)
for c in closing:
    c["placed"] = end_at + LEAD
    at = int((end_at + LEAD) * RATE)
    track[at : at + len(c["audio"])] += c["audio"]
    end_at += LEAD + len(c["audio"]) / RATE + 1.5
peak = np.abs(track).max() or 1
track = (track / peak * 0.89 * 32767).astype(np.int16)
narration = work / "narration.wav"
with wave.open(str(narration), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(track.tobytes())

name = HERE / ("demo-preview.mp4" if PREVIEW else "demo.mp4")
audio_in = len(segs)
cmd = ["ffmpeg", "-y", *inputs, "-i", str(narration), "-filter_complex", ";".join(graph), "-map", cur, "-map", f"{audio_in}:a"]
run([*cmd, *enc, "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", str(name)])

timeline = [
    {"line": ln["id"], "at": round(real[starts[n]] + LEAD, 2), "voice": round(len(ln["audio"]) / RATE, 2), "segment": ln["at"]}
    for n, ln in enumerate(body)
] + [
    {"line": c["id"], "at": round(c["placed"], 2), "voice": round(len(c["audio"]) / RATE, 2), "segment": "end"}
    for c in closing
]
(HERE / ("timeline-preview.json" if PREVIEW else "timeline.json")).write_text(json.dumps({"length": round(offset, 2), "lines": timeline}, indent=1))
print(f"{name.name}: {offset:.1f}s")
for w_ in warnings:
    print("WARNING", w_)
