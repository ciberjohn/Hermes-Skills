#!/usr/bin/env python3
"""Transcribe audio with CrisperWhisper 2.0 — verbatim + intended modes.

Usage:
  transcribe.py <audio> --out <dir> [--model medium] [--language pt] [--words] [--srt] [--backend auto]

  <audio>  local path, http(s) URL, or Dropbox shared link.
  --out    output directory; a dated folder <date>_<slug>/ is created inside.
  --model  small | medium | turbo | large   (default: medium — CPU tradeoff)
  --language  ISO code (pt, en, ...). Omit for auto-detect.
  --words  also write words.tsv with per-word timestamps.
  --srt    also write intended.srt subtitle file.
  --backend  auto | ct2 | transformers   (default: auto — ct2 if importable)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

MODEL_SIZES = ("small", "medium", "turbo", "large")


def log(msg):
    print(f"[transcribe] {msg}", flush=True)


def fetch_source(src, workdir):
    """Return a local path to the audio. Handles URLs and Dropbox shared links."""
    src = str(src)
    if src.startswith(("http://", "https://")):
        url = src
        # Dropbox shared links: force direct download
        if "dropbox.com" in url and "dropboxusercontent.com" not in url:
            url = url.replace("?dl=0", "?dl=1")
            if "?" not in url:
                url += "?dl=1"
            url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
        name = url.split("/")[-1].split("?")[0] or "remote-audio"
        dest = workdir / name
        log(f"downloading {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        log(f"downloaded {dest} ({dest.stat().st_size} bytes)")
        return dest
    p = Path(src)
    if not p.exists():
        raise SystemExit(f"audio not found: {src}")
    return p


def probe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60,
        ).stdout
        return float(json.loads(out)["format"]["duration"])
    except Exception:
        return None


def safe_slug(name):
    base = Path(str(name)).stem
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower()
    return base[:60] or "audio"


def write_srt(words, path):
    def fmt(t):
        ms = int(round(t * 1000))
        h, rem = divmod(ms, 3600000)
        m, rem = divmod(rem, 60000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines, idx = [], 1
    for w in words:
        lines.append(str(idx))
        lines.append(f"{fmt(w.start)} --> {fmt(w.end)}")
        lines.append(w.word)
        lines.append("")
        idx += 1
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", help="local path, URL, or Dropbox shared link")
    ap.add_argument("--out", default=str(Path.home() / "transcribe-out"))
    ap.add_argument("--model", default="medium", choices=MODEL_SIZES)
    ap.add_argument("--language", default=None, help="ISO code; omit for auto-detect")
    ap.add_argument("--words", action="store_true", help="write words.tsv with timestamps")
    ap.add_argument("--srt", action="store_true", help="write intended.srt")
    ap.add_argument("--backend", default="auto", choices=("auto", "ct2", "transformers"))
    args = ap.parse_args()

    workdir = Path("/tmp/transcribe-work")
    workdir.mkdir(parents=True, exist_ok=True)

    audio = fetch_source(args.audio, workdir)
    if not args.language:
        args.language = None  # auto-detect

    from crisperwhisper import CrisperWhisperModel

    backend = args.backend
    if backend == "auto":
        try:
            from importlib.metadata import version as _v
            _v("ctranslate2-crisperwhisper")
            backend = "ct2"
        except Exception:
            backend = "transformers"
    log(f"backend={backend} model={args.model} language={args.language or 'auto'}")

    t0 = time.time()
    # CPU box: ct2 float16 requires a GPU — force int8 quantization for ct2.
    ct_kwargs = {"compute_type": "int8"} if backend == "ct2" else {}
    model = CrisperWhisperModel(args.model, backend=backend, **ct_kwargs)
    log(f"model loaded in {time.time()-t0:.1f}s")

    kwargs = {}
    if args.language:
        kwargs["language"] = args.language

    t0 = time.time()
    if backend == "ct2":
        try:
            verbatim, intended = model.transcribe_dual(
                str(audio), modes=("verbatim", "intended"),
                word_timestamps=args.words or args.srt, **kwargs)
        except NotImplementedError:
            verbatim = model.transcribe(str(audio), mode="verbatim",
                                        word_timestamps=args.words or args.srt, **kwargs)
            intended = model.transcribe(str(audio), mode="intended", **kwargs)
    else:
        verbatim = model.transcribe(str(audio), mode="verbatim",
                                    word_timestamps=args.words or args.srt, **kwargs)
        intended = model.transcribe(str(audio), mode="intended", **kwargs)
    elapsed = time.time() - t0

    duration = probe_duration(audio) or 0
    slug = safe_slug(Path(str(audio)).name)
    outdir = Path(args.out) / f"{datetime.now():%Y-%m-%d}_{slug}"
    outdir.mkdir(parents=True, exist_ok=True)

    (outdir / "verbatim.txt").write_text(verbatim.text.strip() + "\n", encoding="utf-8")
    (outdir / "intended.txt").write_text(intended.text.strip() + "\n", encoding="utf-8")

    if args.words:
        with open(outdir / "words.tsv", "w", encoding="utf-8") as f:
            f.write("start\tend\tword\n")
            for w in verbatim.words:
                f.write(f"{w.start:.2f}\t{w.end:.2f}\t{w.word}\n")
    if args.srt and getattr(intended, "words", None):
        write_srt(intended.words, outdir / "intended.srt")

    meta = {
        "source": str(args.audio),
        "audio_file": Path(str(audio)).name,
        "duration_seconds": round(duration, 1),
        "model": args.model,
        "backend": backend,
        "language": args.language or "auto",
        "language_detected": getattr(intended, "language", None) or None,
        "date": datetime.now().isoformat(timespec="seconds"),
        "transcribe_seconds": round(elapsed, 1),
        "verbatim_words": len(verbatim.text.split()),
        "intended_words": len(intended.text.split()),
        "files": sorted(p.name for p in outdir.iterdir()),
    }
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")

    log(f"done in {elapsed:.1f}s ({duration/60:.1f} min audio) -> {outdir}")
    log(f"  verbatim:  {outdir / 'verbatim.txt'}  ({meta['verbatim_words']} words)")
    log(f"  intended:  {outdir / 'intended.txt'}  ({meta['intended_words']} words)")
    print(f"OUTDIR:{outdir}")


if __name__ == "__main__":
    main()
