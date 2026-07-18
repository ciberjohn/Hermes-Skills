# Medium Feed Cache

> Referenced by `medium-story/SKILL.md` in Step 2 (RSS cross-reference).
> **CUSTOMISE** — Update the paths and URLs for your setup.

## Overview

Medium blocks cloud IP ranges. To work around this, fetch the RSS feed from a residential machine and commit it to the repo. The Hermes agent reads from the local cache file rather than fetching live.

## Cache File

`medium_feed_cache.xml` at the repo root — a local copy of `https://medium.com/feed/@{{YOUR_USERNAME}}`.

## Cron Installation (Residential Machine)

```bash
0 6 * * * /path/to/your/repo/fetch_medium_feed.sh >> /path/to/your/repo/logs/feed_cache.log 2>&1
```

## Health Check

```bash
# Is the cache present?
[ -f medium_feed_cache.xml ] || echo "MISSING: cache not committed"

# When did the cron last run?
[ -f logs/feed_cache_last_run.txt ] && cat logs/feed_cache_last_run.txt
```

## Parse Titles

```bash
grep "<title>" medium_feed_cache.xml | sed 's|.*<title>||;s|</title>.*||' | tail -n +2
```

## Fallback

If the cache is missing or stale, match against `published_index.md` titles only. Do not skip the RSS comparison silently.
