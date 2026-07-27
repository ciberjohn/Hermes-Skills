# OAuth Flow Details

## Pattern: OAuth 2.0 Code-Paste Flow

The core innovation that avoids redirect URI whitelisting:

1. **Auth URL generated** by `social-poster.py auth:<platform>` — contains the platform's registered redirect URI
2. **User authenticates** — Opens URL in browser, authorizes
3. **Code captured** — Browser redirects to the redirect URI with `?code=XXXX` 
4. **Redirect hits your reverse proxy** — The redirect URI points to a URL served by your reverse proxy (Tailscale Serve, NPM, Cloudflare Tunnel, etc.), which forwards to the local callback server
5. **Exchange** — Agent reads the code from `last_code.txt` and calls `store:<platform>` to exchange for access token

## Per-Platform Redirect URIs

| Platform | Redirect URI Used | Notes |
|----------|------------------|-------|
| **LinkedIn** | `https://{{CALLBACK_HOST}}/integrations/social/linkedin` | Must match whitelisted URI in LinkedIn developer portal |
| **Instagram** | `https://{{CALLBACK_HOST}}/integrations/social/instagram-standalone` | Must match whitelisted URI in Facebook app |
| **Facebook** | `https://{{CALLBACK_HOST}}/oauth-callback` | Generic callback path |
| **Threads** | `https://{{CALLBACK_HOST}}/oauth-callback` | Generic callback path |
| **Mastodon** | `https://{{CALLBACK_HOST}}/oauth-callback` | Register this URI in your Mastodon app |
| **Twitch** | `https://{{CALLBACK_HOST}}/oauth-callback` | Register this URI in your Twitch dev app |
| **Reddit** | `https://{{CALLBACK_HOST}}/oauth-callback` | Register this URI in your Reddit app |
| **YouTube** | `http://localhost` | Works because user is on their own machine |
| **X/Twitter** | N/A (PIN-based OAuth 1.0a) | No redirect URI needed |

## Cross-Machine OAuth (Reverse Proxy)

When the agent is on a remote machine and the user is on a different machine,
OAuth redirect URLs need to point somewhere the user's browser can reach.

**You need a reverse proxy** that makes `127.0.0.1:19876` accessible via HTTPS
at a URL your browser can reach. The URL does NOT need to be public on the
internet — just reachable by YOUR browser.

Options: Tailscale Serve, Cloudflare Tunnel, Nginx Proxy Manager, ngrok,
or your VPS hostname with HTTPS.

### Minimum Setup

```bash
# Start the callback server
python3 ~/.social-poster/oauth-callback-server.py 19876 &

# Configure your reverse proxy to route these paths to 127.0.0.1:19876:
# - /oauth-callback
# - /integrations/social/linkedin       (if using LinkedIn)
# - /integrations/social/instagram-standalone  (if using Instagram)
```

Then set `CALLBACK_HOST` env var or config to your proxy's base URL.

### Critical Rules

- **Redirect URI MUST match exactly** between auth URL and token exchange POST
- **`state` parameter is REQUIRED for all OAuth 2.0 flows** — prevents CSRF attacks
- **Reverse proxy must be running BEFORE** the user clicks the OAuth URL
- **Existing whitelisted URIs (from old Postiz setups) can be reused** via your reverse proxy

## Platform Token Endpoints

| Platform | Token Endpoint | Grant Type |
|----------|---------------|------------|
| X/Twitter | `api.twitter.com/oauth/access_token` | OAuth 1.0a (PIN) |
| LinkedIn | `linkedin.com/oauth/v2/accessToken` | authorization_code |
| Instagram | `api.instagram.com/oauth/access_token` | authorization_code |
| Mastodon | `{instance}/oauth/token` | authorization_code |
| Twitch | `id.twitch.tv/oauth2/token` | authorization_code |
| Reddit | `www.reddit.com/api/v1/access_token` | authorization_code (Basic auth) |
| Threads | `graph.threads.net/oauth/access_token` | authorization_code |
| YouTube | `oauth2.googleapis.com/token` | authorization_code |
| Facebook | `graph.facebook.com/v21.0/oauth/access_token` | authorization_code |

## Instagram Long-Lived Token Exchange

Instagram tokens expire in ~1 hour. Immediately exchange via POST:
```
POST graph.instagram.com/access_token
grant_type=ig_exchange_token
client_id={{INSTAGRAM_APP_ID}}
client_secret={{INSTAGRAM_APP_SECRET}}
access_token={{SHORT_LIVED_TOKEN}}
```
Returns 58-day token. Uses POST to avoid leaking credentials in server logs.

## X/Twitter OAuth 1.0a Flow

Uses `requests_oauthlib.OAuth1Session` or manual OAuth signing:
1. `fetch_request_token()` with `callback_uri='oob'`
2. `authorization_url()` generates the URL
3. User gets PIN from web page
4. `fetch_access_token()` with PIN → access_token + access_secret

Dependencies: `pip3 install requests_oauthlib`

## Token Storage Format

```json
{
  "x": {"access_token": "...", "access_secret": "...", "screen_name": "user"},
  "linkedin": {"access_token": "...", "refresh_token": "...", "expires_in": 5184000},
  "instagram": {"access_token": "...", "expires_in": 5184000, "user_id": "..."},
  "mastodon": {"access_token": "...", "instance": "mastodon.social"},
  "twitch": {"access_token": "...", "refresh_token": "..."},
  "reddit": {"access_token": "...", "refresh_token": "..."},
  "bluesky": {"handle": "user.bsky.social", "app_password": "xxxx-xxxx-xxxx-xxxx"}
}
```
Note: `screen_name` is stored WITHOUT `@` prefix (as returned by the X API).
