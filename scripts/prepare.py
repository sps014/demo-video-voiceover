# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""Set up a demo-edit working folder for a screen recording.

    python prepare.py VIDEO WORKDIR

Writes into WORKDIR:
  source.mov      symlink to VIDEO (dodges odd characters in recording names)
  sheets/s_NN.jpg 3x3 contact sheets, one frame every 5 s, labelled with the source time
  freezes.txt     still spans of 2 s or more, "start end" per line (pixel diff at 4 fps)
and prints duration, size, audio presence and the long stills (usually the waits).
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import common

if len(sys.argv) < 3:
    sys.exit(__doc__)
video = Path(sys.argv[1]).expanduser().resolve()
work = Path(sys.argv[2]).expanduser().resolve()
work.mkdir(parents=True, exist_ok=True)
src = work / "source.mov"
if src.is_symlink() or src.exists():
    src.unlink()
src.symlink_to(video)

probe = json.loads(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", str(src)],
    capture_output=True, text=True, check=True).stdout)
duration = float(probe["format"]["duration"])
vs = next(s for s in probe["streams"] if s["codec_type"] == "video")
has_audio = any(s["codec_type"] == "audio" for s in probe["streams"])
print(f"duration {duration:.1f}s  size {vs['width']}x{vs['height']}  fps {vs['r_frame_rate']}  audio {'yes' if has_audio else 'no'}")

# contact sheets
frames = work / "frames"
frames.mkdir(exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "fps=1/5,scale=800:-2", str(frames / "f_%03d.png")], check=True)
fs = sorted(frames.glob("f_*.png"))
font = common.font(28)
(work / "sheets").mkdir(exist_ok=True)
for s in range(0, len(fs), 9):
    batch = fs[s : s + 9]
    w, h = Image.open(batch[0]).size
    sheet = Image.new("RGB", (w * 3, h * 3), "white")
    for k, f in enumerate(batch):
        im = Image.open(f).convert("RGB")
        t = (int(f.stem[2:]) - 1) * 5
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 130, 36], fill="black")
        d.text((6, 2), f"{t}s", fill="yellow", font=font)
        sheet.paste(im, ((k % 3) * w, (k // 3) * h))
    sheet.save(work / "sheets" / f"s_{s // 9:02d}.jpg", quality=80)
print(f"{(len(fs) + 8) // 9} contact sheets in {work / 'sheets'}")

# still spans; ffmpeg freezedetect start/end lines can pair up wrongly, so diff frames directly
W, H, R = 320, 200, 4
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps={R},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True, check=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
still = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)) < 0.05
spans, i = [], 0
while i < len(still):
    if still[i]:
        j = i
        while j < len(still) and still[j]:
            j += 1
        a, b = i / R, (j + 1) / R
        if b - a >= 2:
            spans.append((a, b))
        i = j
    else:
        i += 1
(work / "freezes.txt").write_text("".join(f"{a:.2f} {b:.2f}\n" for a, b in spans))
print(f"{len(spans)} still spans in freezes.txt; longest:")
for a, b in sorted(spans, key=lambda s: s[0] - s[1])[:12]:
    print(f"  {a:7.2f} - {b:7.2f}  ({b - a:.1f}s)")
