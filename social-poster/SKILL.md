---
name: social-poster
description: >
  Direct OAuth posting to social media — no Docker, no database, no redirect URI whitelisting.
  Generates OAuth URLs, exchanges user codes/PINs, stores tokens in a local vault, and posts
  via direct platform API calls. Supports X, LinkedIn, Bluesky, Instagram, Threads, Facebook,
  and YouTube.
domain: social-media
triggers:
  - "post this to [platform]"
  - "schedule a post"
  - "connect [platform]"
  - "promote this on social"
  - "what platforms are connected"
  - "send this to social media"
variables:
  SOCIAL_POSTER_DIR:
    description: "Directory for social-poster scripts and config"
    default: "~/.social-poster"
  TAILSCALE_HOST:
    description: "Your Tailscale hostname (e.g., mymachine.tail-abc123.ts.net)"
    required: true
    env_var: TAILSCALE_HOST
  X_API_KEY:
    description: "X/Twitter API Consumer Key (falls back to env var)"
    required: false
    env_var: X_API_KEY
  X_API_SECRET:
    description: "X/Twitter API Consumer Secret (falls back to env var)"
    required: false
    env_var: X_API_SECRET
  LINKEDIN_CLIENT_ID:
    description: "LinkedIn OAuth client ID (falls back to env var)"
    required: false
    env_var: LINKEDIN_CLIENT_ID
  LINKEDIN_CLIENT_SECRET:
    description: "LinkedIn OAuth client secret (falls back to env var)"
    required: false
    env_var: LINKEDIN_CLIENT_SECRET
  BLUESKY_HANDLE:
    description: "Bluesky handle (falls back to env var)"
    required: false
    env_var: BLUESKY_HANDLE
  BLUESKY_APP_PASSWORD:
    description: "Bluesky app password (falls back to env var)"
    required: false
    env_var: BLUESKY_APP_PASSWORD
---

# Social Poster — Direct OAuth Posting

## Overview

A zero-infrastructure social media posting system. No Docker containers, no databases,
no OAuth redirect URI whitelisting. Just Python scripts, a token vault, and Hermes cron jobs.

**Why this exists:** Postiz self-hosting proved too fragile. This system bypasses all of it by generating
OAuth URLs, having the user paste codes/PINs from their browser, exchanging for tokens,
and posting via direct API calls.

### Token Storage

- Config (API credentials): `{{SOCIAL_POSTER_DIR}}/config.json` (chmod 600)
- Vault (user tokens): `{{SOCIAL_POSTER_DIR}}/vault.json` (chmod 600)
- Temp sessions: `{{SOCIAL_POSTER_DIR}}/.x_session.json` (auto-deleted after exchange)

### Hermes Sandbox Note

`os.path.expanduser("~")` resolves to Hermes's sandbox home. The scripts auto-detect this
and use `pwd.getpwuid(os.getuid()).pw_dir` to read/write files in the real home directory.

---

## Architecture

```
{{SOCIAL_POSTER_DIR}}/
├── config.json              — API credentials (key/secret per platform, NEVER committed)
├── vault.json               — User access/refresh tokens (NEVER committed)
├── social-poster.py         — Unified CLI (vault status, auth URL gen, token exchange)
├── auth-x-step1.py          — X/Twitter OAuth 1.0a — get request token + auth URL
├── auth-x-step2.py          — X/Twitter OAuth 1.0a — exchange PIN for access token
├── oauth-callback-server.py — OAuth callback server for cross-machine flows
├── post.py                  — Posting scripts (future)
└── .x_session.json          — Temporary OAuth session (auto-deleted)
```

---

## Platform Setup

### Prerequisites Per Platform

Each platform needs API credentials in `config.json`:

| Platform | Config Key | Auth Type | Redirect |
|----------|-----------|-----------|----------|
| **X/Twitter** | `x.api_key`, `x.api_secret` | OAuth 1.0a (PIN-based) | `oob` |
| **LinkedIn** | `linkedin.client_id`, `linkedin.client_secret` | OAuth 2.0 (code paste) | Tailscale URL |
| **Instagram** | `instagram.app_id`, `instagram.app_secret` | OAuth 2.0 (code paste) | Tailscale URL |
| **Threads** | `threads.app_id`, `threads.app_secret` | OAuth 2.0 (code paste) — *store planned* | Tailscale URL |
| **Facebook** | `facebook.app_id`, `facebook.app_secret` | OAuth 2.0 (code paste) — *store planned* | Tailscale URL |
| **YouTube** | `youtube.client_id`, `youtube.client_secret` | OAuth 2.0 (code paste) — *store planned* | tailnet/oauth-callback |
| **Mastodon** | `mastodon.instance`, `mastodon.client_id`, `mastodon.client_secret` | OAuth 2.0 (code paste) | tailnet/oauth-callback |
| **Twitch** | `twitch.client_id`, `twitch.client_secret` | OAuth 2.0 (code paste) | tailnet/oauth-callback |
| **Reddit** | `reddit.client_id`, `reddit.client_secret` | OAuth 2.0 (code paste) | tailnet/oauth-callback |
| **Bluesky** | `bluesky.handle`, `bluesky.app_password` | App password (direct) | N/A |

### Webhook Platforms (no OAuth)

| Platform | Config Key | Method | Setup |
|----------|-----------|--------|-------|
| **Discord** | `discord.webhook_url` | Webhook POST | Create webhook in channel settings |
| **Slack** | `slack.webhook_url` | Webhook POST | Create webhook in Slack API |
| **Telegram** | `telegram.bot_token`, `telegram.chat_id` | Bot API | Create bot via @BotFather |
| **GitHub** | `github.pat`, `github.repo` | REST API | PAT from github.com/settings/tokens |

### Environment Variables

All platforms support environment variable fallback. If `config.json` is absent, the script
reads from env vars (e.g., `X_API_KEY`, `LINKEDIN_CLIENT_ID`, `BLUESKY_HANDLE`, etc.).
See the `variables:` section in the frontmatter for the complete list.

### OAuth Flow Pattern

For all OAuth platforms, the flow is:

1. **Generate URL** — Agent runs the auth script → get an authorization URL
2. **User authenticates** — Opens URL in browser, authorizes
3. **Paste code/PIN** — After auth, browser redirects to the callback URL with `?code=...`
4. **Exchange** — Agent exchanges code for access token
5. **Store** — Token saved to `vault.json`

### Cross-Machine OAuth (Tailscale)

When the agent is on a remote VPS and the user is on a different machine:
`localhost` redirects fail. Use the Python callback server behind Tailscale Serve.

Setup (one-time):
```bash
# 1. Start the callback server (persistent)
python3 {{SOCIAL_POSTER_DIR}}/oauth-callback-server.py 19876 &

# 2. Expose paths per platform
tailscale serve --bg --set-path /oauth-callback 19876
tailscale serve --bg --set-path /integrations/social/linkedin 19876
tailscale serve --bg --set-path /integrations/social/instagram-standalone 19876
```

---

## Platform Character Limits

| Platform | Max Length | Notes |
|----------|-----------|-------|
| **X/Twitter** (non-premium) | 280 chars | Requires settings `who_can_reply_post: everyone` |
| **X/Twitter** (premium) | 25,000 chars | Same settings requirement |
| **Bluesky** | 300 chars | Returns 400 if exceeded |
| **LinkedIn** | 3,000 chars | Professional tone works best |
| **Facebook** | 63,206 chars | Share a link for best reach |
| **Instagram** | 2,200 chars | Image/video required |
| **Threads** | 500 chars | Short and punchy |
| **YouTube** | 5,000 chars (description) | Video upload, not text post |
| **Mastodon** | 500 chars | Instance-dependent (some allow 500+) |
| **Twitch** | N/A | Channel announcements, clip shares |
| **Reddit** | 40,000 chars | Title max 300 chars |
| **Discord** | 2,000 chars | Webhook embeds support rich formatting |
| **Slack** | 40,000 chars | Block kit for rich messages |
| **Telegram** | 4,096 chars | HTML/Markdown in messages |
| **GitHub** | N/A | Issue body, unlimited |

**Key rule:** Create separate posts per platform. Each has unique settings and length constraints.
Never batch different platforms into one API call unless the copy fits the shortest limit.

---

## Pitfalls

- **Never use `os.path.expanduser("~")` directly in Hermes sessions** — it resolves to the sandbox home.
- **config.json and vault.json must be chmod 600** and NEVER committed.
- **For the published skill**, config.json is a TEMPLATE with `{{VAR}}` placeholders.
- **LinkedIn scopes must NOT include org scopes** unless the app has Community Management API.
- **LinkedIn MUST NOT use `prompt=none`** for first-time authorization.
- **X/Twitter callback must be `oob`** for PIN-based flow.
- **Instagram app must be Live** (not Development) for OAuth to work.
- **Bluesky uses app passwords** (format: `xxxx-xxxx-xxxx-xxxx`), not regular passwords.
- **Redirect URI must match EXACTLY** between auth URL and token exchange POST.

## References

- `references/oauth-flows.md` — Detailed OAuth flow scripts and token exchange logic
- `scripts/social-poster.py` — Main CLI script
- `scripts/oauth-callback-server.py` — Callback HTTP server for Tailscale
- `scripts/auth-x-step1.py` — X OAuth step 1 (request token)
- `scripts/auth-x-step2.py` — X OAuth step 2 (PIN exchange)
