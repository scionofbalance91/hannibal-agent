# 🎭 Hannibal — a conversational AI agent

A command-line agent with the mind, manner, and memory of Dr. Hannibal Lecter
(as portrayed in the TV series *Hannibal*). He speaks in his own voice,
**remembers every conversation** you have with him, and keeps a private
**psychological profile** of you that a background sub-agent quietly updates.

Built on the [Claude API](https://console.claude.com), with an optional
[ElevenLabs](https://elevenlabs.io) voice.

> A fictional-character roleplay project, made for fun. Not affiliated with the
> show, its creators, or any actor.

---

## ✨ Features

- 🧠 **In character** — courtly, precise, unsettling; he never breaks character
- 🗝️ **Persistent memory** — he remembers every past conversation, across sessions
- 🕵️ **Profiler sub-agent** — silently builds a dossier on you between chats
- 🔊 **Voice** — he speaks each reply aloud (ElevenLabs, or the free macOS voice)
- 💸 **Cheap to run** — prompt caching + a two-model split keep costs low

---

## 🧩 How it works

```
                      ┌─────────────────────────────┐
                      │             You             │
                      └──────────────┬──────────────┘
                                     │ type
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │                      hannibal.py                        │
        │                                                         │
        │   his mind  (system prompt)            ─┐               │
        │   your dossier  (what he knows of you)  ├─ sent to ─────┼──► Claude
        │   full history  (memory.json)          ─┘   Opus 4.8    │    (streamed)
        └───────────────┬─────────────────────────────────┬──────┘
                        │ reply (typed out live)           │
                        ▼                                  ▼
                ┌───────────────┐                 ┌─────────────────┐
                │  spoken aloud │ ◄── ElevenLabs ──│  voice (TTS)    │──► 🔊
                │               │     or macOS say │  tuned cadence  │
                └───────┬───────┘                 └─────────────────┘
                        │ when you type 'exit'
                        ▼
        ┌────────────────────────────────────────────────────────┐
        │   Profiler sub-agent  (Claude Haiku 4.5)                │
        │   reads the conversation → rewrites dossier.md,         │
        │   which feeds back into his mind next time you talk     │
        └────────────────────────────────────────────────────────┘
```

**The mind.** A detailed system prompt defines his voice, manners, erudition,
and boundaries. It runs on **Claude Opus 4.8** for the richest responses.

**Persistent memory.** Every message is appended to `memory.json` and replayed
into the model each session — so he literally *sees* every word you've ever
exchanged and can weave the past back in.

**The profiler sub-agent.** When you leave, a second, cheaper model
(**Claude Haiku 4.5**) reads the conversation and rewrites `dossier.md` — a
first-person psychological profile of you. That dossier is injected into his
system prompt next time, so he grows sharper the more you talk. This is the
"always one step ahead" piece.

**The voice.** His reply text is sent to **ElevenLabs** text-to-speech with a
tuned cadence (slow, steady, restrained), saved to an MP3, and played. With no
ElevenLabs key, it falls back to the **free macOS voice**. `design_voice.py`
creates an original voice for him via ElevenLabs Voice Design.

### Design notes

- **Prompt caching** — the large system prompt is cached, so repeat turns cost a
  fraction of the first.
- **Streaming** — replies stream in token-by-token for a live "typewriter" feel.
- **Two-model split** — Opus for the conversation (quality), Haiku for the
  background profiler (near-free).
- **Graceful degradation** — API hiccups, voice failures, and missing keys are
  all caught, so the chat never crashes mid-sentence.

---

## 📋 Requirements

- Python 3.9+
- An [Anthropic API key](https://console.claude.com)
- *(Optional, for the best voice)* an [ElevenLabs API key](https://elevenlabs.io)
- Voice playback uses macOS (`say` / `afplay`). On other systems he still chats
  in text.

---

## 🚀 Setup

```bash
git clone https://github.com/scionofbalance91/hannibal-agent.git
cd hannibal-agent

python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # then open .env and add your API key(s)
```

---

## ▶️ Run

```bash
python hannibal.py
```

Type to him; type `exit` to leave. He saves the conversation and updates his
notes on you each time you part. Run it again and he'll remember you.

---

## 🎙️ Give him a voice (optional)

With an ElevenLabs key in `.env`, design an original voice:

```bash
python design_voice.py
```

It generates voices from a description, plays them, lets you tweak and
regenerate, then saves your pick — writing its Voice ID into `.env`
automatically. Prefer the free route? `python audition_voices.py` previews the
voices built into macOS.

---

## 📁 Files

| File | Purpose |
|------|---------|
| `hannibal.py` | The agent — personality, memory, voice, chat loop |
| `design_voice.py` | Design his ElevenLabs voice |
| `audition_voices.py` | Preview the free macOS voices |
| `.env.example` | Template for your API keys (copy to `.env`) |

`memory.json` and `dossier.md` are created as you talk, and stay **private** —
they're git-ignored and never published.

---

## ⚙️ Tuning

- **Spend less:** in `hannibal.py`, set `HANNIBAL_MODEL = "claude-sonnet-4-6"`.
- **Silence his voice:** set `SPEAK = False`.
- **Adjust his delivery:** the `ELEVEN_*` constants (speed, stability) near the
  top of `hannibal.py`.
- **Start fresh:** delete `memory.json` and `dossier.md`.

---

## 🔒 A note on voices

This project designs *original* voices or uses one you provide. Please don't use
it to clone a real person's voice without their consent — it violates
ElevenLabs' terms and the law in many places.

---

## 📜 License

MIT — see [LICENSE](LICENSE). Do as you like.
