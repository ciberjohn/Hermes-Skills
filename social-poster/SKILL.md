---
name: social-poster
description: >
  Direct OAuth posting to social media — no Docker, no database, no redirect URI whitelisting.
  Generates OAuth URLs, exchanges user codes/PINs, stores tokens in a local vault, and posts
  via direct platform API calls. Supports 15 platforms across OAuth, webhook, and token-based auth.
domain: social-media
triggers:
  - "what networks can you post to"
  - "connect [platform]"
  - "post this to [platform]"
  - "schedule a post"
  - "promote this on social"
  - "what platforms are connected"
  - "how do I set up [platform]"
  - "send this to social media"
  - "connect a new platform"
  - "configure [platform]"
variables:
  SOCIAL_POSTER_DIR:
    description: "Directory for social-poster scripts and config"
    default: "~/.social-poster"
  TAILSCALE_HOST:
    description: "Your Tailscale hostname (e.g., mymachine.tail-abc123.ts.net)"
    required: true
    env_var: TAILSCALE_HOST
  # All platform credential variables are documented below in the Environment Variables section
references:
  - references/platform-setup-guides.md
  - references/platform-expansion.md
  - references/oauth-flows.md
scripts:
  - scripts/social-poster.py
  - scripts/webhook-poster.py
  - scripts/oauth-callback-server.py
  - scripts/auth-x-step1.py
  - scripts/auth-x-step2.py
---

# Social Poster — Direct OAuth Posting

## Overview

| Attribute | Value |
|-----------|-------|
| Total platforms | 15 |
| OAuth platforms | X, LinkedIn, Instagram, Facebook, Threads, YouTube, Mastodon, Twitch, Reddit |
| Webhook/Token | Discord, Slack, Telegram, GitHub |
| Direct | Bluesky |
| Auth | OAuth 1.0a, OAuth 2.0, App Passwords, Webhooks, PATs |

## User Interaction Flow

### 1. "What networks can you post to?"

The agent should:
1. Run `python3 social-poster.py vault:status` to check which platforms have stored tokens
2. Report the full list of 15 platforms, marking connected ones with ✅ and the rest as ⬜
3. Offer: "Want me to guide you through setting up any of them?"

Example response:
```
15 platforms supported. Currently connected:
  ✅ X, LinkedIn, Bluesky
  ⬜ Instagram, Mastodon, Twitch, Reddit, Discord, Slack, Telegram, GitHub, Threads, Facebook, YouTube, Pinterest
Say 'connect [platform]' and I'll walk you through it."
```

### 2. "Connect [platform]" or "How do I set up [platform]?"

The agent should:
1. Load the platform's setup guide from `references/platform-setup-guides.md`
2. Walk the user through the numbered steps, one at a time
3. For **OAuth platforms**: ask for credentials, save to config.json, generate auth URL, exchange code
4. For **webhook/token platforms**: ask for the URL/token, save to config.json, verify it works

### 3. "Post this to [platforms]: [content]"

The agent should:
1. Check the vault that the requested platforms have tokens
2. Use the platform-specific API to post
3. Report success/failure per platform
4. Respect per-platform character limits (see Platform Character Limits below)

### 4. "Schedule this for [time]"

The agent should:
1. Create a Hermes cron job that calls the posting function at the specified time
2. Use `cronjob action='create'` with the posting instructions

## Architecture

```
{{SOCIAL_POSTER_DIR}}/
├── config.json              — API credentials (key/secret per platform)
├── vault.json               — User access/refresh tokens
├── social-poster.py         — Unified CLI (vault status, auth URL gen, token exchange)
├── webhook-poster.py        — Webhook/Token poster (Discord, Slack, Telegram, GitHub)
├── auth-x-step1.py          — X OAuth step 1 (request token + auth URL)
├── auth-x-step2.py          — X OAuth step 2 (exchange PIN for access token)
├── oauth-callback-server.py — Callback HTTP server (Tailscale Serve)
└── last_code.txt            — Latest OAuth code captured (auto-generated)
```

## Platform Setup Guides

For step-by-step instructions on creating developer apps and getting credentials,
load `references/platform-setup-guides.md`. Each platform has:

- Exact URLs to visit
- Buttons to click and fields to fill
- Where to find credentials
- How the auth flow works

## Quick Reference: Auth Method Summary

| Platform | Auth Method | What User Needs | Config Keys |
|----------|------------|----------------|-------------|
| **X** | OAuth 1.0a PIN | API Key + Secret | `x.api_key`, `x.api_secret` |
| **LinkedIn** | OAuth 2.0 | Client ID + Secret | `linkedin.client_id`, `linkedin.client_secret` |
| **Bluesky** | App password | Handle + App Password | `bluesky.handle`, `bluesky.app_password` |
| **Instagram** | OAuth 2.0 | App ID + Secret | `instagram.app_id`, `instagram.app_secret` |
| **Mastodon** | OAuth 2.0 | Instance + Client ID/Secret | `mastodon.instance`, `mastodon.client_id`, `mastodon.client_secret` |
| **Twitch** | OAuth 2.0 | Client ID + Secret | `twitch.client_id`, `twitch.client_secret` |
| **Reddit** | OAuth 2.0 | Client ID + Secret | `reddit.client_id`, `reddit.client_secret` |
| **Threads** | OAuth 2.0 | App ID + Secret | `threads.app_id`, `threads.app_secret` |
| **Facebook** | OAuth 2.0 | App ID + Secret | `facebook.app_id`, `facebook.app_secret` |
| **YouTube** | OAuth 2.0 | Client ID + Secret | `youtube.client_id`, `youtube.client_secret` |
| **Discord** | Webhook | Webhook URL | `discord.webhook_url` |
| **Slack** | Webhook | Webhook URL | `slack.webhook_url` |
| **Telegram** | Bot token | Token + Chat ID | `telegram.bot_token`, `telegram.chat_id` |
| **GitHub** | PAT | PAT + Repo | `github.pat`, `github.repo` |

## Environment Variables

All platforms support environment variable fallback when `config.json` is absent.
This is useful for CI/CD or ephemeral environments:

| Env Var | Config Key |
|---------|-----------|
| `X_API_KEY` | `x.api_key` |
| `X_API_SECRET` | `x.api_secret` |
| `LINKEDIN_CLIENT_ID` | `linkedin.client_id` |
| `LINKEDIN_CLIENT_SECRET` | `linkedin.client_secret` |
| `INSTAGRAM_APP_ID` | `instagram.app_id` |
| `INSTAGRAM_APP_SECRET` | `instagram.app_secret` |
| `BLUESKY_HANDLE` | `bluesky.handle` |
| `BLUESKY_APP_PASSWORD` | `bluesky.app_password` |
| `MASTODON_INSTANCE` | `mastodon.instance` |
| `MASTODON_CLIENT_ID` | `mastodon.client_id` |
| `MASTODON_CLIENT_SECRET` | `mastodon.client_secret` |
| `TWITCH_CLIENT_ID` | `twitch.client_id` |
| `TWITCH_CLIENT_SECRET` | `twitch.client_secret` |
| `REDDIT_CLIENT_ID` | `reddit.client_id` |
| `REDDIT_CLIENT_SECRET` | `reddit.client_secret` |
| `THREADS_APP_ID` | `threads.app_id` |
| `THREADS_APP_SECRET` | `threads.app_secret` |
| `FACEBOOK_APP_ID` | `facebook.app_id` |
| `FACEBOOK_APP_SECRET` | `facebook.app_secret` |
| `YOUTUBE_CLIENT_ID` | `youtube.client_id` |
| `YOUTUBE_CLIENT_SECRET` | `youtube.client_secret` |
| `DISCORD_WEBHOOK_URL` | `discord.webhook_url` |
| `SLACK_WEBHOOK_URL` | `slack.webhook_url` |
| `TELEGRAM_BOT_TOKEN` | `telegram.bot_token` |
| `TELEGRAM_CHAT_ID` | `telegram.chat_id` |
| `GITHUB_PAT` | `github.pat` |
| `GITHUB_REPO` | `github.repo` |

## Cross-Machine OAuth (Tailscale)

When the agent is on a remote VPS and the user is on a different machine:

```bash
# 1. Start the callback server (persistent)
python3 ~/.social-poster/oauth-callback-server.py 19876 &

# 2. Expose paths per platform
tailscale serve --bg --set-path /oauth-callback 19876
tailscale serve --bg --set-path /integrations/social/linkedin 19876
tailscale serve --bg --set-path /integrations/social/instagram-standalone 19876
```

The callback server captures OAuth codes from Tailscale HTTPS redirects and saves
them to `{{SOCIAL_POSTER_DIR}}/last_code.txt`.

## Platform Character Limits

When posting, respect per-platform limits:

| Platform | Max Length | Notes |
|----------|-----------|-------|
| **X/Twitter** (non-premium) | 280 chars | Requires `who_can_reply_post: everyone` |
| **X/Twitter** (premium) | 25,000 chars | Same |
| **Bluesky** | 300 chars | Returns 400 if exceeded |
| **LinkedIn** | 3,000 chars | Professional tone |
| **Facebook** | 63,206 chars | Link for best reach |
| **Instagram** | 2,200 chars | Image/video required |
| **Threads** | 500 chars | Short and punchy |
| **YouTube** | 5,000 chars | Description only |
| **Mastodon** | 500 chars | Instance-dependent |
| **Twitch** | N/A | Channel announcements |
| **Reddit** | 40,000 chars | Title max 300 |
| **Discord** | 2,000 chars | Embeds supported |
| **Slack** | 40,000 chars | Block kit |
| **Telegram** | 4,096 chars | HTML/Markdown |
| **GitHub** | N/A | Issues/gists |

## Pitfalls

- **Never use `os.path.expanduser("~")` directly in Hermes sessions** — it resolves to the sandbox home. Scripts auto-detect and use `pwd.getpwuid()`.
- **config.json and vault.json must be chmod 600** — NEVER committed to git.
- **LinkedIn scopes must NOT include org scopes** unless the app has Community Management API.
- **LinkedIn MUST NOT use `prompt=none`** for first-time authorization.
- **X/Twitter callback must be `oob`** for PIN-based flow.
- **Instagram app MUST be Live** (not Development) for OAuth.
- **Bluesky uses app passwords** (format: `xxxx-xxxx-xxxx-xxxx`), not regular passwords.
- **Redirect URI MUST match exactly** between auth URL and token exchange POST.
- **`state` parameter is REQUIRED for all OAuth 2.0 flows** — built into all generators.
- **Platform setup guides may drift** as developer portals update their UIs. If a user reports a step doesn't match, verify at the official developer portal URL and update the guide.

## References

- `references/platform-setup-guides.md` — Step-by-step setup guides for all 15 platforms
- `references/platform-expansion.md` — Full roadmap and implementation notes
- `references/oauth-flows.md` — OAuth implementation details and token exchange reference
