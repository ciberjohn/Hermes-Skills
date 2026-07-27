#!/usr/bin/env python3
"""
Webhook/Token Poster for Discord, Slack, Telegram, and GitHub.
No OAuth needed — just a webhook URL, bot token, or PAT.

Usage:
  python3 webhook-poster.py discord     <webhook_url>   "<message>"
  python3 webhook-poster.py slack       <webhook_url>   "<message>"
  python3 webhook-poster.py telegram    <bot_token> <chat_id> "<message>"
  python3 webhook-poster.py github      <pat>      <repo> "<title>" "<body>"
"""
import sys, json, urllib.request, urllib.error

def post(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode(errors='replace')[:200]}"

def post_discord(webhook, text):
    return post(webhook, {"content": text})

def post_slack(webhook, text):
    return post(webhook, {"text": text})

def post_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return post(url, {"chat_id": chat_id, "text": text, "disable_web_page_preview": False})

def post_github(pat, repo, title, body):
    url = f"https://api.github.com/repos/{repo}/issues"
    data = json.dumps({"title": title, "body": body}).encode()
    req = urllib.request.Request(url, data=data,
        headers={"Authorization": f"Bearer {pat}", "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return f"✅ Issue created: {json.loads(r.read())['html_url']}"

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    if cmd == "discord" and len(sys.argv) >= 4:
        print(post_discord(sys.argv[2], sys.argv[3]))
    elif cmd == "slack" and len(sys.argv) >= 4:
        print(post_slack(sys.argv[2], sys.argv[3]))
    elif cmd == "telegram" and len(sys.argv) >= 5:
        print(post_telegram(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif cmd == "github" and len(sys.argv) >= 5:
        print(post_github(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else ""))
    else:
        print(f"Usage: see docstring or python3 {__file__} --help")

if __name__ == "__main__":
    main()
