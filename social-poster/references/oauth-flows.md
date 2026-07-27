# OAuth Flow Details

## Pattern: OAuth 2.0 Code-Paste Flow

The core innovation that avoids redirect URI whitelisting:

1. Set redirect URI to `http://localhost:9876/callback`
2. User opens the auth URL in their browser
3. After authorization, browser redirects to `localhost:9876/callback?code=XXXX`
4. Browser shows "connection refused" — this is expected
5. User copies the FULL URL from the address bar
6. Agent extracts `code` from `?code=XXXX` parameter
7. Exchanges code for access token via direct POST to token endpoint

This works because `localhost` is a valid redirect URI format on all platforms.

## Pattern: OAuth 2.0 Tailscale Serve Flow (Cross-Machine)

When the agent is on a remote VPS and the user is on a different machine:

### Setup (one-time)
```bash
python3 ~/.social-poster/oauth-callback-server.py 19876 &
tailscale serve --bg --set-path /oauth-callback 19876
```

### Per-Platform Flow
1. Generate auth URL with `redirect_uri = https://{{TAILSCALE_HOST}}/integrations/social/{platform}`
2. User visits URL from any machine on the tailnet
3. Platform redirects to Tailscale URL with `?code=...`
4. Callback server captures the code → saves to `/tmp/oauth_code.txt`
5. Exchange code via `social-poster.py store:<platform> "<code>"` — using the SAME redirect URI

### Critical Rules
- **Redirect URI MUST match exactly** between auth URL and token exchange POST
- **`state` parameter is REQUIRED for all OAuth 2.0 flows** — prevents CSRF attacks. Generated as 32 bytes of crypto-random base64, stored in `~/.social-poster/.{platform}_state.json`, verified on code exchange
- **Tailscale Serve must be running BEFORE** the user clicks the OAuth URL
- **Existing whitelisted URIs can be repurposed** as Tailscale Serve proxy paths
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

Instagram tokens expire in ~1 hour. Immediately exchange:
```
GET graph.instagram.com/access_token?grant_type=ig_exchange_token
  &client_id={{INSTAGRAM_APP_ID}}&client_secret={{INSTAGRAM_APP_SECRET}}
  &access_token={{SHORT_LIVED_TOKEN}}
```
Returns 58-day token.

## X/Twitter OAuth 1.0a Flow

Uses `requests_oauthlib.OAuth1Session`:
1. `fetch_request_token()` with `callback_uri='oob'`
2. `authorization_url()` generates the URL
3. User gets PIN from web page
4. `fetch_access_token()` with PIN → access_token + access_secret

Dependencies: `pip3 install requests_oauthlib`

## Token Storage Format

```json
{
  "x": {"access_token": "...", "access_secret": "...", "screen_name": "@user"},
  "linkedin": {"access_token": "...", "refresh_token": "...", "expires_in": 5184000},
  "instagram": {"access_token": "...", "expires_in": 5184000, "user_id": "..."},
  "bluesky": {"handle": "user.bsky.social", "app_password": "xxxx-xxxx-xxxx-xxxx"}
}
```
