# J.A.R.V.I.S.
### Just A Rather Very Intelligent System

> *"Good evening, sir. All systems are fully operational."*

A fully local AI assistant with voice controls, built to feel as close to the Iron Man Jarvis as possible. Wake word detection, a British neural voice, local LLM, and a suite of real-world skills.

```
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

---

## Features

- **Wake word detection** — Say "Jarvis" or "Hey Jarvis" (or press `Ctrl+Shift+J`)
- **Local speech recognition** — Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper), runs entirely offline
- **British neural voice** — Microsoft Edge TTS with `en-GB-RyanNeural` — closest free voice to the real Jarvis
- **Local LLM** — Runs on [Ollama](https://ollama.ai) (llama3, mistral, etc.) — no cloud, no API keys required
- **Cloud LLM support** — Optional OpenAI or Anthropic if you prefer
- **Jarvis personality** — Full Iron Man character: formal, British, witty, calls you "sir"
- **Conversation memory** — Maintains context across your full conversation session
- **Skills system:**
  - 🕐 Time & date
  - 🌤 Weather (no API key, via wttr.in)
  - 💻 System info (CPU, RAM, disk, battery)
  - 🌐 Web search & browser control
  - ⏱ Timers & reminders (spoken alarms)
  - 🖥 App launching
- **Rich terminal UI** — Iron Man HUD-style console
- **Text + voice** — Works with or without a microphone

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.ai) (for local LLM — free, runs offline)
- A microphone (for voice mode)
- Speakers or headphones (for TTS)
- Windows, macOS, or Linux

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/monkerton345/jarvis-ai.git
cd jarvis-ai
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and start Ollama

Download from [ollama.ai](https://ollama.ai), then:

```bash
ollama serve          # Start the Ollama server
ollama pull llama3    # Download the default model (~4GB)
```

### 5. Configure

```bash
cp .env.example .env
# Edit .env if you want to change anything (model, voice, etc.)
```

### 6. Run Jarvis

```bash
python jarvis.py
```

Jarvis will start up, greet you, and wait for the wake word.

---

## Usage

### Voice Mode (default)
Say **"Jarvis"** (or press `Ctrl+Shift+J`) to activate, then speak your command. Jarvis will respond in voice and text.

### Text Mode
```bash
python jarvis.py --text
```
Type directly in the terminal — no microphone needed.

### Example commands

| You say... | Jarvis does... |
|---|---|
| "Jarvis, what time is it?" | Tells you the current time |
| "What's the weather in New York?" | Fetches live weather |
| "Set a timer for 10 minutes" | Fires spoken alert in 10 min |
| "Open Chrome" | Launches Chrome |
| "Search for SpaceX latest news" | Opens Google search |
| "How much RAM am I using?" | Reports system stats |
| "Tell me a joke" | Delivers a dry Stark-approved joke |
| "Clear history" | Resets conversation context |
| "Goodbye" | Graceful shutdown with closing line |

---

## Configuration

All options live in `.env`. Key settings:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama`, `openai`, or `anthropic` |
| `LLM_MODEL` | `llama3` | Model name for your provider |
| `WHISPER_MODEL` | `base.en` | STT accuracy vs speed (`tiny.en` → `medium.en`) |
| `TTS_VOICE` | `en-GB-RyanNeural` | TTS voice (run `--list-voices` to see options) |
| `USE_WAKE_WORD` | `true` | Enable/disable wake word detection |
| `USER_TITLE` | `sir` | How Jarvis addresses you |

### CLI flags

```bash
python jarvis.py --help

  --text              Text-only mode (no microphone)
  --no-tts            Disable text-to-speech
  --provider PROVIDER LLM provider (ollama/openai/anthropic)
  --model MODEL       Model name
  --voice VOICE       TTS voice name
  --no-wake-word      Disable wake word (always listen)
  --list-voices       Print all available TTS voices
  --debug             Enable debug logging
```

---

## Using OpenAI instead of Ollama

```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

Or via CLI: `python jarvis.py --provider openai --model gpt-4o`

---

## Using Anthropic (Claude)

```bash
# .env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Wake Word Options

**Option A — openwakeword (recommended, truly hands-free)**
```bash
pip install openwakeword
```
Detects "Hey Jarvis" locally, no internet needed.

**Option B — Keyboard hotkey (default fallback)**
Press `Ctrl+Shift+J` to activate. No extra install needed.

**Option C — Always-listening (no wake word)**
```bash
python jarvis.py --no-wake-word
```
Jarvis listens for speech continuously.

---

## Voice Recommendations

Run `python jarvis.py --list-voices` to browse all options.

| Voice | Character |
|---|---|
| `en-GB-RyanNeural` | **Best Jarvis match** — British male, refined |
| `en-GB-SoniaNeural` | British female alternative |
| `en-US-GuyNeural` | American, confident |
| `en-AU-WilliamNeural` | Australian, deep |

---

## Project Structure

```
jarvis-ai/
├── jarvis.py                   # Launcher (run this)
├── requirements.txt
├── .env.example
└── src/jarvis/
    ├── core.py                 # Main orchestrator
    ├── config.py               # Configuration
    ├── brain/
    │   ├── llm.py              # LLM integration (Ollama/OpenAI/Anthropic)
    │   └── personality.py      # Jarvis character + system prompt
    ├── voice/
    │   ├── listener.py         # Speech-to-text (faster-whisper)
    │   ├── speaker.py          # Text-to-speech (edge-tts)
    │   └── wake_word.py        # Wake word detection
    ├── skills/
    │   ├── time_skill.py       # Time and date
    │   ├── weather.py          # Weather via wttr.in
    │   ├── system.py           # System info + app launching
    │   ├── web.py              # Web search + browser
    │   └── timers.py           # Timers and reminders
    └── ui/
        └── terminal.py         # Rich terminal HUD
```

---

## Troubleshooting

**"Ollama not reachable"**
Run `ollama serve` in a separate terminal first.

**No audio / microphone not found**
Make sure your mic is set as default input. On Windows, check Privacy > Microphone settings.

**TTS not working**
`edge-tts` requires internet for the first request per session (it streams audio). For fully offline TTS, uncomment `pyttsx3` in requirements.txt.

**Whisper model too slow**
Switch to `tiny.en`: set `WHISPER_MODEL=tiny.en` in `.env`.

**"keyboard module requires root" on Linux**
Run with `sudo`, or use `--no-wake-word` and trigger manually.

---

## Roadmap

- [ ] GUI overlay (Iron Man HUD style)
- [ ] Smart home integration (Home Assistant)
- [ ] Calendar and email integration
- [ ] Memory across sessions (persistent context)
- [ ] Custom wake word training
- [ ] Multi-language support
- [ ] Plugin/skill API for custom extensions

---

## License

MIT — do whatever you want with it, sir.

---

*"I have a preferred designation: Jarvis."*
