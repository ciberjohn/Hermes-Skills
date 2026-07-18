---
name: skill-writer
description: "Creates new Hermes Agent skills from a description. Given a topic and concept, generates SKILL.md, README.md, .gitignore, and supporting files — then runs a 3-reviewer verification pipeline (DevOps, SecOps, AI Engineer), updates the root README, and commits. Ready for the Hermes-Skills repo."
license: MIT
metadata:
  version: "1.1.0"
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
| `SKILL_AUTHOR_NAME` | No | `Your Name` | Your name for attribution in new skills |
| `SKILL_AUTHOR_URL` | No | `https://github.com/your-username` | Your URL for attribution |
| `PEER_REVIEW_ENABLED` | No | `true` | Whether to run the 3-reviewer verification pipeline (DevOps, SecOps, AI Engineer) |

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

Also check `agentskills.io/skill-creation/best-practices.md` for general skill authoring guidelines:
- "Calibrate control" — match specificity to fragility: prescriptive for fragile ops, flexible for creative tasks
- "Provide defaults, not menus" — pick one default tool/approach, mention alternatives briefly
- "Favor procedures over declarations" — teach *how*, not *what*
- "Use Gotchas sections" — environment-specific corrections to mistakes the agent makes
- "Templates for output format" — concrete patterns > prose descriptions
- "Bundle reusable scripts" — when agents reinvent the same logic, bundle it

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
- Use `~/` or `{{SKILL_WORKSPACE_PATH}}` for user home references in example paths
- Every variable in the Config Variables table must be referenced in the pipeline steps
- Include `version: 1.0.0` in the YAML frontmatter
- Compatible with the [agentskills.io](https://agentskills.io/specification.md) open standard — include `name` and `description` at minimum
- Consider adding `license`, `compatibility`, and `metadata` fields where relevant
- Consider generating eval/test cases for the skill (see `agentskills.io/skill-creation/evaluating-skills.md`)

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

### Step Six — Sanitise

Run a self-check:
- [ ] No secrets, tokens, API keys, passwords?
- [ ] No system paths (no `/home/`, `/tmp/`, `/Users/`)?
- [ ] No hostnames or IP addresses?
- [ ] All variables use `{{VAR}}` format?
- [ ] `.gitignore` present?
- [ ] YAML frontmatter valid?
- [ ] British English throughout?

If any check fails, fix it before proceeding.

### Step Seven — Three-Reviewer Verification Pipeline (if enabled)

If `PEER_REVIEW_ENABLED` is true, spawn three sub-agents **in parallel** to review the generated skill from different perspectives. Each returns a structured report. Collect all three, then fix every issue found before proceeding.

If any reviewer reports a **critical or high** severity finding, run a second pass and re-verify before proceeding to the next step.

#### Reviewer 1 — DevOps Engineer

Role the sub-agent as "a seasoned DevOps Engineer performing an operational review." Ask it to check:

1. **Directory structure** — is the skill directory clean and well-organised?
2. **Installation flow** — can a user follow the README and install the skill?
3. **Pipeline operability** — are the pipeline steps clear and actionable for an agent?
4. **Configuration variables** — are they complete? Every variable documented? No missing vars?
5. **Cross-skill consistency** — does the skill follow the same patterns as other skills in the repo? (frontmatter, config tables, pipeline format, {{VAR}} syntax)
6. **Root README** — does the new skill need to be listed in the root README's skills table?
7. **Operational gaps** — missing documentation, unclear steps, assumptions that would break for a new user

#### Reviewer 2 — Security Operations Lead

Role the sub-agent as "a Security Operations Lead specialising in code security and compliance." Ask it to check:

1. **Hardcoded secrets** — any tokens, API keys, passwords, private keys, secrets in any file?
2. **System path leaks** — any `/home/`, `/tmp/`, `/Users/`, `/root/` paths that expose internal infrastructure?
3. **Hostnames / IPs** — any hostnames, IP addresses, Tailscale IPs, internal domains?
4. **PII exposure** — real names, email addresses, usernames, URLs?
5. **Git history** — any secrets or paths committed? (Check before the final commit.)
6. **.gitignore coverage** — does the `.gitignore` adequately protect against accidental credential commits?
7. **Supply chain** — any references to internal registries, private package repos, or dependency confusion risks?
8. **Prompt injection** — do any operations described in the skill create a risk if instructions are manipulated?

#### Reviewer 3 — AI Engineer

Role the sub-agent as "an AI Engineer specialising in agent architectures, prompt engineering, and skill systems." Ask it to check:

1. **agentskills.io compliance** — does the SKILL.md frontmatter use the standard fields? (`name`, `description`, `license`, `metadata:` nesting)
2. **Progressive disclosure** — does the skill follow the name-only → full-load → resource-on-demand pattern?
3. **Pipeline design** — are the steps well-structured for an agent to follow? Clear, sequential, actionable?
4. **Prompt quality** — are the instructions specific enough? Edge cases, error handling, gotchas included?
5. **{{VAR}} consistency** — are variables used consistently? Any hardcoded values that should be variables?
6. **British English** — is it consistent throughout the skill files?
7. **agentskills.io Hub compatibility** — could the skill be published to the Skills Hub?

### Step Eight — Validate (Optional)

If the `skills-ref` validation tool is available, run:

```bash
skills-ref validate ./{skill-name}
```

This checks the SKILL.md against the [agentskills.io](https://agentskills.io/specification.md) specification. Fix any validation errors.

If `skills-ref` is not installed, skip this step.

### Step Nine — Git Commit

Stage all new skill files, commit with message `"feat: add {skill-name} skill — {one-line description}"`, and push.

Note: The root README is updated in the next step, so this commit only contains the new skill directory.

### Step Ten — Root README Maintenance

After the new skill is committed, update the root `README.md` to reflect it. This step ensures the root page stays accurate as new skills are added.

**10a. Add to the Current Skills table**

Find the markdown table under "### Current Skills" and add a new row:

```markdown
| [{{skill-name}}]({{skill-name}}/) | {{one-sentence description}} | {{pipeline summary}} | `/{{skill-name}} [command]` |
```

Insert it alphabetically between the existing rows.

**10b. Add a quick-install prompt**

Find the section with "### Install {skill-name}" quick-install prompts. Add a new one after the last existing install prompt:

> "Install the {{skill-name}} skill into my Hermes agent. Clone github.com/ciberjohn/Hermes-Skills and copy {{skill-name}}/SKILL.md into ~/.hermes/skills/{{category}}/{{skill-name}}/SKILL.md. Also copy {{skill-name}}/.gitignore into the same directory. Then ask me: [list each config variable as a question]. Store my answers, then show me an example: '/{{skill-name}} [example usage]'."

**10c. Add to the repository structure tree**

Find the section showing the repository directory tree. Add the new skill directory in alphabetical order with its description comment.

**10d. Update the slash command mention**

Find the line listing available slash commands: `(/medium-story, /short-videos, ...)`. Add `/{{skill-name}}` to the list.

**10e. Commit the README update**

Stage the modified README.md and commit with message `"docs: add {{skill-name}} to root README — skills table, install prompt, directory tree"`.

Push the commit.

### Step Eleven — Report

Report the result to the user:
- What was created (`{skill-name}/` directory with all files)
- Review results summary (pass/fail per reviewer)
- Where it lives in the repo
- How to install it (install prompt)
- Root README was updated

## Output Files

| File | Description |
|------|-------------|
| `{skill-name}/SKILL.md` | Hermes skill definition |
| `{skill-name}/README.md` | Installation and usage documentation |
| `{skill-name}/.gitignore` | Ignore patterns |
| `{skill-name}/templates/` | Templates if applicable\* |
| `{skill-name}/references/` | Reference files if applicable\* |
| `{skill-name}/scripts/` | Scripts if applicable\* |

\* Created only when the skill genuinely needs them.

## Security Notes

- The skill-writer generates skills for others to use. Every generated skill must be sanitised before committing.
- Never include credentials or secrets in generated output.
- Always use `{{VAR}}` placeholders for configurable values — never hardcode paths.
- The 3-reviewer verification pipeline (DevOps, SecOps, AI Engineer) catches issues before they reach the repo.
- The SecOps reviewer specifically checks for secrets, PII, and infrastructure exposure.
- The skill-writer itself has no credentials — it relies on the user's Git configuration for commits.

## Pitfalls

- **Over-generating.** Not every skill needs templates, scripts, and references. Only create supporting files when the skill genuinely needs them.
- **Forgetting the .gitignore.** Every skill directory must have one. Add it early.
- **Inconsistent variable names.** Use the same `{{VAR}}` name in SKILL.md, README.md, and all supporting files.
- **Skipping the research step.** For technical skills (e.g. Kubernetes, security scanning), research is essential to get the pipeline right.
- **British English drift.** Review the final output for American spellings before committing.
- **Forgetting root README updates.** After adding a new skill, the root README needs 4 changes: skills table, install prompt, directory tree, slash command list. Step Ten handles this, but verify it was applied correctly.
- **Three-reviewer output volume.** Each reviewer returns a full report. Read all three before fixing anything — a fix for one reviewer may address another's finding too.
- **Critical findings block the pipeline.** If any reviewer reports critical or high findings, fix them and re-run verification before git commit.
- **No `delegate_task` fallback.** If the user's Hermes agent does not support `delegate_task`, skip Steps Two (research) and Seven (verification), or use a profile that supports them.
- **Git push failure.** If `git push` fails (no network, no write access, detached HEAD), report the commit hash and tell the user to push manually with `git push origin main`.
- **Interrupted intake.** If the user walks away mid-intake (Step One), save partial answers to a scratch file so they can resume later.
