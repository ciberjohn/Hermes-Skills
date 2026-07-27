# Social Poster — Platform Setup Guides

This file contains step-by-step instructions for every supported platform.
The agent should load this when the user asks "how do I set up [platform]?"
or "connect [platform]".

Each guide is designed to be read aloud by the agent — numbered steps,
exact URLs, exact labels to click.

---

## 1. X/Twitter (OAuth 1.0a — PIN-based)

**Difficulty:** Easy  
**Required:** An X account  
**Time:** 5 minutes

### Step-by-step

1. Go to **https://developer.twitter.com/en/portal/dashboard**
2. Click **"Create Project"** — name it anything, e.g., "Social Poster"
3. Select **"Other"** for use case, then **"Next"**
4. Click **"Create App"** inside the project
5. Name your app (e.g., "social-poster") and **save**
6. Go to the **"Keys and Tokens"** tab
7. Find **"Consumer Keys"** → copy **API Key** and **API Key Secret**
8. Go to **"User Authentication Settings"** → **"Set up"**
9. Set:
   - **App permissions:** "Read and Write"
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
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
5. Go to **"Auth"** tab
6. Find **"Authorized Redirect URLs"** — click **"Add"** and paste:
   ```
   https://{{CALLBACK_HOST}}/integrations/social/linkedin
   ```
7. Copy **Client ID** and **Client Secret** from the **"Auth"** tab
8. Save in `config.json` under `linkedin.client_id` and `linkedin.client_secret`

### Auth Flow
1. Agent runs `python3 social-poster.py auth:linkedin`
2. User opens the URL, authorizes, gets redirected to Tailscale URL with `?code=`
3. Agent extracts code via callback server, runs `store:linkedin <code>`

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

## 4. Instagram Standalone (OAuth 2.0)

**Difficulty:** Medium  
**Required:** A Facebook developer account, an Instagram account  
**Time:** 15 minutes

### Step-by-step

1. Go to **https://developers.facebook.com/**
2. **"Create App"** → **"Business"** as the type
3. Once created, go to **"Add Product"** → find **"Instagram Basic Display"** → **"Set Up"**
4. Go to **"Instagram Basic Display" → "Basic Display"** in the sidebar
5. Under **"Valid OAuth Redirect URIs"**, add:
   ```
   https://{{CALLBACK_HOST}}/integrations/social/instagram-standalone
   ```
6. Go to **"Settings" → "Basic"** and at the top, **toggle the app to Live** (not Development)
7. Copy **App ID** and **App Secret** from the dashboard
8. Save in `config.json` under `instagram.app_id` and `instagram.app_secret`

**Important:** The app MUST be in Live mode. Development mode only works for test users.

### Auth Flow
1. Agent runs `python3 social-poster.py auth:instagram`
2. User authorizes in browser, redirects back with `?code=`
3. Agent exchanges code for long-lived token

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
   - **Redirect URI:** `https://{{CALLBACK_HOST}}/oauth-callback`
   - **Scopes:** check `read` and `write`
4. Click **"Submit"**
5. Copy **Client Key** (this is your client_id) and **Client Secret**
6. Save in `config.json` under `mastodon.instance`, `mastodon.client_id`, `mastodon.client_secret`

**Note:** No app review needed. You register the app on YOUR instance directly.

### Auth Flow
1. Agent runs `python3 social-poster.py auth:mastodon`
2. User authorizes in browser, redirects back with `?code=`
3. Agent runs `store:mastodon <code>`

---

## 6. Twitch (OAuth 2.0)

**Difficulty:** Medium  
**Required:** A Twitch account  
**Time:** 10 minutes

### Step-by-step

1. Go to **https://dev.twitch.tv/console**
2. Click **"Register Your Application"**
3. Fill in:
   - **Name:** anything
   - **OAuth Redirect URL:** `https://{{CALLBACK_HOST}}/oauth-callback`
   - **Category:** "Application Integration"
4. Click **"Create"**
5. Copy **Client ID**
6. Click **"New Secret"** → copy **Client Secret**
7. Save in `config.json` under `twitch.client_id` and `twitch.client_secret`

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

1. Go to **https://www.reddit.com/prefs/apps**
2. Scroll to bottom → click **"Create Another App"**
3. Select **"script"** type
4. Fill:
   - **Name:** anything
   - **Redirect URI:** `https://{{CALLBACK_HOST}}/oauth-callback`
5. Click **"Create App"**
6. Note: your **client_id** is the small string under the app name (e.g., `abc123def`)
7. The **client_secret** is the longer string labeled "secret"
8. Save in `config.json` under `reddit.client_id` and `reddit.client_secret`

**Important:** The app MUST be "script" type, not "web app".

### Auth Flow
1. Agent runs `python3 social-poster.py auth:reddit`
2. User authorizes in browser, redirects back with `?code=`
3. Agent runs `store:reddit <code>`

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
5. Click **"Copy Webhook URL"**
6. Save in `config.json` under `discord.webhook_url`

### Posting
```
python3 webhook-poster.py discord "<webhook_url>" "<message>"
```

---

## 9. Slack (Webhook)

**Difficulty:** Very Easy  
**Required:** A Slack workspace where you can create apps  
**Time:** 3 minutes

### Step-by-step

1. Go to **https://api.slack.com/apps → Create New App → From Scratch**
2. Name it → select workspace → **Create App**
3. Go to **"Incoming Webhooks" → "Activate Incoming Webhooks"** (toggle ON)
4. Click **"Add New Webhook to Workspace"**
5. Select the channel → click **"Allow"**
6. Copy the **Webhook URL** (starts with `https://hooks.slack.com/`)
7. Save in `config.json` under `slack.webhook_url`

### Posting
```
python3 webhook-poster.py slack "<webhook_url>" "<message>"
```

---

## 10. Telegram (Bot Token)

**Difficulty:** Easy  
**Required:** A Telegram account  
**Time:** 5 minutes

### Step-by-step

1. Open Telegram → search for **@BotFather**
2. Send: `/newbot`
3. Follow prompts: name your bot (e.g., "Social Poster Bot")
4. The BotFather will give you a **token** (format: `123456:ABC-DEF1234gh...`)
5. Copy the token
6. To find your **chat_id**: send a message to your bot, then visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
7. Find `"chat":{"id":123456789}` in the response — that's your chat_id
8. Save in `config.json` under `telegram.bot_token` and `telegram.chat_id`

### Posting
```
python3 webhook-poster.py telegram "<token>" <chat_id> "<message>"
```

---

## 11. GitHub (PAT)

**Difficulty:** Easy  
**Required:** A GitHub account  
**Time:** 3 minutes

### Step-by-step

1. Go to **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"**
3. Give it a name (e.g., "Social Poster")
4. Select scopes: **repo** (for private repos) or **public_repo** (for public repos only)
5. Click **"Generate token"**
6. Copy the token (shown only once)
7. Save in `config.json` under `github.pat` and `github.repo` (format: `username/repo`)

### Posting
```
python3 webhook-poster.py github "<pat>" "<repo>" "<title>" "<body>"
```

---

## 12. Threads (OAuth 2.0 — store planned)

**Difficulty:** Medium  
**Setup:** Same as Instagram — Facebook Business App with Threads product

1. Go to **https://developers.facebook.com/**
2. Create or use a Business app
3. Add product: **Threads**
4. Add redirect URI: `https://{{CALLBACK_HOST}}/oauth-callback`
5. Set app to **Live** mode
6. Save credentials under `threads.app_id` and `threads.app_secret`

---

## 13. Facebook (OAuth 2.0 — store planned)

**Difficulty:** Medium  
**Setup:** Facebook Business App with Facebook Pages API

1. Go to **https://developers.facebook.com/**
2. Create a Business app
3. Add product: **Facebook Login** → configure Pages permissions
4. Add redirect URI: `https://{{CALLBACK_HOST}}/oauth-callback`
5. Save under `facebook.app_id` and `facebook.app_secret`

---

## 14. YouTube (OAuth 2.0 — store planned)

**Difficulty:** Medium  
**Setup:** Google Cloud project with YouTube Data API

1. Go to **https://console.cloud.google.com/** → Create Project
2. Enable **YouTube Data API v3**
3. Go to **Credentials** → **Create OAuth 2.0 Client ID**
4. Application type: **Desktop app**
5. Add redirect URI: `http://localhost`
6. Save under `youtube.client_id` and `youtube.client_secret`
