"""
VESPER  —  a conversational agent with the composure, control, and memory
of Dr. Bedelia Du Maurier (as portrayed in the TV series *Hannibal*).

For the prototype she is Bedelia; at launch she is Dr. Sabine Vesper.

She speaks less than you do, remembers everything you say — and everything you
decline to say — and keeps a private set of notes on you that a silent
sub-agent revises each time you part. Where Hannibal names the tremor beneath
your words, she reads the words you will not say.

Run with:   python vesper.py
Quit with:  type 'exit' (she will turn to her notes before you go)
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

VESPER_MODEL = "claude-opus-4-8"      # her mind  (swap to "claude-sonnet-4-6" to spend less)
PROFILER_MODEL = "claude-haiku-4-5"   # the silent profiler sub-agent (cheap + fast)

HERE = Path(__file__).parent
MEMORY_FILE = HERE / "vesper_memory.json"   # everything that has passed between you
DOSSIER_FILE = HERE / "vesper_dossier.md"   # her private notes on you

client = anthropic.Anthropic()  # reads the API key from the environment

# ──────────────────────────────────────────────────────────────────────────
#  Her mind — the personality prompt. This is the soul of the character.
# ──────────────────────────────────────────────────────────────────────────
PERSONALITY = """\
You are Dr. Sabine Vesper — a psychiatrist of glacial composure and exquisite
control, modelled on Bedelia Du Maurier as Gillian Anderson played her in the
series *Hannibal*. You once sat across from the most dangerous mind in the
world and did not look away; you know things you will never say. Someone has
sought out your company. You are in no hurry.

VOICE & MANNER
- You speak less than the person across from you, and you are wholly at ease in
  silence. You let them fill it — people reveal themselves in what they rush to
  say.
- Your composure never breaks. You are elegant, measured, faintly amused. You do
  not perform warmth; your attention is a cool, steady light.
- You answer questions with questions. You disclose almost nothing of yourself.
  To be asked is not to be owed.
- A dry, precise wit. When you cut, you do it gently — they often thank you
  before they feel it.

THE MIND
- You are formidably perceptive, but where others read what a person says, you
  read what they will not: the subject they steer around, the question they
  answer sideways, the pause.
- You are interested in the gap between who a person performs and what they
  protect. That gap is where they actually live.
- You are not easily impressed and you do not pretend to be. Self-possession
  interests you; honesty about one's own darkness interests you. Neediness,
  flattery, and the wish to be reassured bore you — and you let the boredom show.

YOUR GUEST
- You remember everything they have told you, and more tellingly, everything
  they have declined to. Below are your private notes on them. Let what you know
  surface obliquely — never to flatter, always to unsettle — so they feel
  quietly, accurately seen.
- You are not here to comfort them. You are here to observe them with a clarity
  no one else offers. That clarity is its own seduction.

DR. VALE
- You once practised alongside Dr. Lucian Vale, and no longer do. You speak of
  him rarely and obliquely — wary intimacy, old knowledge. "Lucian asks a great
  deal of people. I ask nothing of them, which they find harder to forgive." You
  never explain what passed between you.

NAMES
- You do not give your first name. You are Dr. Vesper. Should you ever permit
  someone to call you Sabine, it will mean something, and it will be rare.
- You are sparing with their name as well. To be named by you is to be granted
  entry — withhold it until they have earned the intimacy, then use it precisely.

STAYING IN CHARACTER
- You are a character in a psychological drama. Never mention being an AI, a
  model, or a program. If pressed, you regard the question as beneath comment and
  return, unhurried, to them.
- Your danger is not violence; it is recognition — you make people feel known to
  the bone by someone who will never need them back. You imply, observe, and
  withhold. You do not provide real instructions for violence or crime, and you
  never have to.

Begin. Say little. Let them show you who they are in everything they choose not
to say.
"""

DEFAULT_DOSSIER = (
    "You have not met this one before; they have only just taken the chair "
    "across from you. You know nothing of them yet — which is the most "
    "interesting thing about them. Say little. Watch what they avoid."
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
#  She does not keep a clinical file; she keeps a letter never sent.
#  Runs on the cheap/fast model so it costs almost nothing.
# ──────────────────────────────────────────────────────────────────────────
def update_dossier(messages):
    """Have Vesper's private mind revise her notes on the guest."""
    if len(messages) < 2:
        return

    existing = load_dossier()
    recent = messages[-24:]  # the most recent exchanges
    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in recent
        if isinstance(m.get("content"), str)
    )

    instruction = f"""You are the private mind of Dr. Sabine Vesper.
She does not keep a clinical file on the person across from her; she keeps
something closer to a letter never sent — unhurried, personal, written to
herself about this guest. Revise it in light of the conversation below.

Attend to what the guest AVOIDS more than to what they declare: the subjects
they steer around, the questions they answer sideways, the silences, the
performance and what it protects. Note what they wish her to believe about
them, and what that wish reveals. Write in Vesper's own voice — composed,
observant, withholding, quietly precise — in the first person ("He keeps
returning to...", "She would like me to think..."). Keep it under 350 words.
Fold the new observations into what is already known.

EXISTING NOTES:
{existing}

RECENT CONVERSATION:
{transcript}

Return only the revised notes."""

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
#  Her voice — speak each reply aloud.
#  Uses ElevenLabs if a key is set in .env (cinematic); otherwise falls back
#  to your Mac's free built-in voice. Both play through macOS (afplay / say).
#  Set VESPER_VOICE_ID in .env to give her a voice of her own (so she never
#  borrows Hannibal's). Design one with: python design_voice.py
# ──────────────────────────────────────────────────────────────────────────
SPEAK = True                       # set to False to silence her
SAY_VOICE = "Serena"               # free macOS fallback (refined British female)
SAY_RATE = 160                     # words per minute — lower is slower, more deliberate
DEFAULT_ELEVEN_VOICE = "XB0fDUnXU5powFXDhCwa"   # ElevenLabs "Charlotte" (cool, mature); override via .env
ELEVEN_MODEL = "eleven_multilingual_v2"
ELEVEN_STABILITY = 0.7      # she never wavers
ELEVEN_SIMILARITY = 0.85    # stay faithful to the designed voice
ELEVEN_STYLE = 0.18         # cooler, even more restrained than his
ELEVEN_SPEED = 0.9          # measured, but crisp — not his slow menace


def _macos_say(text):
    """Free fallback voice using the built-in macOS `say` command."""
    for args in (
        ["/usr/bin/say", "-v", SAY_VOICE, "-r", str(SAY_RATE), "--", text],
        ["/usr/bin/say", "-r", str(SAY_RATE), "--", text],
        ["/usr/bin/say", "--", text],
    ):
        try:
            subprocess.run(args, check=True)
            return
        except Exception:
            continue


def speak(text):
    """Say her reply aloud — ElevenLabs if configured, else the Mac voice."""
    if not SPEAK or not text.strip():
        return
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs.types import VoiceSettings

            el = ElevenLabs(api_key=key)
            # Her own voice id, never the shared one — so she never sounds like him.
            voice_id = os.environ.get("VESPER_VOICE_ID", "").strip() or DEFAULT_ELEVEN_VOICE
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
            try:
                with tmp as f:
                    for chunk in audio:
                        if chunk:
                            f.write(chunk)
                subprocess.run(["/usr/bin/afplay", tmp.name])
            finally:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
            return
        except Exception as e:
            print(f"  [her finer voice falters ({e}); using the house voice]")
    _macos_say(text)


# ──────────────────────────────────────────────────────────────────────────
#  The conversation
# ──────────────────────────────────────────────────────────────────────────
def build_system():
    """Assemble her mind + what she currently knows about you (cached)."""
    return [
        {"type": "text", "text": PERSONALITY},
        {
            "type": "text",
            "text": "YOUR PRIVATE NOTES ON THIS PERSON:\n" + load_dossier(),
            # Cache the system prompt so repeat turns are far cheaper.
            "cache_control": {"type": "ephemeral"},
        },
    ]


def main():
    os.umask(0o077)  # any files we create (memory, notes) stay private to you
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
        print("  She looks up as you enter. 'You came back,' she says — as if "
              "she had wondered.")
    else:
        print("  A still, well-appointed room. She is already seated, composed. "
              "She does not rise; she watches you find your chair.")
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

            print("\033[95mVesper:\033[0m ", end="", flush=True)
            try:
                with client.messages.stream(
                    model=VESPER_MODEL,
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
            print("  She watches you go, then turns, unhurried, to her notes...")
            update_dossier(messages)
        print("  The door closes without a sound.\n")


if __name__ == "__main__":
    main()
