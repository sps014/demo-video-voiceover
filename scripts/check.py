# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""Play-through check of a rendered demo.

    python check.py WORKDIR [--preview]

Prints: length vs audio, line overlaps, silent gaps over 6 s, stills over 2.5 s in the output
(with the line playing over each, if any), and writes WORKDIR/check/sync.jpg with a frame
1.5 s into every line plus the last frame. Read sync.jpg and compare each frame to its line.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    sys.exit(__doc__)
work = Path(args[0]).expanduser().resolve()
preview = "--preview" in sys.argv
video = work / ("demo-preview.mp4" if preview else "demo.mp4")
tl = json.loads((work / ("timeline-preview.json" if preview else "timeline.json")).read_text())
script = {ln["id"]: ln["text"] for ln in json.loads((work / "script.json").read_text())["lines"]}
lines = tl["lines"]

out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0", str(video)],
                     capture_output=True, text=True).stdout.split()
print(video.name, "streams:", " ".join(out))

prev_end = 0.0
for ln in lines:
    end = ln["at"] + ln["voice"]
    if ln["at"] < prev_end - 0.05:
        print(f"OVERLAP {ln['line']} starts {ln['at']} before previous line ends {prev_end:.2f}")
    if ln["at"] - prev_end > 6:
        print(f"silent gap {prev_end:.1f}-{ln['at']:.1f}s ({ln['at'] - prev_end:.1f}s) before {ln['line']}")
    prev_end = end
print(f"{len(lines)} lines, {sum(len(script[l['line']].split()) for l in lines)} words, length {tl['length']}s")

W, H, R = 320, 180, 4
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={R},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
still = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)) < 0.05
i = 0
while i < len(still):
    if still[i]:
        j = i
        while j < len(still) and still[j]:
            j += 1
        a, b = i / R, (j + 1) / R
        if b - a > 2.5:
            over = [l["line"] for l in lines if l["at"] < b and l["at"] + l["voice"] > a]
            print(f"still {a:6.1f}-{b:6.1f}s ({b - a:.1f}s)  voice: {', '.join(over) or 'NONE'}")
        i = j
    else:
        i += 1

times = [round(l["at"] + 1.5, 1) for l in lines] + [max(tl["length"] - 0.5, 0)]
(work / "check").mkdir(exist_ok=True)
subprocess.run([sys.executable, str(Path(__file__).with_name("frames.py")), str(video), str(work / "check" / "sync.jpg"),
                *map(str, times), "--width", "480", "--cols", "4"], check=True)
for l, t in zip(lines, times):
    print(f"  {t:6.1f}s {l['line']}: {script[l['line']][:90]}")
