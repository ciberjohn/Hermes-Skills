# Hermes Skills

A collection of reusable, production-grade Hermes Agent skills for content creation, diagram generation, and repository management.

**By [João Silva](https://github.com/ciberjohn)** — Strategic Technology Leader & AI Platform Engineer

---

## Skills

| Skill | Description | Pipeline |
|-------|-------------|----------|
| **[medium-story](medium-story/)** | Full Medium article package from a topic prompt | 9 steps: sync → research → write → 4 parallel agents → HTML → git |
| **[short-videos](short-videos/)** | 90-second video scripts + LinkedIn posts | 6 steps: sync → research → 3 parallel agents → git |
| **[excalidraw](excalidraw/)** | Excalidraw diagram generation in JSON | Python helpers → JSON generation → git push |
| **[ai-projects](ai-projects/)** | Git repo sync for AI project repositories | Clone/pull → status report |

## Prerequisites

- **Hermes Agent** — [Install from Nous Research](https://hermes-agent.nousresearch.com)
- **Git** — for version control and automated git operations
- **Python 3** — for HTML conversion and diagram generation scripts

## Repository Structure

```
Hermes-Skills/
├── medium-story/          # Medium article pipeline skill
│   ├── SKILL.md           # Hermes skill definition
│   ├── README.md          # Skill documentation
│   └── PERSONA_PROMPT.md  # Voice configuration template
├── short-videos/          # Short video pipeline skill
│   ├── SKILL.md           # Hermes skill definition
│   ├── README.md          # Skill documentation
│   └── VIDEO_FORMAT.md    # Script format specification
├── excalidraw/            # Diagram generation skill
│   ├── SKILL.md           # Hermes skill definition
│   ├── README.md          # Skill documentation
│   └── python_helpers.py  # Reusable diagram helpers
├── ai-projects/           # Repository sync skill
│   ├── SKILL.md           # Hermes skill definition
│   └── README.md          # Skill documentation
├── templates/             # Shared templates
│   └── persona-template.md # Writing voice template
└── scripts/               # Shared scripts
    └── md_to_html.py      # Markdown → HTML converter
```

## Getting Started

1. **Pick a skill** — browse the skill directories above
2. **Configure variables** — each `SKILL.md` has configuration variables at the top (marked `{{VARIABLE_NAME}}`)
3. **Copy to your Hermes profile** — copy the `SKILL.md` to your Hermes skills directory
4. **Install dependencies** — see each skill's `README.md` for details
5. **Run it** — tell your Hermes agent what you want, and the skill handles the rest

## Security

All skills in this repository are sanitised:
- ✅ **No secrets, tokens, or credentials**
- ✅ **No system paths** — all paths use configurable variables
- ✅ **No hostnames or internal IPs**
- ✅ **Environment variables** recommended for sensitive configuration

Review each skill's configuration variables before use and never hardcode credentials.

## License

MIT — use freely, adapt as needed. Attribution appreciated but not required.
