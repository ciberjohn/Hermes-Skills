#!/usr/bin/env python3
"""joplin_capture.py — capture anything into the Joplin INBOX (<10s).

Part of the joplin-brain skill. Writes ONLY via the Joplin REST API.
Every capture lands in the INBOX folder with source + timestamp metadata.
No filing at capture time — the FILER cron decides where it belongs later.

Usage:
  joplin_capture.py --title "T" --body "text" [--source "url|channel"] [--tag x]
  joplin_capture.py --url "https://..." [--title "override"]
  joplin_capture.py --file /path/to/file.pdf [--title "T"]   # attach as resource
  echo "text" | joplin_capture.py --title "T"                # body from stdin
"""
import argparse
import datetime
import os
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joplin_client import Joplin, JoplinError


def fetch_title(url):
    """Best-effort <title> extraction for a URL (no JS). Only http(s) allowed."""
    if not url.lower().startswith(("http://", "https://")):
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 joplin-brain"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read(200_000).decode("utf-8", "ignore")
        import re
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if m:
            return " ".join(m.group(1).split())[:200]
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description="Capture into Joplin INBOX")
    ap.add_argument("--title", help="note title")
    ap.add_argument("--body", help="note body")
    ap.add_argument("--source", default="manual", help="source url or channel (discord/signal/email/voice…)")
    ap.add_argument("--tag", action="append", default=[], help="extra tag (repeatable)")
    ap.add_argument("--url", help="capture a URL (title auto-fetched if not given)")
    ap.add_argument("--file", help="attach a file as resource")
    args = ap.parse_args()

    if not args.title and not args.url:
        ap.error("need --title (or --url)")

    title = args.title
    body = args.body or ""
    source = args.source

    if args.url:
        if not title:
            title = fetch_title(args.url) or args.url
        body = f"{body}\n\nURL: {args.url}".strip()

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    body = (
        f"source: {source}\n"
        f"captured: {now}\n"
        f"tags: capture{('' if not args.tag else ', ' + ', '.join(args.tag))}\n"
        f"---\n\n{body}"
    ).strip()

    j = Joplin()
    inbox = j.inbox_id()
    note = j.create_note(title, body=body, folder_id=inbox, tags=["capture"] + args.tag, source=args.source if args.url else None)

    if args.file:
        j.upload_resource(args.file, note_id=note["id"])

    print(f"captured: {note['id']} -> INBOX ({inbox[:8]}…)\n{title}")


if __name__ == "__main__":
    try:
        main()
    except JoplinError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
