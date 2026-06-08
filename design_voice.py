"""
Design Hannibal's voice with ElevenLabs — no dashboard required.

Needs ELEVENLABS_API_KEY in your .env.

    python design_voice.py

It generates original voices from a written description, plays each one, and
lets you regenerate, tweak the description, or pick one — then saves your choice
and writes its Voice ID into .env automatically.

Getting closer to a specific sound:
  • Edit VOICE_DESCRIPTION below to be as specific as you can (age, depth,
    accent, pace, texture, mood), or tweak it live with the 't' option.
  • OPTIONAL: steer the timbre with a reference recording of YOUR OWN voice
    (or audio you have the rights to) — set REFERENCE_AUDIO to its path.
"""

from __future__ import annotations

import os
import base64
import tempfile
import subprocess
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).parent
ENV_FILE = HERE / ".env"
load_dotenv()

# A detailed description of the qualities you want. Be specific — this is the
# single biggest lever on how the voice turns out.
VOICE_DESCRIPTION = (
    "A man in his mid-fifties with a very deep, smooth, resonant low baritone. "
    "He speaks softly and slowly — almost a hushed murmur — with long, deliberate "
    "pauses and surgical precision. A subtle Scandinavian, faintly Danish accent "
    "colours his refined, formal English. His tone is calm, controlled, and nearly "
    "flat, with little emotional inflection — warmth and menace held in perfect "
    "balance. Velvety, breathy, intimate, hypnotic; a gracious host who is also a "
    "predator."
)

# What he says in the auditions (100–1000 characters).
SAMPLE_TEXT = (
    "Good evening. I have been expecting you. Please, sit — the chair by the fire. "
    "You look as though you have carried the cold a long way. Tell me everything, "
    "and leave nothing off the plate; we have all the time in the world."
)

# OPTIONAL reference audio to steer the timbre. Use YOUR OWN voice, or audio you
# have the rights to — not a copyrighted recording of someone else.
# Example: REFERENCE_AUDIO = HERE / "my_voice.mp3"   (10–30s, clean, one speaker)
REFERENCE_AUDIO = ""
PROMPT_STRENGTH = 0.5   # with reference audio: 0 = follow text, 1 = follow audio


def play_base64_mp3(b64):
    data = base64.b64decode(b64)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    with tmp as f:
        f.write(data)
    subprocess.run(["afplay", tmp.name])
    os.remove(tmp.name)


def set_env_voice_id(voice_id):
    lines = ENV_FILE.read_text().splitlines()
    out, found = [], False
    for line in lines:
        if line.startswith("ELEVENLABS_VOICE_ID="):
            out.append(f"ELEVENLABS_VOICE_ID={voice_id}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"ELEVENLABS_VOICE_ID={voice_id}")
    ENV_FILE.write_text("\n".join(out) + "\n")


def reference_b64():
    if not REFERENCE_AUDIO:
        return None
    p = Path(REFERENCE_AUDIO)
    if not p.exists():
        print(f"  (reference audio not found at {p} — ignoring it)")
        return None
    return base64.b64encode(p.read_bytes()).decode()


def generate(client, description):
    kwargs = dict(voice_description=description, text=SAMPLE_TEXT)
    ref = reference_b64()
    if ref:
        kwargs["reference_audio_base_64"] = ref
        kwargs["prompt_strength"] = PROMPT_STRENGTH
    return client.text_to_voice.design(**kwargs).previews or []


def play_all(previews):
    for i, p in enumerate(previews, 1):
        print(f"  ── Voice {i} ──")
        play_base64_mp3(p.audio_base_64)


def main():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        print(
            "\n  No ELEVENLABS_API_KEY found in .env.\n"
            "  Sign up at https://elevenlabs.io, create an API key, paste it into\n"
            "  .env after ELEVENLABS_API_KEY=, then run me again.\n"
        )
        return

    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=key)
    description = VOICE_DESCRIPTION

    chosen = None
    while chosen is None:
        print("\n  Designing voices from the description... (a moment)\n")
        try:
            previews = generate(client, description)
        except Exception as e:
            print(f"  Generation failed: {e}\n  Try again, or adjust the description.\n")
            if input("  Press Enter to retry, or 'q' to quit: ").strip().lower() == "q":
                return
            continue

        if not previews:
            print("  No voices came back — trying again.")
            continue

        print(f"  {len(previews)} voices generated. Listen:\n")
        play_all(previews)

        while True:
            ans = input(
                f"\n  Pick a voice (1-{len(previews)}), or:\n"
                "    a = generate again (same description)\n"
                "    t = tweak the description, then generate\n"
                "    r = replay them\n"
                "    q = quit\n"
                "  > "
            ).strip().lower()

            if ans == "q":
                print("  Cancelled — nothing saved.")
                return
            if ans == "r":
                play_all(previews)
                continue
            if ans == "a":
                break  # regenerate with same description
            if ans == "t":
                extra = input(
                    "  Describe the change (e.g. 'deeper, slower, stronger Danish "
                    "accent, raspier'): "
                ).strip()
                if extra:
                    description = VOICE_DESCRIPTION + " Additionally: " + extra + "."
                break
            if ans.isdigit() and 1 <= int(ans) <= len(previews):
                chosen = previews[int(ans) - 1]
                break
            print("  Please type a number, or a / t / r / q.")

    print("\n  Saving him to your ElevenLabs account...")
    try:
        voice = client.text_to_voice.create(
            voice_name="Hannibal",
            voice_description=description,
            generated_voice_id=chosen.generated_voice_id,
        )
    except Exception as e:
        print(f"  Could not save the voice: {e}")
        return

    set_env_voice_id(voice.voice_id)
    print(f"\n  ✓ His voice is saved (Voice ID {voice.voice_id}) and written to .env.\n")
    print("  Now run:  python hannibal.py\n")


if __name__ == "__main__":
    main()
