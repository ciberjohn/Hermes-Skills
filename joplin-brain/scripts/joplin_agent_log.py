#!/usr/bin/env python3
"""joplin_agent_log.py — chronological agent memory log in Joplin (__SYSTEM/AGENT LOG).

Extended agent memory: after a working session, append a digest of actions,
decisions and outcomes. Core facts stay in Hermes memory (injected every turn);
this is the readable, queryable archive that also syncs to the user's devices
via the configured Joplin sync target (Dropbox, Nextcloud, S3, etc.).

Rules:
  - NEVER delete or edit past entries (append-only, newest first, like FILER LOG).
  - Resolve the AGENT LOG note by listing the __SYSTEM folder directly —
    do NOT use /search (FTS lags and caused a duplicate FILER LOG note once).
  - Create the note in __SYSTEM if missing (never in INBOX, never at root).

Usage:
  joplin_agent_log.py --entry "line 1\nline 2" [--title "Short summary"]
  joplin_agent_log.py --file /path/to/entry.md [--title "Short summary"]
  joplin_agent_log.py --show                # print most recent entries
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joplin_client import Joplin, JoplinError

LOG_TITLE = "AGENT LOG"


def find_system_folder(j):
    """Resolve __SYSTEM folder id, paginating (client handles has_more)."""
    for f in j.folders().get("items", []):
        if f["title"] == "__SYSTEM":
            return f["id"]
    return None


def find_log_note(j, sys_id):
    """Find the AGENT LOG note inside __SYSTEM by listing the folder directly."""
    for n in j.notes_in_folder(sys_id, limit=100).get("items", []):
        if n.get("title") == LOG_TITLE:
            return n["id"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", help="entry text (multiline OK inside quotes)")
    ap.add_argument("--file", help="read entry text from a file")
    ap.add_argument("--title", default="agent note", help="one-line summary after the timestamp")
    ap.add_argument("--show", action="store_true", help="print most recent entries")
    args = ap.parse_args()

    j = Joplin()

    if args.show:
        sys_id = find_system_folder(j)
        if not sys_id:
            print("__SYSTEM folder not found — AGENT LOG does not exist yet.")
            return 0
        note_id = find_log_note(j, sys_id)
        if not note_id:
            print("AGENT LOG note not found in __SYSTEM.")
            return 0
        body = j.get_note(note_id, fields="id,title,body").get("body", "")
        print(f"=== AGENT LOG ({len(body)} chars) ===\n")
        print(body[:6000])
        return 0

    if not args.entry and not args.file:
        print("Provide --entry, --file, or --show.", file=sys.stderr)
        return 1

    try:
        text = args.entry if args.entry else open(args.file, encoding="utf-8").read().strip()
    except OSError as e:
        print(f"ERROR: cannot read {args.file}: {e}", file=sys.stderr)
        return 1
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    entry = f"## {ts} — {args.title}\n{text}\n"

    sys_id = find_system_folder(j) or j.system_folder_id()  # create __SYSTEM if missing
    if not sys_id:
        print("ERROR: __SYSTEM folder not found — cannot place AGENT LOG.", file=sys.stderr)
        return 1

    note_id = find_log_note(j, sys_id)
    if note_id:
        existing = j.get_note(note_id, fields="body").get("body", "")
        j.update_note(note_id, body=entry + existing)
        print(f"appended to AGENT LOG ({note_id[:8]}… in __SYSTEM)")
    else:
        j.create_note(LOG_TITLE, body=entry, folder_id=sys_id)
        print(f"AGENT LOG created in __SYSTEM")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except JoplinError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
