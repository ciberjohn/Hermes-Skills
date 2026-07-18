---
name: skill-writer
version: 1.0.0
description: "Creates new Hermes Agent skills from a description. Given a topic and concept, generates SKILL.md, README.md, .gitignore, and supporting files — sanitized, peer-reviewed, and ready for the Hermes-Skills repo."
tags: [meta, skill-creation, development, automation, publishing]
platforms: [linux, darwin]
---

# Skill-Writer

Creates new Hermes Agent skills. Given a description of what a skill should do, the skill-writer generates a complete, sanitized skill package — SKILL.md with YAML frontmatter, README.md with installation instructions, .gitignore, templates, and reference files — and adds it to the Hermes-Skills repository.

## Configuration Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HERMES_SKILLS_REPO_PATH` | Yes | — | Absolute path to the Hermes-Skills repository on disk |
| `HERMES_SKILLS_REPO_URL` | Yes | — | Git remote URL for the Hermes-Skills repo |
| `SKILL_AUTHOR_NAME` | No | `João Silva` | Your name for attribution in new skills |
| `SKILL_AUTHOR_URL` | No | `https://github.com/ciberjohn` | Your URL for attribution |
| `SKILL_LICENSE` | No | `MIT` | License for new skills |
| `PEER_REVIEW_ENABLED` | No | `true` | Whether to run peer review sub-agent on output |

## Prerequisites

- **Hermes Agent** — with `delegate_task` capability for sub-agent spawning
- **Git** — for committing new skills to the Hermes-Skills repo
- **Path to Hermes-Skills repo** — set in `HERMES_SKILLS_REPO_PATH`

## Pipeline

### Step One — Intake

Ask the user these questions, one at a time:

1. **What is the skill called?** (short kebab-case name, e.g. `docker-cleanup`)
2. **What category does it belong to?** (e.g. `devops`, `creative`, `security`, `productivity`, `data-science`, `monitoring`)
3. **What does the skill do?** (one-sentence description for the YAML frontmatter)
4. **Describe the pipeline in detail.** What steps should the skill perform? What tools does it need? What does it produce?
5. **What are the configuration variables?** List each with: name, required/optional, default, description
6. **What are the prerequisites?** Any tools, accounts, or setup the user needs before using this skill
7. **Does this skill produce output files?** What files and where?
8. **Any special considerations?** Pitfalls, edge cases, rate limits, security notes

If the user says "I don't know" to any question, use your judgment to fill in reasonable defaults.

### Step Two — Research (Optional)

If the skill involves a technical topic, spawn a research sub-agent to gather:
- Best practices and common pitfalls
- Reference implementations
- Tool-specific documentation
- Security considerations

If the skill is straightforward (e.g. a simple git sync), skip this step.

### Step Three — Generate SKILL.md

Create `{HERMES_SKILLS_REPO_PATH}/{skill-name}/SKILL.md` with the following structure:

```yaml
---
name: {skill-name}
version: 1.0.0
description: "{one-sentence description}"
tags: [{category}, ...additional tags]
platforms: [linux, darwin]
---
```

Follow the standard Hermes Skill format:
1. **`# {Skill Name}`** — Title
2. **Configuration Variables** section — table with Variable, Required, Default, Description
3. **Prerequisites** section
4. **Pipeline** — numbered steps describing what the skill does
5. **Output Files** section — what files are produced and where
6. **Writer Voice & Style Guide** — if the skill creates content, include a style guide
7. **Pre-Publish Checklist** — if the skill produces content, include quality checks
8. **Security Notes** — any security considerations
9. **Pitfalls** — common mistakes and how to avoid them

Rules:
- Use `{{VARIABLE_NAME}}` syntax for all configurable paths and values (not `${}`)
- Use British English throughout
- No hardcoded system paths, hostnames, IPs, secrets, or credentials
- Use `/home/user/` as example paths in documentation
- Every variable in the Config Variables table must be referenced in the pipeline steps
- Include `version: 1.0.0` in the YAML frontmatter

### Step Four — Generate README.md

Create `{HERMES_SKILLS_REPO_PATH}/{skill-name}/README.md` with:
- What the skill does (one paragraph)
- Prerequisites
- Installation steps using `~/.hermes/skills/<category>/`
- Configuration variables table
- How to use it (examples)
- Output files
- Install prompt — a sentence the user can copy-paste to their Hermes agent to install this skill

### Step Five — Generate Supporting Files

Create:
- `.gitignore` — standard Hermes skill ignores: `*.html`, `__pycache__/`, `.env`, `secrets/`, `*.pyc`, `.DS_Store`, `.vscode/`, `.idea/`
- `references/` or `templates/` directory — if the skill references external files, create them as stubs with "CUSTOMISE THIS" notes
- `scripts/` — if the skill needs executable scripts, include them with variables for paths

### Step Six — Sanitize

Run a self-check:
- [ ] No secrets, tokens, API keys, passwords?
- [ ] No system paths (no `/home/`, `/tmp/`, `/Users/`)?
- [ ] No hostnames or IP addresses?
- [ ] All variables use `{{VAR}}` format?
- [ ] `.gitignore` present?
- [ ] YAML frontmatter valid?
- [ ] British English throughout?

If any check fails, fix it before proceeding.

### Step Seven — Peer Review (if enabled)

If `PEER_REVIEW_ENABLED` is true, spawn a sub-agent to review the generated skill:

Role the sub-agent as "Senior Developer reviewing a new Hermes skill." Ask it to check:
1. Does the SKILL.md follow the standard format?
2. Are all configuration variables documented?
3. Are the pipeline steps clear and actionable?
4. Are there any missing files or broken references?
5. Is the skill sanitised (no secrets, no paths, no hostnames)?
6. Would a new user be able to install and use this skill from the README alone?

Collect the review output as a structured report. Fix any issues found.

### Step Eight — Git Commit

Stage all new files, commit with message `"feat: add {skill-name} skill — {one-line description}"`, and push.

Report the result to the user: what was created, where it lives, how to install it.

## Output Files

| File | Description |
|------|-------------|
| `{skill-name}/SKILL.md` | Hermes skill definition |
| `{skill-name}/README.md` | Installation and usage documentation |
| `{skill-name}/.gitignore` | Ignore patterns |
| `{skill-name}/templates/` | Templates if applicable |
| `{skill-name}/references/` | Reference files if applicable |
| `{skill-name}/scripts/` | Scripts if applicable |

## Security Notes

- The skill-writer generates skills for others to use. Every generated skill must be sanitised before committing.
- Never include credentials or secrets in generated output.
- Always use `{{VAR}}` placeholders for configurable values — never hardcode paths.
- The peer review step catches issues before they reach the repo.
- The skill-writer itself has no credentials — it relies on the user's Git configuration for commits.

## Pitfalls

- **Over-generating.** Not every skill needs templates, scripts, and references. Only create supporting files when the skill genuinely needs them.
- **Forgetting the .gitignore.** Every skill directory must have one. Add it early.
- **Inconsistent variable names.** Use the same `{{VAR}}` name in SKILL.md, README.md, and all supporting files.
- **Skipping the research step.** For technical skills (e.g. Kubernetes, security scanning), research is essential to get the pipeline right.
- **British English drift.** Review the final output for American spellings before committing.
