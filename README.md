# Hermes Skills

A growing collection of reusable Hermes Agent skills, built to be installed, extended, and adapted through natural language — no YAML, no config files, no manual directory wrangling.

**By [João Silva](https://github.com/ciberjohn)**

---

## Installation

Every skill in this repo is designed to be installed the way you would tell a colleague what to do: in natural language.

Each skill lives in its own folder with a README containing a **copy-paste install prompt**. Send that prompt to your Hermes agent and it handles the rest — cloning the repo, placing the files in `~/.hermes/skills/`, and asking you the configuration questions it needs.

Once installed, the skill is available as a slash command (`/medium-story`, `/short-videos`, `/excalidraw`, `/ai-projects`) — or you can invoke it naturally by describing what you want.

### Current Skills

| Skill | What it does | Pipeline | Slash command |
|-------|-------------|----------|---------------|
| [skill-writer](skill-writer/) | Meta-skill: creates new Hermes Agent skills from a description. Generates SKILL.md, README.md, .gitignore, templates, and runs peer review | 8 steps: intake → research → generate → create supporting → sanitize → review → commit | `/skill-writer [description]` |
| [medium-story](medium-story/) | Produces a full article package (markdown, video script, LinkedIn post, YouTube script, HTML) from a single topic prompt. Includes a mandatory anti-AI-slop writing pass (Step 6b) before the output agents run | 9 steps: sync → cross-ref → research → write → anti-slop pass → 4 parallel output agents → HTML → git | `/medium-story [topic]` |
| [ciberjohn-no-slop](ciberjohn-no-slop/) | General-purpose writing constraints that make output sound human, not AI-generated. Banned vocabulary, structural rules, punctuation discipline, accuracy rules, plus a verification script | Enforce → self-check → run `no_slop_check.py` → ship | `/ciberjohn-no-slop` |
| [short-videos](short-videos/) | Generates 90-second video scripts and standalone LinkedIn posts | 6 steps: sync → research → 3 parallel agents → git | `/short-videos [topic]` |
| [excalidraw](excalidraw/) | Creates Excalidraw diagrams as JSON files, saved to a GitHub repo | Python helpers → JSON generation → git push | `/excalidraw [description]` |
| [ai-projects](ai-projects/) | Syncs a Git repository of AI projects to a local directory | Clone → pull → status report | `/ai-projects [action]` |
| [3dprinter](3dprinter/) | Slices STL/3MF files headlessly with OrcaSlicer for a Flashforge AD5X and drives the printer's LAN API — material-station asks, SOP-tuned profiles, bed-temp verification, upload/print | Slice → verify temps → confirm channels → upload → print | `"print this STL"` |
| [t3mp3st-autonomous-security](t3mp3st-autonomous-security/) | Autonomous security ops — installs T3MP3ST for recon, scanning, CVE hunting, and kill-chain ops with an LLM-driven AI agent | Setup → verify → configure scope → autonomous hunting → fleet assessment | `/t3mp3st-autonomous-security [target]` |
| [social-poster](social-poster/) | Direct OAuth social media posting — no Docker, no database. Generate URLs, exchange PINs/codes, store tokens, and post via direct API calls | OAuth → token vault → post → schedule | `"post this to X"` |
| [uk-business-consultant](uk-business-consultant/) | UK business consultant — two-mode framework for side hustles (£500–£2k/mo) and full-time ventures (£3k–£8k/mo). Includes viability scorecard, financial modelling, UK tax/regs, low-cost marketing playbook | Understand → Scorecard → Model → Recommend → Deliver | `/uk-business-consultant [goal]` |
| [technical-trainer](technical-trainer/) | Full lifecycle technical course creation — AI and Linux courses in English (UK) and Portuguese (PT). Market research, fact-checked content, bilingual production, and B2B packaging via parallel sub-agents | 6 steps: Intake → Market Research → Curriculum Design → 4 parallel sub-agents (Fact Checker, Technical Writer, Translator, B2B Specialist) → Repository Assembly → Delivery | `"Create a course on [topic]"` |
| [transcribe](transcribe/) | Local speech-to-text: transcribe audio (Dropbox links, uploads, URLs) with CrisperWhisper and commit verbatim + intended transcripts to a private GitHub repo — one dated folder per audio | Fetch → transcribe (verbatim + intended) → dated folder → git commit + push | `"transcribe this Dropbox link"` |
| [joplin-brain](joplin-brain/) | Self-filing second brain on Joplin: capture anything into INBOX in under ten seconds, file it on a schedule with a deterministic classifier, and answer with grounded retrieval from your own notes | Capture → daily FILER (dry-run default) → grounded ASK → AGENT LOG | `"save this to my second brain"` |

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

### Natural Language Auto-Discovery

You can also install a skill simply by telling your Hermes agent what you want:

> "I need to write a Medium article about why SSH key management still fails in 2026."

If the `medium-story` skill is installed, Hermes automatically matches your goal to the skill's description, loads the full instructions, and runs the pipeline. No slash command needed.

The same applies to every installed skill. The skill descriptions at the top of each `SKILL.md` file are what Hermes uses for discovery, so the more descriptive they are, the better the agent picks the right one.

---

## How Skills Work

Skills are an open standard (compatible with [agentskills.io](https://agentskills.io)). Each skill is a folder containing a `SKILL.md` file with metadata and instructions that tell your Hermes agent how to perform a specific task. Skills can also bundle scripts, reference materials, and templates.

Once a skill is in your `~/.hermes/skills/` directory, Hermes discovers it at startup and loads only the name and description — just enough to know when it might be relevant. When you give Hermes a task that matches a skill's description, it loads the full instructions and executes the pipeline.

**You never manage sessions, approve permission prompts, or restart stalled processes.** The agent handles everything.

---

## The Pattern

These skills follow the same architecture that runs my own fleet: a main agent that delegates work to specialised sub-agents, communicates through messaging gateways, and runs on a schedule through Hermes cron. You do not need that exact setup to use the skills. They work with any Hermes profile.

The key insight is that the skill system lets you package operational knowledge as something an agent can load and follow, the same way a human engineer reads a runbook. The more skills you build, the more your agent understands about your infrastructure, your workflows, and your preferences — all expressed in natural language, all stored as plain markdown files.

---

## Repository Structure

```
Hermes-Skills/
├── skill-writer/             # Meta-skill: creates new skills
├── medium-story/             # Medium article pipeline
├── ciberjohn-no-slop/        # Anti-AI-slop writing constraints + checker
├── short-videos/             # Short video pipeline
├── excalidraw/               # Diagram generation
├── ai-projects/              # Repository sync
├── 3dprinter/                # Flashforge AD5X headless slicing + printing
├── t3mp3st-autonomous-security/ # Autonomous security ops
├── social-poster/               # Direct OAuth social media posting
├── technical-trainer/           # Course creation pipeline
├── transcribe/                  # Local audio transcription pipeline
├── joplin-brain/                # Self-filing second brain on Joplin
├── uk-business-consultant/      # UK business consultant skill
├── templates/                # Shared templates
│   └── persona-template.md   # Writing voice template
└── scripts/                  # Shared scripts
    └── md_to_html.py         # Markdown → HTML converter
```

---

## Future Skills

This is a living collection. Planned additions include security scanning pipelines, infrastructure health monitors, backup orchestrators, and notification dispatchers — all following the same pattern of natural-language configuration and agent-native execution.

---

## License

MIT — use freely, adapt as needed. Attribution appreciated but not required.
