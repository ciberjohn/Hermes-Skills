#!/usr/bin/env python3
"""X/Twitter OAuth 1.0a — Step 1: Get request token + auth URL."""
import sys, os, json
from requests_oauthlib import OAuth1Session

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, "config.json")

with open(CONFIG_PATH) as f:
    config = json.load(f)

ck, cs = config["x"]["api_key"], config["x"]["api_secret"]
oauth = OAuth1Session(ck, client_secret=cs, callback_uri='oob')
fetch = oauth.fetch_request_token('https://api.twitter.com/oauth/request_token')
url = oauth.authorization_url('https://api.twitter.com/oauth/authorize')

print(f"\n🔗 {url}\n")
print("📝 Visit the URL, authorize, and paste the PIN code.")
print("   Then run: python3 auth-x-step2.py <PIN>")

json.dump({"oauth_token": fetch["oauth_token"], "oauth_token_secret": fetch["oauth_token_secret"]},
          open(os.path.join(DIR, ".x_session.json"), "w"))
