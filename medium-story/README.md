# medium-story — Hermes Agent Skill

Generate full Medium article packages from a single topic prompt: article in markdown, 90-second HeyGen video script, LinkedIn post, YouTube screencast script, fact-check report, and HTML versions ready for publishing.

## Prerequisites

- **Hermes Agent** — installed and configured (`pip install hermes-agent` or via [Nous Research](https://hermes-agent.nousresearch.com))
- **GitHub repository** — for your Medium articles, structured as `unpublished_stories/` and `published_stories/`
- **Medium account** — to publish the output
- **Python 3** — for the HTML conversion script (`markdown` library required)

## Installation

1. Copy `SKILL.md` to your Hermes skills directory:
   ```bash
   cp medium-story/SKILL.md ${SKILLS_DIR:-~/.hermes/profiles/default/skills/creative}/medium-story/SKILL.md
   ```

2. Configure the variables at the top of `SKILL.md`:
   - `{{MEDIUM_REPO_PATH}}` — absolute path to your Medium articles repo
   - `{{MEDIUM_REPO_URL}}` — Git remote URL
   - `{{PERSONA_FILE}}` — path to your persona template (see `templates/persona-template.md`)
   - `{{MD_TO_HTML_SCRIPT}}` — path to `scripts/md_to_html.py`
   - `{{SECRETS_FILE}}` — path to your env vars file (if any)

3. Copy the supporting files:
   ```bash
   cp templates/persona-template.md {{PERSONA_FILE}}
   cp scripts/md_to_html.py /your/repo/path/
   ```

4. Create the directory structure in your repo:
   ```
   your-medium-repo/
   ├── unpublished_stories/
   ├── published_stories/
   ├── published_index.md
   ├── medium_feed_cache.xml
   └── logs/
   ```

5. Install Python dependencies:
   ```bash
   pip install markdown
   ```

## Configuration Variables

Edit the top of `SKILL.md` to set:

| Variable | Purpose | Example |
|----------|---------|---------|
| `MEDIUM_REPO_PATH` | Absolute path to your Medium repo | `/home/user/Medium-Articles` |
| `MEDIUM_REPO_URL` | Git remote URL | `github.com/user/Medium-Articles.git` |
| `PERSONA_FILE` | Path to your writing persona | `/home/user/persona.md` |
| `MD_TO_HTML_SCRIPT` | Path to the HTML converter | `{MEDIUM_REPO_PATH}/md_to_html.py` |
| `STORY_NUMBER` | Set automatically by the skill | — |

## How It Works

The skill executes a 9-step pipeline:

1. **Sync repo** — pulls latest from Git
2. **RSS cross-reference** — checks published stories against Medium's RSS feed cache
3. **Read context** — loads persona, finds next story number
4. **Research** — spawns a subagent to research the topic
5. **Create directory** — creates `unpublished_stories/NN_slug/`
6. **Write** — subagent produces the article
7. **4 parallel agents** — Revisor, HeyGen Script, LinkedIn Post, YouTube Script
8. **HTML conversion** — runs `md_to_html.py`
9. **Git commit** — commits and pushes everything

## Output Files

Each story produces:

| File | Description |
|------|-------------|
| `medium-story.md` | Full article in markdown |
| `medium-story.fragment.html` | Paste-ready HTML for Medium |
| `medium-story.full.html` | Full-page HTML preview |
| `video-script.md` | 90-second HeyGen teleprompter script |
| `linkedin-post.md` | Standalone LinkedIn post (≤3,000 chars, 5 hashtags) |
| `youtube-script.md` | 8-12 minute screencast script with OBS notes |
| `revisor-fact-check-report.md` | Fact-check, spelling, and quality report |

## Writing Voice

The skill uses a writing voice defined in your persona file. The included `templates/persona-template.md` provides a starting point with:

- Core voice guidelines (direct, practitioner, British English)
- Pre-publish checklist (10 categories of AI-typical language to avoid)
- Configuration fields for your personal style, title, and experience

## Security Notes

- Never hardcode tokens or secrets in the skill file — use environment variables
- The skill references variables for paths, not absolute system paths
- Review the pre-publish checklist before publishing to ensure authentic voice

## Example

```bash
# Tell your Hermes agent:
"Write a Medium article about why SSH key management still fails in 2026"

# The agent loads the medium-story skill and runs the full pipeline.
# 5-10 minutes later, everything is committed to your repo.
```

## License

MIT — use freely, adapt as needed.
