# Short Videos — Hermes-Native Video Script Pipeline

Automate the creation of 90-second short-form video scripts for HeyGen, Instagram Reels, LinkedIn Video, and YouTube Shorts — along with standalone LinkedIn posts and quality reports — using a 6-step pipeline in Hermes Agent.

## What It Does

Given a topic, this skill produces three deliverables in a single pipeline run:

1. **Universal video script** (`video-script.md`) — a 90-second teleprompter script with 6 timestamped blocks, platform-neutral CTA, and word count target of 200–230 spoken words.
2. **Standalone LinkedIn post** (`linkedin-post.md`) — insight content that exists independently, not as marketing for a video. ≤3,000 characters, 5 hashtags.
3. **Quality report** (`quality-report.md`) — fact-check, word count verification, British English audit, hook strength rating, and CTA compliance.

All outputs are British English, practitioner-voiced, and platform-neutral.

## Prerequisites

- **Hermes Agent** — installed and configured on a Linux system
- **Git repository** — a content repo cloned locally (e.g. a Medium Articles and Stories repo)
- **Python 3** — for automated word-count verification of spoken sections
- **Git remote** — configured with push access (GitHub, GitLab, etc.)
- **HeyGen** (optional) — scripts are HeyGen digital-twin ready but work with any teleprompter

## Installation

### 1. Clone or create the content repository

```bash
# If you already have a content repo:
git clone <your-repo-url> /path/to/your-repo

# Set the repo root for this skill:
export REPO_ROOT=/path/to/your-repo
```

### 2. Place the skill files

Copy the contents of this directory into your Hermes Agent skills directory:

```bash
cp -r short-videos/ ${HOME}/.hermes/profiles/spock/skills/creative/
```

Or symlink for live development:

```bash
ln -s /path/to/Hermes-Skills/short-videos ${HOME}/.hermes/profiles/spock/skills/creative/short-videos
```

### 3. Enable the skill in Hermes

```bash
hermes skills enable short-videos
```

### 4. Set environment variables

Add these to your Hermes profile config or shell profile:

```bash
export REPO_ROOT=/path/to/your-content-repo
```

## Configuration Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `{{REPO_ROOT}}` | Yes | — | Absolute path to your Git content repository |
| `{{RP_VIDEO_DIR}}` | No | `{{REPO_ROOT}}/short_videos` | Directory under the repo root for video folders |

Set `{{REPO_ROOT}}` in your Hermes profile configuration or as an environment variable before running the pipeline.

## Expected Directory Structure

```
{{REPO_ROOT}}/
├── CLAUDE.md                  # Project-level instructions (optional)
├── techblogger.md             # Writer persona (optional)
├── md_to_html.py              # Utility (optional)
├── unpublished_stories/       # Medium story articles (sibling pipeline)
└── short_videos/              # Video content directory ({{RP_VIDEO_DIR}})
    ├── 01_first-topic/
    │   ├── video-script.md
    │   ├── linkedin-post.md
    │   └── quality-report.md
    ├── 02_second-topic/
    │   ├── video-script.md
    │   ├── linkedin-post.md
    │   └── quality-report.md
    └── ...
```

Each video folder is numbered sequentially, zero-padded to 2 digits (`01_`, `02_`, etc.), and named with a slug describing the topic.

## Output Files

### `video-script.md`

A universal teleprompter script structured as 6 timestamped blocks:

| Block | Time | Purpose |
|-------|------|---------|
| HOOK | 00:00–00:05 | Grab attention within 3 seconds |
| SETUP | 00:05–00:20 | Establish context and relevance |
| INSIGHT 1 | 00:20–00:40 | Core fact or argument |
| INSIGHT 2 | 00:40–01:00 | Second supporting point |
| PAYOFF | 01:00–01:20 | Synthesise and drive the point home |
| CTA | 01:20–01:30 | Platform-neutral call to action |

Each block contains: spoken text, on-screen text overlay, stage direction, and B-roll/graphic suggestions.

### `linkedin-post.md`

A standalone, insight-driven LinkedIn post. Not marketing for the video. 3-6 short paragraphs, 3,000 character limit, exactly 5 hashtags, ending with a question or provocation.

### `quality-report.md`

A review of both script and post covering: fact accuracy, word count, timing, British English, dash usage, character count, hook strength (1–5 rating), and CTA compliance. Lists actionable issues only — does not rewrite the files.

## Pipeline Overview

```
Step 1: git pull the repo
Step 2: Read context files, determine next video number
Step 3: Research topic via delegate_task (angle, facts, example, quotes)
Step 4: mkdir -p short_videos/NN_slug/
Step 5: Spawn 3 parallel agents:
         ├── Agent A: video-script.md (90s, 200-230 words, 6 blocks)
         ├── Agent B: linkedin-post.md (standalone, ≤3k chars, 5 hashtags)
         └── Agent C: quality-report.md (fact-check, audit, ratings)
Step 6: git add, commit, push
```

## Writing Conventions

- **British English always.** -ise not -ize. Colour, favour, behaviour, defence.
- **No mid-sentence dashes.** Use commas, colons, or parentheses.
- **No fluffy openers.** No "In today's digital landscape", no "With over 20 years of experience".
- **No platform-specific CTAs.** No "swipe up", no "link in bio". Use "follow for more", "drop a comment", "save this one".
- **Hook lands in 3 seconds.** Vertical video is unforgiving — the first sentence is everything.
- **Spoken word count: 200–230 words.** Verified programmatically after every draft.

## Related Skills

- **medium-story** — full-length Medium article pipeline (writes to `unpublished_stories/` in the same repo)
- **technical-writing** — umbrella for content creation workflows

## License

Internal tooling — distribute and modify freely within your organisation.
