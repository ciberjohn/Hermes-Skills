# Hermes Skills

A growing collection of reusable Hermes Agent skills, built to be installed, extended, and adapted through natural language — no YAML, no config files, no manual directory wrangling.

**By [João Silva](https://github.com/ciberjohn)**

---

## How Installation Works

Every skill in this repo is designed to be installed the way you would tell a colleague what to do: in natural language.

Copy one of the prompts below, paste it to your Hermes agent, and it handles the rest — cloning the repo, placing the files in `~/.hermes/skills/`, and asking you the configuration questions it needs.

Once installed, the skill is available as a slash command (`/medium-story`, `/short-videos`, `/excalidraw`, `/ai-projects`) — or you can invoke it naturally by describing what you want.

---

### Alternative: Install via Skills Hub CLI (Advanced)

Hermes also has a built-in Skills Hub with CLI commands for power users:

```bash
# Add this repo as a permanent tap (external source)
hermes skills tap add ciberjohn/Hermes-Skills

# Install a specific skill from the tap
hermes skills install ciberjohn/Hermes-Skills/medium-story

# Or install directly from a URL
hermes skills install https://raw.githubusercontent.com/ciberjohn/Hermes-Skills/main/medium-story/SKILL.md

# List installed skills
hermes skills list

# Browse available skills from all sources
hermes skills browse

# Search across hub sources
hermes skills search pipeline
```

Taps add the entire repo as an external skill directory. Skills update automatically when you update the repo.

---

### Natural Language Auto-Discovery

You can also install a skill simply by telling your Hermes agent what you want:

> "I need to write a Medium article about why SSH key management still fails in 2026."

If the `medium-story` skill is installed, Hermes automatically matches your goal to the skill's description, loads the full instructions, and runs the pipeline. No slash command needed.

The same applies to every installed skill. The skill descriptions at the top of each `SKILL.md` file are what Hermes uses for discovery, so the more descriptive they are, the better the agent picks the right one.

If you already know the natural language approach above, stick with it — it asks you the configuration questions rather than requiring you to hunt down variables.

---

### Quick Install — All Skills

Copy and paste this to your Hermes agent:

> "Clone github.com/ciberjohn/Hermes-Skills into a local directory. Then copy the SKILL.md from each subdirectory — medium-story, short-videos, excalidraw, ai-projects — into my Hermes skills directory under ~/.hermes/skills/ with their category folders (creative/ for medium-story and short-videos, devops/ for excalidraw and ai-projects). If the directories don't exist, create them. Then, for each skill, ask me the configuration questions it needs — repo paths, URLs, persona file locations. Let me know when everything is installed and show me how to use each one with a slash command example."

---

### Install medium-story

Copy and paste:

> "Install the medium-story skill into my Hermes agent. Clone github.com/ciberjohn/Hermes-Skills to a temporary directory and copy medium-story/SKILL.md into ~/.hermes/skills/creative/medium-story/SKILL.md. If creative/ doesn't exist, create it. Then copy the contents of medium-story/references/ into ~/.hermes/skills/creative/medium-story/references/. After that, ask me these configuration questions one at a time:
> 1. Where is my Medium articles repository on disk? (absolute path)
> 2. What is the GitHub remote URL for that repository?
> 3. Where is my writing persona file?
> 4. Where is my md_to_html.py script located?
> 5. What Medium RSS feed URL should I cache (optional)?
> 6. What byline name should articles use?
> When I answer each, store the values so the skill works next time I use it. Finally, show me an example of how to invoke it: '/medium-story write an article about why SSH key management still fails in 2026'."

---

### Install short-videos

Copy and paste:

> "Install the short-videos skill into my Hermes agent. Clone github.com/ciberjohn/Hermes-Skills and copy short-videos/SKILL.md into ~/.hermes/skills/creative/short-videos/SKILL.md. Then ask me:
> 1. Where is my content repository on disk?
> 2. Where should short video folders be created inside that repo?
> Store my answers, then show me an example: '/short-videos create a video about zero-trust networking for remote Kubernetes clusters'."

---

### Install excalidraw

Copy and paste:

> "Install the excalidraw skill into my Hermes agent. Clone github.com/ciberjohn/Hermes-Skills and copy excalidraw/SKILL.md into ~/.hermes/skills/devops/excalidraw/SKILL.md. Also copy excalidraw/python_helpers.py into a location I specify. Then ask me:
> 1. Where is my excalidraw diagrams repository on disk?
> 2. What is the GitHub URL for that repository?
> 3. Where should I put python_helpers.py?
> 4. What is the URL of my self-hosted Excalidraw instance (optional)?
> Store my answers, then show me an example: '/excalidraw generate a pipeline architecture diagram for the CI/CD flow'."

---

### Install ai-projects

Copy and paste:

> "Install the ai-projects skill into my Hermes agent. Clone github.com/ciberjohn/Hermes-Skills and copy ai-projects/SKILL.md into ~/.hermes/skills/devops/ai-projects/SKILL.md. Then ask me:
> 1. What is the GitHub URL of my AI projects repository?
> 2. Where should I clone it on disk?
> Store my answers, then show me an example: '/ai-projects sync the latest projects'."

---

## How Skills Work

Skills are an open standard (compatible with [agentskills.io](https://agentskills.io)). Each skill is a folder containing a `SKILL.md` file with metadata and instructions that tell your Hermes agent how to perform a specific task. Skills can also bundle scripts, reference materials, and templates.

Once a skill is in your `~/.hermes/skills/` directory, Hermes discovers it at startup and loads only the name and description — just enough to know when it might be relevant. When you give Hermes a task that matches a skill's description, it loads the full instructions and executes the pipeline.

**You never manage sessions, approve permission prompts, or restart stalled processes.** The agent handles everything.

### Current Skills

| Skill | What it does | Pipeline | Slash command |
|-------|-------------|----------|---------------|
| [medium-story](medium-story/) | Produces a full article package (markdown, video script, LinkedIn post, YouTube script, HTML) from a single topic prompt | 9 steps: sync → cross-ref → research → write → 4 parallel output agents → HTML → git | `/medium-story [topic]` |
| [short-videos](short-videos/) | Generates 90-second video scripts and standalone LinkedIn posts | 6 steps: sync → research → 3 parallel agents → git | `/short-videos [topic]` |
| [excalidraw](excalidraw/) | Creates Excalidraw diagrams as JSON files, saved to a GitHub repo | Python helpers → JSON generation → git push | `/excalidraw [description]` |
| [ai-projects](ai-projects/) | Syncs a Git repository of AI projects to a local directory | Clone → pull → status report | `/ai-projects [action]` |

---

## The Pattern

These skills follow the same architecture that runs my own fleet: a main agent that delegates work to specialised sub-agents, communicates through messaging gateways, and runs on a schedule through Hermes cron. You do not need that exact setup to use the skills. They work with any Hermes profile.

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
