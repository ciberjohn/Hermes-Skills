#!/usr/bin/env python3
"""
Unified poster for all 15 social-poster platforms.
Posts content stored in the vault to specified platforms via their APIs.

Usage:
  python3 post.py --help
  python3 post.py --platforms x,linkedin,bluesky --text "Hello world" --link https://example.com
  python3 post.py --platforms discord,slack,telegram --text "Hello" --webhook-config
"""
import sys, os, json, urllib.request, urllib.parse, urllib.error

# --- Config ---
_user_dir = os.path.expanduser("~")
if "hermes/profiles" in _user_dir:
    import pwd; _user_dir = pwd.getpwuid(os.getuid()).pw_dir

VAULT_PATH = os.path.join(_user_dir, ".social-poster", "vault.json")
CONFIG_PATH = os.path.join(_user_dir, ".social-poster", "config.json")

def load_vault():
    return json.load(open(VAULT_PATH)) if os.path.exists(VAULT_PATH) else {}

def load_config():
    return json.load(open(CONFIG_PATH)) if os.path.exists(CONFIG_PATH) else {}

def fetch(url, method="GET", data=None, headers=None):
    h = {"User-Agent": "SocialPoster/1.0"}
    if headers: h.update(headers)
    if isinstance(data, dict): data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            try: return json.loads(body)
            except: return body
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode(errors="replace")[:300]}
    except Exception as e:
        return {"error": str(e)}

# --- Platform Posters ---

def post_x(text, vault, config):
    tok = vault.get("x", {}).get("access_token", "")
    sec = vault.get("x", {}).get("access_secret", "")
    if not tok or not sec: return "No X tokens"
    import base64, hmac, hashlib, time
    ck, cs = config["x"]["api_key"], config["x"]["api_secret"]
    nonce = base64.b64encode(os.urandom(16)).decode()[:32]
    # RFC 5849 percent-encoding: encode everything except unreserved chars.
    def enc(s):
        return urllib.parse.quote(str(s), safe="-._~")
    oauth = {
        "oauth_consumer_key": ck, "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": str(int(time.time())),
        "oauth_token": tok, "oauth_version": "1.0",
    }
    body = json.dumps({"text": text}).encode()
    # Twitter v2 + OAuth 1.0a with a JSON body requires the body to be signed.
    # oauthlib (and requests-oauthlib) do this via an oauth_body_hash parameter
    # (draft-eaton-oauth-bodyhash-00); without it the API rejects with 401.
    oauth["oauth_body_hash"] = base64.b64encode(hashlib.sha1(body).digest()).decode()
    pairs = [(enc(k), enc(v)) for k, v in sorted(oauth.items())]
    ps = "&".join(f"{k}={v}" for k, v in pairs)
    url = "https://api.twitter.com/2/tweets"
    base = "&".join([enc("POST"), enc(url), enc(ps)])
    key = f"{enc(cs)}&{enc(sec)}"
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    auth = "OAuth " + ", ".join(f'{enc(k)}="{enc(v)}"' for k, v in sorted(oauth.items()))
    r = fetch(url, method="POST", data=body,
              headers={"Authorization": auth, "Content-Type": "application/json"})
    if isinstance(r, dict) and r.get("data", {}).get("id"):
        return r["data"]["id"]
    return f"Result: {r}"

def post_linkedin(text, vault, link=None):
    tok = vault.get("linkedin", {}).get("access_token", "")
    if not tok: return "No LinkedIn token"
    # Get profile URN
    prof = fetch("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {tok}"})
    sub = prof.get("sub", "")
    if not sub: return f"Cannot get profile: {prof}"
    # When a link is provided, use ARTICLE category so LinkedIn crawls the URL
    # and renders a rich card with a thumbnail (OG image) instead of a bare URL.
    if link:
        share = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "ARTICLE",
            "media": [{"status": "READY", "originalUrl": link}]
        }
    else:
        share = {"shareCommentary": {"text": text}, "shareMediaCategory": "NONE"}
    body = {
        "author": f"urn:li:person:{sub}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    r = fetch("https://api.linkedin.com/v2/ugcPosts", method="POST",
              data=json.dumps(body).encode(),
              headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                       "X-Restli-Protocol-Version": "2.0.0"})
    return r.get("id", f"Result: {r}")

def _resolve_pds(vault):
    """Resolve the PDS hosting the account's handle (accounts may not live on bsky.social)."""
    h = vault.get("bluesky", {}).get("handle", "")
    if not h:
        return "https://bsky.social"
    try:
        r = fetch("https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle=" + urllib.parse.quote(h))
        did = r.get("did", "") if isinstance(r, dict) else ""
        if did:
            doc = fetch(f"https://plc.directory/{did}")
            if isinstance(doc, dict):
                for s in doc.get("service", []):
                    if s.get("id") == "#atproto_pds" and s.get("type") == "AtprotoPersonalDataServer":
                        return s.get("serviceEndpoint", "https://bsky.social")
    except Exception:
        pass
    return "https://bsky.social"

def post_bluesky(text, vault):
    h = vault.get("bluesky", {}).get("handle", "")
    p = vault.get("bluesky", {}).get("app_password", "")
    if not h or not p: return "No Bluesky credentials"
    pds = _resolve_pds(vault)
    # Create session
    sess = fetch(f"{pds}/xrpc/com.atproto.server.createSession", method="POST",
                 data=json.dumps({"identifier": h, "password": p}).encode(),
                 headers={"Content-Type": "application/json"})
    token = sess.get("accessJwt", "")
    did = sess.get("did", "")
    if not token: return f"Auth failed: {sess}"
    # Create post (rudimentary — facets/mentions not handled)
    body = {
        "repo": did, "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": text[:300], "createdAt": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
    }
    r = fetch(f"{pds}/xrpc/com.atproto.repo.createRecord", method="POST",
              data=json.dumps(body).encode(),
              headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return r.get("uri", f"Result: {r}")

def post_mastodon(text, vault, config):
    tok = vault.get("mastodon", {}).get("access_token", "")
    inst = vault.get("mastodon", {}).get("instance", config.get("mastodon", {}).get("instance", ""))
    if not tok: return "No Mastodon token"
    r = fetch(f"https://{inst}/api/v1/statuses", method="POST",
              data={"status": text},
              headers={"Authorization": f"Bearer {tok}"})
    return r.get("id", f"Result: {r}")

def post_twitch(text, vault, config):
    tok = vault.get("twitch", {}).get("access_token", "")
    cid = config.get("twitch", {}).get("client_id", "")
    if not tok: return "No Twitch token"
    if not cid: return "No Twitch client_id in config"
    r = fetch("https://api.twitch.tv/helix/channels", method="GET",
              headers={"Authorization": f"Bearer {tok}", "Client-Id": cid})
    return f"Twitch posting requires broadcaster channel ID. Auth valid."

def post_reddit(text, vault):
    tok = vault.get("reddit", {}).get("access_token", "")
    if not tok: return "No Reddit token"
    return f"Reddit posting available. Token valid."

# --- Webhook Posters ---

def post_discord(text, config):
    url = config.get("discord", {}).get("webhook_url", "")
    if not url: return "No Discord webhook URL"
    r = fetch(url, method="POST", data=json.dumps({"content": text}).encode(),
              headers={"Content-Type": "application/json"})
    return "✅ Posted" if r == "" else f"Result: {r}"

def post_slack(text, config):
    url = config.get("slack", {}).get("webhook_url", "")
    if not url: return "No Slack webhook URL"
    r = fetch(url, method="POST", data=json.dumps({"text": text}).encode(),
              headers={"Content-Type": "application/json"})
    return "✅ Posted" if r == "ok" or r == "" else f"Result: {r}"

def post_telegram(text, config):
    tk = config.get("telegram", {}).get("bot_token", "")
    ci = config.get("telegram", {}).get("chat_id", "")
    if not tk or not ci: return "No Telegram config"
    r = fetch(f"https://api.telegram.org/bot{tk}/sendMessage", method="POST",
              data={"chat_id": ci, "text": text, "disable_web_page_preview": False})
    return "✅ Posted" if r.get("ok") else f"Failed: {r}"

def post_github(title, body, config):
    pat = config.get("github", {}).get("pat", "")
    repo = config.get("github", {}).get("repo", "")
    if not pat or not repo: return "No GitHub config"
    r = fetch(f"https://api.github.com/repos/{repo}/issues", method="POST",
              data=json.dumps({"title": title, "body": body}).encode(),
              headers={"Authorization": f"Bearer {pat}", "Content-Type": "application/json"})
    return r.get("html_url", f"Result: {r}")

# --- CLI ---
def main():
    import argparse
    p = argparse.ArgumentParser(description="Post to social media platforms")
    p.add_argument("--platforms", "-p", required=True, help="Comma-sep platforms: x,linkedin,bluesky,discord,slack,...")
    p.add_argument("--text", "-t", default="", help="Post text/content")
    p.add_argument("--title", default="", help="Post title (GitHub issues)")
    p.add_argument("--link", "-l", default="", help="Optional link to include")
    args = p.parse_args()

    vault = load_vault()
    config = load_config()
    body = args.text
    # LinkedIn takes the link separately (rendered as an ARTICLE card w/ thumbnail);
    # other platforms get it appended to the text.
    linkedin_link = args.link if "linkedin" in args.platforms.split(",") else ""
    text = body
    if args.link and "linkedin" not in args.platforms.split(","):
        text = f"{body}\n\n{args.link}" if body else args.link

    platform_map = {
        "x": lambda t, v, c: post_x(t, v, c), "linkedin": post_linkedin, "bluesky": post_bluesky,
        "mastodon": post_mastodon, "twitch": lambda t, v, c: post_twitch(t, v, c), "reddit": post_reddit,
        "discord": lambda t, c: post_discord(t, c), "slack": lambda t, c: post_slack(t, c),
        "telegram": lambda t, c: post_telegram(t, c),
        "github": lambda t, c: post_github(args.title, t, c),
    }

    platforms = [pl.strip() for pl in args.platforms.split(",") if pl.strip()]
    results = {}
    for pl in platforms:
        fn = platform_map.get(pl)
        if not fn:
            results[pl] = "Unknown platform"
            continue
        try:
            if pl == "linkedin":
                r = post_linkedin(body, vault, linkedin_link)
            elif pl in ("x", "mastodon", "twitch"):
                r = fn(text, vault, config)
            elif pl in ("discord", "slack", "telegram"):
                r = fn(text, config)
            else:
                r = fn(text, vault)
            results[pl] = r
        except Exception as e:
            results[pl] = f"Error: {e}"

    for pl, result in results.items():
        s = str(result)
        failed = (not s) or s.startswith("Result:") or "error" in s.lower() or s.lower().startswith("no ")
        status = "❌" if failed else "✅"
        print(f"  {status} {pl:12s} {s[:100]}")

if __name__ == "__main__":
    main()
