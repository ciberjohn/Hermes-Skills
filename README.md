# Hermes Skills

A growing collection of reusable Hermes Agent skills, built to be installed, extended, and adapted through natural language — no YAML, no config files, no manual directory wrangling.

**By [João Silva](https://github.com/ciberjohn)**

---

## How Installation Works (No Manual Steps)

Every skill in this repo is designed to be installed the way you would tell a colleague what to do: in natural language.

Copy one of the prompts below, paste it to your Hermes agent, and it handles the rest — cloning the repo, placing the files, and asking you the configuration questions it needs.

### Quick Install — All Skills

> "Install the Hermes Skills collection from github.com/ciberjohn/Hermes-Skills. Clone it to a local directory, then copy each skill's SKILL.md into my Hermes profiles under the appropriate category folder. For each skill, ask me to configure the path variables it needs."

### Install a Single Skill — `medium-story`

> "Install the medium-story skill from github.com/ciberjohn/Hermes-Skills. Copy the SKILL.md into my Hermes skills directory under creative/medium-story/. Then ask me where my Medium articles repo lives, where my persona file is, and what GitHub URL it should push to."

### Install a Single Skill — `short-videos`

> "Install the short-videos skill from github.com/ciberjohn/Hermes-Skills. Copy the SKILL.md into my Hermes skills directory under creative/short-videos/. Then ask me where my content repository is and where video folders should be created."

### Install a Single Skill — `excalidraw`

> "Install the excalidraw Hermes skill from github.com/ciberjohn/Hermes-Skills. Copy the SKILL.md into my Hermes skills directory, and copy python_helpers.py to a location I specify. Ask me where my excalidraw diagrams repo is and where to clone it."

### Install a Single Skill — `ai-projects`

> "Install the ai-projects Hermes skill from github.com/ciberjohn/Hermes-Skills. Copy the SKILL.md into my Hermes skills directory. Ask me for the GitHub URL of my AI projects repo and where to clone it locally."

---

## How It Works

Each skill defines a **pipeline**: a sequence of steps that your Hermes agent executes when you give it a goal. The steps use Hermes-native tools — `delegate_task` to spawn sub-agents, `write_file` to save output, `terminal` to run git commands — without external process managers, tmux sessions, or MCP servers.

When you tell your agent what you want, it loads the skill, reads the configuration, and runs the pipeline. You do not manage sessions, approve permissions, or restart stalled processes.

### Current Skills

| Skill | What it does | Pipeline |
|-------|-------------|----------|
| [medium-story](medium-story/) | Produces a full article package (markdown, video script, LinkedIn post, YouTube script, HTML) from a single topic prompt | 9 steps: sync → cross-ref → research → write → 4 parallel output agents → HTML → git |
| [short-videos](short-videos/) | Generates 90-second video scripts and standalone LinkedIn posts | 6 steps: sync → research → 3 parallel agents → git |
| [excalidraw](excalidraw/) | Creates Excalidraw diagrams as JSON files, saved to a GitHub repo | Python helpers → JSON generation → git push |
| [ai-projects](ai-projects/) | Syncs a Git repository of AI projects to a local directory | Clone → pull → status report |

---

## Prerequisites

- **Hermes Agent** — [Install from Nous Research](https://hermes-agent.nousresearch.com)
- **Git** — for version control and automated git operations
- **Python 3** — for supporting scripts (HTML conversion, diagram helpers)

Each skill's README lists its specific requirements.

---

## The Pattern

These skills follow the same architecture that runs my own fleet: a single main agent (Spock) that delegates work to specialised sub-agents, communicates through Discord webhooks, and runs on a schedule through Hermes cron. You do not need that exact setup to use the skills. They work with any Hermes profile.

The key insight is that the skill system lets you package operational knowledge as something an agent can load and follow, the same way a human engineer reads a runbook. The more skills you build, the more your agent understands about your infrastructure, your workflows, and your preferences — all expressed in natural language, all stored as plain markdown files.

---

## Repository Structure

```
Hermes-Skills/
├── medium-story/            # Medium article pipeline
├── short-videos/            # Short video pipeline
├── excalidraw/              # Diagram generation
├── ai-projects/             # Repository sync
├── templates/               # Shared templates
│   └── persona-template.md  # Writing voice template
└── scripts/                 # Shared scripts
    └── md_to_html.py        # Markdown → HTML converter
```

---

## Future Skills

This is a living collection. Planned additions include security scanning pipelines, infrastructure health monitors, backup orchestrators, and notification dispatchers — all following the same pattern of natural-language configuration and agent-native execution.

---

## Security

All skills are sanitised for public use:

- ✅ No secrets, tokens, or credentials
- ✅ No system paths — all configurable through `{{VARIABLE}}` placeholders
- ✅ No hostnames, IP addresses, or internal infrastructure details
- ✅ Environment variables recommended for sensitive configuration

Review each skill's config variables before first use. Never hardcode credentials.

---

## License

MIT — use freely, adapt as needed. Attribution appreciated but not required.
