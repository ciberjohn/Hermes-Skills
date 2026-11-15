# HyperFrames add-on: Transcript-Driven Cutting

**An add-on for [HyperFrames](https://github.com/heygen-com/hyperframes).** Install
HyperFrames, point your own local Hermes agent at it with your own model, and you can
edit video, build motion graphics, record voiceover, render and publish — everything
HyperFrames allows, on your own machine, without sending the rushes anywhere. What that
agent cannot do is *hear*. This skill closes that gap: Hermes transcribes the raw footage
first and gets word-level timings for every syllable, so the editing decisions it makes
are measured instead of guessed.

Cut video against numbers, not estimates. Transcribe the recording locally first, and
every decision after that — which sentence to keep, where the clip starts, how much air
sits around it, what the captions say, whether the render actually matches — reads from
the same word-level timings.

> **Why this exists.** A video agent has no ears. Asked to "cut from the bit about the
> second failure", it can guess, and a guess is what produces a clip that opens on the
> last phoneme of "and" or two seconds of dead air before the first word. Word-level
> timestamps turn that into `12.840 - 13.200`: a cut on a word boundary, 0.15 s of air
> before it, 0.25 s after, and a caption built from the same data so it cannot drift
> from the picture.

**Pipeline:** probe → extract 16 kHz mono → transcribe to word-level JSON → locate the phrase → cut list → clip markup → render → verify with silence detection.

**Works without HyperFrames too.** Step 4 (`find`) and the transcription step are
engine- and editor-agnostic: point them at any recording and you get JSON, SRT and
in/out points you can take to any NLE. Only the final `clips` output speaks
HyperFrames' format, because that is the editor this add-on is built to feed.

## What you get

- **Two local engines, both free, no cloud, no upload.** Parakeet inside the HyperFrames
  CLI (~7x realtime on a 14-core CPU, transcript JSON written beside the file), and
  Whisper as a standalone sidecar — OpenAI's weights through faster-whisper/CTranslate2,
  CPU int8, any language, SRT export, works on any file without a project.
- **`asr.py`, one file, three subcommands.** `transcribe` a file, `find` a spoken phrase
  and get its in/out points, `clips` turn a cut list into HyperFrames clip markup — one
  timed `<video>` element per clip, with the trim and the gap between clips carried in the
  offsets. `find` and `clips` are pure standard library — they read the JSON and run on a
  machine that has never downloaded a model. They read either transcript schema, `word`
  (this script) or `text` (Parakeet and most Whisper tooling), so a transcript from the
  other engine needs no conversion.
- **Cuts that cannot start mid-word.** Phrases resolve on word boundaries and are snapped
  outward to whole words, because a word clipped in half is the one mistake a listener
  hears every time. A range you typed is the opposite case and is taken exactly as given,
  to the frame.
- **Verification that is evidence, not opinion.** `ffmpeg -af silencedetect=noise=-32dB:d=0.35`
  on the finished render reports where the audio actually goes quiet, and those numbers
  should match the timeline positions the cut list produced.

## How it works

1. **Probe** with `ffprobe`. Never trust the extension; confirm there is an audio stream
   before a model run.
2. **Extract** 16 kHz mono PCM to a WAV you own. One known-good decode path for a phone
   clip, a screen recording, a 48 kHz camera file.
3. **Transcribe** to JSON with a `words` array — each word carrying `start`, `end` and its
   surface text under `word` (this script) or `text` (Parakeet, Whisper tooling), both of
   which `find` and `clips` read. Segments are for reading; words are for cutting.
4. **Locate** the phrase you want. Exact match on normalised words first; a similarity
   fallback labelled `fuzzy 0.9x` for when the transcript says "there's" and you typed
   "there is".
5. **Cut list** — one cut per line: a phrase, a phrase with an occurrence `[2]`, or an
   explicit `in-out` range.
6. **Clip markup** — one timed `<video>` element per clip, HyperFrames' own shape:
   `data-start`, `data-duration`, `data-media-start`, `data-has-audio="true"`,
   `data-volume="1"`. Frame-snapped at 25 fps by default; a typed range is honoured as
   given. Nothing but those elements reaches stdout.
7. **Verify** the render with silence detection and compare the reported boundaries to
   the numbers you planned.

## Prerequisites

- **Python 3.10+** (verified on 3.12). `find` and `clips` need nothing but the standard
  library; `transcribe` needs `faster-whisper` and `numpy`, so install it in a venv
  rather than fighting a PEP 668 system interpreter.
- **ffmpeg and ffprobe** on `PATH`. Debian/Ubuntu: `sudo apt-get install -y ffmpeg`;
  macOS: `brew install ffmpeg`.
- **Disk for one model**, once: `small.en` is ~480 MB, `medium.en` ~1.5 GB. Cached after
  the first run.
- Optional: the HyperFrames CLI if you want the Parakeet engine
  (`hyperframes models install parakeet`).

## Install

Copy-paste this to your Hermes agent (any profile):

```text
"Install the transcript-driven-cutting skill from github.com/ciberjohn/Hermes-Skills into
~/.hermes/skills/media/transcript-driven-cutting/. Copy SKILL.md and README.md into that
directory, and scripts/asr.py into ~/.hermes/skills/media/transcript-driven-cutting/scripts/,
creating those directories if they do not exist, then chmod +x the script. Then set it up:
verify ffmpeg and ffprobe are on PATH, create a Python 3.12 virtual environment for the
model runtime, and install faster-whisper into it. Then ask me these questions one at a
time:
1. Where should the transcription virtual environment live? `TRANSCRIPT_VENV_PATH`
   (default ~/.venvs/asr)
2. Which Whisper model should be the default? `TRANSCRIPT_MODEL` (default small.en — about
   480 MB, good boundaries; medium.en only when a single word matters)
3. Do I have the HyperFrames CLI and want the Parakeet engine as well? `USE_PARAKEET`
   (default no)
When I answer each, store the values, then verify the whole pipeline on a short clip I
give you: transcribe it, find one phrase, produce clip markup, and show me the numbers."
```

Or install manually:

```bash
# Clone the skills repo into a fresh directory, not a predictable path in /tmp
src="$(mktemp -d)"
git clone https://github.com/ciberjohn/Hermes-Skills.git "$src"

# Copy the skill into your Hermes skills directory
mkdir -p ~/.hermes/skills/media/transcript-driven-cutting/scripts
cp "$src/transcript-driven-cutting/SKILL.md" \
   "$src/transcript-driven-cutting/README.md" \
   ~/.hermes/skills/media/transcript-driven-cutting/
cp "$src/transcript-driven-cutting/scripts/asr.py" \
   ~/.hermes/skills/media/transcript-driven-cutting/scripts/
chmod +x ~/.hermes/skills/media/transcript-driven-cutting/scripts/asr.py

# Model runtime, in its own venv
python3.12 -m venv ~/.venvs/asr
~/.venvs/asr/bin/pip install --upgrade pip faster-whisper

# ffmpeg (decode + verification)
sudo apt-get install -y ffmpeg        # Debian/Ubuntu
```

## Usage

```bash
ASR=~/.hermes/skills/media/transcript-driven-cutting/scripts/asr.py
PY=~/.venvs/asr/bin/python

# 1. word-level transcript, plus subtitles from the same pass
"$PY" "$ASR" transcribe take.mp4 --model small.en --srt

# 2. where does that phrase start and end?
"$PY" "$ASR" find take.transcript.json "recorded in a quiet room" --context 3

# 3. cut list -> clip markup, frame-snapped at 25 fps
"$PY" "$ASR" clips take.transcript.json --cut-list cuts.txt --fps 25 --gap 0.25 --stats
```

`cuts.txt`, one cut per line:

```text
# opening: the failed take
The first take was unusable
recorded in a quiet room [2]
161.530-164.120
```

Markup out — HyperFrames clip markup, one element per clip and nothing else on stdout:

```html
<video id="clip-00" class="clip" data-start="0.00" data-duration="2.12" data-media-start="0.00" data-has-audio="true" data-volume="1" src="take.mp4"></video>
<video id="clip-01" class="clip" data-start="2.37" data-duration="2.08" data-media-start="7.36" data-has-audio="true" data-volume="1" src="take.mp4"></video>
```

`data-start` is the running timeline offset — `0` for the first clip, then the previous
`data-start` + previous `data-duration` + `--gap`, so the silence between clips lives in the
offsets rather than in a separate element. `data-duration` is out − in, and
`data-media-start` is where picture and sound are taken from the source. Ids are unique and
zero padded, `src` is `--source` verbatim, values carry two decimals, and the element is
never `muted`: the speaker's own sound is the point.

The audit comment lines and the `--stats` timeline summary go to stderr, so stdout stays
pasteable and `--out` writes the same clean elements to a file.

Then verify the render — this output is from a real 4.45 s render of those two clips:

```bash
ffmpeg -nostdin -i render.mp4 -af silencedetect=noise=-32dB:d=0.35 -f null -
```

```
silence_start: 2.119909
silence_end: 2.473469 | silence_duration: 0.35356
silence_start: 4.084263
silence_end: 4.458231 | silence_duration: 0.373968
```

The first `silence_start` is 2.120 — exactly clip 1's `data-start + data-duration`
(0.00 + 2.12). The picture changed where the transcript said it would, and that is a fact
you can show rather than a feeling you can defend.

## What's included

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill instructions: engines, pipeline, model guidance, pitfalls, checklist |
| `README.md` | This document — install prompt, worked example, reasoning |
| `scripts/asr.py` | `transcribe` / `find` / `clips` in one dependency-light file |
| `.gitignore` | Keeps venvs, caches, model weights and real transcripts out of git |

## Distinction from `transcribe`

The [`transcribe`](../transcribe/) skill gets a faithful written transcript of an audio
file: verbatim and cleaned, committed to a private repo. This skill uses transcription as
a **measurement step** for editing picture and sound — cutting, sequencing, captions, and
proving the result. Same model family, opposite deliverable. If the answer is a document,
use `transcribe`. If the answer is a video, use this.

## Security

- **No cloud, no API key, no upload.** Both engines run on your CPU; the audio stays on
  your disk.
- **Nothing hardcoded.** Venv and model paths are `{{VARIABLE}}` placeholders resolved at
  install time; no absolute paths in the skill.
- **Transcripts and media are gitignored.** A transcript is a verbatim record of what
  someone said; treat it as sensitive and keep it out of public repos.
- **No network at run time** beyond the one-time model download from Hugging Face.

## Performance notes

Measured on a 6-core CPU, int8, model already cached: a 9.47 s clip decodes in **12-16 s**
with `small.en` (about realtime) and **4.7 s** with `tiny.en` (about 2-3x realtime), both
figures including the one-off model load. So a 45-minute recording with `small.en` is a
45-70 minute job — run it in the background with `notify_on_complete=true` rather than
blocking a conversation, and tell the user the estimate. `medium.en` is several times
slower again. Parakeet inside HyperFrames reached ~7x realtime on a 14-core CPU on the
same class of audio, which is why it is the better choice inside an existing project.

## License

MIT — see [LICENSE](../LICENSE)
