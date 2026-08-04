# Transcribe — Audio → Transcripts → GitHub

> **Local speech-to-text for Hermes.** Drop a Dropbox link, upload a file, or point at a URL — get two clean transcripts (verbatim + intended) committed to your own private GitHub repo, one dated folder per audio. Runs entirely on your machine; no cloud transcription APIs.

## Install

Copy-paste this to your Hermes agent (any profile):

```text
"Install the transcribe skill from github.com/ciberjohn/Hermes-Skills into ~/.hermes/skills/media/transcribe/. Copy SKILL.md into that directory and scripts/transcribe.py into ~/.hermes/skills/media/transcribe/scripts/. Then set it up: create a Python 3.10+ virtual environment for CrisperWhisper, install the package with `pip install crisperwhisper[all]` in it, install ffmpeg (sudo apt-get install -y ffmpeg on Debian/Ubuntu), and create a private GitHub repository for transcripts with a local clone. Then ask me these questions one at a time:
1. Where should the CrisperWhisper virtual environment live? `{{TRANSCRIBE_VENV_PATH}}` (default ~/.venvs/crisperwhisper)
2. Where is my private transcripts repository checked out locally? `{{TRANSCRIPTS_REPO_PATH}}` (default ~/transcripts)
3. What is the git remote URL of that repository? `{{TRANSCRIPTS_REPO_URL}}` (e.g. https://github.com/<your-user>/transcripts.git)
4. Which Whisper model should be the default? `{{TRANSCRIBE_MODEL}}` (default medium — recommended for CPU)
When I answer each, store the values, then verify by running the script on a short test audio file and show me the output."
```
Or install manually (Linux):

```bash
# Clone the skills repo
git clone https://github.com/ciberjohn/Hermes-Skills.git ~/Hermes-Skills

# Copy the skill into your Hermes skills directory
mkdir -p ~/.hermes/skills/media/transcribe/scripts
cp ~/Hermes-Skills/transcribe/SKILL.md ~/.hermes/skills/media/transcribe/
cp ~/Hermes-Skills/transcribe/scripts/transcribe.py ~/.hermes/skills/media/transcribe/scripts/

# Create the CrisperWhisper environment
python3 -m venv ~/.venvs/crisperwhisper
~/.venvs/crisperwhisper/bin/pip install "crisperwhisper[all]"

# Install ffmpeg (audio decoding)
sudo apt-get install -y ffmpeg        # Debian/Ubuntu

# Create the private transcripts repo
gh repo create transcripts --private
git clone git@github.com:<your-user>/transcripts.git ~/transcripts
```

## How it Works

1. **You hand Hermes an audio source** — Dropbox shared link, direct URL, uploaded file, or local path
2. **The script fetches it locally** (Dropbox shared links are auto-converted to direct-download URLs)
3. **CrisperWhisper transcribes it in two modes**, locally on your machine:
   - `verbatim.txt` — word-for-word, including fillers (`[UM]`, `[UH]`)
   - `intended.txt` — clean, readable, formatted (numbers, times, names normalised)
4. **A dated folder** (`YYYY-MM-DD_<slug>/`) is created in your transcripts repo with the texts, metadata, and optional word timestamps / subtitles
5. **The folder is committed and pushed** to your private GitHub repo

## Configuration Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `{{TRANSCRIBE_VENV_PATH}}` | Yes | Absolute path to the CrisperWhisper Python virtual environment | `~/.venvs/crisperwhisper` |
| `{{TRANSCRIBE_SCRIPT_PATH}}` | Yes | Absolute path to the driver script | `~/.hermes/skills/media/transcribe/scripts/transcribe.py` |
| `{{TRANSCRIPTS_REPO_PATH}}` | Yes | Local checkout of the private transcripts GitHub repo | `~/transcripts` |
| `{{TRANSCRIPTS_REPO_URL}}` | Yes | Git remote URL of that repo | `https://github.com/<your-user>/transcripts.git` |
| `{{TRANSCRIBE_MODEL}}` | No | Default Whisper model size (`small`/`medium`/`turbo`/`large`) | `medium` |

## What's Included

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill instructions — pipeline, options, pitfalls, verification checklist |
| `scripts/transcribe.py` | The driver script: fetch audio → transcribe (verbatim + intended) → write dated output folder |
| `.gitignore` | Ignores Python cache, env files, and local audio |

## Usage

Once installed, tell your Hermes agent:

- _"Transcribe this Dropbox link: https://www.dropbox.com/s/xxxx/meeting.m4a"_
- _"Here's an audio file — transcribe it and push to my repo"_
- _"Transcribe this podcast episode and also generate word timestamps"_
- _"Transcribe this recording — it's in Portuguese"_

The agent runs the pipeline, commits the dated folder to your private repo, and reports the language detected, model/backend used, duration, and a sample of each transcript mode.

### Output Files (per audio)

| File | Contents |
|------|----------|
| `verbatim.txt` | Word-for-word transcript including fillers (`[UM]`, `[UH]`) |
| `intended.txt` | Clean, readable transcript (numbers/times normalised) |
| `meta.json` | Source, duration, model, backend, language, timings, word counts |
| `words.tsv` | Per-word timestamps (only with `--words`) |
| `intended.srt` | Subtitles (only with `--srt`) |

## Performance Notes

The ct2 backend (CTranslate2, int8 quantised) is the default and runs **roughly in realtime on CPU** (a 10.6 s clip decodes in ~10 s on a 6-core EPYC; 1 h audio ≈ 1 h CPU). The transformers fallback is >50× slower on CPU and only useful as a compatibility check. First run downloads the model (~1.5 GB for `medium`) and converts it once; subsequent runs are fast.

## Security

- The transcripts repo should be **private** — transcripts often contain sensitive spoken content
- Audio files are never committed to the repo; only text and metadata
- No API keys, cloud transcription services, or third-party data handlers — everything runs locally
- No hardcoded paths — all locations configured via `{{VAR}}` placeholders at install time

## License

MIT — see [LICENSE](../LICENSE)
