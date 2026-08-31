#!/usr/bin/env python3
"""Generate an image via OpenRouter using an image-capable model.

Usage:
    python3 generate_image.py <out.png> "<prompt>" [model]

Key precedence (implements the skill's stale-key mitigation):
1. OPENROUTER_ENV_FILE (explicit path) -> read the key from that file
2. OPENROUTER_API_KEY environment variable
3. default ~/.hermes/.env if it exists

The image comes back embedded in the JSON response as a data:image URL --
walk the entire response recursively to find it (message.content may be null).
"""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request


def load_key():
    env_file = os.environ.get("OPENROUTER_ENV_FILE")
    if env_file:
        env_file = os.path.expanduser(env_file)
        if os.path.exists(env_file):
            for line in open(env_file):
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    default = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(default):
        for line in open(default):
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


KEY = load_key()
if not KEY:
    sys.exit("no OpenRouter key: set OPENROUTER_ENV_FILE or OPENROUTER_API_KEY")

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/image.png"
PROMPT = sys.argv[2] if len(sys.argv) > 2 else "A simple test image, a red circle on white."
MODEL = sys.argv[3] if len(sys.argv) > 3 else "google/gemini-3.1-flash-lite-image"

payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": PROMPT}],
    "n": 1,
}
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "X-Title": "Hermes image generation",
    },
)
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.load(resp)
except urllib.error.HTTPError as e:
    sys.exit(f"API error {e.code}: {e.read().decode(errors='replace')[:500]}")

found = []

def walk(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            walk(v)
    elif isinstance(obj, list):
        for v in obj:
            walk(v)
    elif isinstance(obj, str):
        if obj.startswith("data:image"):
            found.append(obj)
        elif obj.startswith("http") and re.search(r"image|img|png|jpe?g|webp", obj, re.I):
            found.append(obj)

walk(data)

if not found:
    sys.exit("NO IMAGE FOUND in response. Top-level keys: " + ", ".join(data.keys()))

raw = found[0]
if raw.startswith("data:"):
    img = base64.b64decode(raw.split(",", 1)[1])
else:
    with urllib.request.urlopen(raw, timeout=60) as r:
        img = r.read()
with open(OUT, "wb") as f:
    f.write(img)
print(f"OK wrote {OUT} ({len(img)} bytes)")
