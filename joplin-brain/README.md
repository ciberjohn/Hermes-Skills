# joplin-brain

A **Hermes Agent** skill that turns a Joplin notebook into a self-filing second brain: capture anything into INBOX in under ten seconds, file it on a schedule with a deterministic classifier, and answer questions with grounded retrieval from your own notes.

## What It Does

- **CAPTURE** — saves links, text, thoughts, and files into a Joplin `INBOX` folder with source + timestamp metadata, via the Joplin REST API. Under ten seconds, zero filing decisions.
- **FILER** — a deterministic classifier scores each INBOX note against your existing folder names and moves confident matches (`>= 0.5`) into place, tagging low-confidence items `needs-review`. Dry-run by default; audit trail written to `__SYSTEM/FILER LOG`.
- **ASK** — grounded retrieval: searches your corpus, reads the top matches, answers with note titles attached. Never invents sources.
- **AGENT LOG** — the notebook doubles as the agent's readable memory archive: append-only session digests in `__SYSTEM/AGENT LOG`, newest first.

## Quick Install

Copy and paste this to your Hermes agent (any profile):

```text
Install the joplin-brain skill into my Hermes agent. Clone
https://github.com/ciberjohn/Hermes-Skills and copy joplin-brain/SKILL.md into
~/.hermes/skills/productivity/joplin-brain/SKILL.md, the contents of
joplin-brain/references/ into .../references/, and the contents of
joplin-brain/scripts/ into .../scripts/. Create the subdirectories if they
don't exist. Then ask me:
1. What is the Git URL of the repo where I keep my Joplin scripts?
2. Where should I clone it on disk?
Store my answers, then verify Joplin's REST API is reachable
(python3 scripts/joplin_client.py ping) and show me an example:
'capture this link into my second brain'.
```

## Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com) — the skill engine.
- **Joplin** with the REST API enabled (`joplin server start`, or the web clipper server running). Token in `~/.config/joplin/settings.json` under `api.token`.
- **Python 3** for the bundled scripts.
- An `INBOX` folder in Joplin (the capture script creates it automatically if missing).

## Installation

1. Place the skill directory inside your Hermes skills path:
   ```
   ~/.hermes/skills/productivity/joplin-brain/
   ```
2. Set the configuration variables (or answer the install prompt):

   ```yaml
   # ~/.hermes/profiles/default.yaml  (or your active profile)
   skills:
     joplin-brain:
       SECOND_BRAIN_REPO_URL: "https://github.com/you/second-brain.git"
       SECOND_BRAIN_REPO_PATH: "/home/you/second-brain"
   ```

3. Verify the REST API is reachable (token read in-process, not on the command line):
   ```bash
   python3 ~/.hermes/skills/productivity/joplin-brain/scripts/joplin_client.py ping
   # → JoplinClipperServer
   ```

## Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SECOND_BRAIN_REPO_URL` | Yes | Git URL of the repo holding your Joplin scripts | `https://github.com/you/second-brain.git` |
| `SECOND_BRAIN_REPO_PATH` | Yes | Absolute path to the local clone of that repo | `~/second-brain` |
| `JOPLIN_SETTINGS_PATH` | No | Path to Joplin's `settings.json` (default `~/.config/joplin/settings.json`) | `~/.config/joplin/settings.json` |
| `JOPLIN_API_PORT` | No | REST API port (default `41184`) | `41184` |

If you do not have a scripts repo yet, the bundled `scripts/` directory contains everything needed — copy it to `SECOND_BRAIN_REPO_PATH/scripts/` and point the variable at your clone.

## Expected Directory Structure

```
joplin-brain/
├── SKILL.md                 # Skill instructions (this skill)
├── README.md                # This file
├── .gitignore
├── references/
│   ├── joplin-rest-api.md       # REST API cheat sheet
│   ├── html-pack-conversion.md  # HTML → Joplin Markdown conversion
│   └── article-extraction.md    # Article → knowledge note recipe
└── scripts/
    ├── joplin_client.py         # REST API wrapper (CLI + library)
    ├── joplin_capture.py        # Capture into INBOX
    ├── joplin_filer.py          # Deterministic folder classifier
    ├── joplin_ask.py            # Grounded retrieval
    ├── joplin_agent_log.py      # Append-only agent memory log
    └── html_pack_to_markdown.py # Styled HTML → Markdown converter
```

## How to Use

Say things like:

- "Save this link to my second brain" (CAPTURE → INBOX)
- "Search my notes for what I know about X" (ASK, grounded)
- "How is my brain doing?" (FILER dry-run status)
- "Log what we did this session" (AGENT LOG)

The daily FILER run is typically scheduled via Hermes cron (07:00), with a thin wrapper script so the cron stays script-only. The wrapper lives in the profile scripts dir, so it must `cd` to the repo scripts dir explicitly:

```bash
#!/bin/sh
cd /home/you/second-brain/scripts   # {{SECOND_BRAIN_REPO_PATH}}/scripts
exec python3 joplin_filer.py --apply
```

## Customising

- **Filing threshold** — adjust `--min-score` (default `0.5`); lower files more aggressively, higher leaves more in INBOX for review.
- **Folders** — the skill creates `INBOX` (on first capture) and `__SYSTEM` (on first FILER/AGENT LOG run); it files into whatever folders you already have. If a cron runs before any capture, `joplin_filer.py` errors with "INBOX not found" — run one capture first.
- **Sync** — works with any Joplin sync target (Dropbox, Nextcloud, S3, filesystem). Notes created via the REST API reach other devices on the next Joplin sync cycle.

## Development

The main logic lives in `SKILL.md` as a structured Hermes skill definition. Scripts are plain Python 3 with no third-party dependencies (stdlib only). The `.gitignore` prevents committing local state.

## Licence

MIT — see [LICENSE](../LICENSE) in the repository root.
