#!/usr/bin/env python3
"""X/Twitter OAuth 1.0a — Step 2: Exchange PIN for access token."""
import sys, os, json
from requests_oauthlib import OAuth1Session

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, "config.json")
VAULT_PATH = os.path.join(DIR, "vault.json")
SESSION_PATH = os.path.join(DIR, ".x_session.json")

if len(sys.argv) < 2 or not sys.argv[1].isdigit():
    print("Usage: python3 auth-x-step2.py <PIN>"); sys.exit(1)

with open(CONFIG_PATH) as f: config = json.load(f)
with open(SESSION_PATH) as f: session = json.load(f)

ck, cs = config["x"]["api_key"], config["x"]["api_secret"]
oauth = OAuth1Session(ck, client_secret=cs,
    resource_owner_key=session["oauth_token"],
    resource_owner_secret=session["oauth_token_secret"],
    verifier=sys.argv[1])
access = oauth.fetch_access_token('https://api.twitter.com/oauth/access_token')

print(f"\n✅ X connected! @{access['screen_name']}")

vault = json.load(open(VAULT_PATH)) if os.path.exists(VAULT_PATH) else {}
vault["x"] = {"access_token": access["oauth_token"], "access_secret": access["oauth_token_secret"],
              "user_id": access["user_id"], "screen_name": access["screen_name"]}
json.dump(vault, open(VAULT_PATH, "w"), indent=2)
os.chmod(VAULT_PATH, 0o600)
os.remove(SESSION_PATH)
print("Token saved.")
