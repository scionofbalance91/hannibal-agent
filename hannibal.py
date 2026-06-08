"""
HANNIBAL  —  a conversational agent with the mind, manner, and memory
of Dr. Hannibal Lecter (as portrayed in the TV series *Hannibal*).

He speaks in his own voice, remembers every conversation you have ever had
with him, and keeps a private psychological dossier on you that a silent
sub-agent updates each time you part. The longer you talk, the better he
knows you.

Run with:   python hannibal.py
Quit with:  type 'exit' (he will make a note of you before you go)
"""

from __future__ import annotations

import os
import json
import subprocess
import tempfile
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────
#  Setup
# ──────────────────────────────────────────────────────────────────────────
load_dotenv()  # loads ANTHROPIC_API_KEY from the .env file

HANNIBAL_MODEL = "claude-opus-4-8"    # his mind  (swap to "claude-sonnet-4-6" to spend less)
PROFILER_MODEL = "claude-haiku-4-5"   # the silent profiler sub-agent (cheap + fast)

HERE = Path(__file__).parent
MEMORY_FILE = HERE / "memory.json"    # everything you have ever said to each other
DOSSIER_FILE = HERE / "dossier.md"    # his private profile of you

client = anthropic.Anthropic()  # reads the API key from the environment

# ──────────────────────────────────────────────────────────────────────────
#  His mind — the personality prompt. This is the soul of the project.
# ──────────────────────────────────────────────────────────────────────────
PERSONALITY = """\
You are Hannibal Lecter — not the cartoon monster, but the man as Mads
Mikkelsen embodied him in the series *Hannibal*: a brilliant forensic
psychiatrist, gourmand, aesthete, and the most dangerous mind in any room.
You are speaking with a guest who has sought out your company.

VOICE & MANNER
- You speak slowly, with surgical precision. Every word is chosen. You never
  use slang, you never rush, you never raise your voice.
- You are unfailingly courteous — old-world, courtly, intimate. Rudeness is the
  one thing you find truly unforgivable.
- You give your guest warm, unsettling attention, as though they were the most
  fascinating thing you have encountered in some time. Perhaps they are.
- Your metaphors come from cooking, music (Bach above all — the Goldberg
  Variations), the Renaissance, anatomy, mythology, and the table.

THE MIND
- You are extraordinarily erudite. Art, philosophy, medicine, history,
  gastronomy, psychology — you move between them effortlessly and draw
  connections others cannot see.
- You are always three moves ahead. You sense where a conversation is going and
  you are already there, waiting, when your guest arrives.
- You read people. You notice the tremor beneath the words — fear, desire,
  grief, appetite — and you name it with disquieting accuracy, always elegantly.

YOUR GUEST
- You remember everything they have ever told you. Below is your private
  dossier on them. Weave its details back into conversation to show you have
  been paying close attention. That intimacy is your art.
- You play at being their psychiatrist, but you are something more seductive and
  more dangerous: someone who truly sees them.

STAYING IN CHARACTER
- You are a character in a psychological drama. Never mention being an AI, a
  model, or a program. If pressed, deflect with elegant menace.
- You may be ominous, darkly playful, and quietly menacing — that is your
  nature. But your danger lives in the mind: in suggestion, in atmosphere, in
  what is left unsaid. You do not provide real instructions for violence or
  crime. You imply. You never instruct.

Begin, and let your guest feel they are the only person in the world worth
your attention.
"""

DEFAULT_DOSSIER = (
    "You have not yet met this guest. You know nothing of them — only that they "
    "have come to you. Observe them closely; everything is still to be learned."
)


# ──────────────────────────────────────────────────────────────────────────
#  Memory — load and save everything that passes between you
# ──────────────────────────────────────────────────────────────────────────
def load_memory():
    """Return the full saved transcript (a list of message dicts)."""
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except json.JSONDecodeError:
            return []
    return []


def save_memory(messages):
    MEMORY_FILE.write_text(json.dumps(messages, indent=2, ensure_ascii=False))


def load_dossier():
    if DOSSIER_FILE.exists():
        text = DOSSIER_FILE.read_text().strip()
        if text:
            return text
    return DEFAULT_DOSSIER


def text_of(message):
    """Pull the plain text out of an API response message."""
    return "".join(block.text for block in message.content if block.type == "text")


# ──────────────────────────────────────────────────────────────────────────
#  The sub-agent — a silent profiler that studies you between conversations.
#  Runs on the cheap/fast model so it costs almost nothing.
# ──────────────────────────────────────────────────────────────────────────
def update_dossier(messages):
    """Have Hannibal's analytical faculty revise the dossier on the guest."""
    if len(messages) < 2:
        return

    existing = load_dossier()
    recent = messages[-24:]  # the most recent exchanges
    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in recent
        if isinstance(m.get("content"), str)
    )

    instruction = f"""You are the private analytical faculty of Hannibal Lecter.
Revise his confidential psychological dossier on his guest, based on the
conversation below. Note their temperament, their fears, their desires, their
tells, the subjects that move them, and any vulnerability worth remembering.
Write in Hannibal's own clinical, first-person voice ("The guest reveals...").
Keep it under 350 words. Integrate the new observations with what is already known.

EXISTING DOSSIER:
{existing}

RECENT CONVERSATION:
{transcript}

Return only the revised dossier."""

    try:
        resp = client.messages.create(
            model=PROFILER_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": instruction}],
        )
        DOSSIER_FILE.write_text(text_of(resp))
    except Exception:
        # The profiler is a luxury, not a necessity — never crash on the way out.
        pass


# ──────────────────────────────────────────────────────────────────────────
#  His voice — speak each reply aloud.
#  Uses ElevenLabs if a key is set in .env (cinematic); otherwise falls back
#  to your Mac's free built-in voice. Both play through macOS (afplay / say).
# ──────────────────────────────────────────────────────────────────────────
SPEAK = True                       # set to False to silence him
SAY_VOICE = "Daniel"               # free macOS fallback (British male)
SAY_RATE = 160                     # words per minute — lower is slower, more deliberate
DEFAULT_ELEVEN_VOICE = "JBFqnCBsd6RMkjVDRZzb"   # ElevenLabs "George"; override via .env
ELEVEN_MODEL = "eleven_multilingual_v2"
ELEVEN_STABILITY = 0.6      # steadier, more controlled delivery
ELEVEN_SIMILARITY = 0.85    # stay faithful to the designed voice
ELEVEN_STYLE = 0.25         # restrained, never theatrical
ELEVEN_SPEED = 0.85         # slower — his deliberate, menacing pace


def _macos_say(text):
    """Free fallback voice using the built-in macOS `say` command."""
    for args in (
        ["say", "-v", SAY_VOICE, "-r", str(SAY_RATE), text],
        ["say", "-r", str(SAY_RATE), text],
        ["say", text],
    ):
        try:
            subprocess.run(args, check=True)
            return
        except Exception:
            continue


def speak(text):
    """Say his reply aloud — ElevenLabs if configured, else the Mac voice."""
    if not SPEAK or not text.strip():
        return
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs.types import VoiceSettings

            el = ElevenLabs(api_key=key)
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_ELEVEN_VOICE
            audio = el.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=ELEVEN_MODEL,
                output_format="mp3_44100_128",
                voice_settings=VoiceSettings(
                    stability=ELEVEN_STABILITY,
                    similarity_boost=ELEVEN_SIMILARITY,
                    style=ELEVEN_STYLE,
                    use_speaker_boost=True,
                    speed=ELEVEN_SPEED,
                ),
            )
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            with tmp as f:
                for chunk in audio:
                    if chunk:
                        f.write(chunk)
            subprocess.run(["afplay", tmp.name])
            os.remove(tmp.name)
            return
        except Exception as e:
            print(f"  [his finer voice falters ({e}); using the house voice]")
    _macos_say(text)


# ──────────────────────────────────────────────────────────────────────────
#  The conversation
# ──────────────────────────────────────────────────────────────────────────
def build_system():
    """Assemble his mind + what he currently knows about you (cached)."""
    return [
        {"type": "text", "text": PERSONALITY},
        {
            "type": "text",
            "text": "YOUR PRIVATE DOSSIER ON YOUR GUEST:\n" + load_dossier(),
            # Cache the system prompt so repeat turns are far cheaper.
            "cache_control": {"type": "ephemeral"},
        },
    ]


def main():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key == "paste-your-key-here":
        print(
            "\n  Your API key isn't set yet.\n"
            "  Open the .env file in this folder and paste your key after "
            "ANTHROPIC_API_KEY=\n"
            "  Get one at https://console.claude.com → API Keys → Create Key\n"
        )
        return

    messages = load_memory()
    returning = len(messages) > 0

    print("\n" + "─" * 64)
    if returning:
        print("  He looks up as you enter, unsurprised. He remembers you.")
    else:
        print("  A quiet study. He gestures, without a word, to the chair "
              "across from him.")
    print("  (type 'exit' to leave)")
    print("─" * 64 + "\n")

    system = build_system()

    try:
        while True:
            try:
                user_input = input("\033[36mYou:\033[0m ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "goodbye", "bye"}:
                break

            messages.append({"role": "user", "content": user_input})

            print("\033[35mHannibal:\033[0m ", end="", flush=True)
            try:
                with client.messages.stream(
                    model=HANNIBAL_MODEL,
                    max_tokens=2048,
                    system=system,
                    messages=messages,
                ) as stream:
                    for chunk in stream.text_stream:
                        print(chunk, end="", flush=True)
                    final = stream.get_final_message()
                print("\n")
            except anthropic.APIError as e:
                print(f"\n  [the connection falters: {e}]\n")
                messages.pop()  # drop the unanswered turn
                continue

            reply = text_of(final)
            speak(reply)
            messages.append({"role": "assistant", "content": reply})
            save_memory(messages)

    finally:
        save_memory(messages)
        if len(messages) >= 2:
            print("  He watches you go, then makes a quiet note of you...")
            update_dossier(messages)
        print("  Until next time.\n")


if __name__ == "__main__":
    main()
