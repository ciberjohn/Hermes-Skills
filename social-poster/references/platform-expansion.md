# Social Poster — Platform Expansion Roadmap

## Integration Methods

### Webhook-Based (no OAuth, just POST a URL)
| Platform | What to Post | Setup Time | Implementation |
|----------|-------------|-----------|---------------|
| **Discord** | Rich embed with link + description | 5 min | One webhook URL → POST JSON |
| **Slack** | Rich message with link | 5 min | One webhook URL → POST JSON |
| **Telegram** | Text + link to a channel | 10 min | Bot token + chat_id → API call |

### Personal Access Token (no OAuth dance)
| Platform | What to Post | Setup Time | Implementation |
|----------|-------------|-----------|---------------|
| **GitHub** | Issues, gists, repo discussions | 5 min | PAT from github.com/settings/tokens |
| **Signal** | Encrypted messages | 30 min | signal-cli D-Bus or REST |

### OAuth (needs developer app creation)
| Platform | What to Post | Setup Time | Notes |
|----------|-------------|-----------|-------|
| **Mastodon** | Toot with media | 15 min | Register app on your instance — no review needed |
| **Twitch** | Stream announcement, clip share | 20 min | Twitch dev app — no review for channel info |
| **Reddit** | Post to subreddits | 20 min | Reddit app — script type, no review needed |
| **Pinterest** | Pin image + link | 30 min | Pinterest app — requires basic review |
| **TikTok** | Video upload | Heavy | TikTok dev app — requires publish review |
| **Snapchat** | Spotlight upload | Heavy | Snap Kit — requires business verification |

## My Recommendation: Order of Implementation

1. **Discord** (webhook, 5 min) — highest bang for buck
2. **Slack** (webhook, 5 min) — same code pattern as Discord
3. **Telegram** (bot token, 10 min) — one-time setup
4. **GitHub** (PAT, 5 min) — useful for content repos
5. **Mastodon** (OAuth, 15 min) — no app review, works on any instance
6. **Twitch** (OAuth, 20 min) — game streaming integration
7. **Reddit** (OAuth, 20 min) — content distribution
8. **Pinterest** (OAuth, 30 min)
9. **TikTok / Snapchat** (heavy, defer)

## Code Architecture

All webhooks follow the same pattern:
```python
def post(platform, content):
    payload = {"content": content["text"], "embeds": [...]}
    POST content["webhook_url"] with payload
```

OAuth platforms use the same social-poster pattern: generate URL → authenticate → store token → post via API.
