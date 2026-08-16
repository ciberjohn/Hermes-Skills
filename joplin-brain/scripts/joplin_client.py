#!/usr/bin/env python3
"""joplin_client.py — thin wrapper around the Joplin REST API (localhost:41184).

Part of the joplin-brain skill (see the skill's README for the full package).
Rules: REST API is the ONLY write surface. Never write to the SQLite DB directly.

Usage (CLI):
  joplin_client.py ping
  joplin_client.py count
  joplin_client.py folders [--title-only]
  joplin_client.py search "<query>" [--limit N] [--fields id,title]
  joplin_client.py inbox-id
  joplin_client.py create --title "T" [--body "B"] [--folder ID] [--tags a,b]
  joplin_client.py get <note-id>
  joplin_client.py update <note-id> --body "B" [--title "T"]
  joplin_client.py move <note-id> --folder <folder-id-or-title>
  joplin_client.py recent [--limit N]
  joplin_client.py folder-id "<folder title>"

Usage (library):
  from joplin_client import Joplin
  j = Joplin()
  j.count_notes(); j.create_note(title, body, folder_id, tags); j.search("x")
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_BASE = f"http://localhost:{os.environ.get('JOPLIN_API_PORT', '41184')}"
# Agent shells may redirect HOME to a profile dir; the real Joplin config lives
# in the actual user home. Override with JOPLIN_REAL_HOME if your setup differs.
REAL_USER_HOME = os.environ.get("JOPLIN_REAL_HOME") or os.path.expanduser("~")
SETTINGS_CANDIDATES = [
    os.environ.get("JOPLIN_SETTINGS_PATH") or os.path.join(REAL_USER_HOME, ".config/joplin/settings.json"),
    os.path.expanduser("~/.config/joplin/settings.json"),
]
INBOX_TITLE = "INBOX"
SYSTEM_TITLE = "__SYSTEM"


class JoplinError(RuntimeError):
    pass


def _token():
    for path in SETTINGS_CANDIDATES:
        try:
            with open(path) as f:
                tok = json.load(f).get("api.token", "")
                if tok:
                    _warn_if_world_readable(path)
                    return tok
        except OSError:
            continue
    raise JoplinError(f"no api.token found in any of {SETTINGS_CANDIDATES}")


def _warn_if_world_readable(path):
    """Defense-in-depth: settings.json holds the API token; flag loose permissions."""
    try:
        mode = os.stat(path).st_mode & 0o777
        if mode & 0o044:
            print(f"WARNING: {path} is group/world-readable (mode {oct(mode)}) — consider chmod 600", file=sys.stderr)
    except OSError:
        pass


class Joplin:
    def __init__(self, base=API_BASE, token=None):
        self.base = base
        self.token = token or _token()
        if not self.token:
            raise JoplinError("no api.token in settings.json — enable the REST API first")

    def _req(self, method, path, data=None, params=None):
        params = dict(params or {})
        params.setdefault("token", self.token)
        url = f"{self.base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
                if not raw:
                    return None
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw  # e.g. /ping returns plain text "JoplinClipperServer"
        except urllib.error.HTTPError as e:
            raise JoplinError(f"HTTP {e.code} on {method} {path}: {e.read().decode()[:300]}")
        except urllib.error.URLError as e:
            raise JoplinError(f"connection failed (is `joplin server start` running?): {e}")

    def ping(self):
        return self._req("GET", "/ping")

    # --- notes ---
    def count_notes(self):
        n, page = 0, 1
        while True:
            d = self._req("GET", "/notes", params={"fields": "id", "limit": 100, "page": page})
            n += len(d.get("items", []))
            if not d.get("has_more"):
                return n
            page += 1

    def search(self, query, limit=10, fields="id,title"):
        return self._req("GET", "/search", params={"query": query, "limit": limit, "fields": fields})

    def get_note(self, note_id, fields="id,title,body,parent_id,updated_time"):
        return self._req("GET", f"/notes/{note_id}", params={"fields": fields})

    def _resolve_folder(self, folder):
        """Accept a folder id (32 hex chars) or a title; raise if unresolvable."""
        if folder and folder.isalnum() and len(folder) == 32:
            return folder
        f = self.folder_by_title(folder)
        if not f:
            raise JoplinError(f"folder not found: '{folder}'")
        return f["id"]

    def create_note(self, title, body="", folder_id=None, tags=None, source=None):
        data = {"title": title, "body": body}
        if folder_id:
            data["parent_id"] = folder_id
        if source:
            data["source_url"] = source
        note = self._req("POST", "/notes", data=data)
        if tags:
            self._set_tags(note["id"], tags)
        return note

    def update_note(self, note_id, body=None, title=None):
        data = {}
        if body is not None:
            data["body"] = body
        if title is not None:
            data["title"] = title
        return self._req("PUT", f"/notes/{note_id}", data=data)

    def move_note(self, note_id, folder_id):
        return self._req("PUT", f"/notes/{note_id}", data={"parent_id": folder_id})

    def delete_note(self, note_id):
        return self._req("DELETE", f"/notes/{note_id}")

    def notes_in_folder(self, folder_id, limit=100, fields="id,title"):
        return self._req("GET", f"/folders/{folder_id}/notes", params={"limit": limit, "fields": fields})

    def recent_notes(self, limit=10):
        return self._req("GET", "/notes", params={"limit": limit, "fields": "id,title,updated_time", "order_by": "updated_time", "order_dir": "DESC"})

    # --- folders ---
    def folders(self, fields="id,title"):
        items, page = [], 1
        while True:
            d = self._req("GET", "/folders", params={"fields": fields, "limit": 100, "page": page})
            items += d.get("items", [])
            if not d.get("has_more"):
                return {"items": items}
            page += 1

    def create_folder(self, title):
        return self._req("POST", "/folders", data={"title": title})

    def folder_by_title(self, title):
        for f in self.folders().get("items", []):
            if f["title"].lower() == title.lower():
                return f
        return None

    def folder_by_id(self, folder_id):
        if not folder_id:
            return None
        for f in self.folders().get("items", []):
            if f["id"] == folder_id:
                return f
        return None

    def inbox_id(self, create=True):
        f = self.folder_by_title(INBOX_TITLE)
        if f:
            return f["id"]
        if create:
            return self.create_folder(INBOX_TITLE)["id"]
        raise JoplinError(f"folder '{INBOX_TITLE}' not found")

    def system_folder_id(self, create=True):
        """Resolve __SYSTEM (or create it). Used for FILER LOG / AGENT LOG placement."""
        f = self.folder_by_title(SYSTEM_TITLE)
        if f:
            return f["id"]
        if create:
            return self.create_folder(SYSTEM_TITLE)["id"]
        raise JoplinError(f"folder '{SYSTEM_TITLE}' not found")

    # --- tags ---
    def _set_tags(self, note_id, tags):
        for t in tags:
            tag = self._req("GET", "/tags", params={"fields": "id,title", "limit": 100})
            found = next((x for x in tag.get("items", []) if x["title"].lower() == t.lower()), None)
            if not found:
                found = self._req("POST", "/tags", data={"title": t})
            self._req("POST", f"/tags/{found['id']}/notes", data={"id": note_id})

    # --- resources (attachments) ---
    def upload_resource(self, filepath, filename=None, note_id=None):
        """Attach a file as a resource. Optionally link to an existing note."""
        import mimetypes
        import uuid

        filename = filename or os.path.basename(filepath)
        with open(filepath, "rb") as f:
            data = f.read()
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        boundary = "----joplin" + uuid.uuid4().hex
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="data"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n".encode() + data + b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        body = b"".join(parts)
        url = f"{self.base}/resources?token={self.token}"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode())
        if note_id:
            self._req("POST", f"/notes/{note_id}/resources", data={"id": res["id"]})
        return res


def _cli(argv):
    j = Joplin()
    cmd = argv[0] if argv else "help"
    try:
        if cmd == "ping":
            print(j.ping())
        elif cmd == "count":
            print(j.count_notes())
        elif cmd == "folders":
            title_only = "--title-only" in argv
            for f in j.folders().get("items", []):
                print(f["title"] if title_only else f"{f['id']}  {f['title']}")
        elif cmd == "folder-id":
            f = j.folder_by_title(argv[1])
            print(f["id"] if f else "NOT FOUND")
        elif cmd == "inbox-id":
            print(j.inbox_id())
        elif cmd == "search":
            q = argv[1]
            limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 10
            for n in j.search(q, limit=limit).get("items", []):
                print(f"{n.get('id','')}  {n.get('title','')}")
        elif cmd == "get":
            n = j.get_note(argv[1])
            print(f"# {n.get('title')}\n{n.get('body','')}")
        elif cmd == "create":
            title = argv[argv.index("--title") + 1]
            body = argv[argv.index("--body") + 1] if "--body" in argv else ""
            folder = argv[argv.index("--folder") + 1] if "--folder" in argv else None
            tags = argv[argv.index("--tags") + 1].split(",") if "--tags" in argv else None
            if folder:
                folder = j._resolve_folder(folder)
            n = j.create_note(title, body=body, folder_id=folder, tags=tags)
            print(f"created {n['id']} in folder {folder or 'none'}")
        elif cmd == "update":
            nid = argv[1]
            body = argv[argv.index("--body") + 1] if "--body" in argv else None
            title = argv[argv.index("--title") + 1] if "--title" in argv else None
            j.update_note(nid, body=body, title=title)
            print(f"updated {nid}")
        elif cmd == "move":
            nid = argv[1]
            folder = argv[argv.index("--folder") + 1]
            folder = j._resolve_folder(folder)
            j.move_note(nid, folder)
            print(f"moved {nid} -> {folder}")
        elif cmd == "recent":
            for n in j.recent_notes(int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 10).get("items", []):
                print(f"{n.get('updated_time')}  {n.get('title','')}")
        else:
            print(__doc__)
            return 1
    except JoplinError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
