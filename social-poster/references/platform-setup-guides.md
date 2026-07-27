# Social Poster — Platform Setup Guides

This file contains step-by-step instructions for every supported platform.
The agent should load this when the user asks "how do I set up [platform]?"
or "connect [platform]".

Each guide is designed to be read aloud by the agent — numbered steps,
exact URLs, exact labels to click.

> **⚠️ SECURITY NOTICE — Read before proceeding**
>
> All credentials you generate (API keys, secrets, tokens, passwords) are
> **secrets**. Never commit them to version control.
>
> 1. Add `config.json` to `.gitignore`: `echo "config.json" >> .gitignore`
> 2. Restrict permissions: `chmod 600 config.json`
> 3. Consider using environment variables instead of plaintext files
>
> The agent will help you generate and store these credentials securely.

---

## 1. X/Twitter (OAuth 1.0a — PIN-based)

**Difficulty:** Easy  
**Required:** An X account  
**Time:** 5 minutes

> **Note:** As of 2025, the X developer portal requires login at x.com before accessing
> the dashboard. The developer docs have moved to docs.x.com. X API now uses a
> pay-per-use pricing model. Free tier (Basic) provides 3,000 posts/month and 15,000 reads.

### Step-by-step

1. Go to **https://developer.twitter.com/en/portal/dashboard** (will redirect to x.com login)
2. Once logged in, click **"Create Project"** — name it anything, e.g., "Social Poster"
3. Select **"Other"** for use case, then **"Next"**
4. Click **"Create App"** inside the project
5. Name your app (e.g., "social-poster") and **save**
6. Go to the **"Keys and Tokens"** tab
7. Find **"Consumer Keys"** → copy **API Key** and **API Key Secret**
8. Go to **"User Authentication Settings"** → **"Set up"**
9. Set:
   - **App permissions:** "Read and Write" (or "Read, Write, and Direct Messages" for DMs)
   - **Type of app:** "Web App, Automated App or Bot"
   - **Callback URI / Redirect URL:** `oob`
   - **Website URL:** any valid URL (e.g., `https://example.com`)
10. Save the credentials in `config.json` under `x.api_key` and `x.api_secret`

### Auth Flow
1. Agent runs `python3 social-poster.py auth:x` → generates a URL
2. User opens URL, authorizes, gets a **7-digit PIN**
3. User sends PIN to agent
4. Agent runs `python3 social-poster.py store:x <PIN>` → tokens saved

---

## 2. LinkedIn (OAuth 2.0)

**Difficulty:** Medium  
**Required:** A LinkedIn account, LinkedIn Developer Portal access  
**Time:** 10 minutes

### Step-by-step

1. Go to **https://www.linkedin.com/developers/**
2. Click **"Create App"**
3. Name it, link your company page (or skip), upload a 1×1 logo (any image works)
4. Under **"Products"** tab, add:
   - **Sign In with LinkedIn using OpenID Connect** (provides `openid`, `profile`, `email` scopes)
   - **Share on LinkedIn** (provides `w_member_social` scope for posting)
5. Go to **"Auth"** tab
6. Find **"Authorized Redirect URLs"** — click **"Add"** and paste:
   ```
   https://{{CALLBACK_HOST}}/integrations/social/linkedin
   ```
7. Copy **Client ID** and **Client Secret** from the **"Auth"** tab

> **⚠️ NOTE:** The `w_member_social` scope requires LinkedIn app review before the app can be used outside of self-testing. After creating your app, go to **"Products" → "Share on LinkedIn"** and check the status. If it says "Awaiting review", click **"Request Review"** and follow LinkedIn's submission process. During development, only your own account can authorize.
8. Save in `config.json` under `linkedin.client_id` and `linkedin.client_secret`

### Auth Flow
1. Agent runs `python3 social-poster.py auth:linkedin`
2. User opens the URL, authorizes, gets redirected to Tailscale URL with `?code=`
3. Agent extracts code via callback server, runs `store:linkedin <code>`

### Permissions
- `openid` — Verify LinkedIn member identity
- `profile` — Read member's profile
- `email` — Read member's email address
- `w_member_social` — Create posts on behalf of the member

---

## 3. Bluesky (App Password)

**Difficulty:** Easy  
**Required:** A Bluesky account  
**Time:** 2 minutes

### Step-by-step

1. Log in to **https://bsky.app**
2. Go to **Settings → Privacy & Security → App Passwords**
3. Click **"Add App Password"**
4. Name it (e.g., "social-poster") → click **"Create"**
5. Copy the password (format: `xxxx-xxxx-xxxx-xxxx`)
6. Save in `config.json` under `bluesky.handle` and `bluesky.app_password`

### Auth Flow
No OAuth needed. Just save credentials to vault:
```
python3 social-poster.py store:bluesky
```

---

## 4. Instagram (OAuth 2.0 — Instagram API with Instagram Login)

**Difficulty:** Medium  
**Required:** A Meta developer account, an Instagram professional account (Business or Creator)  
**Time:** 15 minutes  

> **Important:** Meta deprecated Instagram Basic Display in April 2024.  
> Use **Instagram API with Instagram Login** instead. No Facebook Page is required.

### Step-by-step

1. Go to **https://developers.facebook.com/**
2. **"Create App"** → select **"Business"** as the app type → **"Next"**
3. Name your app → **"Create App"**
4. In the App Dashboard, go to **"Add Product"** → find **"Instagram Login"** → **"Set Up"**
5. Go to **"Instagram" → "Instagram API with Instagram Login" → "Get started"** in the sidebar
6. Under **"Valid OAuth Redirect URIs"**, add:
   ```
   https://{{CALLBACK_HOST}}/integrations/social/instagram
   ```
7. To associate your Instagram professional account:
   - Go to **"Instagram" → "API with Instagram Login" → "Configure"**
   - Click **"Generate Token"** or manage via **Instagram Testers**
8. Go to **"Settings" → "Basic"** — copy **App ID** and **App Secret**
9. **Important:** Set the app to **Live** mode (top toggle switch in the dashboard).
   Development mode only works for test users.
10. Save in `config.json` under `instagram.app_id` and `instagram.app_secret`

### Auth Flow
1. Agent runs `python3 social-poster.py auth:instagram`
2. User authorizes in browser, redirects back with `?code=`
3. Agent exchanges code for a long-lived access token

### Scopes
- `instagram_business_basic` — Read profile info
- `instagram_business_content_publish` — Publish media
- `instagram_business_manage_comments` — Moderate comments
- `instagram_business_manage_messages` — Respond to messages

---

## 5. Mastodon (OAuth 2.0)

**Difficulty:** Easy  
**Required:** A Mastodon account on any instance (e.g., mastodon.social)  
**Time:** 5 minutes

### Step-by-step

1. Log in to your Mastodon instance (e.g., `https://mastodon.social`)
2. Go to **Preferences → Development → New Application**
3. Fill in:
   - **Application name:** "Social Poster"
   - **Redirect URI:** `urn:ietf:wg:oauth:2.0:oob`
   - **Scopes:** check only `read:statuses` and `write:statuses` — these are the minimum for a posting bot. Do not use the broader `read` and `write` scopes unless you need additional functionality (follows, blocks, account management).
4. Click **"Submit"**
5. Copy **Client Key** (this is your `client_id`) and **Client Secret**
6. Save in `config.json` under `mastodon.instance`, `mastodon.client_id`, `mastodon.client_secret`

> **Note:** As of Mastodon 4.3+, servers support OAuth Authorization Server Metadata at
> `/.well-known/oauth-authorization-server` to discover supported scopes.
> No app review needed — you register the app on YOUR instance directly.

### Auth Flow
1. Agent runs `python3 social-poster.py auth:mastodon`
2. User authorizes in browser, gets back a code
3. Agent exchanges code for access token via `POST /oauth/token`

Alternatively, you can register the app programmatically via the API:
```bash
curl -X POST \
  -F 'client_name=Social Poster' \
  -F 'redirect_uris=urn:ietf:wg:oauth:2.0:oob' \
  -F 'scopes=read write' \
  https://mastodon.example/api/v1/apps
```

---

## 6. Twitch (OAuth 2.0)

**Difficulty:** Medium  
**Required:** A Twitch account  
**Time:** 10 minutes

### Step-by-step

1. Go to **https://dev.twitch.tv/console** → click **"Log in"** if needed
2. Click **"Register Your Application"**
3. Fill in:
   - **Name:** anything (e.g., "Social Poster")
   - **OAuth Redirect URL:** `https://{{CALLBACK_HOST}}/oauth-callback`
   - **Category:** "Application Integration"
4. Click **"Create"**
5. Copy **Client ID** (shown on the app details page)
6. Click **"New Secret"** → copy **Client Secret**
7. Save in `config.json` under `twitch.client_id` and `twitch.client_secret`

### Required Scopes for posting
- `user:write:chat` — Send chat messages (if posting to chat)
- `channel:manage:broadcast` — Manage stream information
- `moderator:manage:announcements` — Send announcements

### Auth Flow
1. Agent runs `python3 social-poster.py auth:twitch`
2. User authorizes in browser, redirects back with `?code=`
3. Agent runs `store:twitch <code>`

---

## 7. Reddit (OAuth 2.0)

**Difficulty:** Medium  
**Required:** A Reddit account  
**Time:** 10 minutes

### Step-by-step

1. Go to **https://www.reddit.com/prefs/apps** (log in if prompted)
2. Scroll to bottom → click **"Create Another App"** or **"Create App"**
3. Select **"script"** type (NOT "web app")
4. Fill:
   - **Name:** anything (e.g., "Social Poster")
   - **Redirect URI:** `https://{{CALLBACK_HOST}}/oauth-callback`
5. Click **"Create App"**
6. Note: your **client_id** is the small string under the app name (e.g., `abc123def`)
7. The **client_secret** is the longer string labeled "secret"
8. Save in `config.json` under `reddit.client_id` and `reddit.client_secret`

**Important:** The app MUST be "script" type, not "web app". Script apps use
password-based OAuth flow (no interactive user authorization).

### Auth Flow
1. Agent uses `client_id` + `client_secret` + Reddit username/password to get an access token
2. Token is sent via HTTP Basic auth to `POST /api/v1/access_token`
3. Agent runs `store:reddit` to save the token

---

## 8. Discord (Webhook)

**Difficulty:** Very Easy  
**Required:** A Discord server where you have "Manage Webhooks" permission  
**Time:** 2 minutes

### Step-by-step

1. Open your Discord server → go to the channel you want to post to
2. Click the gear icon (**Channel Settings**)
3. Go to **Integrations → Webhooks → Create Webhook**
4. Name it (e.g., "Social Poster")
5. Click **"Copy Webhook URL"** (format: `https://discord.com/api/webhooks/...`)
6. Save in `config.json` under `discord.webhook_url`

> **Developer Portal:** For more control (rate limits, audit logs), visit
> **https://discord.com/developers/applications** → create an app → Bot → webhooks.

### Posting
```python
python3 social-poster.py post discord "Hello from Social Poster!"
```

---

## 9. Slack (Webhook)

**Difficulty:** Very Easy  
**Required:** A Slack workspace where you can create apps  
**Time:** 3 minutes

### Step-by-step

1. Go to **https://api.slack.com/apps** → **"Create New App"** → **"From Scratch"**
2. Name it → select workspace → **Create App**
3. Go to **"Incoming Webhooks"** → **"Activate Incoming Webhooks"** (toggle ON)
4. Click **"Add New Webhook to Workspace"**
5. Select the channel → click **"Allow"**
6. Copy the **Webhook URL** (starts with `https://hooks.slack.com/services/...`)
7. Save in `config.json` under `slack.webhook_url`

### Posting
```python
python3 social-poster.py post slack "Hello from Social Poster!"
```

---

## 10. Telegram (Bot Token)

**Difficulty:** Easy  
**Required:** A Telegram account  
**Time:** 5 minutes

### Step-by-step

1. Open Telegram → search for **@BotFather** (or open https://t.me/botfather)
2. Send: `/newbot`
3. Follow prompts: name your bot (e.g., "Social Poster Bot")
4. Choose a username ending in `bot` (e.g., `SocialPosterBot`)
5. The BotFather will give you a **token** (format: `123456:ABC-DEF1234gh...`)
6. Copy the token
7. To find your **chat_id**: send a message to your bot, then run this command from your terminal:
   ```bash
   curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][0]['message']['chat']['id'])"
   ```
   > **⚠️ Security tip:** Use an environment variable (`BOT_TOKEN=...`) instead of pasting the token into a URL. URLs are captured by browser history and server logs.
9. Save in `config.json` under `telegram.bot_token` and `telegram.chat_id`

> **Tip:** For group chats, add the bot to the group, send a message, then check
> `/getUpdates` — the chat_id will be a negative number.

### Posting
```python
python3 social-poster.py post telegram "<message>"
```

---

## 11. GitHub (PAT — Personal Access Token)

**Difficulty:** Easy  
**Required:** A GitHub account  
**Time:** 3 minutes

### Step-by-step

#### Option A: Fine-grained Token (recommended)
1. Go to **https://github.com/settings/tokens?type=beta**
2. Click **"Generate new token"** → **"Generate new fine-grained token"**
3. Give it a name (e.g., "Social Poster")
4. Set **Expiration** (choose a reasonable period)
5. Set **Repository access**: "Only select repositories" → pick the repos you need
6. Under **Permissions** → **Contents** → set **"Access: Read and write"**
7. Click **"Generate token"**
8. Copy the token (shown only once; prefix: `github_pat_...`)

#### Option B: Classic Token (⚠️ broader permissions — use only if fine-grained doesn't work)
1. Go to **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"**
3. Give it a name (e.g., "Social Poster")
4. Select the **minimum** scope:
   - `public_repo` — for public repos only (limited access)
   - `repo` — for private repos (**grants access to ALL your repos, not just the target one**)
5. Click **"Generate token"**
6. Copy the token (shown only once)

7. Save in `config.json` under `github.pat` and `github.repo` (format: `username/repo`)

### Posting
```python
python3 social-poster.py post github "Issue title" "Issue body"
```

---

## 12. Threads (OAuth 2.0)

**Difficulty:** Medium  
**Required:** A Meta developer account, a Threads professional account  
**Time:** 15 minutes

> **Note:** The Threads API is fully GA as of 2026. It supports posting,
> media retrieval, reply moderation, insights, and webhooks.

### Step-by-step

1. Go to **https://developers.facebook.com/**
2. **"Create App"** → select **"Business"** as the app type
3. Once created, navigate to the app dashboard
4. Go to **"Add Product"** → find **"Threads"** → **"Set Up"** (or select the Threads Use Case)
5. Under **"Threads"** in the sidebar, you'll see:
   - **"Get started"** — follow the on-screen wizard
   - **"Create an app"** → link your Threads professional account
6. Add your **Redirect URI**:
   ```
   https://{{CALLBACK_HOST}}/integrations/social/threads
   ```
7. Go to **"Settings" → "Basic"** — copy **Threads App ID** and **Threads App Secret**
8. Set the app to **Live** mode (toggle in the dashboard header)
9. Save in `config.json` under `threads.app_id` and `threads.app_secret`

### Permissions
- `threads_basic` — Read basic profile info
- `threads_content_publish` — Create and publish posts
- `threads_manage_replies` — Moderate replies
- `threads_read_replies` — Read replies
- `threads_insights` — Access post-level insights

### Auth Flow
1. Agent runs `python3 social-poster.py auth:threads`
2. User authorizes in browser, redirects back with `?code=`
3. Agent exchanges code for a short-lived token (1 hour), then exchanges for long-lived (60 days)

---

## 13. Facebook (OAuth 2.0 — Facebook Login / Pages API)

**Difficulty:** Medium  
**Required:** A Meta developer account, a Facebook Page you manage  
**Time:** 15 minutes

### Step-by-step

1. Go to **https://developers.facebook.com/**
2. **"Create App"** → select **"Business"** as the app type
3. Once created, go to the app dashboard
4. Go to **"Add Product"** → find **"Facebook Login"** → **"Set Up"**
5. Under **"Facebook Login" → "Settings"**, add:
   ```
   https://{{CALLBACK_HOST}}/integrations/social/facebook
   ```
   as a **Valid OAuth Redirect URI**
6. Under **"Facebook Login" → "Settings"** → enable **"Embedded Browser OAuth Login"**
   and **"Login from Devices"** if needed for CLI flow
7. Go to **"Settings" → "Basic"** — copy **App ID** and **App Secret**
8. Go to **"App Review" → "Permissions and Features"** and request:
   - `pages_manage_posts` — Post to Pages
   - `pages_read_engagement` — Read post analytics
   - `pages_show_list` — List Pages you manage
9. Set the app to **Live** mode (toggle in dashboard header)
10. Long-lived Page Access Tokens expire after 60 days; set up token refresh
11. Save in `config.json` under `facebook.app_id` and `facebook.app_secret`

### Auth Flow
1. Agent runs `python3 social-poster.py auth:facebook`
2. User authorizes in browser, gets a User Access Token
3. Token is exchanged for a long-lived Page Access Token via:
   - `GET /me/accounts` → get Page Access Token
   - `GET /{page-id}?fields=access_token` → extended Page token
4. Agent runs `store:facebook <page_token>`

---

## 14. YouTube (OAuth 2.0)

**Difficulty:** Medium  
**Required:** A Google account  
**Time:** 15 minutes

### Step-by-step

1. Go to **https://console.cloud.google.com/** → sign in → **"Create Project"** (or select existing)
2. Name your project (e.g., "Social Poster") → **"Create"**
3. Go to **"APIs & Services" → "Library"**
4. Search for **"YouTube Data API v3"** → click **"Enable"**
5. Go to **"APIs & Services" → "Credentials"**
6. Click **"Create Credentials"** → **"OAuth 2.0 Client ID"**
7. If not yet configured, configure the **OAuth consent screen**:
   - User Type: **"External"** (or Internal if using Google Workspace)
   - Fill in app name, support email, developer contact info
   - Add scopes: `https://www.googleapis.com/auth/youtube.upload`
   - Add test users (your YouTube email)
8. Back in **"Credentials"**, set:
   - **Application type:** "Desktop app"
   - **Name:** e.g., "Social Poster"
   - Click **"Create"**
9. Copy **Client ID** and **Client Secret**
10. Save in `config.json` under `youtube.client_id` and `youtube.client_secret`

### Scopes (choose minimal)
- `https://www.googleapis.com/auth/youtube.upload` — **Recommended** — Upload videos only
- `https://www.googleapis.com/auth/youtube.readonly` — Read-only (analytics, metadata)
- `https://www.googleapis.com/auth/youtube.force-ssl` — Manage videos (upload, update, delete)

> ⚠️ **Do NOT use** `https://www.googleapis.com/auth/youtube` ("Full access") unless your application specifically needs it. It grants complete control over your channel including deletion, private data, and monetization settings.

### Auth Flow
1. Agent runs `python3 social-poster.py auth:youtube`
2. User opens the URL, authorizes in browser, gets redirect to localhost with `?code=`
3. Agent exchanges code for refresh + access tokens
4. Agent runs `store:youtube`
