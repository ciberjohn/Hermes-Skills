---
name: transcript-driven-cutting
description: "Use when cutting video from a word-level transcript."
version: 1.0.0
author: João Silva
license: MIT
platforms: [linux, darwin]
metadata:
  hermes:
    tags: [video-editing, cutting, transcription, whisper, parakeet, ffmpeg, captions, subtitles]
    related_skills: [transcribe, short-videos]
---

# Transcript-Driven Cutting

A video agent has no ears. It cannot watch a file and know where a sentence starts; it
can only guess, and a guess is what produces a cut that begins on the last phoneme of
"and", or two seconds of dead air before anyone speaks.

So transcribe first, locally, and every editing decision downstream becomes a number
instead of an estimate.

- "About seven seconds in" becomes `12.840 - 13.200`.
- A cut lands on a word boundary because the boundary is written down.
- Air before and after speech is a value you chose, not a value you got.
- Captions come from the same data, so they cannot drift from the picture.

Nothing here calls a cloud service. Both engines run on your CPU, on your machine, for
free, and the audio never leaves it.

## When to Use

Use this skill when the work is **choosing which parts of a recording to keep**:

- cutting a long talk, interview or screen recording down to a short
- removing false starts, filler, or a bad take and keeping the retake
- reordering spoken segments into a cleaner narrative
- captioning the result from the same timings that drove the cuts
- proving, after rendering, that the speech boundaries are where the transcript said

Not for producing a faithful written document of an audio file. That is the `transcribe`
skill: same Whisper family, different goal. If the deliverable is text, use `transcribe`.
If the deliverable is picture and sound edited against those timings, use this.

## Two Engines, Both Local

Pick one per job. They write comparable word-level data, so the rest of the pipeline does
not care which ran.

| | Parakeet | Whisper sidecar |
|---|---|---|
| Where | inside the HyperFrames CLI | `scripts/asr.py` in this skill |
| Install | `hyperframes models install parakeet` | `pip install faster-whisper` |
| Run | `hyperframes transcribe FILE -e parakeet --json` | `asr.py transcribe FILE` |
| Speed | ~7x realtime on a 14-core CPU | ≈ realtime on 6 CPU cores (`small.en`) |
| Output | transcript JSON written beside the file | transcript JSON, SRT on request |
| Needs a project | yes, one already set up | no, any file anywhere |
| Languages | strong English, decent European | any language Whisper supports |
| Best for | long footage inside an existing edit | a one-off file, non-English, subtitles |

Parakeet is the faster path when you are already working inside a HyperFrames project.
`asr.py` is the path when you have a file and no project, when the audio is not English,
or when you want an SRT out of the same pass.

## Pipeline

    probe -> extract 16 kHz mono -> transcribe to word-level JSON
          -> locate the phrase            (asr.py find)
          -> cut list -> clip markup      (asr.py clips)
          -> render -> verify with silence detection

### 1. Probe the media

Never trust the extension. `ffprobe` says what is actually inside, and whether there is
an audio stream at all — a screen recording with a muted track is a common surprise, and
it is better to learn that before a five-minute model run.

```bash
ffprobe -v error -print_format json -show_format -show_streams take.mp4
```

`asr.py transcribe` does this for you and refuses a file with no audio.

### 2. Extract 16 kHz mono audio

Whisper's native rate is 16 kHz mono; anything else gets resampled on the way in. Do the
conversion once, explicitly, into a WAV you own:

```bash
ffmpeg -nostdin -v error -y -i take.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav
```

### 3. Transcribe to word-level JSON

```bash
<venv>/bin/python scripts/asr.py transcribe take.mp4 --model small.en --srt
# -> take.transcript.json beside the file, plus take.transcript.srt
```

Output shape (abridged):

```json
{
  "schema": "asr.transcript/1",
  "source": "take.mp4",
  "model": "small.en",
  "language": "en",
  "duration": 486.2,
  "segments": [{"id": 0, "start": 0.0, "end": 4.88, "text": "..."}],
  "words": [
    {"start": 0.0, "end": 0.28, "word": "The", "probability": 0.62},
    {"start": 0.28, "end": 0.66, "word": "first", "probability": 0.97}
  ]
}
```

The `words` array is the whole point. Segments are for reading; words are for cutting.

**Model size, for cutting** (CPU, int8):

| Model | Disk | Use it when |
|-------|------|-------------|
| `tiny.en` | ~80 MB | you only need to find obvious phrase boundaries |
| `base.en` | ~150 MB | clean speech, nothing hangs on one word |
| `small.en` | ~480 MB | **default** for cutting: boundaries good, still fast |
| `medium.en` | ~1.5 GB | a single word matters — a name, a figure, a quote |

Do not reach for `medium.en` out of habit. It is several times slower, and the extra
accuracy mostly shows up inside long proper nouns, not at boundaries. Reach for it when
you are cutting *around a claim* and the exact wording will be quoted.

### 4. Locate the phrase

```bash
<venv>/bin/python scripts/asr.py find take.transcript.json "the second failure" --context 3
```

```
phrase: the second failure
1 match in take.transcript.json

[1] 2:41.680  in 161.530  out 164.120  (2.590s, exact)
    ...and that is why I want to talk about
    >>> the second failure, which nobody
    ...instrumented at all
```

Exact match on lowercased, punctuation-stripped words first, because two numbers that
agree exactly cannot be wrong. When nothing matches exactly — the transcript says
"there's" and you typed "there is" — it falls back to a similarity score over same-length
windows, and labels the result `fuzzy 0.93` so you know to look at it. `--json` for
machine use, `[n]` / `--index` to pick between repeated phrases.

The printed `first word` / `last word` matter: if the match is fuzzy, read them.

### 5. Build the cut list

One cut per line, `#` for comments, in the order you want them on the timeline:

```text
# opening: the failed take
The first take was unusable        # a phrase, resolved against the transcript
recorded in a quiet room [2]       # the second time it is said
161.530-164.120                    # or an explicit source range
```

A range written by hand is snapped outward to whole words anyway. That is deliberate: it
is the one class of mistake a listener hears every single time.

### 6. Turn the cut list into clip markup

```bash
<venv>/bin/python scripts/asr.py clips take.transcript.json --cut-list cuts.txt \
    --fps 25 --gap 0.25 --out take.clips.txt
```

```xml
<!-- 2 clip(s) from take.mp4, transcript: take.transcript.json -->
<!-- 1: The first take was unusable -->
<clip src="take.mp4" in="0.000" out="2.120" timeline-in="0.000" timeline-out="2.120"/>
<gap dur="0.250"/>
<clip src="take.mp4" in="7.360" out="9.440" timeline-in="2.360" timeline-out="4.440"/>
```

Four numbers per clip, and each one has one meaning:

- `in` / `out` — where to take the picture and sound *from* the source
- `timeline-in` / `timeline-out` — where it *lands* on the finished timeline
- `<gap>` — silence inserted between clips, so two sentences that were adjacent in the
  source do not arrive butt-joined

`--fps` snaps every number to a frame boundary at that rate, because a cut at 7.373 is
not a cut at 25 fps; it is 7.360 with a rounding error waiting to show up in a render.
`--lead` (0.15 s) and `--tail` (0.25 s) set the air around speech. Leave them alone
unless you have listened and disagree.

The markup is plain enough to paste into whatever timeline DSL you use, and easy to map
if yours names the attributes differently.

### 7. Render, then verify with silence

This is the step that turns "I think the cuts are right" into evidence. Feed the rendered
file to `silencedetect`; it reports where the audio actually falls quiet.

```bash
ffmpeg -nostdin -i render.mp4 -af silencedetect=noise=-32dB:d=0.35 -f null -
```

```
silence_start: 2.119909
silence_end: 2.473469 | silence_duration: 0.35356
silence_start: 4.084263
silence_end: 4.458231 | silence_duration: 0.373968
```

Read it against the markup above: the first `silence_start` is **2.120**, which is exactly
`timeline-out` of clip 1. The picture changed where the transcript said it would. If a
`silence_start` lands 0.4 s before the number you planned, a cut is early and you fix the
number, not the listener's patience.

`-32dB` is the threshold that separates speech from room tone on ordinary recordings;
`d=0.35` ignores the natural pauses inside a sentence, so only real boundaries are
reported. Raise `d` to 0.5 if you get a report per comma.

## Reading the Numbers Honestly

Two properties of word timestamps shape every decision, and both are worth internalising:

**Word timings are contiguous.** Word N ends where word N+1 begins, so a transcript
contains no "gap" between words to borrow air from. The tail of a word's span is its
release — quiet, inaudible as a fragment — so the lead air is allowed to borrow at most
40% of the previous word and no more. That is why a cut that looks like it has 0.15 s of
air may really have 0.09.

**Boundaries are approximate at the edges of speech.** Whisper is usually within 50-80 ms
on a clean recording and worse on one recorded in a room with a fan in it. Do not build a
rhythm that depends on 20 ms; do build one that depends on 200 ms, which the data can
actually support.

## Pitfalls

- **Handing the model a path instead of samples.** faster-whisper's path-based decode
  goes through PyAV, and on `av >= 15` that path raises on files ffmpeg reads happily.
  Always feed float32 samples decoded from a WAV you made yourself. `asr.py` does this;
  do not "simplify" it back to `model.transcribe("file.mp4")`.
- **VAD off.** With voice-activity filtering disabled, the decoder invents fluent
  sentences over music beds and room tone. A hallucinated word is worse than a gap,
  because it looks like data. Leave VAD on; `--no-vad` exists only for diagnosing it.
- **`tiny.en` is confidently wrong.** On a synthetic test clip it rendered "hissed all
  through it" as "is toil through it" — grammatical, plausible, invisible unless you read
  the transcript. A bigger model is not a guarantee either: on the same clip `small.en`
  dropped the word entirely and produced "the microphone is all through it". Read the
  words around a cut before you trust them, and if the line will appear on screen, cut
  around a lower-confidence word rather than through it.
- **The first run downloads the model.** A few hundred MB into the Hugging Face cache,
  once. It looks like a hang for the first 30-60 seconds; it is not.
- **Float16 on CPU fails.** `ValueError: Requested float16 compute type...` — the
  compute type must be `int8` on CPU. Never remove that argument.
- **Segment text is not cut text.** Cutting on segment boundaries gives you whatever
  length the decoder chose, usually 5-15 s, including the half-sentence it padded with.
  Cut on word boundaries; segments are for orientation.
- **A cut can hide a word without deleting it.** If `in` and `out` both fall inside the
  same word's span, the clip is a fragment. `clips --stats` warns below 0.4 s.
- **Long files.** `small.en` runs at about realtime on six CPU cores — measured: a 9.5 s
  clip decodes in 12-16 s including model load, and `tiny.en` took 4.7 s. So a 45-minute
  recording is a 45-70 minute job: run it in the background and say so, rather than
  blocking a conversation.
- **Two clips from the same source can overlap.** If clip 2's lead reaches back into clip
  1's tail, the same second of audio plays twice. `clips` warns; the fix is a smaller
  `--lead`, not a smaller `--gap`.

## Verification Checklist

- [ ] `ffprobe` confirmed an audio stream before the model run
- [ ] transcript JSON has a non-empty `words` array and the language is right
- [ ] every `find` result was read, not just used — `exact` or `fuzzy 0.9x`
- [ ] no clip's `in`/`out` lands inside a word's span
- [ ] clip durations are plausible for speech (0.4 s floor)
- [ ] `silencedetect` on the render reports boundaries matching `timeline-out` values
- [ ] audio and picture are cut with the same numbers — a video-only trim desynchronises

## Files

| File | Purpose |
|------|---------|
| `scripts/asr.py` | `transcribe`, `find`, `clips` — one file, standard library plus the model runtime |
| `README.md` | Install prompt, worked example, and the reasoning |
| `.gitignore` | Keeps model weights, venvs and real transcripts out of the repo |
