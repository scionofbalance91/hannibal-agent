"""
Audition the voices installed on your Mac, to choose one for Hannibal.

    python audition_voices.py              # hear every English voice
    python audition_voices.py "Daniel"     # hear just one (replay a favourite)

Tip: for far better quality, download richer voices first —
     System Settings → Accessibility → Spoken Content → System Voice →
     Manage Voices → get the "Enhanced" / "Premium" English (UK) male voices.
"""

import subprocess
import sys

LINE = (
    "Good evening. I have been expecting you. "
    "Sit, and tell me everything — leave nothing off the plate."
)
RATE = "160"  # words per minute; lower is slower and more deliberate


def installed_english_voices():
    """Return [(name, locale), ...] for English voices `say` can use."""
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    voices = []
    for row in out.splitlines():
        parts = row.split()
        for i, token in enumerate(parts):
            # the locale token looks like en_GB / en_US / en_AU ...
            if "_" in token and token.split("_")[0].isalpha():
                name = " ".join(parts[:i])
                if token.startswith("en") and name:
                    voices.append((name, token))
                break
    return voices


def say(name):
    print(f"  ♪ {name}")
    subprocess.run(["say", "-v", name, "-r", RATE, LINE])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        say(" ".join(sys.argv[1:]))
    else:
        voices = installed_english_voices()
        print(f"\nAuditioning {len(voices)} English voices "
              f"(press Ctrl+C to stop)\n")
        for name, _ in voices:
            say(name)
        print("\nHeard one you like? Tell Claude the name and he'll make it "
              "Hannibal's voice.\n")
