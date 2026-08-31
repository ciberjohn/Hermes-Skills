#!/usr/bin/env python3
"""Verify a generated image via a cheap OpenRouter vision model.

Usage:
    python3 verify_image_vision.py <image.png> [model]

Key precedence (implements the skill's stale-key mitigation):
1. OPENROUTER_ENV_FILE (explicit path) -> read the key from that file
2. OPENROUTER_API_KEY environment variable
3. default ~/.hermes/.env if it exists

Sends the PNG as a data: URL in a content array (text + image_url) to a
vision-capable model and prints its description. Use when the configured aux
vision provider rejects images (e.g. a text-only model).
"""
import base64
import json
import os
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

if len(sys.argv) < 2:
    sys.exit("usage: python3 verify_image_vision.py <image.png> [model]")
IMG = sys.argv[1]
MODEL = sys.argv[2] if len(sys.argv) > 2 else "google/gemini-3.5-flash-lite"

b64 = base64.b64encode(open(IMG, "rb").read()).decode()
data_url = f"data:image/png;base64,{b64}"

prompt = (
    "Describe this image precisely. Questions: "
    "(1) What is the main subject and does it match the requested character/scene? "
    "(2) Is there any required text, and is it legible and correctly spelled? "
    "(3) Are the requested elements all present? "
    "(4) What is the overall style and composition? Be concise."
)

payload = {
    "model": MODEL,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ],
    }],
}
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
except urllib.error.HTTPError as e:
    sys.exit(f"API error {e.code}: {e.read().decode(errors='replace')[:500]}")

# Same recursive walk as generate_image.py: message.content may be null or
# nested (the documented failure mode), so never trust direct indexing.
parts = []

def walk(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            walk(v)
    elif isinstance(obj, list):
        for v in obj:
            walk(v)
    elif isinstance(obj, str):
        parts.append(obj)

walk(data)
text = "\n".join(parts).strip()
if not text:
    sys.exit("no text content in response. Top-level keys: " + ", ".join(data.keys()))
print(text)
