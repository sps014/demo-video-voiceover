# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Grid of labelled frames from a video, for finding exact screen changes or checking sync.

    python frames.py VIDEO OUT.jpg TIMES... [--width 400] [--cols 6]

TIMES are seconds (412.5) or ranges START:END:STEP (412:430:1). Read OUT.jpg afterwards.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

import common


def opt(name: str, default: int) -> int:
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


argv = [a for k, a in enumerate(sys.argv) if not a.startswith("--") and not (k and sys.argv[k - 1].startswith("--"))]
if len(argv) < 4:
    sys.exit(__doc__)
video, out = argv[1], argv[2]
times = []
for tok in argv[3:]:
    if ":" in tok:
        a, b, step = (float(x) for x in tok.split(":"))
        t = a
        while t <= b + 1e-9:
            times.append(round(t, 2))
            t += step
    else:
        times.append(float(tok))
width, cols = opt("--width", 400), opt("--cols", 6)
font = common.font(18)
tiles = []
with tempfile.TemporaryDirectory() as tmp:
    for k, t in enumerate(times):
        p = Path(tmp) / f"{k}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", "-vf", f"scale={width}:-2", str(p)])
        if p.exists():
            tiles.append((t, Image.open(p).convert("RGB")))
if not tiles:
    sys.exit("no frames extracted")
h = tiles[0][1].height
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (width * cols, (h + 22) * rows), "white")
d = ImageDraw.Draw(sheet)
for k, (t, im) in enumerate(tiles):
    x, y = (k % cols) * width, (k // cols) * (h + 22)
    sheet.paste(im, (x, y + 22))
    d.text((x + 4, y + 2), f"{t:g}s", fill="black", font=font)
sheet.save(out, quality=78)
print(out, len(tiles), "frames")
