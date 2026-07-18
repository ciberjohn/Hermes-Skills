# skill-writer — Hermes Meta-Skill

Creates new Hermes Agent skills from a description. Given a topic and concept, generates a complete, sanitised skill package ready for the Hermes-Skills repo.

This is a **meta-skill**: it encodes the process I used to build every other skill in this repo. If you can describe what a skill should do, the skill-writer handles the rest.

## Prerequisites

- **Hermes Agent** — with `delegate_task` capability
- **Git** — configured with your GitHub credentials
- **Hermes-Skills repo** — cloned locally, set as `HERMES_SKILLS_REPO_PATH`

## Installation

Copy `SKILL.md` into your Hermes skills directory:

```bash
cp skill-writer/SKILL.md ~/.hermes/skills/meta/skill-writer/SKILL.md
cp skill-writer/.gitignore ~/.hermes/skills/meta/skill-writer/.gitignore 2>/dev/null || true
```

Then configure the variables:

```bash
export HERMES_SKILLS_REPO_PATH=/path/to/Hermes-Skills
export HERMES_SKILLS_REPO_URL=https://github.com/your-username/Hermes-Skills
export SKILL_AUTHOR_NAME="Your Name"
export SKILL_AUTHOR_URL=https://github.com/your-username
export PEER_REVIEW_ENABLED=true
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HERMES_SKILLS_REPO_PATH` | Yes | — | Absolute path to the Hermes-Skills repository |
| `HERMES_SKILLS_REPO_URL` | Yes | — | Git remote URL for the Hermes-Skills repo |
| `SKILL_AUTHOR_NAME` | No | `Your Name` | Name for attribution |
| `SKILL_AUTHOR_URL` | No | `https://github.com/your-username` | URL for attribution |
| `PEER_REVIEW_ENABLED` | No | `true` | Run peer review sub-agent on output |

## How to Use It

Just describe what you want:

> "/skill-writer I need a skill that monitors disk usage across a fleet of servers and posts alerts to a Discord webhook when any volume exceeds 90%."

The skill-writer asks you questions, generates all files, runs a peer review, and commits the result to the repo.

### What It Generates

```
{skill-name}/
├── SKILL.md          # Hermes skill definition with pipeline
├── README.md         # Installation and usage docs
├── .gitignore        # Standard ignores
├── templates/        # Templates if needed (with CUSTOMISE notes)
├── references/       # Reference docs if needed
└── scripts/          # Helper scripts if needed
```

### Pipeline

1. **Intake** — asks you 8 questions about the skill
2. **Research** — optionally researches the topic
3. **Generate SKILL.md** — full pipeline with config variables
4. **Generate README.md** — installation and usage
5. **Generate supporting files** — .gitignore, templates, references
6. **Sanitize** — self-check for secrets, paths, hostnames
7. **Peer review** — sub-agent reviews the output
8. **Git commit** — adds and pushes to the repo

## Examples

```
/skill-writer Create a skill that scans Docker images for CVEs using Trivy and reports results to a file
```

```
/skill-writer I need a weekly newsletter generator that scrapes HN, compiles top stories, and formats an email
```

```
/skill-writer A skill that backs up my Hermes profile to a GitHub repo with encryption
```

## Security

The skill-writer generates skills for public use. Every output is sanitised:
- No secrets, tokens, or credentials
- No system paths — all `{{VAR}}` placeholders
- No hostnames or IPs
- Peer review catches issues before commit

## License

MIT
