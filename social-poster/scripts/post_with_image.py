#!/usr/bin/env python3
"""Post text + a single image to X, LinkedIn, Bluesky, Mastodon and Discord.

post.py in the social-poster skill has no media support, so this adds the image
upload paths for each platform and reuses the same vault.json / config.json.

Usage:
  python3 post_with_image.py --platforms x,linkedin,bluesky,mastodon,discord \
      --text-file DIR/<platform>.md --image DIR/card.jpg [--dry-run]
  # per-platform text: DIR/<platform>.md is read automatically when --text-file
  # is given as a directory... (instead use --dir DIR)
"""
import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import pwd
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HOME = os.path.expanduser("~")
if "hermes/profiles" in HOME:
    HOME = pwd.getpwuid(os.getuid()).pw_dir
VAULT_PATH = os.path.join(HOME, ".social-poster", "vault.json")
CONFIG_PATH = os.path.join(HOME, ".social-poster", "config.json")
LI_VERSION = "202601"
CO_URN = "urn:li:organization:106478606"          # Coffee and Bytes
CO_NAME = "Coffee and Bytes"
CO_TITLE = "CyberMonday EP008: Humanity's Zero-Day"
CO_DESC = "CyberMonday EP008 promo card"
UA = "SocialPoster/1.0 (+ciberjohn)"


def load(path):
    return json.load(open(path)) if os.path.exists(path) else {}


def req(url, method="GET", data=None, headers=None, raw=False, timeout=120):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = resp.read()
            if raw:
                return resp.status, body
            try:
                return json.loads(body.decode())
            except Exception:
                return body.decode(errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:600]
        return {"__error__": f"HTTP {e.code}", "body": detail}
    except Exception as e:  # noqa: BLE001
        return {"__error__": str(e)}


# ---------------------------------------------------------------- multipart
def multipart(fields, files):
    """fields: dict[str,str]; files: list[(name, filename, bytes, content_type)]."""
    b = uuid.uuid4().hex
    out = b""
    for k, v in fields.items():
        out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
    for name, fn, blob, ct in files:
        out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{name}\"; "
                f"filename=\"{fn}\"\r\nContent-Type: {ct}\r\n\r\n").encode()
        out += blob + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return out, f"multipart/form-data; boundary={b}"


# ---------------------------------------------------------------- X
def _enc(s):
    return urllib.parse.quote(str(s), safe="-._~")


def _oauth_header(method, url, cfg, vault, body=None):
    ck, cs = cfg["api_key"], cfg["api_secret"]
    tok = vault["access_token"]
    sec = vault["access_secret"]
    oauth = {
        "oauth_consumer_key": ck,
        "oauth_nonce": base64.b64encode(os.urandom(16)).decode()[:32],
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": tok,
        "oauth_version": "1.0",
    }
    if body is not None:
        oauth["oauth_body_hash"] = base64.b64encode(hashlib.sha1(body).digest()).decode()
    pairs = [( _enc(k), _enc(v)) for k, v in sorted(oauth.items())]
    ps = "&".join(f"{k}={v}" for k, v in pairs)
    base = "&".join([_enc(method.upper()), _enc(url), _enc(ps)])
    key = f"{_enc(cs)}&{_enc(sec)}"
    oauth["oauth_signature"] = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(
        f'{_enc(k)}="{_enc(v)}"' for k, v in sorted(oauth.items()))


def x_upload_image(blob, cfg, vault):
    """v1.1 chunked-free upload; falls back to the v2 JSON endpoint."""
    url = "https://upload.twitter.com/1.1/media/upload.json"
    mp, ct = multipart({}, [("media", "card.jpg", blob, "image/jpeg")])
    auth = _oauth_header("POST", url, cfg, vault)
    r = req(url, method="POST", data=mp, headers={"Authorization": auth, "Content-Type": ct})
    if isinstance(r, dict) and r.get("media_id_string"):
        return r["media_id_string"], "v1.1"
    v1_err = r
    url2 = "https://api.x.com/2/media/upload"
    payload = json.dumps({"media": base64.b64encode(blob).decode(),
                          "media_type": "image/jpeg",
                          "media_category": "tweet_image"}).encode()
    auth2 = _oauth_header("POST", url2, cfg, vault, body=payload)
    r2 = req(url2, method="POST", data=payload,
             headers={"Authorization": auth2, "Content-Type": "application/json"})
    if isinstance(r2, dict) and (r2.get("data", {}) or {}).get("id"):
        return r2["data"]["id"], "v2"
    return None, f"v1.1={v1_err} v2={r2}"


def post_x(text, image, vault, cfg):
    c = cfg.get("x", {})
    v = vault.get("x", {})
    if not c or not v:
        return "no X credentials"
    mid, how = x_upload_image(image, c, v)
    if not mid:
        return f"media upload failed: {how}"
    url = "https://api.twitter.com/2/tweets"
    body = json.dumps({"text": text, "media": {"media_ids": [str(mid)]}}).encode()
    auth = _oauth_header("POST", url, c, v, body=body)
    r = req(url, method="POST", data=body,
            headers={"Authorization": auth, "Content-Type": "application/json"})
    if isinstance(r, dict) and r.get("data", {}).get("id"):
        return f"POSTED https://x.com/ciberjohn/status/{r['data']['id']} (media {how})"
    return f"tweet failed: {r}"


# ---------------------------------------------------------------- LinkedIn
def post_linkedin(text, image, vault, media_title=CO_TITLE, media_description=CO_DESC,
                  company_mention="required"):
    """Image post via the legacy assets + ugcPosts flow.

    /rest/posts returns HTTP 500 for every active LinkedIn-Version on this app,
    and a /rest/images URN inside a ugcPost fails 'not owned by the author', so
    register the asset through /v2/assets and post with shareMediaCategory IMAGE.
    """
    tok = vault.get("linkedin", {}).get("access_token", "")
    if not tok:
        return "no LinkedIn token"
    hdr = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
           "X-Restli-Protocol-Version": "2.0.0"}
    prof = req("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {tok}"})
    sub = prof.get("sub", "")
    if not sub:
        return f"no profile: {prof}"
    owner = f"urn:li:person:{sub}"

    reg = req("https://api.linkedin.com/v2/assets?action=registerUpload", method="POST",
              data=json.dumps({"registerUploadRequest": {
                  "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                  "owner": owner,
                  "serviceRelationships": [{"relationshipType": "OWNER",
                                            "identifier": "urn:li:userGeneratedContent"}]}}).encode(),
              headers=hdr)
    val = (reg or {}).get("value", {}) if isinstance(reg, dict) else {}
    up_url = (val.get("uploadMechanism", {})
              .get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
              .get("uploadUrl"))
    asset = val.get("asset")
    if not up_url or not asset:
        return f"asset register failed: {reg}"
    st, _ = req(up_url, method="PUT", data=image,
                headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/jpeg"},
                raw=True)
    if st not in (200, 201):
        return f"image PUT failed: HTTP {st}"

    commentary = {"text": text}
    idx = text.find(CO_NAME)
    if idx < 0 and company_mention == "required":
        return f"text must contain '{CO_NAME}' for the company mention"
    if idx >= 0 and text.count(CO_NAME) == 1:
        commentary["attributes"] = [{
            "start": idx, "length": len(CO_NAME),
            "value": {"com.linkedin.common.CompanyAttributedEntity": {"company": CO_URN}}}]
    body = {
        "author": owner,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {
            "shareCommentary": commentary,
            "shareMediaCategory": "IMAGE",
            "media": [{"status": "READY",
                       "description": {"text": media_description},
                       "media": asset,
                       "title": {"text": media_title}}]}},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    r = req("https://api.linkedin.com/v2/ugcPosts", method="POST",
            data=json.dumps(body).encode(), headers=hdr)
    rid = r.get("id") if isinstance(r, dict) else None
    if rid:
        return f"POSTED https://www.linkedin.com/feed/update/{rid}"
    return f"post failed: {r}"


# ---------------------------------------------------------------- Bluesky
def post_bluesky(text, image, vault):
    v = vault.get("bluesky", {})
    h, p = v.get("handle", ""), v.get("app_password", "")
    if not h or not p:
        return "no Bluesky credentials"
    pds = "https://bsky.social"
    sess = req(f"{pds}/xrpc/com.atproto.server.createSession", method="POST",
               data=json.dumps({"identifier": h, "password": p}).encode(),
               headers={"Content-Type": "application/json"})
    token, did = sess.get("accessJwt", ""), sess.get("did", "")
    if not token:
        return f"auth failed: {sess}"
    blob = req(f"{pds}/xrpc/com.atproto.repo.uploadBlob", method="POST", data=image,
               headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"})
    if not isinstance(blob, dict) or not blob.get("blob"):
        return f"blob upload failed: {blob}"
    rec = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "embed": {"$type": "app.bsky.embed.images",
                  "images": [{"alt": "CyberMonday EP008 promo card: >10% chance AI kills all "
                                     "of us this decade, with ciberjohn",
                              "image": blob["blob"]}]},
    }
    r = req(f"{pds}/xrpc/com.atproto.repo.createRecord", method="POST",
            data=json.dumps({"repo": did, "collection": "app.bsky.feed.post",
                             "record": rec}).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    uri = r.get("uri") if isinstance(r, dict) else None
    return f"POSTED {uri}" if uri else f"post failed: {r}"


# ---------------------------------------------------------------- Mastodon
def post_mastodon(text, image, vault, cfg, description=""):
    v = vault.get("mastodon", {})
    tok = v.get("access_token", "")
    inst = v.get("instance") or cfg.get("mastodon", {}).get("instance", "")
    if not tok:
        return "no Mastodon token"
    mp, ct = multipart({"description": description or "Illustration"},
                       [("file", "card.jpg", image, "image/jpeg")])
    m = req(f"https://{inst}/api/v2/media", method="POST", data=mp,
            headers={"Authorization": f"Bearer {tok}", "Content-Type": ct})
    mid = m.get("id") if isinstance(m, dict) else None
    if not mid:
        return f"media upload failed: {m}"
    for _ in range(10):
        if isinstance(m, dict) and m.get("url"):
            break
        time.sleep(2)
        m = req(f"https://{inst}/api/v1/media/{mid}", headers={"Authorization": f"Bearer {tok}"})
    st = req(f"https://{inst}/api/v1/statuses", method="POST",
             data=urllib.parse.urlencode({"status": text, "media_ids[]": mid}).encode(),
             headers={"Authorization": f"Bearer {tok}",
                      "Content-Type": "application/x-www-form-urlencoded"})
    uri = st.get("url") if isinstance(st, dict) else None
    return f"POSTED {uri}" if uri else f"post failed: {st}"


# ---------------------------------------------------------------- Discord
def post_discord(text, image, cfg):
    url = cfg.get("discord", {}).get("webhook_url", "")
    if not url:
        return "no Discord webhook"
    mp, ct = multipart({"payload_json": json.dumps({"content": text})},
                       [("files[0]", "ep008-promo.jpg", image, "image/jpeg")])
    r = req(url, method="POST", data=mp, headers={"Content-Type": ct})
    if isinstance(r, dict) and r.get("__error__"):
        return f"post failed: {r}"
    return "POSTED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platforms", "-p", required=True)
    ap.add_argument("--dir", required=True, help="dir holding <platform>.md files")
    ap.add_argument("--image", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--media-title", default=CO_TITLE)
    ap.add_argument("--media-description", default="",
                    help="alt text for the image; used by LinkedIn and Mastodon")
    ap.add_argument("--company-mention", default="required", choices=["required", "auto"])
    args = ap.parse_args()

    vault = load(VAULT_PATH)
    cfg = load(CONFIG_PATH)
    image = open(args.image, "rb").read()
    print(f"image: {args.image} ({len(image)} bytes)")

    for pl in [x.strip() for x in args.platforms.split(",") if x.strip()]:
        tf = os.path.join(args.dir, f"{pl}.md")
        if not os.path.exists(tf):
            print(f"  ❌ {pl:10s} no text file {tf}")
            continue
        text = "\n".join(l for l in open(tf, encoding="utf-8").read().splitlines()
                         if not l.startswith("# CHARACTER COUNT")).strip()
        if args.dry_run:
            print(f"  .. {pl:10s} {len(text)} chars (dry run)")
            continue
        try:
            if pl == "x":
                out = post_x(text, image, vault, cfg)
            elif pl == "linkedin":
                out = post_linkedin(text, image, vault,
                                    media_title=args.media_title,
                                    media_description=args.media_description,
                                    company_mention=args.company_mention)
            elif pl == "bluesky":
                out = post_bluesky(text, image, vault)
            elif pl == "mastodon":
                out = post_mastodon(text, image, vault, cfg,
                                    description=args.media_description)
            elif pl == "discord":
                out = post_discord(text, image, cfg)
            else:
                out = f"unsupported platform {pl}"
        except Exception as e:  # noqa: BLE001
            out = f"EXCEPTION {type(e).__name__}: {e}"
        mark = "✅" if str(out).startswith("POSTED") else "❌"
        print(f"  {mark} {pl:10s} {out}")


if __name__ == "__main__":
    main()
