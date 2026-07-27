#!/usr/bin/env python3
"""
Social Poster — Token Vault & OAuth URL Generator
Hermes-native social media posting system.

Usage:
  python3 social-poster.py vault:status          # Show which platforms have tokens
  python3 social-poster.py auth:[platform]       # Generate OAuth URL
  python3 social-poster.py store:[platform] ...  # Exchange code for token
"""
import sys, os, json, base64, urllib.request, urllib.parse

# --- Config Paths ---
_user_dir = os.path.expanduser("~")
if "hermes/profiles" in _user_dir:
    import pwd
    _user_dir = pwd.getpwuid(os.getuid()).pw_dir

CONFIG_DIR = os.path.join(_user_dir, ".social-poster")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
VAULT_PATH = os.path.join(CONFIG_DIR, "vault.json")
CALLBACK_HOST = os.environ.get("CALLBACK_HOST", "{{CALLBACK_HOST}}")

def _make_state():
    """Generate cryptographically random state for CSRF protection."""
    return base64.b64encode(os.urandom(24)).decode().strip("=")

def _write_state_file(path, data):
    """Write OAuth state/session data with restricted permissions."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
    os.chmod(path, 0o600)

# --- Config Loader ---
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    env_map = {
        "X_API_KEY":"x.api_key","X_API_SECRET":"x.api_secret",
        "LINKEDIN_CLIENT_ID":"linkedin.client_id","LINKEDIN_CLIENT_SECRET":"linkedin.client_secret",
        "INSTAGRAM_APP_ID":"instagram.app_id","INSTAGRAM_APP_SECRET":"instagram.app_secret",
        "THREADS_APP_ID":"threads.app_id","THREADS_APP_SECRET":"threads.app_secret",
        "FACEBOOK_APP_ID":"facebook.app_id","FACEBOOK_APP_SECRET":"facebook.app_secret",
        "YOUTUBE_CLIENT_ID":"youtube.client_id","YOUTUBE_CLIENT_SECRET":"youtube.client_secret",
        "BLUESKY_HANDLE":"bluesky.handle","BLUESKY_APP_PASSWORD":"bluesky.app_password",
    }
    cfg = {}
    for ek, ck in env_map.items():
        v = os.environ.get(ek)
        if v:
            p1, p2 = ck.split(".")
            cfg.setdefault(p1, {})[p2] = v
    return cfg

def load_vault():
    return json.load(open(VAULT_PATH)) if os.path.exists(VAULT_PATH) else {}

def save_vault(vault):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(VAULT_PATH, "w") as f:
        json.dump(vault, f, indent=2)
    os.chmod(VAULT_PATH, 0o600)

def fetch(url, method="GET", data=None, headers=None):
    h = {"User-Agent": "SocialPoster/1.0"}
    if headers: h.update(headers)
    if isinstance(data, dict): data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return json.loads(body) if ("json" in r.headers.get("Content-Type","") or body.startswith("{")) else body
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode(errors="replace")[:500]}
    except Exception as e:
        return {"error": str(e)}

# --- OAuth URL Generators ---
def auth_x(config):
    ck, cs = config.get("x",{}).get("api_key",""), config.get("x",{}).get("api_secret","")
    if not ck or not cs: return {"error": "X_API_KEY and X_API_SECRET not configured"}
    oauth = {
        "oauth_consumer_key": ck, "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(__import__("time").time())),
        "oauth_nonce": base64.b64encode(__import__("os").urandom(16)).decode()[:32],
        "oauth_version": "1.0", "oauth_callback": "oob"
    }
    sig = _oauth_sign("POST", "https://api.twitter.com/oauth/request_token", oauth, cs, "")
    oauth["oauth_signature"] = sig
    auth_h = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(v)}"' for k,v in sorted(oauth.items()))
    result = fetch("https://api.twitter.com/oauth/request_token", headers={"Authorization": auth_h})
    if isinstance(result, str):
        p = urllib.parse.parse_qs(result)
        tok = p.get("oauth_token", [""])[0]
        sec = p.get("oauth_token_secret", [""])[0]
        if tok:
            return {"url": f"https://api.twitter.com/oauth/authorize?oauth_token={tok}",
                    "oauth_token": tok, "oauth_token_secret": sec,
                    "instruction": "Visit the URL, authorize, and paste the PIN code here."}
    return {"error": f"Failed: {result}"}

def auth_linkedin(config):
    cid = config.get("linkedin",{}).get("client_id","")
    if not cid: return {"error": "LINKEDIN_CLIENT_ID not configured"}
    state = _make_state()
    redirect = f"https://{CALLBACK_HOST}/integrations/social/linkedin"
    scopes = "openid profile w_member_social"
    url = (f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={cid}"
           f"&redirect_uri={urllib.parse.quote(redirect)}&state={state}&scope={urllib.parse.quote(scopes)}")
    # Store state for CSRF validation
    _write_state_file(os.path.join(CONFIG_DIR, ".linkedin_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize, paste the FULL redirect URL with ?code=... here."}

def auth_instagram(config):
    aid = config.get("instagram",{}).get("app_id","")
    if not aid: return {"error": "INSTAGRAM_APP_ID not configured"}
    state = _make_state()
    redirect = f"https://{CALLBACK_HOST}/integrations/social/instagram-standalone"
    scopes = "instagram_business_basic,instagram_business_content_publish"
    url = (f"https://www.instagram.com/oauth/authorize?enable_fb_login=0&client_id={aid}"
           f"&redirect_uri={urllib.parse.quote(redirect)}&state={state}&response_type=code&scope={urllib.parse.quote(scopes)}")
    _write_state_file(os.path.join(CONFIG_DIR, ".instagram_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize, paste the FULL redirect URL here."}

def auth_facebook(config):
    aid = config.get("facebook",{}).get("app_id","")
    if not aid: return {"error": "FACEBOOK_APP_ID not configured"}
    state = _make_state()
    redirect = f"https://{CALLBACK_HOST}/oauth-callback"
    scopes = "pages_read_engagement,pages_manage_posts,pages_show_list"
    url = (f"https://www.facebook.com/v21.0/dialog/oauth?client_id={aid}"
           f"&redirect_uri={urllib.parse.quote(redirect)}&state={state}&scope={urllib.parse.quote(scopes)}&response_type=code")
    _write_state_file(os.path.join(CONFIG_DIR, ".facebook_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize, paste the FULL redirect URL here."}

def auth_youtube(config):
    cid = config.get("youtube",{}).get("client_id","")
    if not cid: return {"error": "YOUTUBE_CLIENT_ID not configured"}
    state = _make_state()
    redirect = "http://localhost"
    scopes = "https://www.googleapis.com/auth/youtube.upload"
    url = (f"https://accounts.google.com/o/oauth2/v2/auth?client_id={cid}"
           f"&redirect_uri={urllib.parse.quote(redirect)}&state={state}&response_type=code&scope={urllib.parse.quote(scopes)}"
           f"&access_type=offline&prompt=consent")
    _write_state_file(os.path.join(CONFIG_DIR, ".youtube_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize. Browser will redirect to localhost - copy that URL."}

def auth_threads(config):
    aid = config.get("threads",{}).get("app_id","")
    if not aid: return {"error": "THREADS_APP_ID not configured"}
    state = _make_state()
    redirect = f"https://{CALLBACK_HOST}/oauth-callback"
    scopes = "threads_basic,threads_content_publish"
    url = (f"https://www.threads.net/oauth/authorize?client_id={aid}"
           f"&redirect_uri={urllib.parse.quote(redirect)}&state={state}&scope={urllib.parse.quote(scopes)}&response_type=code")
    _write_state_file(os.path.join(CONFIG_DIR, ".threads_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize, paste the FULL redirect URL here."}

def auth_mastodon(config):
    inst = config.get("mastodon",{}).get("instance","")
    cid = config.get("mastodon",{}).get("client_id","")
    cs = config.get("mastodon",{}).get("client_secret","")
    if not inst or not cid: return {"error": "MASTODON_INSTANCE, CLIENT_ID, CLIENT_SECRET required"}
    state = _make_state()
    redirect = f"https://{CALLBACK_HOST}/oauth-callback"
    scopes = "read write"
    url = (f"https://{inst}/oauth/authorize?response_type=code&client_id={cid}"
           f"&redirect_uri={urllib.parse.quote(redirect)}&state={state}&scope={urllib.parse.quote(scopes)}")
    _write_state_file(os.path.join(CONFIG_DIR, ".mastodon_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize, paste the FULL redirect URL here."}

def auth_twitch(config):
    cid = config.get("twitch",{}).get("client_id","")
    if not cid: return {"error": "TWITCH_CLIENT_ID not configured"}
    state = _make_state()
    redirect = f"https://{CALLBACK_HOST}/oauth-callback"
    scopes = "user:read:email channel:read:stream_key"
    url = (f"https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={cid}"
           f"&redirect_uri={urllib.parse.quote(redirect)}&state={state}&scope={urllib.parse.quote(scopes)}")
    _write_state_file(os.path.join(CONFIG_DIR, ".twitch_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize, paste the FULL redirect URL here."}

def auth_reddit(config):
    cid = config.get("reddit",{}).get("client_id","")
    if not cid: return {"error": "REDDIT_CLIENT_ID not configured"}
    state = _make_state()
    redirect = f"https://{CALLBACK_HOST}/oauth-callback"
    scopes = "submit identity"
    url = (f"https://www.reddit.com/api/v1/authorize?client_id={cid}"
           f"&response_type=code&state={state}&redirect_uri={urllib.parse.quote(redirect)}"
           f"&duration=permanent&scope={urllib.parse.quote(scopes)}")
    _write_state_file(os.path.join(CONFIG_DIR, ".reddit_state.json"), {"state": state})
    return {"url": url, "redirect_uri": redirect,
            "instruction": "Visit URL, authorize, paste the FULL redirect URL here."}

def _oauth_sign(method, url, params, consumer_secret, token_secret):
    import hmac, hashlib
    ps = "&".join(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}" for k,v in sorted(params.items()))
    base = f"{method}&{urllib.parse.quote(url)}&{urllib.parse.quote(ps)}"
    key = f"{urllib.parse.quote(consumer_secret)}&{urllib.parse.quote(token_secret)}"
    return base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()

# --- Token Exchanges ---
def store_x_token(pin, oauth_token, oauth_token_secret, config):
    ck, cs = config["x"]["api_key"], config["x"]["api_secret"]
    oauth = {
        "oauth_consumer_key": ck, "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(__import__("time").time())),
        "oauth_nonce": base64.b64encode(__import__("os").urandom(16)).decode()[:32],
        "oauth_version": "1.0", "oauth_token": oauth_token, "oauth_verifier": pin
    }
    sig = _oauth_sign("POST", "https://api.twitter.com/oauth/access_token", oauth, cs, oauth_token_secret)
    oauth["oauth_signature"] = sig
    auth_h = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(v)}"' for k,v in sorted(oauth.items()))
    result = fetch("https://api.twitter.com/oauth/access_token", headers={"Authorization": auth_h})
    if isinstance(result, str) and "oauth_token" in result:
        p = urllib.parse.parse_qs(result)
        vault = load_vault()
        vault["x"] = {"access_token": p["oauth_token"][0], "access_secret": p["oauth_token_secret"][0],
                      "user_id": p["user_id"][0], "screen_name": p["screen_name"][0]}
        save_vault(vault)
        return {"success": True, "screen_name": vault["x"]["screen_name"]}
    return {"error": f"Failed: {result}"}

def store_linkedin_token(code, config):
    cid, cs = config["linkedin"]["client_id"], config["linkedin"]["client_secret"]
    redirect = f"https://{CALLBACK_HOST}/integrations/social/linkedin"
    data = {"grant_type":"authorization_code","code":code,"redirect_uri":redirect,"client_id":cid,"client_secret":cs}
    result = fetch("https://www.linkedin.com/oauth/v2/accessToken", method="POST", data=data)
    if result.get("access_token"):
        vault = load_vault()
        vault["linkedin"] = {"access_token": result["access_token"],
            "refresh_token": result.get("refresh_token",""),"expires_in": result.get("expires_in",0)}
        save_vault(vault)
        # Clean up state file
        sf = os.path.join(CONFIG_DIR, ".linkedin_state.json")
        if os.path.exists(sf): os.remove(sf)
        return {"success": True}
    return {"error": f"Failed: {result}"}

def store_instagram_token(code, config):
    aid, asc = config["instagram"]["app_id"], config["instagram"]["app_secret"]
    redirect = f"https://{CALLBACK_HOST}/integrations/social/instagram-standalone"
    data = {"client_id":aid,"client_secret":asc,"grant_type":"authorization_code","redirect_uri":redirect,"code":code}
    result = fetch("https://api.instagram.com/oauth/access_token", method="POST", data=data)
    if result.get("access_token"):
        # POST-based long-lived exchange (avoids leaking credentials in URL)
        ll_data = {"grant_type":"ig_exchange_token","client_id":aid,"client_secret":asc,"access_token":result["access_token"]}
        ll = fetch("https://graph.instagram.com/access_token", method="POST", data=ll_data)
        vault = load_vault()
        vault["instagram"] = {"access_token":ll.get("access_token",result["access_token"]),
                              "expires_in":ll.get("expires_in",0),"user_id":result.get("user_id","")}
        save_vault(vault)
        sf = os.path.join(CONFIG_DIR, ".instagram_state.json")
        if os.path.exists(sf): os.remove(sf)
        return {"success": True}
    return {"error": f"Failed: {result}"}

# --- CLI ---
def main():
    config = load_config()
    args = sys.argv[1:] if len(sys.argv) > 1 else ["help"]

    if args[0] == "vault:status":
        vault = load_vault()
        for p in ["x","linkedin","bluesky","instagram","threads","facebook","youtube",
                    "mastodon","twitch","reddit"]:
            t = vault.get(p,{})
            s = "✅" if (t.get("access_token") or t.get("app_password")) else ("⬜" if not t else "❌")
            print(f"  {p:15s} {s}")

    elif args[0].startswith("auth:"):
        plat = args[0].split(":")[1]
        fn = {"x":auth_x,"linkedin":auth_linkedin,"instagram":auth_instagram,
              "facebook":auth_facebook,"youtube":auth_youtube,"threads":auth_threads,
              "mastodon":auth_mastodon,"twitch":auth_twitch,"reddit":auth_reddit}.get(plat)
        if not fn: print(f"Unknown platform: {plat}"); return
        r = fn(config)
        if "url" in r:
            print(f"\n🔗 {r['url']}\n")
            print(f"📝 {r['instruction']}")
            if "oauth_token" in r:
                _write_state_file(os.path.join(CONFIG_DIR, ".x_session.json"), r)
        else:
            print(f"❌ {r.get('error','Unknown')}")

    elif args[0].startswith("store:"):
        plat = args[0].split(":")[1]
        if len(args) < 2: print(f"Usage: python3 social-poster.py store:{plat} <code>"); return
        code = args[1]
        if "code=" in code: code = urllib.parse.parse_qs(code.split("?")[1] if "?" in code else code).get("code",[code])[0]
        if plat == "x":
            sp = os.path.join(CONFIG_DIR, ".x_session.json")
            if not os.path.exists(sp): print("❌ No X session. Run auth:x first."); return
            s = json.load(open(sp))
            r = store_x_token(code, s["oauth_token"], s["oauth_token_secret"], config)
            if r.get("success"): print(f"✅ X connected as @{r['screen_name']}"); os.remove(sp)
            else: print(f"❌ {r.get('error','Failed')}")
        elif plat == "linkedin":
            r = store_linkedin_token(code, config)
            print("✅ LinkedIn connected!" if r.get("success") else f"❌ {r.get('error','Failed')}")
        elif plat == "instagram":
            r = store_instagram_token(code, config)
            print("✅ Instagram connected!" if r.get("success") else f"❌ {r.get('error','Failed')}")
        elif plat == "bluesky":
            h = config.get("bluesky",{}).get("handle","")
            p = config.get("bluesky",{}).get("app_password","")
            if h and p:
                vault = load_vault(); vault["bluesky"]={"handle":h,"app_password":p}; save_vault(vault)
                print(f"✅ Bluesky ({h}) saved!")
            else: print("❌ Set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD in config")
        elif plat == "mastodon":
            inst = config.get("mastodon",{}).get("instance","")
            cid = config.get("mastodon",{}).get("client_id","")
            cs = config.get("mastodon",{}).get("client_secret","")
            redirect = f"https://{CALLBACK_HOST}/oauth-callback"
            r = fetch(f"https://{inst}/oauth/token", method="POST",
                data={"grant_type":"authorization_code","code":code,"redirect_uri":redirect,
                      "client_id":cid,"client_secret":cs})
            if r.get("access_token"):
                vault = load_vault(); vault["mastodon"]={"access_token":r["access_token"],"instance":inst}; save_vault(vault)
                print(f"✅ Mastodon ({inst}) connected!")
            else: print(f"❌ {r.get('error','Failed')}")
        elif plat == "twitch":
            cid = config.get("twitch",{}).get("client_id","")
            cs = config.get("twitch",{}).get("client_secret","")
            redirect = f"https://{CALLBACK_HOST}/oauth-callback"
            r = fetch("https://id.twitch.tv/oauth2/token", method="POST",
                data={"grant_type":"authorization_code","code":code,"redirect_uri":redirect,
                      "client_id":cid,"client_secret":cs})
            if r.get("access_token"):
                vault = load_vault(); vault["twitch"]={"access_token":r["access_token"],
                    "refresh_token":r.get("refresh_token","")}; save_vault(vault)
                print("✅ Twitch connected!")
            else: print(f"❌ {r.get('error','Failed')}")
        elif plat == "reddit":
            cid = config.get("reddit",{}).get("client_id","")
            cs = config.get("reddit",{}).get("client_secret","")
            redirect = f"https://{CALLBACK_HOST}/oauth-callback"
            import base64
            auth = base64.b64encode(f"{cid}:{cs}".encode()).decode()
            r = fetch("https://www.reddit.com/api/v1/access_token", method="POST",
                data={"grant_type":"authorization_code","code":code,"redirect_uri":redirect},
                headers={"Authorization": f"Basic {auth}"})
            if r.get("access_token"):
                vault = load_vault(); vault["reddit"]={"access_token":r["access_token"],
                    "refresh_token":r.get("refresh_token","")}; save_vault(vault)
                print("✅ Reddit connected!")
            else: print(f"❌ {r.get('error','Failed')}")
        else:
            print(f"store:{plat} not implemented yet")

    elif args[0] in ("help","--help"):
        print(__doc__)
    else:
        print(f"Unknown: {args[0]}")

if __name__ == "__main__":
    main()
