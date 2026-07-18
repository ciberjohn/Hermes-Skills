---
name: short-videos
description: "Produce 90-second universal short-video scripts (HeyGen / Instagram Reels / LinkedIn Video / YouTube Shorts) and standalone LinkedIn posts using native Hermes tools. No Claude Code dependency."
version: 1.2.0
author: Hermes Agent Skill Template
tags: [video, linkedin, social-media, content, short-form, heygen]
platforms: [linux]
related_skills: [medium-story, technical-writing]
---

# Short Videos — Hermes-Native Video Script Pipeline

Produce a 90-second universal short-video script and standalone LinkedIn post using Hermes tools directly. **No tmux, no Claude Code CLI.**

## Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `{{REPO_ROOT}}` | *(required)* | Path to your Git repository root, e.g. `/home/user/projects/my-content-repo` |
| `{{RP_VIDEO_DIR}}` | `{{REPO_ROOT}}/short_videos` | Directory holding numbered video folders under the repo root |

Before running the pipeline, set `{{REPO_ROOT}}` to your actual content repository path. All file operations reference this variable — never hardcode absolute paths.

## Prerequisites

- **Hermes Agent** (runtime environment)
- **Git repo** (your content repository — clone it to `{{REPO_ROOT}}`)
- **GitHub / Git remote** configured for push
- **HeyGen** (optional) — scripts are HeyGen-ready but work on any teleprompter platform
- Python 3 for word-count verification

## When to Use

- User says "create a short video about..." or "make a reel on..."
- User wants a LinkedIn post that stands alone (not marketing for a video or article)
- User needs a HeyGen script for their digital twin

## Outputs Produced

| File | Format | Description |
|------|--------|-------------|
| `video-script.md` | Markdown (90s, timestamped blocks) | Universal teleprompter script for HeyGen/Reels/Shorts/LinkedIn Video |
| `linkedin-post.md` | Markdown | Standalone LinkedIn post (no article link, ≤3,000 chars, 5 hashtags) |
| `quality-report.md` | Markdown | Fact-check, word count, British English, hook strength, character count |

## Repo & Conventions

- **Repo path:** `{{REPO_ROOT}}`
- **Video folders:** `{{RP_VIDEO_DIR}}/NN_slug/` — numbered sequentially, zero-padded to 2 digits (01, 02, 03...)
- **Root files:** `CLAUDE.md` (project instructions), `techblogger.md` (writer persona), `md_to_html.py`
- **Sibling pipeline:** `medium-story` writes to `unpublished_stories/` — this pipeline writes to `{{RP_VIDEO_DIR}}/` in the same repo

## Pipeline Steps

### Step 1: Sync the repo

```bash
terminal(command="git -C {{REPO_ROOT}} pull --ff-only origin main", timeout=30)
```

### Step 2: Read context files and find next video number

Read these files from the repo root:
- `CLAUDE.md` — project-level instructions
- `techblogger.md` — writer persona

Find the next video number:
```bash
terminal(command="ls {{RP_VIDEO_DIR}}/ 2>/dev/null | grep -E '^[0-9]+_' | sed 's/_.*//' | sort -n | tail -1")
```
If the folder doesn't exist yet, start at `01`. Otherwise next = that value + 1, zero-padded to 2 digits.

### Step 3: Research the topic

Spawn a research subagent via `delegate_task`. The research must produce:
- **One sharp angle / thesis** — the single most provocative or useful truth about this topic
- **3-5 concrete facts or statistics** (UK/EU sources preferred; US only where no EU equivalent exists)
- **One real-world example or incident** that makes the abstract tangible
- **Quotable phrasing candidates** — short, punchy, tweetable sentences
- **Audience relevance** — why does this matter right now to infrastructure and security professionals?

### Step 4: Create video directory

```bash
terminal(command="mkdir -p {{RP_VIDEO_DIR}}/NN_slug/")
```

### Step 5: Run three parallel agents

Use `delegate_task` with `tasks: [...]` to spawn all three simultaneously. Pass research context to each.

#### Agent A — Universal Video Script (`video-script.md`)

Write a 90-second teleprompter script for the presenter's HeyGen digital twin, designed for:
- **Instagram Reels** (9:16, vertical, mobile-first, caption-dependent viewers)
- **LinkedIn Video** (square or 9:16, professional audience, often watched muted)
- **YouTube Shorts** (9:16, vertical, algorithm-driven discovery)

**Script structure — use exactly this format:**

```markdown
TOPIC: [topic name]
SPOKEN WORD COUNT TARGET: 200–230 words
PLATFORMS: Instagram Reels · LinkedIn Video · YouTube Shorts

---

[HOOK] 00:00–00:05
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[SETUP] 00:05–00:20
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[INSIGHT 1] 00:20–00:40
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[INSIGHT 2] 00:40–01:00
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[PAYOFF] 01:00–01:20
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[CTA] 01:20–01:30
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

---

CAPTION (universal — use for all three platforms):
[3-5 lines: hook, core insight, 5 hashtags. No "link in bio".]

THUMBNAIL CONCEPT:
[One sentence describing a still frame that works as a cover image across all platforms.]
```

**Script rules:**
- Hook lands within the first 3 seconds — bold claim, provocative question, or counterintuitive fact
- Spoken text must sound natural read aloud at steady pace — no bullet points, no headers, no jargon dumps
- On-screen text: max 6 words per frame — reinforce spoken word, don't duplicate verbatim
- Stage directions: brief cues (e.g. "lean forward slightly", "pause for emphasis")
- B-roll/graphic: practical suggestions (e.g. "terminal output animation", "NCSC logo fade in")
- British English throughout
- No mid-sentence dashes — use commas, colons, or semicolons
- No fluffy openers — do not start with "I've been in infrastructure for X years"
- End CTA must be platform-neutral — no "swipe up", no "link in bio". Use "follow for more", "drop a comment", or "save this one"

**Word count verification (mandatory after each draft):**
After writing the script, extract and count the spoken words to verify the total is within 200–230:

```bash
python3 -c "
import sys, re
text = open(sys.argv[1]).read()
# Match 'Spoken: <text>' lines in inline-colon format
blocks = re.findall(r'^Spoken:\\s*(.*?)$', text, re.MULTILINE)
total = sum(len(b.split()) for b in blocks)
print(f'Spoken word count: {total}')
if total < 200: print('TOO LOW — expand spoken sections')
elif total > 230: print('TOO HIGH — trim spoken sections')
else: print('Within target range.')
"
```

Run this after every edit to the spoken text until the count is between 200 and 230. Do not guess — verify.

#### Agent B — LinkedIn Post (`linkedin-post.md`)

Write a standalone LinkedIn post — **not** marketing for a video or article. It stands alone as a piece of insight content.

- Hook line: must stop the scroll in the first sentence
- Body: 3-6 short paragraphs, each punchy and self-contained
- No "link in comments" — there is no link
- No "watch my video" language — this post exists independently
- 3,000 character hard limit (LinkedIn cap) — count carefully
- End with a question or provocation that invites comments
- Exactly 5 hashtags at the end
- British English, no mid-sentence dashes
- Do not open with "I've been in infrastructure for X years" or any years-of-experience framing

#### Agent C — Quality Check (`quality-report.md`)

Review both `video-script.md` and `linkedin-post.md` once drafted, producing a report covering:

1. **Fact accuracy** — verify each statistic and claim; flag anything unverifiable or misleading
2. **Spoken word count** — count spoken sections of video script; flag if outside 200-230 words
3. **Timing sense-check** — does script feel paced correctly for 90 seconds at natural speech rate?
4. **British English** — flag any Americanisms
5. **Dash check** — flag any mid-sentence em dashes or en dashes used as parenthetical breaks
6. **LinkedIn character count** — report exact count and flag if over 3,000
7. **Hook strength** — rate the video hook and LinkedIn hook on 1-5 scale with reasoning
8. **CTA check** — confirm video CTA contains no platform-specific mechanics

If issues found, list as actionable items. Do not rewrite the files — report only.

### Step 6: Commit and push

```bash
terminal(command="cd {{REPO_ROOT}} && git add {{RP_VIDEO_DIR}}/NN_slug/ && git commit -m 'Add short video NN: [topic summary]' && git push", timeout=30)
```

Always push. Never leave new video content uncommitted.

## Writer Voice & Style Guide

This section is derived from analysing a practitioner's published work across multiple platforms. The patterns below describe what the voice actually sounds like — not a theoretical style guide.

### Core Voice

- **Practitioner, not pundit.** Speaks from experience managing real infrastructure at scale.
- **British English always.** -ise not -ize, colour, favour, behaviour, defence, whilst, amongst, licence, harbour, realise, analyse.
- **Dry, understated wit.** Surfaces naturally when the situation is absurd. "The catch, in this case, is that there is not one." / "I collect them the way people collect gym memberships: with great optimism and almost zero follow-through."
- **Leads with impact, then explains mechanism.** The human/operational consequence first, the technical explanation second.

### Short Video Script Voice (90 seconds, spoken)

Because the short video format compresses everything, the voice translates differently:

- **Hook lands by reframing or surprising.** Not a question. Not a clickbait opener. A short, sharp statement of the unexpected truth.
- **Sentences are shorter than in articles but maintain the same rhythm.** 15-25 words spoken per sentence. Still precise. Still British English. Still no filler.
- **"Here is the thing" / "Here is what matters"** are still banned. Say the thing. Don't announce you're about to say it.
- **End CTA is direct and platform-neutral:** "Follow for more." / "Drop a comment." / "Save this one." Never "swipe up", never "link in bio."

### LinkedIn Post Voice (standalone)

- **Opens like telling a colleague what happened.** "Ran the NCSC exercise with Rui this week." / "Microsoft Edge decrypts every single saved password the moment it launches."
- **No emoji-headlines.** No "🛑 What would you do if...?" — that's ad copy, not the writer's voice.
- **3-6 short paragraphs, each punchy.** 3,000 character hard limit. Every sentence earns its place.
- **No "with over 20 years of experience"** framing — authority comes from the content, not the opener.
- **Ends with a question or provocation** that invites comments.
- **Exactly 5 hashtags.**

### What NEVER Appears

- ❌ Mid-sentence dashes (em dashes, en dashes) — use commas or parentheses
- ❌ AI transition phrases: "Here's what matters", "What this means is", "Here's the thing"
- ❌ Corporate jargon: "data estate", "operational reality", "measured in inconvenience"
- ❌ Fluffy openers: "In today's digital landscape"
- ❌ Credentials-first: "With over 20 years of experience..."
- ❌ Ad-copy hooks: "Not hypothetically. In the next 60 seconds."
- ❌ Paired oppositions (language-model parallelism)
- ❌ American spellings — ever
- ❌ "It is important to note that" — just note it
- ❌ "Furthermore", "Moreover", "Additionally" — use "And"

### The Test

Read it aloud. If it sounds like a LinkedIn post from someone trying to sound authoritative, cut it. If it sounds like someone who just got off a call with a vendor who overpromised and underdelivered — that is the voice.

### Pre-Publish Checklist

Before saving any script or LinkedIn post, run this check:

| Pattern | Fix |
|---------|-----|
| "delve", "tapestry", "realm", "leverage" | Replace with plain English |
| "in order to" | Replace with "to" |
| "it is worth [verb]ing" | Replace with "Let me [verb]" |
| "it is important to note that" | Delete |
| "Furthermore," / "Moreover," | Replace with "And" or nothing |
| "Not only... but also" | Simplify |
| "By [verb]ing..." (sentence opener) | Rephrase |
| "One of the most [adjective]" | Be specific or delete |
| "In today's [X]" / "In an era of" | Delete entirely |
| Contractions missing | Add don't/won't/it's/can't |

Run this checklist before returning. If any pattern appears, rewrite.
- **Authority** comes from tone and insight, not from stating credentials

## Pitfalls

- **Research agents may fabricate statistics.** The quality check agent catches these — trust but verify. The quality report is a genuine check, not a rubber stamp.
- **LinkedIn post is standalone.** No "link in bio/description" CTA. The quality agent enforces this.
- **Video script CTA must be platform-neutral.** No "swipe up", no "link in bio". Use "follow for more", "drop a comment", "save this one".
- **Spoken word count target is 200-230 words.** Shorter scripts feel rushed or sparse; longer scripts exceed 90 seconds at natural speech rate.
- **Hook must land within 3 seconds.** Vertical video viewers decide whether to watch in the first 1-2 seconds. The hook is the single most important element.
- **Git authentication:** If `git push` fails, report the error. The files exist locally — don't lose them.
- **Delegate_task context limits:** For the video script agent especially, the output format is very specific. Include the full script template in the context to ensure correct structure.
