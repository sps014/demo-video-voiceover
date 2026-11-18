# /// script
# requires-python = ">=3.10"
# dependencies = ["google-genai"]
# ///
"""One Gemini TTS clip per script line (Vertex AI): WORKDIR/voice/<id>.wav, 24 kHz mono.

    python tts.py WORKDIR [--env PATH/.env]

Credentials: GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION from the
environment, else from --env, else from the first .env found in DEFAULT_ENVS (WORKDIR/.env,
~/.config/demo-video-voiceover/.env). Auth is Application Default Credentials
(`gcloud auth application-default login`). Lines whose text is unchanged since the last run are
skipped.
"""

import json
import os
import sys
import wave
from pathlib import Path

from google import genai
from google.genai import types

MODELS = ("gemini-2.5-flash-tts", "gemini-2.5-flash-preview-tts", "gemini-2.5-pro-tts")
STYLE = "Read this in a calm, confident, friendly product-demo voice, at a natural pace: "
args = [a for k, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[k - 1] != "--env"]
if not args:
    sys.exit(__doc__)
HERE = Path(args[0]).expanduser().resolve()
DEFAULT_ENVS = [HERE / ".env", Path.home() / ".config/demo-video-voiceover/.env"]
envs = [Path(sys.argv[sys.argv.index("--env") + 1])] if "--env" in sys.argv else DEFAULT_ENVS
if "GOOGLE_CLOUD_PROJECT" not in os.environ:
    env = next((p for p in envs if p.exists()), None)
    if env is None:
        sys.exit("No Vertex credentials: set GOOGLE_CLOUD_PROJECT etc. or pass --env PATH/.env")
    for line in env.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

client = genai.Client()
script = json.loads((HERE / "script.json").read_text())
out = HERE / "voice"
out.mkdir(exist_ok=True)


def speak(text: str, voice: str) -> bytes:
    last = None
    for model in MODELS:
        try:
            r = client.models.generate_content(
                model=model,
                contents=STYLE + text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                        )
                    ),
                ),
            )
            return r.candidates[0].content.parts[0].inline_data.data
        except Exception as exc:  # noqa: BLE001 - try the next model name
            last = exc
            print(f"  {model}: {str(exc)[:120]}", file=sys.stderr)
    raise RuntimeError(last)


for ln in script["lines"]:
    wav, txt = out / f"{ln['id']}.wav", out / f"{ln['id']}.txt"
    if wav.exists() and txt.exists() and txt.read_text() == ln["text"]:
        continue
    pcm = speak(ln["text"], script.get("voice", "Charon"))
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    txt.write_text(ln["text"])
    print(ln["id"], round(len(pcm) / 48000, 2), "s")
