#!/usr/bin/env python3
"""joplin_filer.py — agent-filed organization of the INBOX.

Deterministic folder classifier: scores each INBOX note against existing folder
names (title + body keywords), moves high-confidence matches, flags low-confidence
with `needs-review`, writes an audit trail to the FILER LOG note.

Rules (from the joplin-brain skill design):
  - NEVER delete notes.
  - NEVER touch notes outside INBOX.
  - Never move monthly journal notes ('<N> <Month> <Year>') — those are capture journals.
  - Low confidence (< threshold) → leave in INBOX, tag `needs-review`.
  - Dry-run is the default; --apply performs moves.

Usage:
  joplin_filer.py                # dry run: print what WOULD happen
  joplin_filer.py --apply        # actually file
  joplin_filer.py --min-score 0.6  # confidence threshold (default 0.5)
"""
import argparse
import datetime
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joplin_client import Joplin, JoplinError

# Folder titles that are capture journals / system folders — never file into these
JOURNAL_RE = re.compile(r"^\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December) \d{4}$", re.I)
SYSTEM_FOLDERS = {"INBOX", "__SYSTEM"}
SYSTEM_NOTES = {"FILER LOG", "TAG VOCABULARY"}

# stopwords for scoring
STOP = set("the a an and or of to in for on with by from at as is are was were be been being this that these those it its i you he she we they my your our their not no yes do does did have has had will would can could should may might must about into over under after before between out up down off all any both each few more most other some such only own same so than too very just but what which who whom whose when where why how".split())


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1}


def score(note_text, folder_title):
    """Coverage-based score: how much of the folder's identity appears in the note.
    Primary signal = folder tokens present in the note (word-boundary);
    Jaccard adds a small secondary signal for topical breadth."""
    nt = tokens(note_text)
    ft = tokens(folder_title)
    if not ft or not nt:
        return 0.0
    matched = sum(1 for w in ft if re.search(r"\b" + re.escape(w), note_text.lower()))
    coverage = matched / len(ft)
    inter = len(nt & ft)
    union = len(nt | ft)
    jac = inter / union if union else 0.0
    return min(1.0, coverage * 0.8 + jac * 0.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="perform moves (default: dry run)")
    ap.add_argument("--min-score", type=float, default=0.5, help="confidence threshold (default 0.5)")
    ap.add_argument("--folder", help="restrict filing to one folder title (debug)")
    args = ap.parse_args()

    j = Joplin()
    inbox_id = j.inbox_id(create=False)
    notes = j.notes_in_folder(inbox_id, limit=100).get("items", [])
    if not notes:
        print("INBOX is empty — nothing to file.")
        return 0

    folders = [f for f in j.folders().get("items", []) if f["title"] not in SYSTEM_FOLDERS and not JOURNAL_RE.match(f["title"])]

    plan = []
    for n in notes:
        title = n.get("title", "")
        if any(title == p for p in SYSTEM_NOTES):
            continue  # don't file system notes
        full = j.get_note(n["id"], fields="id,title,body")
        text = f"{full.get('title','')} {full.get('body','')[:4000]}"
        scored = sorted(((score(text, f["title"]), f) for f in folders), key=lambda x: -x[0])
        best_score, best_folder = scored[0]
        if best_score >= args.min_score:
            plan.append((n, best_folder, best_score))
        else:
            plan.append((n, None, best_score))

    print(f"INBOX: {len(notes)} notes | threshold {args.min_score}\n")
    moved = 0
    for n, folder, s in sorted(plan, key=lambda x: -(x[2] if x[1] else 0)):
        if folder:
            action = "MOVE" if args.apply else "would move"
            if args.apply:
                j.move_note(n["id"], folder["id"])
            print(f"  {action:12s} [{s:.2f}] {n['title'][:60]!r} -> {folder['title']}")
            moved += 1
        else:
            print(f"  needs-review [{s:.2f}] {n['title'][:60]!r}  (best: {scored[0][1]['title'] if scored else '?'})")
            if args.apply:
                j.update_note(n["id"], body=f"{j.get_note(n['id'])['body']}\n\n<!-- filer: needs-review -->")
                # tag needs-review (via client tag attach)
                try:
                    j._set_tags(n["id"], ["needs-review"])
                except JoplinError:
                    pass

    # audit log
    if args.apply:
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        log_lines = [f"\n## {ts} — filer run ({len(notes)} INBOX notes, {moved} filed)"]
        for n, folder, s in plan:
            log_lines.append(f"- {n['title'][:60]!r} -> {folder['title'] if folder else 'needs-review'} ({s:.2f})")
        body = "\n".join(log_lines)
        # Resolve FILER LOG by LISTING __SYSTEM (never /search — FTS lag creates duplicates)
        sys_id = j.system_folder_id()
        log_note = None
        for n in j.notes_in_folder(sys_id, limit=100).get("items", []):
            if n.get("title") == "FILER LOG":
                log_note = n["id"]
                break
        if log_note:
            existing = j.get_note(log_note).get("body", "")
            j.update_note(log_note, body=body + "\n" + existing)
            print("\naudit appended to FILER LOG")
        else:
            j.create_note("FILER LOG", body=body, folder_id=sys_id)
            print("\nFILER LOG note created in __SYSTEM")
    else:
        print("\n(dry run — rerun with --apply to execute; add --min-score to tune)")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except JoplinError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
