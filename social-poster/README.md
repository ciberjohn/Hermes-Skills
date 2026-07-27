# Social Poster — Direct OAuth Posting for Hermes

> **Zero-infrastructure social media posting.** No Docker. No databases. No redirect URI gymnastics. Just Python scripts and your Hermes agent.

## Install

Copy-paste this to your Hermes agent (any profile):

```
I want to install the social-poster skill. Load skill-writer, load social-poster from github.com/ciberjohn/Hermes-Skills, and set up the scripts in ~/.social-poster/. Ask me for my TAILSCALE_HOST when you need it.
```

Or install manually:

```bash
# Clone the skills repo
git clone https://github.com/ciberjohn/Hermes-Skills.git ~/Hermes-Skills

# Copy scripts
cp -r ~/Hermes-Skills/social-poster/scripts/* ~/.social-poster/

# Create config template
cat > ~/.social-poster/config.json << 'EOF'
{
  "x": { "api_key": "{{X_API_KEY}}", "api_secret": "{{X_API_SECRET}}" },
  "linkedin": { "client_id": "{{LINKEDIN_CLIENT_ID}}", "client_secret": "{{LINKEDIN_CLIENT_SECRET}}" },
  "instagram": { "app_id": "{{INSTAGRAM_APP_ID}}", "app_secret": "{{INSTAGRAM_APP_SECRET}}" },
  "threads": { "app_id": "{{THREADS_APP_ID}}", "app_secret": "{{THREADS_APP_SECRET}}" },
  "bluesky": { "handle": "{{BLUESKY_HANDLE}}", "app_password": "{{BLUESKY_APP_PASSWORD}}" }
}
EOF

chmod 600 ~/.social-poster/config.json

# Install deps
pip3 install requests_oauthlib
```

## How it Works

1. **You create developer apps** on each platform (X, LinkedIn, etc.) and add the API keys to `config.json`
2. **Your Hermes agent generates OAuth URLs** — you open them, authorize, paste back the code
3. **Tokens are stored** in an encrypted vault (`vault.json`, chmod 600)
4. **You post via Hermes** — `"Spock, post this to X and Bluesky"` or schedule it as cron

## Platforms Supported

| Platform | Auth Method | What You Need |
|----------|------------|--------------|
| **X/Twitter** | OAuth 1.0a PIN | API Key + Secret (developer.twitter.com) |
| **LinkedIn** | OAuth 2.0 code | Client ID + Secret (developer.linkedin.com) |
| **Bluesky** | App password | Handle + App Password (Settings → App Passwords) |
| **Instagram** | OAuth 2.0 code | App ID + Secret (developers.facebook.com) |
| **Threads** | OAuth 2.0 code | App ID + Secret (developers.facebook.com) |
| **Facebook** | OAuth 2.0 code | App ID + Secret (developers.facebook.com) |
| **YouTube** | OAuth 2.0 code | Client ID + Secret (console.cloud.google.com) |

## Creating Developer Apps (Quick Guides)

Your Hermes agent should guide you through each platform's developer portal step-by-step. These are the minimum requirements:

### X/Twitter
- Go to developer.twitter.com → Create App
- Enable **OAuth 1.0a** with **Read and Write** permissions
- No callback URL needed (uses PIN-based flow)

### LinkedIn
- Go to developer.linkedin.com → Create App
- Add products: **Sign In with LinkedIn** + **Share on LinkedIn**
- Add redirect URL: `https://{{YOUR_TAILSCALE_HOST}}/integrations/social/linkedin`
- Scopes: `openid`, `profile`, `w_member_social` (no org scopes)

### Bluesky
- No app needed. Go to Settings → Privacy & Security → App Passwords
- Generate an app password (format: `xxxx-xxxx-xxxx-xxxx`)

### Instagram / Threads / Facebook
- Go to developers.facebook.com → Create App (type: Business)
- Add product: **Instagram Basic Display** for Instagram
- Set app to **Live** mode (not Development)
- Add your Instagram account as a **Tester**
- Add redirect URL to Valid OAuth Redirect URIs

### YouTube
- Go to console.cloud.google.com → Create Project
- Enable YouTube Data API v3
- Create OAuth 2.0 credentials (Desktop application type)
- Add redirect URL: `http://localhost`

## Usage

Once connected, tell your Hermes agent:

- _"Post this to X and LinkedIn: [content]"_
- _"Schedule a LinkedIn post for Friday at 10am"_
- _"What platforms are connected?"_
- _"Connect Instagram"_

## Security

- API keys and tokens are stored locally, never transmitted
- `config.json` and `vault.json` are chmod 600
- The skill uses `{{VAR}}` placeholders — no hardcoded secrets
- Tokens stay on your machine; Hermes posts from your infrastructure

## License

MIT — see [LICENSE](../LICENSE)
