---
name: transcribe
description: "Transcribe audio (Dropbox links, uploaded files, URLs, local paths) with CrisperWhisper running locally, and commit each transcript to a private GitHub repo — one dated folder per transcription."
license: MIT
metadata:
  version: "1.0.0"
  tags: [transcription, whisper, audio, dropbox, github, speech-to-text]
  platforms: [linux]
  category: media
  related_skills: []
---

# Transcribe — Audio → Transcripts → GitHub

Use when the user gives you an audio file or link (Dropbox shared link, direct URL,
uploaded file, local path) and wants it transcribed. Produces **two transcripts per
audio** — `verbatim.txt` (word-for-word, fillers included) and `intended.txt` (clean,
readable) — and commits each into its own dated folder in a **private** GitHub repo,
then pushes.

## Configuration Variables

Set these at install time (the natural-language install prompt asks for them):

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `{{TRANSCRIBE_VENV_PATH}}` | Yes | Absolute path to the CrisperWhisper Python virtual environment | `~/.venvs/crisperwhisper` |
| `{{TRANSCRIBE_SCRIPT_PATH}}` | Yes | Absolute path to the driver script | `~/.hermes/skills/media/transcribe/scripts/transcribe.py` |
| `{{TRANSCRIPTS_REPO_PATH}}` | Yes | Local checkout of the private transcripts GitHub repo | `~/transcripts` |
| `{{TRANSCRIPTS_REPO_URL}}` | Yes | Git remote URL of that repo | `https://github.com/<your-user>/transcripts.git` |
| `{{TRANSCRIBE_MODEL}}` | No | Default Whisper model size (`small`/`medium`/`turbo`/`large`) | `medium` |

## Prerequisites

| Component | Notes |
|-----------|-------|
| Python 3.10+ venv | `crisperwhisper[all]` installed (torch, transformers, ctranslate2 fork) |
| ffmpeg | Required for audio decode (mp3/m4a/ogg/wav). Debian/Ubuntu: `sudo apt-get install -y ffmpeg`; macOS: `brew install ffmpeg` |
| Private GitHub repo | The transcripts output repo; needs a local clone and `git push` access |
| Model cache | First run downloads the Whisper model (~1.5 GB for `medium`) from HuggingFace and converts it once for the ct2 backend; cached afterwards |

## Procedure

### 1. Get the audio locally

Any of these work; pass the source string straight to the script:

- **Dropbox shared link** — the script auto-converts `www.dropbox.com/s/...` → `dl.dropboxusercontent.com` and appends `?dl=1` for a direct download. Works with `?dl=0` links too.
- **Direct URL** (http/https) — downloaded with a browser User-Agent.
- **Uploaded file** — Hermes desktop uploads land somewhere local; pass the path.
- **Local path** — pass as-is.

### 2. Run the transcription

```bash
"{{TRANSCRIBE_VENV_PATH}}/bin/python" "{{TRANSCRIBE_SCRIPT_PATH}}" "<SOURCE>" --out "{{TRANSCRIPTS_REPO_PATH}}" [OPTIONS]
```

Defaults: `--model {{TRANSCRIBE_MODEL}}` (CPU tradeoff), language **auto-detect**, both verbatim + intended.

| Option | Effect |
|--------|--------|
| `--model small\|medium\|turbo\|large` | Size/quality tradeoff. medium is the CPU sweet spot. |
| `--language pt\|en\|...` | Force ISO language; omit for auto-detect. |
| `--words` | Also write `words.tsv` with per-word timestamps. |
| `--srt` | Also write `intended.srt` subtitles. |
| `--backend auto\|ct2\|transformers` | auto prefers ct2 (verified ~50× faster than transformers on CPU). See backend notes below. |

**Backend reality check (measured 2026-08-02, medium model, 10.6 s audio, 6-core EPYC CPU, no GPU):**

| Backend | Model load | Decode 10.6 s audio | Verdict |
|---------|-----------|--------------------|---------|
| ct2 (int8) | ~26 s (first run includes one-time HF→CT2 conversion) | ~10 s (≈ realtime, RTF ≈ 1.0) | **Default** |
| transformers (torch) | ~30 s | >9 min (RTF > 50×), aborted | Unusable on CPU |

Never use `--backend transformers` on a CPU-only box except as a compatibility check —
it will make the user wait hours for a podcast.

**Long audio:** with ct2, transcription is roughly **realtime** (1 h audio ≈ 1 h CPU,
single transcription; medium, int8). Still worth running in background with
`notify_on_complete=true` for anything over ~15 min, and tell the user the ETA.
Do NOT block the chat.

### 3. Verify output

The script prints `OUTDIR:<path>` and the word counts. Check:

```bash
ls -la "{{TRANSCRIPTS_REPO_PATH}}/<YYYY-MM-DD>_<slug>/"
```

Expect: `verbatim.txt`, `intended.txt`, `meta.json` (+ `words.tsv` / `intended.srt` if requested).
Spot-check both texts — if a transcript is empty or obviously wrong, rerun with
`--language <code>` explicitly (auto-detect occasionally fails on short clips).

### 4. Commit and push

```bash
cd "{{TRANSCRIPTS_REPO_PATH}}"
git add <YYYY-MM-DD>_<slug>/
git commit -m "transcribe: <slug> (<lang>, <model>, <duration>s)"
git push
```

**Never commit the original audio** — GitHub caps files at 100 MB and repos stay lean
without LFS. The source is recorded in `meta.json`; the downloaded audio lives in the
ephemeral work dir (`/tmp/transcribe-work/`) — if the user wants it kept, copy it to an
audio archive folder before cleaning up.

### 5. Report

Give the user:
- The folder path (local) and the GitHub URL: `{{TRANSCRIPTS_REPO_URL}}/tree/main/<folder>`
- Language detected, model/backend used, audio duration vs transcription time
- A 1–2 line sample of each mode so they can see the verbatim/intended difference

## Pitfalls

- **Hermes profile HOME isolation** — Under a Hermes profile, `~` may resolve to the
  profile's sandbox home (e.g. `~/.hermes/profiles/<profile>/home/`), so the HF model
  cache and any path built from `~` land in odd places. Always use **absolute paths**
  for the venv, script, and repo (the `{{VAR}}` values). The model only downloads once
  and is reused.
- **First run is slow** — downloads the model (~1.5 GB for `medium`) from HuggingFace,
  and the ct2 backend converts HF→CT2 once. Subsequent runs skip both. Don't panic if
  the first run takes several minutes before "model loaded".
- **transformers 5.x tokenizer failure** — crisperwhisper 2.0.1 was built for
  transformers 4.x. If you see `OSError: Can't load tokenizer for 'nyralabs/...'`,
  it's usually an interrupted first download (re-run fixes it). If it persists, pin
  `transformers<5` in the venv: `pip install "transformers<5"`.
- **No GPU** — on a CPU-only box, `large` will be slow and may OOM with word
  timestamps; stick to `medium` unless the user asks otherwise.
- **ct2 float16 on CPU fails** — `ValueError: Requested float16 compute type...` The
  ct2 backend defaults to `compute_type="float16"`, which needs a GPU. The script
  forces `compute_type="int8"` when the backend is ct2; don't remove that.
- **First ct2 run converts the model** — HF→CT2 conversion of `medium` on CPU takes
  ~10–15 min once; cached afterwards. The transformers backend has no conversion step
  but is slower per-decode.
- **Unauthenticated HF downloads** — fine but slower; don't block on rate limits, just
  retry.
- **Empty transcript on silence** — by design (both backends decode with
  begin-of-sequence suppression disabled). If the audio is genuinely silent, that's
  the correct output.
- **Dropbox links with `&` in the URL** — quote the source argument in the shell.

## Verification checklist

- [ ] `verbatim.txt` and `intended.txt` non-empty, language looks right
- [ ] `meta.json` has source, duration, model, backend, language
- [ ] `git status` clean after push; `git log --oneline -1` shows the new commit
- [ ] User can open the GitHub link (private repo — their account only)
