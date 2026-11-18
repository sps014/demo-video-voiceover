# demo-video-voiceover

An agent skill that turns a raw screen recording into a client-ready product demo:

- **AI voice-over** with Gemini TTS on Vertex AI, written to match what is on screen
- **Waits sped up** (spinners, "working on it", progress) to ~1.5 s with a *Processing... (sped up)* label
- **Noise cut**: errors and retries, OS popups, file-picker fumbling, rapid switching
- **Reordering**: e.g. move the part where you showed the input files to the start
- **Sync checks**: frame at every narration line, still-frame and overlap detection

Hand the agent a recording ("make a demo of this with a voice-over") and it follows the workflow in [SKILL.md](SKILL.md) with sensible defaults, so you don't have to spell them out each time.

## Install

The repo is the skill: clone it into the skills folder your agent reads. The agent picks it up from the `description` in `SKILL.md` whenever you hand it a recording and ask for a demo, voice-over or clean-up.

| Agent | Personal (all projects) | Project only (commit it with the repo) |
|---|---|---|
| Cursor | `~/.cursor/skills/demo-video-voiceover` | `.cursor/skills/demo-video-voiceover` |
| Codex (CLI, IDE extension, app) | `~/.agents/skills/demo-video-voiceover` (older versions: `~/.codex/skills/`) | `.agents/skills/demo-video-voiceover` |
| Claude Code | `~/.claude/skills/demo-video-voiceover` | `.claude/skills/demo-video-voiceover` |

```bash
# Cursor
git clone https://github.com/sps014/demo-video-voiceover ~/.cursor/skills/demo-video-voiceover
# Codex
git clone https://github.com/sps014/demo-video-voiceover ~/.agents/skills/demo-video-voiceover
# Claude Code
git clone https://github.com/sps014/demo-video-voiceover ~/.claude/skills/demo-video-voiceover
```

Restart the agent (or start a new session) after installing. Update later with `git -C <that folder> pull`.

### Codex

Once installed, Codex lists the skill under `/skills`. Ask normally, or name it:

```text
$demo-video-voiceover make a client demo of ~/Desktop/recording.mov with a voice-over
```

Codex runs shell commands in a sandbox. Rendering needs `ffmpeg`, `uv` (which downloads packages on first run) and network access to Vertex AI for the voice, so allow network access for the session (for example `codex --sandbox workspace-write -c sandbox_workspace_write.network_access=true`) or approve the commands when asked.

### Any other agent

Any harness that can read files and run shell commands can use it, even without built-in skill support:

1. Clone the repo anywhere, e.g. `~/skills/demo-video-voiceover`.
2. Point the agent at it from its instructions file (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, a system prompt, ...):

   ```markdown
   ## Demo videos
   When I share a screen recording and ask for a demo, voice-over or clean-up, read
   ~/skills/demo-video-voiceover/SKILL.md and follow it. Its scripts are in
   ~/skills/demo-video-voiceover/scripts/ and run with `uv run`.
   ```

3. Or, one-off, start the prompt with: "Read ~/skills/demo-video-voiceover/SKILL.md and follow it for this recording: ...".

The agent needs to be able to view images (it reads contact sheets and sync frames to map the recording and check the result). Text-only models can still render from a hand-written `edit_list.json` and `script.json`, but can't do the sync check.

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
