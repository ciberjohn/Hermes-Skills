# OAuth Flow Details

## Pattern: OAuth 2.0 Code-Paste Flow

The core innovation that avoids redirect URI whitelisting:

1. **Auth URL generated** by `social-poster.py auth:<platform>` — contains the platform's whitelisted redirect URI
2. **User authenticates** — Opens URL in browser, authorizes
3. **Code captured** — Browser redirects to the redirect URI with `?code=XXXX`
4. **Redirect fails (intentionally)** — The redirect URI goes to a Tailscale-hosted callback server (`/oauth-callback`) or localhost (for YouTube). The code is visible in the address bar
5. **Exchange** — Agent extracts code and calls `store:<platform>` to exchange for access token

## Per-Platform Redirect URIs

| Platform | Redirect URI Used | Notes |
|----------|------------------|-------|
| **LinkedIn** | `https://{{TAILSCALE_HOST}}/integrations/social/linkedin` | Must match whitelisted URI in LinkedIn developer portal |
| **Instagram** | `https://{{TAILSCALE_HOST}}/integrations/social/instagram-standalone` | Must match whitelisted URI in Facebook app |
| **Facebook** | `https://{{TAILSCALE_HOST}}/oauth-callback` | Generic callback path |
| **Threads** | `https://{{TAILSCALE_HOST}}/oauth-callback` | Generic callback path |
| **YouTube** | `http://localhost` | Works because user is on their own machine |
| **X/Twitter** | N/A (PIN-based OAuth 1.0a) | No redirect URI needed |

## Pattern: OAuth 2.0 Tailscale Serve Flow (Cross-Machine)

When the agent is on a remote VPS and the user is on a different machine:

### Setup (one-time — all paths needed)
```bash
python3 ~/.social-poster/oauth-callback-server.py 19876 &

# Each platform that uses a specific whitelisted path needs its own route
tailscale serve --bg --set-path /oauth-callback 19876
tailscale serve --bg --set-path /integrations/social/linkedin 19876
tailscale serve --bg --set-path /integrations/social/instagram-standalone 19876
```

### Critical Rules
- **Redirect URI MUST match exactly** between auth URL and token exchange POST
- **`state` parameter is REQUIRED for all OAuth 2.0 flows** — prevents CSRF attacks. Generated as 32 bytes of crypto-random base64, stored in `~/.social-poster/.{platform}_state.json`, cleaned up on successful exchange
- **Tailscale Serve must be running BEFORE** the user clicks the OAuth URL
- **Existing whitelisted URIs (from old Postiz setups) can be repurposed** as Tailscale Serve proxy paths
- **The callback server stays alive** — kill when done: `kill %1`

## Platform Token Endpoints

| Platform | Token Endpoint | Grant Type |
|----------|---------------|------------|
| X/Twitter | `api.twitter.com/oauth/access_token` | OAuth 1.0a (PIN) |
| LinkedIn | `linkedin.com/oauth/v2/accessToken` | authorization_code |
| Instagram | `api.instagram.com/oauth/access_token` | authorization_code |
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

Uses `requests_oauthlib.OAuth1Session` (standalone scripts) or manual OAuth signing (unified CLI):
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
  "bluesky": {"handle": "user.bsky.social", "app_password": "xxxx-xxxx-xxxx-xxxx"}
}
```
Note: `screen_name` is stored WITHOUT `@` prefix (as returned by the X API).
