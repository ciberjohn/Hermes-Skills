#!/usr/bin/env python3
"""joplin_ask.py — grounded retrieval over the Joplin corpus.

For the ASK protocol: user asks "what do I know about X?" → this script returns
the top-k matching notes with folder + snippet, so the agent can read the full
bodies and answer WITH citations. Answers must be grounded in retrieved notes.

Usage:
  joplin_ask.py "<query>" [--limit 5] [--folder "Hosting"]
  joplin_ask.py "<query>" --full <id>     # print a note's full body

Output: ranked list — score context, folder, title, id, snippet.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from joplin_client import Joplin, JoplinError

SNIPPET_LEN = 220


def snippet(body, query):
    text = re.sub(r"\s+", " ", body or "")
    low = text.lower()
    q = query.lower()
    idx = low.find(q)
    if idx == -1:
        return text[:SNIPPET_LEN]
    start = max(0, idx - 60)
    return ("…" if start else "") + text[start:start + SNIPPET_LEN] + ("…" if start + SNIPPET_LEN < len(text) else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", help="search query (omit for help)")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--folder", help="restrict to one folder title")
    ap.add_argument("--full", help="print full body of a note id and exit")
    args = ap.parse_args()

    j = Joplin()

    if args.full:
        n = j.get_note(args.full, fields="id,title,body,parent_id")
        folder = "?"
        try:
            f = j.folder_by_id(n.get("parent_id", ""))
            folder = f["title"] if f else "?"
        except JoplinError:
            pass
        print(f"# {n.get('title')}  [{folder}]\n\n{n.get('body', '')}")
        return 0

    if not args.query:
        ap.print_help()
        return 1

    # id->folder map (for folder names in results)
    folder_map = {f["id"]: f["title"] for f in j.folders().get("items", [])}

    results = j.search(args.query, limit=args.limit).get("items", [])
    if args.folder:
        results = [r for r in results if folder_map.get(j.get_note(r["id"], fields="id,parent_id").get("parent_id", ""), "") == args.folder][:args.limit]

    if not results:
        print(f"no matches for: {args.query}")
        return 0

    print(f"top {len(results)} matches for: {args.query}\n")
    for r in results:
        nid = r["id"]
        full = j.get_note(nid, fields="id,title,body,parent_id")
        folder = folder_map.get(full.get("parent_id", ""), "?")
        snip = snippet(full.get("body", ""), args.query)
        print(f"[{folder}] {full.get('title','')}")
        print(f"  id: {nid}")
        print(f"  {snip}")
        print()
    print("(read full bodies with: joplin_ask.py '<query>' --full <id>)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except JoplinError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
