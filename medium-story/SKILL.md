---
name: medium-story
description: "Full Medium article pipeline using native Hermes tools. Research → write → 4 parallel output agents → HTML conversion → git commit/push."
tags: [writing, medium, linkedin, youtube, content, publishing, technical, blog]
platforms: [linux]
related_skills: [short-videos, technical-writing]
---

# Medium Story — Hermes-Native Article Pipeline

Research, write, and publish technical Medium articles using Hermes tools directly. **No tmux, no Claude Code CLI, no external agent dependencies.**

## Prerequisites

Before using this skill, ensure you have:

- **Hermes Agent** installed and configured
- A **Git repository** for your Medium articles (can be private or public)
- A **Medium account** with RSS feed enabled
- (Optional) A **GitHub personal access token** (`$GH_TOKEN`) for unauthenticated API rate-limit bypass during research
- **Python 3** with standard library (for HTML conversion, stats parsing)
- `git` installed and configured for push access to your repo

## Configuration Variables

Set these in your environment before running the pipeline, or document them in a `.env` file at your repo root:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{MEDIUM_REPO_PATH}}` | Absolute path to your local Medium articles Git repository | `/home/user/Medium-Articles` |
| `{{GITHUB_REPO_URL}}` | HTTPS clone URL of your Medium articles repo | `https://github.com/your-username/Medium-Articles.git` |
| `{{MEDIUM_RSS_FEED_URL}}` | RSS feed URL for your Medium publication | `https://your-username.medium.com/feed` |
| `{{MEDIUM_USERNAME}}` | Your Medium publication username | `your-username` |
| `{{STORY_NUMBER}}` | Auto-incremented sequential story number (set by pipeline) | `42` |
| `{{STORY_SLUG}}` | URL-friendly slug derived from the article title | `why-your-mfa-does-not-help` |
| `{{GH_TOKEN}}` | (Optional) GitHub personal access token for API rate-limit bypass | `ghp_xxxxxxxxxxxxxxxxxxxx` |
| `{{REPO_ROOT}}` | Root of the Hermes-Skills repository (for skill development) | `/home/user/Hermes-Skills` |
| `{{SKILLS_DIR}}` | Path to the Hermes skills directory | `/home/user/.hermes/profiles/default/skills` |
| `{{PUBLISHED_AUTHOR}}` | Your byline as it should appear on articles | `Your Name` |
| `{{PERSONA_FILE}}` | Path to your persona prompt file | `templates/persona-template.md` |
| `{{CACHE_PATH}}` | Path to the medium feed cache XML | `{{MEDIUM_REPO_PATH}}/medium_feed_cache.xml` |

## Outputs Produced

| File | Format | Agent |
|------|--------|-------|
| `medium-story.md` | Markdown (2,500+ words) | Writer agent |
| `revisor-fact-check-report.md` | Markdown | Revisor agent (parallel) |
| `video-script.md` | Markdown (90s HeyGen script) | HeyGen agent (parallel) |
| `linkedin-post.md` | Markdown → HTML | LinkedIn agent (parallel) |
| `youtube-script.md` | Markdown (8-12min screencast) | YouTube agent (parallel) |
| `medium-story.fragment.html` | HTML (bare, for Medium CMS) | `md_to_html.py` |
| `medium-story.full.html` | HTML (styled standalone) | `md_to_html.py` |
| `linkedin-post.fragment.html` | HTML (bare) | `md_to_html.py` |
| `linkedin-post.full.html` | HTML (styled standalone) | `md_to_html.py` |

## Repository Conventions

- **Repo path:** `{{MEDIUM_REPO_PATH}}`
- **Published stories:** `published_stories/NN_slug/`
- **Unpublished stories:** `unpublished_stories/NN_slug/`
- **Root files:** `CLAUDE.md`, `{{PERSONA_FILE}}`, `published_index.md`, `md_to_html.py`, `medium_feed_cache.xml`
- **Story numbering:** Sequential, auto-incremented from highest existing folder number across both `published_stories/` and `unpublished_stories/`

---

## Pipeline Steps

### Step 1: Sync the repo

```bash
terminal(command="git -C {{MEDIUM_REPO_PATH}} pull --ff-only origin main", timeout=30)
```

If the repo doesn't exist locally, clone it:
```bash
terminal(command="git clone {{GITHUB_REPO_URL}} {{MEDIUM_REPO_PATH}}", timeout=60)
```

### Step 2: Cross-reference — detect newly published stories

Before writing anything new, check if any `unpublished_stories/` folders have gone live on Medium.

**2a. Read the RSS feed cache:**
Read `{{CACHE_PATH}}` — extract all `<title>` values. These are the 10 most recently published story titles.

If the cache file is missing or stale (heartbeat older than 36 hours), fetch live:
```bash
terminal(command="curl -s {{MEDIUM_RSS_FEED_URL}} 2>/dev/null | grep -oP '(?<=<title>)(.*?)(?=</title>)' | tail -n +2")
```

**2b. Load the published index:**
Read `published_index.md` — the running list of all known published stories.

**2c. Scan `unpublished_stories/`:**
For each folder in `unpublished_stories/`:
- Find the main story file (try: `medium-story.md`, `MEDIUM_STORY.md`, `*draft*.md`, `article-final.md`, `article.md`, `story.md`)
- Extract the H1 title
- If that title appears in either the RSS feed titles OR `published_index.md`, the story has gone live
- Move the folder: `terminal(command="git -C {{MEDIUM_REPO_PATH}} mv unpublished_stories/FOLDER published_stories/FOLDER")`
- Append a row to `published_index.md`

**2d. Commit any movements:**
```bash
terminal(command="cd {{MEDIUM_REPO_PATH}} && git add published_index.md published_stories/ unpublished_stories/ && git commit -m 'chore: move newly published stories to published_stories/' && git push", timeout=30)
```
Skip if nothing moved.

### Step 3: Read context files and find next story number

Read these files:
- `CLAUDE.md` from repo root — project-level instructions
- `{{PERSONA_FILE}}` from repo root — writer persona

Find the next story number:
```bash
terminal(command="ls {{MEDIUM_REPO_PATH}}/published_stories/ {{MEDIUM_REPO_PATH}}/unpublished_stories/ 2>/dev/null | grep -E '^[0-9]+_' | sed 's/_.*//' | sort -n | tail -1")
```
Next = that value + 1.

Read the most recently published story's `medium-story.md` as a format reference.

### Step 4: Run research

Spawn a research subagent via `delegate_task` with the topic, repo path, and persona. Use the **parallel multi-source research methodology** below rather than a single generic search.

#### Research Methodology: Parallel Multi-Source Web Research

When browser tools are unavailable (common on VPS/headless environments), use this curl-based parallel pattern for authoritative, verifiable research.

**Phase 1 — Ecosystem discovery via HN Algolia API**

The HN Algolia API returns community-vetted sources (highest-point posts correlate with quality and credibility):

```bash
# Discovery: find stories on the topic
curl -sL "https://hn.algolia.com/api/v1/search?query=<topic+keywords>&tags=story&hitsPerPage=10" -o /tmp/hn-discovery.json

# Get details + comments on a specific discussion
curl -sL "https://hn.algolia.com/api/v1/items/<OBJECTID>" -o /tmp/hn-item.json
```

Fire 3-5 facet-shifted queries in parallel (broad topic, specific tool, adjacent trend, critical/contrarian angle). Parse with python3 reading from the saved file.

**Phase 2 — Statistics via GitHub API**

For every tool, framework, or project mentioned in research, pull live ecosystem metrics:

```bash
curl -sL "https://api.github.com/repos/OWNER/REPO" -o /tmp/gh-stats.json
python3 -c "import json; d=json.load(open('/tmp/gh-stats.json')); print(f'Stars: {d.get(\"stargazers_count\")}, Forks: {d.get(\"forks_count\")}')"

# Ecosystem breadth
curl -sL "https://api.github.com/search/repositories?q=<topic>&sort=stars&per_page=5" -o /tmp/gh-search.json
python3 -c "import json; d=json.load(open('/tmp/gh-search.json')); print(f'Total repos: {d[\"total_count\"]}'); [print(f'{i[\"full_name\"]}: {i[\"stargazers_count\"]}') for i in d['items'][:5]]"
```

**Phase 3 — Deep content extraction (browser bypass)**

For plain HTML pages (not SPAs), use curl + Python for structured extraction:

```bash
curl -sL "https://example.com/article" -o /tmp/article.html
python3 -c "
import re, html
with open('/tmp/article.html') as f: content = f.read()
text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = html.unescape(text)
text = re.sub(r'\\s+', ' ', text)
for line in text.split('. '):
    if any(kw in line.lower() for kw in ['agent', 'adopt', 'transition', 'ecosystem', 'workflow']):
        print(line[:300])
"
```

**Security scanner workaround:** Always save curl output to `/tmp/` first, then process with a separate `python3 -c` reading from the file. Piped `curl | python3` is blocked by some security scanners.

**Phase 4 — Multi-source triangulation**

Cross-reference every claim across at least 2 of these source types:
- **Primary source** (GitHub README, official docs, company blog)
- **Community signal** (HN discussion points, Show HN projects, GitHub stars)
- **Third-party analysis** (TechCrunch, industry blogs, analyst reports)
- **Ecosystem proof** (related repo counts, fork activity, ecosystem trends)

**Phase 5 — Compile research brief**

The research agent must produce a structured brief with these sections:

1. **Background Context** — History, evolution, why this matters now
2. **Key Statistics** — Tabular with source annotations (never unverified)
3. **Technical Comparisons** — Architecture diagrams (ASCII), trade-off analysis, before/after patterns
4. **"So What"** — Why infrastructure and engineering leaders should care
5. **Source List** — 5-8 authoritative URLs with descriptions (not just URLs)
6. **Notes for Article Drafting** — Tone guidance, narrative thread, potential angles

Save to the story folder as `research-brief.md`. This becomes the reference input for the writer agent in Step 6.

#### Common pitfalls in research

- **GitHub API rate limiting:** Unauthenticated requests capped at 60/hr. Authenticate with `curl -H "Authorization: Bearer $GH_TOKEN"` when doing more than a few calls.
- **Medium blocks VPS IPs:** Live feed fetches may 403. Use cached RSS feed or alternative sources.
- **HN Algolia empty results:** Simplify the query. The API is brittle with long multi-word AND queries.
- **Browser-required pages:** SPAs and paywalled pages will not work with curl. Note these as gaps rather than fabricating content.
- **Claim verification:** Never conflate vendor marketing claims with independent data. Always attribute: "the vendor says X" vs "data confirms X."
- **Research brief format:** See `templates/research-brief-template.md` for the canonical output format.

### Step 5: Create story directory

```bash
terminal(command="mkdir -p {{MEDIUM_REPO_PATH}}/unpublished_stories/{{STORY_NUMBER}}_{{STORY_SLUG}}/")
```

### Step 6: Writer agent

Spawn a writer subagent via `delegate_task` with full context including the research output.

## Writer Voice & Style Guide

This section is derived from analysing published articles — the voice patterns, sentence structures, and rhythms drawn from your body of published work, not a theoretical style guide.

### Core Voice

- **Practitioner, not pundit.** Speak from experience managing real infrastructure at scale. Reference the war stories you have.
- **British English always.** -ise not -ize, colour, favour, behaviour, defence, whilst, amongst, licence, harbour, neighbour, realise, analyse, organise, recognised.
- **Dry, understated wit.** Not forced humour. Surfaces naturally when the situation is absurd (vendor overclaiming, predictable failures).
- **Professional skepticism.** Question vendor claims. Distinguish between "I assume" and "I have verified." Call out lazy thinking directly but without aggression.
- **Leads with impact, then explains mechanism.** Never open with theory and work towards relevance — do the opposite. The human/operational consequence comes first, the technical explanation second.

### Sentence Construction

- **Complex, multi-clause sentences.** Write long, grammatically precise sentences — 25-50 words is normal. Clauses separated by commas, colons, and parenthetical qualifiers.
- **Parenthetical asides extensively used** — they add precision and personality.
- **Very few one-sentence paragraphs.** Reserved for emphasis. A one-sentence paragraph is a statement meant to land hard.
- **Paragraphs are substantial** — 4-8 sentences, 80-150 words. Dense with information. Not skimmable; designed to be read.
- **Colons used extensively** for explanation.

### Structure Patterns

- **Hook** is a strong, often single paragraph that reframes the topic or states the surprising truth. Can be 3-7 sentences long with a pay-off at the end.
- **Roadmap paragraph** follows the hook — tells the reader what the article will cover, often as a single long sentence.
- **`---` horizontal rules** separate major sections. They create natural pause points for readers.
- **Section headers** are provocative or unexpected, not generic category labels.
- **Subheadlines/bold leads** under section headers set the scene before diving in.
- **Ends with "What to Do" or "The Takeaway"** — concrete, actionable, prioritised. Not a summary. New content that synthesises and directs.
- **"Sources" section** at the very end with live hyperlinks. Not a reference list — a short list of the key documents cited, each with a brief description.

### Distinctive Phrasing Patterns

These patterns appear across body-of-work — they are fingerprints of your voice:

| Pattern | Example |
|---------|---------|
| "This is not [X]. It is [Y]." | "This is not a clever exploit of a Microsoft bug." |
| "Not because... but because..." | "Not because the finding is complex... but because it is so straightforward..." |
| "Let us be precise about this, because the nuance matters operationally" | Used when a distinction matters |
| "Read that again." | Breaks the fourth wall to emphasise — use sparingly, once per article max |
| "I have seen [X] more than I would like to admit" | Self-aware honesty about industry patterns |
| "This is the kind of [thing] that [consequence]" | "This is the kind of bug that erodes trust" |
| "I want to be unambiguous about that, because..." | Used when you want to prevent misinterpretation |
| "Someone out there, right now, [is doing X]" | Places the reader in the real-world scenario |
| "That is not a [position]. That is someone who has [experience]." | Elevates or reframes a judgement |

### What This Voice NEVER Writes

These patterns have been explicitly rejected and must NEVER appear:

- ❌ Mid-sentence dashes (em dashes or en dashes as parenthetical breaks) — use commas or parentheses
- ❌ Corporate jargon: "data estate", "uninsured liability", "measured in inconvenience"
- ❌ AI transition phrases: "Here's what matters", "What this means is", "Here's the thing", "I need you to understand something"
- ❌ Fluffy openers: "In today's digital landscape", "In an era of rapid technological change"
- ❌ Credentials-first openings: "With over 20 years of experience in infrastructure..."
- ❌ Ad-copy hooks: "Not hypothetically. In the next 60 seconds." / Emoji-lead headlines
- ❌ Paired oppositions: "measured in inconvenience" / "measured in survival" (language-model parallelism)
- ❌ "It is important to note that" — just note it
- ❌ "Furthermore", "Moreover", "Additionally" — use "And" or just continue the sentence
- ❌ American spellings — ever

### The Test

Read the dialogue aloud. If it sounds like a LinkedIn post from someone trying to sound authoritative, cut it. If it sounds like someone who just came off a conference call with a vendor who overpromised and underdelivered — that is the voice.

### Attribution / Byline Format

Use this attribution format:

> {{PUBLISHED_AUTHOR}} — *{{BYLINE_DESCRIPTION}}*

The article title should never include "Medium" (avoid "Medium story", "on Medium"). Use "article", "story", or just the hook.

### Pre-Publish Checklist

Before saving any article, run this grep check against the draft:

| Pattern | Fix |
|---------|-----|
| "delve", "tapestry", "realm", "leverage" | Replace with plain English |
| "in order to" | Replace with "to" |
| "it is worth [verb]ing" | Replace with "Let me [verb]" |
| "it is important to note that" | Delete — just say the thing |
| "Furthermore," / "Moreover," | Replace with "And" or nothing |
| "In conclusion" / "To summarize" | Delete — just end |
| "Not only... but also" | Simplify |
| "By [verb]ing..." (sentence opener) | Rephrase |
| "One of the most [adjective]" | Be specific or delete |
| "In today's [X]" / "In an era of" | Delete entirely |

The writer agent must run this checklist before returning. If any of these patterns appear, rewrite them.

Save the article to `unpublished_stories/{{STORY_NUMBER}}_{{STORY_SLUG}}/medium-story.md`. **Before saving, run the What This Voice NEVER Writes checklist against every paragraph.**

### Step 7: Run four parallel output agents

Spawn agents via `delegate_task` in **two batches** because of the `max_concurrent_children=3` limit (configurable in `config.yaml` under `delegation.max_concurrent_children`, but default is 3).

**Batch 1 (3 agents — use `delegate_task` with `tasks: [...]`):**
- Read each agent's file from the story folder after the batch completes to confirm output was written.

**Batch 2 (1 agent — separate `delegate_task` call):**
- The YouTube agent. Dispatch this immediately after Batch 1 — it does not need to wait for Batch 1's agents to finish; the two batches run concurrently. The total parallel count is 3 + 1 = 4, but they are submitted as separate calls so the system never sees more than 3 at once.

**Important:** Each agent must be told to write its output to the story folder using absolute paths. Do not rely on relative paths in subagent contexts.

#### Agent A — Revisor (`revisor-fact-check-report.md`)
- Improve the story: fix British English, remove dashes, sharpen headings
- Fact-check every statistic and claim
- Flag any unverifiable or misleading statements
- Check for mid-sentence dashes (em dashes or en dashes used as parenthetical breaks)
- Report findings as actionable items — do not rewrite the article
- **See `references/revisor-methodology.md`** for the structured fact-checking methodology: GitHub API verification patterns, grep commands for British English and Americanism detection, dash audit commands, source URL validation, and report formatting.

#### Agent B — HeyGen Script (`video-script.md`)
- 90-second teleprompter script for your HeyGen digital twin
- Timestamped blocks: `[HOOK] 00:00–00:05`, `[SETUP] 00:05–00:20`, `[INSIGHT 1] 00:20–00:40`, `[INSIGHT 2] 00:40–01:00`, `[PAYOFF] 01:00–01:20`, `[CTA] 01:20–01:30`
- Each block uses inline colons (NOT markdown tables) with four fields:
  `Spoken: <text>` — spoken word content
  `On-screen text: <text>` — max 6 words, reinforce don't duplicate
  `Stage direction: <text>` — brief physical/performance cue
  `B-roll / graphic: <text>` — practical visual suggestion
- Match the format from the `short-videos` skill exactly — the old table-format (`| **Spoken** | ... |`) is deprecated.
- Target spoken word count: 200-230 words total
- British English throughout
- No mid-sentence dashes in spoken text
- CTA must be platform-neutral (no "swipe up", no "link in bio", no "link in description" — use "full article linked below" or "follow for more")
- Include a `CAPTION (universal)` section (3-5 lines, 5 hashtags, no "link in bio") and a `THUMBNAIL CONCEPT` line after the CTA block
- **Word count verification (mandatory):** After writing, run this to confirm using the inline-colon format regex:

```bash
python3 -c "
import sys, re
text = open(sys.argv[1]).read()
blocks = re.findall(r'^Spoken:\\s*(.*?)$', text, re.MULTILINE)
total = sum(len(b.split()) for b in blocks)
print(f'Spoken word count: {total}')
for i, b in enumerate(blocks):
    print(f'  Block {i+1}: {len(b.split())} words')
if total < 200: print('TOO LOW — expand spoken sections')
elif total > 230: print('TOO HIGH — trim spoken sections')
else: print('Within target range.')
"
```

#### Agent C — LinkedIn Post (`linkedin-post.md`)
- Standalone post — NOT marketing for the article. It stands alone.
- Hook line in first sentence
- 3-6 short paragraphs, each punchy and self-contained
- 3,000 character hard limit (LinkedIn cap)
- Exactly 5 hashtags at the end
- No "link in comments" — the Medium article URL goes IN the post body
- No "watch my video" language
- British English, no mid-sentence dashes
- No tenure-based openings ("I've been in infrastructure for X years")
- End with a question or provocation that invites comments

#### Agent D — YouTube Script (`youtube-script.md`)
- 8-12 minute screencast script for recording with OBS (screen capture + webcam)
- NOT an avatar/HeyGen script — real person, real voice
- Format: conversational talking points the user can follow naturally
- Include: suggested screen content at each point, chapter markers, thumbnail concept
- YouTube SEO: title + description + tags
- British English

### Step 8: HTML conversion

```bash
terminal(command="cd {{MEDIUM_REPO_PATH}} && python3 md_to_html.py {{STORY_NUMBER}} --select medium-story,linkedin-post", timeout=30)
```

Produces (in the story folder):
- `medium-story.fragment.html` — bare HTML, paste into Medium
- `medium-story.full.html` — styled standalone page
- `linkedin-post.fragment.html` — bare HTML
- `linkedin-post.full.html` — styled standalone page

### Step 9: Commit and push

```bash
terminal(command="cd {{MEDIUM_REPO_PATH}} && git add unpublished_stories/{{STORY_NUMBER}}_{{STORY_SLUG}}/ && git commit -m 'Add story {{STORY_NUMBER}}: [topic summary]' && git push", timeout=30)
```

---

## Pitfalls

- **Feed cache staleness:** If `medium_feed_cache.xml` is older than 36 hours, fetch live. If live fetch fails (403 from Medium's datacenter block), fall back to matching against `published_index.md` titles only, and flag the staleness.
- **Story number collision:** The pipeline auto-increments from folder listings. If you manually create folders, use the next available number.
- **HTML conversion requires `md_to_html.py`** in the repo root. Verify it exists before Step 8. If missing, skip HTML conversion and report.
- **Git authentication:** If `git push` fails, the SSH key or credential helper may not be configured. Report the error — don't lose the article.
- **Mid-sentence dashes forbidden:** The revisor checks for these. Manually verify before final.
- **Infrastructure claims require live verification:** Before describing any service, container, or tool in the article, verify against live state. Run `docker ps` to check what's actually running. Check the last backup date. An incorrect infrastructure claim in the article will be spotted by technical readers and erodes trust. When in doubt, say "let me check" rather than guessing from memory.
- **Research agent context window:** For very broad topics, the research agent may produce more text than fits in context. Keep the research brief to essential findings. Pass the full research as a file read reference rather than inline text.
- **LinkedIn character count:** The 3,000 char limit is hard. The revisor checks it, but verify manually.
- **Parallel agent limit (4 tasks):** `delegate_task` has `max_concurrent_children=3` by default. You cannot dispatch all 4 agents in one call. Split into Batch A (3 agents: Revisor, HeyGen, LinkedIn) and Batch B (1 agent: YouTube). Both batches run concurrently — the system sees 3 + 1 across two calls, never 4 at once.
- **Diagram PNG export for articles:** If the article references Excalidraw diagrams, the `#json=` URLs from excalidraw.com do not render inline in Medium. After generating the `.excalidraw` file, render it to a transparent-background PNG using the `design` skill's `scripts/render_excalidraw.py`, place the PNG in the story folder, and use `[*FILENAME.png*]` as a placeholder that the user replaces with uploaded images when publishing.

## References

- `references/medium-feed-cache.md` — RSS feed cache architecture, health-check, live fallback, and cron installation. Consult when the cache is missing, stale, or returning unexpected results.
- `references/revisor-methodology.md` — Structured fact-checking methodology for the Revisor agent. Covers GitHub API verification, grep-based British English/Americanism/dash auditing, source URL validation, valuation cross-referencing, and report formatting. Load when fact-checking any article or claim.
- `references/session-63-claude-code-commands-research.md` — Worked example: complete research brief for a pipeline migration topic. Demonstrates the research methodology format.
- `templates/research-brief-template.md` — Canonical output format for the research brief produced in Step 4. Use this as the structure reference when writing `research-brief.md`.
- `templates/persona-template.md` — Persona prompt template. Customise this to match your writing voice and then reference it in your CLAUDE.md or Hermes configuration.
