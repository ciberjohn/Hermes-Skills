# ai-projects

A **Hermes Agent** skill that keeps a local copy of an AI projects repository
synchronised with its upstream Git remote.

## What It Does

- Clones the repository if it does not exist locally.
- Pulls the latest changes via `git pull --ff-only` when the local copy already
  exists.
- Reports the current branch, latest commit, and working-tree status after
  every sync.

## Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com) — the skill engine.
- **Git** — installed and accessible on `PATH`.
- A **GitHub** (or any Git) repository URL containing your AI projects.
- **Network access** to the remote repository.

## Installation

1. Place the `ai-projects` skill directory inside your Hermes skills path:
   ```
   ~/.hermes/skills/ai-projects/
   ```
   or configure a custom skills directory in your Hermes profile.

2. Set the required configuration variables in your profile:

   ```yaml
   # ~/.hermes/profiles/default.yaml  (or your active profile)
   skills:
     ai-projects:
       AI_PROJECTS_REPO_URL: "https://github.com/your-org/ai-projects.git"
       AI_PROJECTS_LOCAL_PATH: "/home/you/ai-projects"
   ```

3. Run the skill:
   ```bash
   hermes skill run ai-projects
   ```

## Configuration

| Variable | Required | Description |
|---|---|---|
| `AI_PROJECTS_REPO_URL` | Yes | The remote Git URL to clone from. |
| `AI_PROJECTS_LOCAL_PATH` | Yes | Absolute path to the local working copy. |

## Usage Examples

```bash
# Sync once
hermes skill run ai-projects

# Schedule periodic syncing (via Hermes cron)
hermes cron add --name sync-ai-projects --schedule "0 * * * *" --skill ai-projects
```

## How It Works

1. **Clone or update** — If the local path is empty or missing, the repository
   is cloned fresh. Otherwise `git pull --ff-only` is executed inside the
   existing working tree.

2. **Status report** — After pulling, the skill prints the current branch name,
   the most recent commit hash and subject line, and whether there are any
   uncommitted changes in the working tree.

3. **Error reporting** — Any Git failures (network errors, merge conflicts,
   dirty working trees) are surfaced as clear error messages.

## Development

If you want to contribute or modify this skill, the main logic lives in
`SKILL.md` as a structured Hermes skill definition. The `.gitignore` in this
directory prevents accidental commits of sensitive or generated files.

## Licence

MIT — see [LICENCE](../LICENCE) in the repository root.
