# QA / Consistency Review — social-poster skill

Review date: 2026-07-27
Files reviewed: 11 (6 scripts, 3 reference docs, SKILL.md, README.md)

## Syntax

| File | Status |
|------|--------|
| social-poster.py | ✅ Syntax OK |
| post.py | ✅ Syntax OK |
| webhook-poster.py | ✅ Syntax OK |
| auth-x-step1.py | ✅ Syntax OK |
| auth-x-step2.py | ✅ Syntax OK |
| oauth-callback-server.py | ✅ Syntax OK |

All 6 scripts pass `py_compile`. No syntax errors.

---

## BUG: post.py — Discord/Slack/Telegram dispatch passes `vault` instead of `config`

**Severity: BUG**
**File:** `scripts/post.py`, line 200
**Description:** The platform dispatch ternary unconditionally passes `vault` to webhook
platforms, but those functions expect `config` as their second parameter.

```python
r = fn(text, vault, config) if pl in ("x", "mastodon") else fn(text, vault) if pl != "github" else post_github(...)
```

- `post_discord(text, config)` → called as `post_discord(text, vault)` — vault has no `discord.webhook_url` → returns "No Discord webhook URL"
- `post_slack(text, config)` → same pattern → broken
- `post_telegram(text, config)` → same pattern → broken

**Suggested fix:** Add these platforms to the 3-param dispatch list OR refactor the dispatch to be
table-driven, making the parameter requirements explicit per platform:

```python
POST_ARGS = {
    "x": 3, "mastodon": 3, "discord": 3, "slack": 3, "telegram": 3,
    "github": "special",
}
```

---

## BUG: post.py — Twitch `Client-Id` header is hardcoded literal "twitch"

**Severity: BUG**
**File:** `scripts/post.py`, line 129
**Description:** `post_twitch()` sends `Client-Id: twitch` as the Twitch client ID. All Twitch
API calls require a valid `Client-Id` matching the registered app. The correct client ID
lives in `config["twitch"]["client_id"]`, but `post_twitch()` doesn't accept config as a parameter.

```python
headers={"Authorization": f"Bearer {tok}", "Client-Id": "twitch"}
```

**Fix:** Either add `config` parameter to `post_twitch()` and read `config.get("twitch",{}).get("client_id","")`,
or since Twitch posting is not really implemented (returns placeholder), either remove the broken
API call or fix it.

---

## BUG: auth-x-step1.py / auth-x-step2.py — path isolation from social-poster.py

**Severity: BUG** (conditional — applies when not run from `~/.social-poster/`)
**Files:** `scripts/auth-x-step1.py` line 6-7, `scripts/auth-x-step2.py` lines 6-9
**Description:** Both `auth-x-step*.py` scripts derive their data directory from `__file__`:

```python
DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(DIR, "config.json")
```

But `social-poster.py` uses `~/.social-poster/` unconditionally:

```python
CONFIG_DIR = os.path.join(_user_dir, ".social-poster")
```

If the user copies scripts to `~/.social-poster/` (as the README instructs), `DIR` resolves to
`~/.social-poster/` and everything is consistent. However, if someone runs them directly from
the checkout (`python3 ~/Hermes-Skills/social-poster/scripts/auth-x-step1.py`), the scripts
look for `config.json` and `.x_session.json` in the scripts directory, NOT `~/.social-poster/`.

Additionally, the X session file path is inconsistent:
- `social-poster.py store:x` (line 295): reads `.x_session.json` from `CONFIG_DIR` (`~/.social-poster/`)
- `auth-x-step2.py` (line 9): reads `.x_session.json` from `DIR` (script directory)

**Fix:** Change `auth-x-step*.py` to import and use the same path logic as `social-poster.py`,
or consolidate from a shared module.

---

## INCONSISTENCY: SKILL.md lists Pinterest in example but it's not a supported platform

**Severity: INCONSISTENCY**
**File:** `SKILL.md`, line 68-69
**Description:** The "What networks can you post to?" example response lists Pinterest as one of
the 15 platforms, but Pinterest is never mentioned in the "Total platforms: 15" count or in any
of the platform tables/implementations. The only Pinterest reference is in
`references/platform-expansion.md` as a future possibility:

```
⬜ Instagram, Mastodon, Twitch, Reddit, Discord, Slack, Telegram, GitHub, Threads, Facebook, YouTube, **Pinterest**
```

That's 12 platforms with ⬜ (plus 3 connected = 15). But there are only 14 real platforms
(plus Pinterest = 15 named but only 14 actual). The table in the overview and setup section
lists 14 distinct platforms.

**Fix:** Remove Pinterest from the example, or add it as a 15th platform if it's being tracked.

---

## INCONSISTENCY: `tiktok.com` reference in platform-expansion.md — not tracked in SKILL.md

**Severity: INCONSISTENCY**
**File:** `references/platform-expansion.md`, line 25
**Description:** TikTok is listed in the expansion roadmap as "Heavy" implementation effort,
but it's not mentioned anywhere in `SKILL.md` or the platform setup guides. This is a minor
planning doc inconsistency.

---

## MISSING: store:facebook, store:threads, store:youtube — not implemented

**Severity: MISSING-FEATURE (documented as planned)**
**File:** `scripts/social-poster.py`, line 353
**Description:** These three platforms have `auth:*` URL generators (lines 122-157) but no
token exchange functions. Running `store:facebook`, `store:threads`, or `store:youtube` hits:

```python
else:
    print(f"store:{plat} not implemented yet")
```

The SKILL.md and reference docs correctly mark these as "*store planned*", so this is
consistent with documentation. Listed here for completeness.

---

## EDGE CASE: X PIN vs OAuth 2.0 code extraction logic

**Severity: EDGE_CASE**
**File:** `scripts/social-poster.py`, line 293
**Description:** The unified code extraction at line 293 applies to ALL store commands,
including X (which uses PIN-based OAuth 1.0a, not code-based):

```python
if "code=" in code:
    code = urllib.parse.parse_qs(code.split("?")[1] if "?" in code else code).get("code",[code])[0]
```

X PINs are numeric (7 digits), so `"code=" in "1234567"` is `False` and this is a no-op for X.
However, if the user pastes a full URL with `?code=` for a non-X platform, the extraction
works. This is correctly a no-op for X but could cause subtle issues if the data format
changes.

---

## EDGE CASE: Instagram scope/platform mismatch

**Severity: EDGE_CASE**
**File:** `scripts/social-poster.py`, lines 115-116
**Description:** The Instagram auth URL uses `instagram_business_basic,instagram_business_content_publish`
scopes (Instagram Graph API / Business endpoints), but the setup guide in
`references/platform-setup-guides.md` instructs users to add the "Instagram Basic Display"
product. Basic Display uses `basic` and `content_publish` scopes against
`api.instagram.com/oauth/access_token`. Business scopes require "Instagram Graph API" product
and use `graph.facebook.com` endpoints.

The token exchange at line 247 POSTs to `api.instagram.com/oauth/access_token` (Basic Display
endpoint) with Business scopes. This may produce an `invalid scope` error at OAuth time.

**Fix:** Either change scopes to `basic,content_publish` (Basic Display) or change the setup
guide to use Instagram Graph API product and the `graph.facebook.com` token endpoint.

---

## SUMMARY

### Real bugs (will cause failures in production)

| # | File | Line | Issue | Fix Priority |
|---|------|------|-------|-------------|
| 1 | post.py | 200 | Discord/Slack/Telegram get `vault` instead of `config` | **High** |
| 2 | post.py | 129 | Twitch `Client-Id` hardcoded as `"twitch"` | **High** |
| 3 | auth-x-step1.py | 7 | Path isolation from social-poster.py | **Medium** |
| 4 | auth-x-step2.py | 6-9 | Path isolation (same as #3) | **Medium** |
| 5 | social-poster.py | 115-116 | Instagram scopes (Business) vs token endpoint (Basic Display) mismatch | **Medium** |

### Documentation inconsistencies

| # | File | Line | Issue | Fix Priority |
|---|------|------|-------|-------------|
| 6 | SKILL.md | 69 | Pinterest listed in example but not a supported platform | **Low** |
| 7 | post.py | 200 | Complex nested ternary dispatch is fragile | **Low (refactor)** |
| 8 | social-poster.py | 353 | store:facebook/threads/youtube documented as planned | **N/A** |
