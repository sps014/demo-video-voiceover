# demo-video-voiceover

An agent skill that turns a raw screen recording into a client-ready product demo:

- **AI voice-over** with Gemini TTS on Vertex AI, written to match what is on screen
- **Waits sped up** (spinners, "working on it", progress) to ~1.5 s with a *Processing... (sped up)* label
- **Noise cut**: errors and retries, OS popups, file-picker fumbling, rapid switching
- **Reordering**: e.g. move the part where you showed the input files to the start
- **Sync checks**: frame at every narration line, still-frame and overlap detection

Hand the agent a recording ("make a demo of this with a voice-over") and it follows the workflow in [SKILL.md](SKILL.md) with sensible defaults, so you don't have to spell them out each time.

## Install

Cursor (personal skill):

```bash
git clone https://github.com/sps014/demo-video-voiceover ~/.cursor/skills/demo-video-voiceover
```

Claude Code: clone into `~/.claude/skills/demo-video-voiceover` instead. Any agent that reads `SKILL.md` skills works the same way.

## Requirements

- [uv](https://docs.astral.sh/uv/): scripts declare their dependencies inline, `uv run` installs them on first use
- `ffmpeg` and `ffprobe` (`brew install ffmpeg`, `apt install ffmpeg`)
- Vertex AI access for the voice:

```bash
gcloud auth application-default login
mkdir -p ~/.config/demo-video-voiceover
cat > ~/.config/demo-video-voiceover/.env <<'EOF'
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
EOF
```

## Scripts

All take a working folder (`WORKDIR`) and are run with `uv run scripts/<name>.py`.

| Script | Does |
|---|---|
| `prepare.py VIDEO WORKDIR` | links the source, makes labelled contact sheets (1 frame / 5 s), detects still spans |
| `frames.py VIDEO OUT.jpg 412:430:1 ...` | grid of frames at given times, for pinning exact screen changes |
| `tts.py WORKDIR` | one Gemini TTS clip per line in `script.json` (only changed lines) |
| `render.py WORKDIR [--preview]` | builds `demo.mp4` from `edit_list.json` + `script.json`, cached per piece |
| `check.py WORKDIR [--preview]` | overlaps, silent gaps, long stills, and a sync contact sheet |

File formats and script-writing guidance: [reference.md](reference.md).

## Manual use

```bash
S=~/.cursor/skills/demo-video-voiceover/scripts
W=~/Desktop/demo-edit-myapp
uv run $S/prepare.py "Screen Recording.mov" $W
# write $W/edit_list.json and $W/script.json (see reference.md)
uv run $S/tts.py $W
uv run $S/render.py $W --preview && uv run $S/check.py $W --preview
uv run $S/render.py $W            # final: $W/demo.mp4
```

## License

MIT
