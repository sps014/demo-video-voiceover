# Reference

## edit_list.json

```json
{
  "source": "Screen Recording 2026-01-05 at 3.12.40 PM.mov",
  "segments": [
    {"id": "o1", "start": 632.1, "end": 651.0, "mode": "keep", "what": "the input invoice PDF (shown at the end, moved to the start)"},
    {"id": "s01", "start": 0.0, "end": 17.0, "mode": "keep", "what": "assistant asks for the invoices"},
    {"id": "s02", "start": 17.0, "end": 30.0, "mode": "keep", "what": "pick the files"},
    {"id": "s02f", "start": 30.0, "end": 49.25, "mode": "fast", "what": "uploading"},
    {"id": "s03", "start": 49.25, "end": 263.5, "mode": "fast", "what": "extracting line items"},
    {"id": "s04", "start": 263.5, "end": 298.25, "mode": "keep", "what": "extracted summary"},
    {"id": "x1", "start": 388.5, "end": 402.25, "mode": "drop", "what": "error and retry"}
  ]
}
```

- `start`/`end`: seconds in the source. `id`: any unique string. `what`: notes for you.
- `mode`: `keep` (real time, stills over 2 s squeezed to 1 s), `fast` (plays in 1.5 s with the label), `drop` (removed; listing drops is optional but documents the cut).
- Output order = list order. Moving a segment earlier in the list moves it earlier in the video.

## script.json

```json
{
  "voice": "Charon",
  "lines": [
    {"id": "l01", "at": "o1", "text": "This is the Invoice Assistant. It starts from the invoices you already receive, like this supplier PDF with forty line items."},
    {"id": "l02", "at": "s04", "text": "The assistant reads every invoice and pulls out the supplier, the dates, and each line item with its tax code, then asks you to confirm."},
    {"id": "l11", "at": "end", "text": "From a pile of invoices to clean, coded entries in your ledger, in a few short steps."}
  ]
}
```

- `at`: the segment where the line's screen begins; a line plays from 0.3 s after that segment starts.
- A line owns the footage from its segment up to the next line's segment. If the voice is longer, `fast` pieces and squeezed stills in that window are slowed first, then the last frame is held (warning when the hold is over 2 s).
- `"at": "end"` lines play over a hold on the final frame.

## Script style

- Open with what the product is and the inputs it starts from; close with one line on the outcome.
- Describe each step by what it does for the user ("reads the schedule and pulls out every package with its dates"), using the product's own feature names from the docs and the counts shown on screen.
- Avoid UI mechanics ("click the plus button"), filler, and claims not on screen or in the docs (time savings, accuracy).
- Typical: 10–16 lines, 250–400 words, for a 2.5–4 min video.

## Outputs in WORKDIR

| File | What |
|---|---|
| `demo.mp4`, `demo-preview.mp4` | final (1920 wide) and preview (960 wide) |
| `timeline*.json` | each line's start in the output, voice length, segment |
| `voice/<id>.wav` | TTS clips (24 kHz mono) |
| `work*/` | cached pieces; delete to force a full re-render |
| `check/sync.jpg` | frames 1.5 s into each line, plus the last frame |
