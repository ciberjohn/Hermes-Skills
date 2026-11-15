#!/usr/bin/env python3
"""asr.py -- offline word-level transcription sidecar for transcript-driven cutting.

One file, three subcommands, no service:

    transcribe   media file  ->  transcript JSON with word-level timings (+ optional SRT)
    find         transcript  ->  source in/out points for a spoken phrase
    clips        transcript  ->  ready-to-paste clip markup from a cut list

`transcribe` needs the model runtime (faster-whisper + numpy) and ffmpeg on PATH.
`find` and `clips` are pure standard library: they only read the JSON, so they run
anywhere, including a machine that has never downloaded a model.

The point of the whole exercise is that a cutting decision stops being an estimate.
"About seven seconds in" becomes 6.98-7.41, and every later step -- trimming,
ordering, captions, verification -- reads the same numbers.

Model sizes, for cutting work on CPU (int8):
    tiny.en   ~80 MB    fast, fine for picking out obvious phrase boundaries
    base.en   ~150 MB   the smallest size that is usually right on clean speech
    small.en  ~480 MB   the default: good boundaries, ~2-4x realtime on a laptop
    medium.en ~1.5 GB   when a single word genuinely matters (names, figures)

Usage:
    asr.py transcribe talk.mp4
    asr.py find talk.transcript.json "the part about the second failure" --context 3
    asr.py clips talk.transcript.json cuts.txt --fps 25 --out talk.clips.txt
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import NoReturn

SAMPLE_RATE = 16000          # Whisper's native rate; anything else is resampled first
DEFAULT_MODEL = "small.en"
DEFAULT_LEAD = 0.15          # air kept before the first word of a cut
DEFAULT_TAIL = 0.25          # air kept after the last word: 0.2-0.3 s reads as natural
DEFAULT_GAP = 0.25           # silence inserted between two timeline clips


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def die(message: str, code: int = 1) -> NoReturn:
    print("error: " + message, file=sys.stderr)
    raise SystemExit(code)


def warn(message: str) -> None:
    print("warning: " + message, file=sys.stderr)


def need(binary: str) -> str:
    found = shutil.which(binary)
    if not found:
        die("%s not found on PATH -- install ffmpeg (it ships ffprobe)" % binary)
    return found


def probe(path: Path) -> dict:
    """Duration and stream facts, via ffprobe. Never trust the file extension."""
    out = subprocess.run(
        [need("ffprobe"), "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        die("ffprobe could not read %s: %s" % (path, out.stderr.strip()[:400]))
    info = json.loads(out.stdout or "{}")
    duration = float(info.get("format", {}).get("duration") or 0.0)
    video = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    return {
        "duration": duration,
        "has_video": bool(video),
        "has_audio": bool(audio),
        "video_codec": video[0].get("codec_name") if video else None,
        "audio_codec": audio[0].get("codec_name") if audio else None,
        "audio_channels": audio[0].get("channels") if audio else None,
        "audio_rate": audio[0].get("sample_rate") if audio else None,
    }


def extract_wav(media: Path, wav_path: Path) -> None:
    """16 kHz mono PCM.

    Whisper only ever wants 16 kHz mono, and doing the conversion here means one
    known-good decode path for every input container -- a phone clip, a screen
    recording, a 48 kHz camera file, a video.
    """
    cmd = [
        need("ffmpeg"), "-nostdin", "-v", "error", "-y",
        "-i", str(media),
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-c:a", "pcm_s16le", "-f", "wav", str(wav_path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        die("ffmpeg could not extract audio: %s" % (out.stderr.strip()[:400]))


def read_wav_float32(wav_path: Path):
    """Read the PCM we just wrote as float32 in [-1, 1].

    Why not hand faster-whisper the media path and let it decode? Its path-based
    decode goes through PyAV, and on av >= 15 that path raises on perfectly valid
    files. Handing the model a float32 numpy array skips PyAV entirely: we own the
    decode, so the model cannot break because of a container quirk.
    """
    import numpy as np

    with wave.open(str(wav_path), "rb") as wav:
        if wav.getframerate() != SAMPLE_RATE:
            die("internal: unexpected sample rate %d" % wav.getframerate())
        if wav.getnchannels() != 1:
            die("internal: unexpected channel count %d" % wav.getnchannels())
        if wav.getsampwidth() != 2:
            die("internal: unexpected sample width %d" % wav.getsampwidth())
        frames = wav.readframes(wav.getnframes())

    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples


def fmt_ts(seconds: float) -> str:
    """3 dp, because a frame at 25 fps is 0.04 s and 2 dp rounds badly."""
    seconds = max(0.0, float(seconds))
    return "%0.3f" % seconds


def fmt_clock(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes, rest = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return "%d:%02d:%06.3f" % (hours, minutes, rest)
    return "%d:%06.3f" % (minutes, rest)


def fmt_clock_short(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes, rest = divmod(seconds, 60)
    return "%d:%04.1f" % (int(minutes), rest)


def parse_ts(text: str) -> float:
    """'83.4', '1:23.4' and '0:01:23.400' all mean the same instant."""
    parts = [p for p in text.strip().split(":") if p != ""]
    if not parts:
        raise ValueError("empty timestamp")
    value = float(parts[-1])
    for index, part in enumerate(reversed(parts[:-1]), start=1):
        value += float(part) * (60 ** index)
    return value


_STRIP = re.compile(r"[^0-9a-z']+")


def norm_word(text: str) -> str:
    return _STRIP.sub("", text.lower()).strip("'")


def words_of(transcript: dict) -> list:
    """Word list, or segments promoted to one-word entries with their own span."""
    if transcript.get("words"):
        return transcript["words"]
    promoted = []
    for seg in transcript.get("segments", []):
        parts = [p for p in seg.get("text", "").split() if p]
        if not parts:
            continue
        step = (seg["end"] - seg["start"]) / len(parts)
        for index, part in enumerate(parts):
            promoted.append({
                "start": seg["start"] + index * step,
                "end": seg["start"] + (index + 1) * step,
                "word": part,
                "probability": seg.get("avg_logprob"),
                "promoted": True,
            })
    return promoted


# --------------------------------------------------------------------------- #
# transcribe
# --------------------------------------------------------------------------- #

def cmd_transcribe(args: argparse.Namespace) -> int:
    media = Path(args.media).expanduser()
    if not media.is_file():
        die("no such file: %s" % media)

    facts = probe(media)
    if not facts["has_audio"]:
        die("%s has no audio stream -- nothing to transcribe" % media.name)

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("faster-whisper is not installed in this interpreter.\n"
            "  python3 -m venv <venv> && <venv>/bin/pip install faster-whisper\n"
            "then run this script with <venv>/bin/python")

    work = Path(tempfile.mkdtemp(prefix="asr-", dir=args.tmpdir or None))
    try:
        wav_path = work / "audio.wav"
        extract_wav(media, wav_path)
        samples = read_wav_float32(wav_path)
        audio_seconds = len(samples) / float(SAMPLE_RATE)

        print("probe: %s, %.2fs audio (%s)" % (
            media.name, audio_seconds, facts["audio_codec"] or "unknown"), file=sys.stderr)
        print("model: %s, cpu int8" % args.model, file=sys.stderr)

        model = WhisperModel(args.model, device="cpu", compute_type="int8")
        segments_iter, info = model.transcribe(
            samples,
            language=args.language,
            beam_size=args.beam,
            word_timestamps=True,
            # VAD on by default: without it the decoder invents sentences over
            # room tone and music beds, and a hallucinated word is worse than a
            # gap because it looks like data.
            vad_filter=not args.no_vad,
            vad_parameters={"min_silence_duration_ms": 300} if not args.no_vad else None,
            # Each chunk is decoded independently, so one repeated line early in
            # the file cannot cascade through the rest of the transcript.
            condition_on_previous_text=False,
        )

        segments = []
        words = []
        for index, seg in enumerate(segments_iter):
            segments.append({
                "id": index,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "avg_logprob": round(seg.avg_logprob, 4) if seg.avg_logprob else None,
            })
            for word in seg.words or []:
                text = word.word.strip()
                if not text:
                    continue
                words.append({
                    "start": round(word.start, 3),
                    "end": round(word.end, 3),
                    "word": text,
                    "probability": round(word.probability, 4) if word.probability else None,
                })
            if args.progress and index and index % 20 == 0:
                print("  ... %s / %s" % (fmt_clock_short(seg.end),
                                         fmt_clock_short(audio_seconds)), file=sys.stderr)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if not words:
        warn("no words decoded -- silence, music only, or the wrong language forced")

    payload = {
        "schema": "asr.transcript/1",
        "source": media.name,
        "engine": "faster-whisper",
        "model": args.model,
        "language": info.language if info else args.language,
        "language_probability": round(info.language_probability, 4) if info else None,
        "duration": round(facts["duration"] or audio_seconds, 3),
        "audio_seconds": round(audio_seconds, 3),
        "has_video": facts["has_video"],
        "vad": not args.no_vad,
        "segments": segments,
        "words": words,
    }

    out_path = Path(args.out).expanduser() if args.out else media.with_name(
        media.stem + ".transcript.json")
    out_path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")

    print("TRANSCRIPT:%s" % out_path)
    print("words: %d in %d segments, language %s (%.2f)" % (
        len(words), len(segments), payload["language"],
        payload["language_probability"] or 0.0))

    if args.srt:
        srt_path = out_path.with_suffix(".srt")
        write_srt(segments, srt_path)
        print("SRT:%s" % srt_path)

    if words:
        print("verify a boundary with:\n  ffmpeg -i %s -af silencedetect=noise=-32dB:d=0.35 -f null -"
              % media.name)
    return 0


def write_srt(segments: list, path: Path) -> None:
    def stamp(value: float) -> str:
        millis = int(round(max(0.0, value) * 1000))
        hours, millis = divmod(millis, 3600000)
        minutes, millis = divmod(millis, 60000)
        seconds, millis = divmod(millis, 1000)
        return "%02d:%02d:%02d,%03d" % (hours, minutes, seconds, millis)

    lines = []
    for number, seg in enumerate(segments, start=1):
        lines.append(str(number))
        lines.append("%s --> %s" % (stamp(seg["start"]), stamp(seg["end"])))
        lines.append(seg["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# find
# --------------------------------------------------------------------------- #

def load_transcript(path: str) -> dict:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        die("no such transcript: %s" % file_path)
    try:
        data = json.loads(file_path.read_text())
    except json.JSONDecodeError as exc:
        die("%s is not valid JSON (%s)" % (file_path, exc))
    if not data.get("words") and not data.get("segments"):
        die("%s holds no words and no segments" % file_path)
    return data


def locate(words: list, phrase: str, min_ratio: float = 0.72) -> list:
    """Every place the phrase is spoken, best first.

    Exact match on lowercased, punctuation-stripped words first, because a pair
    of numbers that agree exactly cannot be wrong. Only when nothing matches
    exactly do we fall back to difflib over same-length windows -- a transcript
    says "there's" where you typed "there is", and that should still cut.
    """
    query = [w for w in (norm_word(part) for part in phrase.split()) if w]
    if not query:
        return []

    spoken = [norm_word(w["word"]) for w in words]
    span = len(query)
    hits = []

    for index in range(0, len(spoken) - span + 1):
        if spoken[index:index + span] == query:
            hits.append((1.0, index))
    if hits:
        return [_hit(words, index, span, score, exact=True) for score, index in hits]

    scored = []
    for index in range(0, len(spoken) - span + 1):
        window = " ".join(spoken[index:index + span])
        if not window.strip():
            continue
        ratio = difflib.SequenceMatcher(None, window, " ".join(query)).ratio()
        if ratio >= min_ratio:
            scored.append((ratio, index))

    # Keep the best match in each neighbourhood so one phrase cannot report
    # itself five times as word alignment shifts by a word.
    scored.sort(reverse=True)
    kept = []
    for ratio, index in scored:
        if all(abs(index - other) > span for _, other in kept):
            kept.append((ratio, index))
    kept.sort()
    return [_hit(words, index, span, score, exact=False) for score, index in kept]


def _hit(words: list, index: int, span: int, score: float, exact: bool) -> dict:
    chunk = words[index:index + span]
    return {
        "start": chunk[0]["start"],
        "end": chunk[-1]["end"],
        "score": round(score, 3),
        "exact": exact,
        "word_index": index,
        "text": " ".join(w["word"] for w in chunk),
        "confidence": round(min([w["probability"] for w in chunk
                                 if w.get("probability") is not None] or [1.0]), 3),
        "first_word": chunk[0]["word"],
        "last_word": chunk[-1]["word"],
    }


def context_lines(words: list, start: float, end: float, span: float) -> tuple:
    before = [w for w in words if start - span <= w["end"] <= start + 0.001]
    after = [w for w in words if end - 0.001 <= w["start"] <= end + span]
    return (" ".join(w["word"] for w in before[-6:]),
            " ".join(w["word"] for w in after[:6]))


def cmd_find(args: argparse.Namespace) -> int:
    transcript = load_transcript(args.transcript)
    words = words_of(transcript)
    if not words:
        die("transcript has no usable words")

    hits = locate(words, args.phrase, min_ratio=args.fuzzy)
    if not hits:
        print("no match for: %s" % args.phrase, file=sys.stderr)
        print("the words may differ; raise --fuzzy (currently %.2f) or quote fewer words"
              % args.fuzzy, file=sys.stderr)
        return 2

    if args.index is not None:
        if args.index < 1 or args.index > len(hits):
            die("only %d occurrence(s); --index must be 1-%d" % (len(hits), len(hits)))
        hits = [hits[args.index - 1]]

    results = []
    for hit in hits:
        before, after = context_lines(words, hit["start"], hit["end"],
                                      args.context if args.context is not None else 2.0)
        cut_in = max(0.0, hit["start"] - args.lead)
        cut_out = hit["end"] + args.tail
        # Whisper's word timings are contiguous: word N ends exactly where word
        # N+1 begins, so there is no "gap" to take the lead air from. The last
        # part of a word's span is its release, which is quiet, so let the lead
        # borrow at most 40% of the previous word rather than cut it to zero.
        if hit["word_index"] > 0:
            previous = words[hit["word_index"] - 1]
            floor = previous["start"] + 0.4 * (previous["end"] - previous["start"])
            cut_in = max(cut_in, floor)
        results.append({
            "in": round(cut_in, 3),
            "out": round(cut_out, 3),
            "duration": round(cut_out - cut_in, 3),
            "phrase_start": round(hit["start"], 3),
            "phrase_end": round(hit["end"], 3),
            "score": hit["score"],
            "exact": hit["exact"],
            "first_word": hit["first_word"],
            "last_word": hit["last_word"],
            "text": hit["text"],
            "context_before": before,
            "context_after": after,
        })

    if args.json:
        print(json.dumps({"phrase": args.phrase, "matches": results}, indent=2))
        return 0

    print("phrase: %s" % args.phrase)
    print("%d match%s in %s\n" % (len(results), "" if len(results) == 1 else "es",
                                  Path(args.transcript).name))
    for number, item in enumerate(results, start=1):
        tag = "exact" if item["exact"] else "fuzzy %.2f" % item["score"]
        print("[%d] %s  in %s  out %s  (%ss, %s)" % (
            number, fmt_clock(item["in"]), fmt_ts(item["in"]), fmt_ts(item["out"]),
            fmt_ts(item["duration"]), tag))
        if item["context_before"]:
            print("    ...%s" % item["context_before"])
        print("    >>> %s" % item["text"])
        if item["context_after"]:
            print("    %s..." % item["context_after"])
        print()
    print("paste as a cut-list line:")
    for item in results:
        print("  %s-%s" % (fmt_ts(item["in"]), fmt_ts(item["out"])))
    return 0


# --------------------------------------------------------------------------- #
# clips
# --------------------------------------------------------------------------- #

_TIME_RANGE = re.compile(r"^\s*([0-9:.]+)\s*-\s*([0-9:.]+)\s*$")
_OCCURRENCE = re.compile(r"\s*\[(\d+)\]\s*$")


def parse_cut_line(line: str) -> dict:
    """One cut: either an in-out range or a phrase (with an optional [n])."""
    text = line.strip()
    occurrence = None
    trailing = _OCCURRENCE.search(text)
    if trailing:
        occurrence = int(trailing.group(1))
        text = _OCCURRENCE.sub("", text)

    ranged = _TIME_RANGE.match(text)
    if ranged:
        start = parse_ts(ranged.group(1))
        end = parse_ts(ranged.group(2))
        if end <= start:
            raise ValueError("range ends at or before it starts: %s" % line.strip())
        return {"kind": "range", "start": start, "end": end,
                "label": "%s-%s" % (fmt_ts(start), fmt_ts(end))}
    return {"kind": "phrase", "phrase": text, "occurrence": occurrence, "label": text}


def resolve_cuts(words: list, cuts: list, fuzzy: float) -> tuple:
    resolved = []
    problems = []
    for position, cut in enumerate(cuts, start=1):
        if cut["kind"] == "range":
            found = {"start": cut["start"], "end": cut["end"], "text": cut["label"],
                     "score": 1.0, "exact": True}
        else:
            hits = locate(words, cut["phrase"], min_ratio=fuzzy)
            if not hits:
                problems.append("cut %d: no match for %r" % (position, cut["phrase"]))
                continue
            wanted = cut["occurrence"] or 1
            if wanted > len(hits):
                problems.append("cut %d: %r occurs %d time(s), asked for [%d]"
                                % (position, cut["phrase"], len(hits), wanted))
                continue
            found = hits[wanted - 1]

        # Snap outward to whole words. A cut that begins or ends mid-word is the
        # one mistake a listener hears every single time.
        overlapping = [w for w in words
                       if w["end"] > found["start"] + 0.001 and w["start"] < found["end"] - 0.001]
        if overlapping:
            snapped_in = min(w["start"] for w in overlapping)
            snapped_out = max(w["end"] for w in overlapping)
        else:
            snapped_in, snapped_out = found["start"], found["end"]

        first = words[0]["start"]
        last = words[-1]["end"] if words else snapped_out
        resolved.append({
            "start": max(first, snapped_in),
            "end": min(last, snapped_out),
            "text": found.get("text", cut["label"]),
            "score": found.get("score", 1.0),
            "exact": found.get("exact", True),
        })

    resolved.sort(key=lambda item: item["start"])
    return resolved, problems


def snap(value: float, fps: float) -> float:
    if not fps:
        return value
    return round(value * fps) / fps


def cmd_clips(args: argparse.Namespace) -> int:
    transcript = load_transcript(args.transcript)
    words = words_of(transcript)
    if not words:
        die("transcript has no usable words")

    raw_lines = []
    for item in args.cut or []:
        raw_lines.append(item)
    if args.cut_list:
        listing = Path(args.cut_list).expanduser()
        if not listing.is_file():
            die("no such cut list: %s" % listing)
        for line in listing.read_text().splitlines():
            if line.strip() and not line.strip().startswith("#"):
                raw_lines.append(line)
    if not raw_lines:
        die("no cuts: pass --cut-list FILE or one or more --cut 'phrase' / --cut 'in-out'")

    cuts = []
    for line in raw_lines:
        try:
            cuts.append(parse_cut_line(line))
        except ValueError as exc:
            die(str(exc))

    resolved, problems = resolve_cuts(words, cuts, args.fuzzy)
    for message in problems:
        warn(message)
    if not resolved:
        die("no cut could be resolved against this transcript")

    source = args.source or transcript.get("source") or Path(args.transcript).name

    timeline = 0.0
    placements = []
    previous = None
    for cut in resolved:
        in_point = max(0.0, cut["start"] - args.lead)
        out_point = cut["end"] + args.tail
        if previous is not None:
            # The lead air must not reach back into the previous clip's tail.
            in_point = max(in_point, (previous["end"] + cut["start"]) / 2.0)
            if in_point < previous["end"]:
                warn("cut at %s starts before the previous one ends in the source; "
                     "the same audio appears twice" % fmt_ts(cut["start"]))
            timeline += args.gap
        previous = cut
        in_point = min(in_point, out_point - 0.05)
        in_frame = snap(in_point, args.fps)
        out_frame = snap(out_point, args.fps)
        span = max(0.0, out_frame - in_frame)
        placements.append({
            "in": in_frame, "out": out_frame, "span": span,
            "timeline_in": snap(timeline, args.fps),
            "timeline_out": snap(timeline + span, args.fps),
            "text": cut["text"],
        })
        timeline += span

    lines = ["<!-- %d clip(s) from %s, transcript: %s -->" % (
        len(placements), source, Path(args.transcript).name)]
    for number, clip in enumerate(placements, start=1):
        if number > 1 and args.gap > 0:
            lines.append('<gap dur="%s"/>' % fmt_ts(args.gap))
        if not args.plain:
            spoken = " ".join(clip["text"].split())
            if len(spoken) > 70:
                spoken = spoken[:67] + "..."
            lines.append("<!-- %d: %s -->" % (number, spoken))
        lines.append('<clip src="%s" in="%s" out="%s" timeline-in="%s" timeline-out="%s"/>'
                     % (source, fmt_ts(clip["in"]), fmt_ts(clip["out"]),
                        fmt_ts(clip["timeline_in"]), fmt_ts(clip["timeline_out"])))
    markup = "\n".join(lines) + "\n"
    total = placements[-1]["timeline_out"] if placements else 0.0

    if args.out:
        Path(args.out).expanduser().write_text(markup)
        print("CLIPS:%s" % Path(args.out).expanduser())
    else:
        print(markup)

    if args.stats:
        print("timeline: %s (%.3fs), %d clip(s), %.2fs gap each" % (
            fmt_clock(total), total, len(placements), args.gap), file=sys.stderr)
        for number, clip in enumerate(placements, start=1):
            if clip["span"] < 0.4:
                warn("clip %d is only %.2fs -- shorter than a word, check the source" % (
                    number, clip["span"]))
        if placements:
            print("\nverify the finished render -- speech should start and stop where these say:",
                  file=sys.stderr)
            print("  ffmpeg -i <render> -af silencedetect=noise=-32dB:d=0.35 -f null -",
                  file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# command line
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asr.py",
        description="Word-level transcription and cut planning that runs locally.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    transcribe = sub.add_parser("transcribe", help="media file -> transcript JSON")
    transcribe.add_argument("media", help="video or audio file (ffmpeg decides what it is)")
    transcribe.add_argument("--model", default=DEFAULT_MODEL,
                            help="faster-whisper model name (default %s)" % DEFAULT_MODEL)
    transcribe.add_argument("--language", default=None,
                            help="force a language code; omit to auto-detect")
    transcribe.add_argument("--out", default=None,
                            help="transcript path (default: beside the media, .transcript.json)")
    transcribe.add_argument("--srt", action="store_true", help="also write subtitles")
    transcribe.add_argument("--no-vad", action="store_true",
                            help="disable voice-activity filtering (rarely wanted)")
    transcribe.add_argument("--beam", type=int, default=5, help="beam size (default 5)")
    transcribe.add_argument("--progress", action="store_true", help="progress on stderr")
    transcribe.add_argument("--tmpdir", default=None,
                            help="where to put the extracted WAV (default: system temp)")
    transcribe.set_defaults(func=cmd_transcribe)

    find = sub.add_parser("find", help="transcript -> in/out points for a phrase")
    find.add_argument("transcript")
    find.add_argument("phrase")
    find.add_argument("--index", type=int, default=None,
                      help="report only the nth occurrence")
    find.add_argument("--context", type=float, default=2.0,
                      help="seconds of surrounding words to print (default 2.0)")
    find.add_argument("--lead", type=float, default=DEFAULT_LEAD, help="air before the first word")
    find.add_argument("--tail", type=float, default=DEFAULT_TAIL, help="air after the last word")
    find.add_argument("--fuzzy", type=float, default=0.72,
                      help="minimum similarity when no exact match exists (default 0.72)")
    find.add_argument("--json", action="store_true", help="machine-readable output")
    find.set_defaults(func=cmd_find)

    clips = sub.add_parser("clips", help="transcript + cut list -> clip markup")
    clips.add_argument("transcript")
    clips.add_argument("--cut-list", default=None, help="file, one cut per line")
    clips.add_argument("--cut", action="append", default=None,
                       help="a cut inline: a phrase or an in-out range (repeatable)")
    clips.add_argument("--lead", type=float, default=DEFAULT_LEAD, help="air before each cut")
    clips.add_argument("--tail", type=float, default=DEFAULT_TAIL, help="air after each cut")
    clips.add_argument("--gap", type=float, default=DEFAULT_GAP,
                       help="silence between clips on the timeline (default 0.25)")
    clips.add_argument("--fps", type=float, default=None,
                       help="snap to frame boundaries at this rate (e.g. 25, 29.97, 30)")
    clips.add_argument("--source", default=None, help="source file name used in the markup")
    clips.add_argument("--out", default=None, help="write markup here instead of stdout")
    clips.add_argument("--plain", action="store_true",
                       help="omit the per-clip comment lines from the markup")
    clips.add_argument("--fuzzy", type=float, default=0.72, help="phrase match threshold")
    clips.add_argument("--stats", action="store_true", help="timeline summary on stderr")
    clips.set_defaults(func=cmd_clips)

    return parser


def main(argv: list) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command", None) is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
