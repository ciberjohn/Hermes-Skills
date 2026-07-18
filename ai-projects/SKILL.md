---
name: ai-projects
description: Sync a Git repository of AI projects to a local directory.
keywords: [git, sync, clone, pull, projects, automation]
category: devops
---

# ai-projects

Syncs a configured Git repository containing AI projects to a local directory.
If the directory already exists, it performs a `git pull` to update. If not, it
clones the repository fresh. Always reports the current status of the local
working tree.

## Configuration Variables

| Variable | Purpose | Example |
|---|---|---|
| `{{AI_PROJECTS_REPO_URL}}` | The full Git remote URL to clone from | `https://github.com/example/ai-projects.git` |
| `{{AI_PROJECTS_LOCAL_PATH}}` | Absolute path to the local copy | `/home/user/ai-projects` |

Set these in your Hermes profile configuration under the `ai-projects` skill
block, or export them as environment variables before invoking the skill.

## Steps

1. **Check existence** — If `{{AI_PROJECTS_LOCAL_PATH}}` does not exist, clone
   `{{AI_PROJECTS_REPO_URL}}` into it. If it already exists and is a Git
   repository, proceed to step 2.

2. **Update** — Run `git pull --ff-only` inside `{{AI_PROJECTS_LOCAL_PATH}}` to
   fetch and merge upstream changes without creating merge commits.

3. **Report** — Print the current branch, latest commit hash, commit message,
   and whether the working tree is clean.

## Prerequisites

- **Hermes Agent** — The skill relies on Hermes's variable interpolation and
  terminal execution.
- **Git** — Must be installed and available on `PATH`.
- **Network access** — The remote repository must be reachable from the
  execution environment.

## Error Handling

- If `{{AI_PROJECTS_LOCAL_PATH}}` exists but is not a Git repository, the skill
  halts with an error message.
- If the remote is unreachable, `git pull` will fail with the underlying Git
  error — review network connectivity and repository URL.
- If the local tree has uncommitted changes, `git pull --ff-only` will reject
  the update. Stash or commit local changes before running the skill again.

## Usage

```bash
# The skill is invoked via Hermes:
#   "sync my ai projects"
# or directly from the shell:
hermes skill run ai-projects
```
