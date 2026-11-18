---
name: demo-video-voiceover
description: Turns a raw screen recording into a client-ready product demo video by adding an AI voice-over (Gemini TTS on Vertex), speeding up waiting/processing phases with a "Processing... (sped up)" label, cutting errors, popups and rapid switching, and reordering parts of the recording. Use when the user shares a screen recording (.mov/.mp4) and asks for a demo, voice-over, narration, cleaning up or tightening a video, or says "same as before" for another recording.
---

# Demo video voice-over

Turn a screen recording into a narrated, tightened demo. Apply the defaults below without asking; only ask when the recording itself is ambiguous (e.g. you cannot tell what the product does and no repo or docs are given).

## Defaults (do not ask)

- Voice: Gemini TTS via Vertex, voice `Charon`, calm product-demo style.
- Waits (spinners, "working on it", progress bars): sped up to about 1.5 s with a "Processing... (sped up)" label. Not cut.
- Cut: error messages and retries, OS popups (app updates, permission dialogs), Finder/file-picker fumbling beyond the one pick, rapid back-and-forth switching, stopping the recording.
- Stills longer than 2 s inside kept parts are squeezed to 1 s automatically.
- Target: 1–2 sentences of 15–30 words per line, about 85–110 words per minute of final video, high-level features (what it does for the user), not UI mechanics.
- Output 1920 wide, 30 fps, H.264 + AAC, in a working folder outside any git repo: `~/Desktop/demo-edit-<short-name>/`.
- Apply user notes such as "I showed X at the end, it should be at the start" by reordering segments.

## Tools

Run every script with `uv run` (each declares its own dependencies inline, so there is nothing to install). Needs `uv`, `ffmpeg`/`ffprobe` (any build; labels are Pillow overlays, so `drawtext` is not required) and, for the voice, Vertex AI access through Application Default Credentials. Scripts live in this skill's `scripts/` folder; run them, don't rewrite them. Below, `S` is that folder (e.g. `~/.cursor/skills/demo-video-voiceover/scripts`).

Vertex settings (`GOOGLE_GENAI_USE_VERTEXAI=True`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`) come from the environment, `--env PATH`, `WORKDIR/.env` or `~/.config/demo-video-voiceover/.env`. If `tts.py` reports no credentials, ask the user for their project once and write `~/.config/demo-video-voiceover/.env`.

Recording names often contain a narrow no-break space before "PM"; locate them with a glob (`ls Screen\ Recording*4.17.16*.mov`) and pass that path.

## Workflow

```
- [ ] 1. Prepare working folder and contact sheets
- [ ] 2. Learn the product (repo/docs if given)
- [ ] 3. Map the recording and find exact boundaries
- [ ] 4. Write edit_list.json
- [ ] 5. Write script.json and generate voice
- [ ] 6. Render preview and check sync; fix and repeat
- [ ] 7. Render final, check, clean up, report
```

**1. Prepare.** `uv run S/prepare.py VIDEO ~/Desktop/demo-edit-<name>` creates `source.mov`, `sheets/s_NN.jpg` (one frame per 5 s, labelled) and `freezes.txt`, and lists the longest stills. Read every contact sheet.

**2. Learn the product.** If the user gives a repo URL, clone shallowly to `/tmp/<name>` (`gh repo clone owner/repo /tmp/<name> -- --depth 1`), read the README and the main workflow or prompt files for the feature names and steps, then `rm -rf` the clone when the script is written. Never state numbers or claims that are not on screen or in the docs.

**3. Map and find boundaries.** From the sheets, label each stretch: action (keep), waiting (fast), noise (drop). Then pin exact times with
`uv run S/frames.py source.mov /tmp/x.jpg 412:430:1` (or a list of times) and read the image. Pin these always:
- the moment a result or message actually appears (it usually lags the "working" state by a few seconds); the line describing it must start at that moment, so start its segment there and make the time before it `fast`;
- transient windows that flash in (file converters, "Opening…" dialogs, update popups); keep them inside `fast` or `drop` stretches;
- the last frame: the closing line holds on it, so end on a clean, representative screen (no half-open windows).

**4. edit_list.json.** Segments play in list order (that is how reordering works); a 0.25 s crossfade is added automatically wherever footage jumps. Format and an example: [reference.md](reference.md).

**5. script.json + voice.** One line per narrated beat, each anchored to the segment where its screen starts (`"at": "<segment id>"`), plus an optional closing line with `"at": "end"`. Lines must follow segment order. Then `uv run S/tts.py WORKDIR` (only changed lines are regenerated).

**6. Preview and check.**
`uv run S/render.py WORKDIR --preview` then `uv run S/check.py WORKDIR --preview`, and read `WORKDIR/check/sync.jpg`.
- Every frame in sync.jpg must show what its line talks about. If not, move the boundary (step 3) rather than rewording.
- `WARNING ... needs Ns of hold` means the line is longer than its footage: shorten the line, or attach it to an earlier segment.
- `OVERLAP` should never happen; `silent gap` over ~8 s: add or lengthen a line, or tighten the segment.
- Stills reported with `voice: NONE` longer than 3 s: squeeze, speed up or drop that footage. Stills under a line during a sped-up wait are fine if something on screen still moves (counter, progress bar).
- Edit JSON files with Python or the editor, not sed (formatting changes break patterns).

**7. Final.** `uv run S/render.py WORKDIR` → `WORKDIR/demo.mp4`, then `uv run S/check.py WORKDIR`. Delete any repo clone. Report to the user: path, final vs original length, what was sped up, cut and reordered, anything that could not be fixed from the footage (e.g. a screen never shown), and that `script.json` / `edit_list.json` can be edited and re-rendered with the same commands.

## Additional resources

- JSON formats, an example edit list and script, timing rules: [reference.md](reference.md)
