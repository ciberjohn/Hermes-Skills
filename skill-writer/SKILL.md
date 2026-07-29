---
name: skill-writer
description: "Creates new Hermes Agent skills from a description. Given a topic and concept, generates SKILL.md, README.md, .gitignore, and supporting files (references/, templates/, scripts/) — sanitised, peer-reviewed, and ready for the Hermes-Skills repo. Can also publish existing local skills with full linked-file support."
license: MIT
metadata:
  version: "1.2.0"
  tags: [meta, skill-creation, development, automation, publishing]
  platforms: [linux, darwin]
  related_skills: [skill-publishing, development-methodology]
---

# Skill-Writer

Creates new Hermes Agent skills from a description.

## Pipeline

1. Intake — 8 config questions
2. Research — optional sub-agent
3. Generate SKILL.md — agentskills.io compliant
4. Generate README.md
5. **Generate supporting files** — create subdirectories and populate:
   - Create `references/`, `templates/`, `scripts/`, `assets/` as needed
   - Write reference docs the skill depends on (API docs, regulatory guides, etc.)
   - Write templates the skill uses (report templates, config files, etc.)
   - Write scripts the skill executes
   - **Every subdirectory must be accounted for** — the install prompt in step 4 (README.md) must reference each one
6. Sanitise — self-check (grep for leaked secrets, stale hostnames, `youruser` pattern)
7. **Peer review** — dispatch **ALL THREE mandatory reviewers** in parallel. The peer review is not optional — it catches factual errors, hardcoded secrets, and stale content that the author cannot see.

   **⚠️ Common pitfall: skipping the Technical Writer.** The Technical Writer verifies live sources in a browser. If the skill references external URLs (gov.uk, API docs, developer portals), the Technical Writer **must** be dispatched. Only skip if the skill contains zero external references — otherwise you risk publishing stale or incorrect data.

   Two sequencing modes depending on whether files need modification:

   **Mode A: Parallel (default)** — dispatch all 3 simultaneously. Use this when review findings only need to be reported, not applied during the review itself (the author applies all fixes in Step 8).

   **Mode B: Sequential (when tech writer updates files)** — dispatch the Technical Writer FIRST to investigate, write corrections, and modify skill files. Wait for it to finish. THEN dispatch QA + DevSecOps in parallel to review the UPDATED files. Use this when platform setup guides need browser verification, or when the tech writer is rewriting sections from scratch — the later reviewers must see the corrected files, not the originals.

   **Mandatory reviewers (dispatch ALL three):**

   **1. DevSecOps** (security focused):
   > Check for hardcoded secrets (API keys, tokens, passwords), hardcoded paths (/home/, /Users/), hardcoded hostnames, stale env var names, credential files in .gitignore, chmod 600 on all state files, OAuth security (CSRF state validation on token exchange), deprecated endpoints. Return findings with severity CRITICAL/HIGH/MEDIUM/LOW.

   **2. QA/Consistency** (code + docs focused):
   > Check cross-file consistency: do redirect URIs in docs match redirect URIs in code? Do platform counts match? Does the config.json template in README match what the scripts expect? Are all referenced commands and file paths correct? Are there unimplemented features referenced as available? Return findings with severity BUG/INCONSISTENCY/EDGE_CASE.

   **3. Technical Writer** (user experience + live source verification — MANDATORY):
   > VERIFY every claim that references an external source by visiting the live URL in a browser (use browser_navigate + browser_snapshot + browser_scroll). Check that product names, scopes, redirect URI formats, pricing, and app types match CURRENT reality — portals change frequently. Watch for deprecated APIs, renamed products, and changed UI flows. Also check readability, completeness, placeholder correctness, and markdown formatting. Return findings with severity DOCS/CONSISTENCY/COMPLETENESS/STALE.
   >
   > **Critical rule:** when the Technical Writer finds factual errors on live sites, it must write the CORRECTED version of the reviewed files, not just a report. This changes file paths between before and after the Technical Writer runs — subsequent reviewers (QA, DevSecOps) MUST wait for and review the UPDATED files, not the originals (use Mode B).

   **Optional 4th reviewer (add when architecture matters):**
   > **AI Engineer** — architecture/design review. Check that the skill design is modular, follows agentskills.io conventions, and fits naturally into the user's skill library.

8. **Apply fixes from ALL reviews in one batch** — wait for ALL sub-agents to complete before
   starting any fix. Fix every finding (CRITICAL/HIGH/MEDIUM first, then LOW/COSMETIC),
   re-run syntax checks on all scripts, then git commit and push once. Do NOT commit between
   reviews — this would create unnecessary git history noise if a later review finds
   additional issues in files you already touched.

   **IMPORTANT:** After applying fixes, do ONE final grep for stale references before committing:
   `grep -rn "TAILSCALE\|YOUR_HOSTNAME\|old-hostname\|your_user\|youruser\|your_domain" <skill-dir>/ --include="*.md" --include="*.py"`

### Existing Skill Pattern (publishing a local skill to the Hermes-Skills repo)

Use this when you already have a skill installed in `~/.hermes/skills/` and need to publish it to the Hermes-Skills public repo with full documentation.

1. **Set working directory** — `cd "$HERMES_SKILLS_REPO_PATH"` and ensure it's clean (`git status`)

2. **Load the original skill** — `skill_view(name="<original-skill>")` to get its content. Also inspect all linked files:
   ```
   skill_view(name="<original-skill>", file_path="references/<filename>")
   skill_view(name="<original-skill>", file_path="templates/<filename>")
   skill_view(name="<original-skill>", file_path="scripts/<filename>")
   ```
   If the skill doesn't list linked files in its output, use `find` on its directory:
   ```
   find ~/.hermes/skills/<category>/<original-skill>/ -type f | sort
   ```

3. **Identify hardcoded content** — inspect SKILL.md and all linked files for paths, names, hostnames, secrets, personal emails. List every file that needs sanitising.

4. **Create a new directory** — under Hermes-Skills with a public-facing name:
   ```bash
   mkdir -p "$HERMES_SKILLS_REPO_PATH/<public-name>/{references,templates,scripts}"
   ```
   Create ALL subdirectories upfront — references/, templates/, scripts/ — even if you're not sure they'll be used. An empty directory costs nothing; forgetting to create one means a later cp fails.

5. **Write SKILL.md** — sanitised copy of the original with `{{VARIABLE}}` placeholders for:
   - User paths (`~/.hermes/profiles/<name>`, `/home/<user>`)
   - Personal names and emails
   - Hostnames and domains (Tailscale, internal IPs)
   - Config values specific to the original user

6. **Sanitise and copy linked files** — for EVERY file found in step 2 that belongs in the public repo:
   - Read the original file
   - Replace personal data (emails, names, paths, hostnames) with `{{VARIABLE}}` placeholders or generic text
   - Write the sanitised version to the corresponding subdirectory in the new Hermes-Skills folder
   - **Do NOT copy** files that contain secrets only (e.g. credential templates with actual API keys) — those belong in .gitignore

7. **Write README.md** — following the established pattern (see social-poster/README.md or excalidraw/README.md for reference):
   - Title and tagline (~1 sentence)
   - **Install section** with:
     - A copy-paste NL prompt for the user's Hermes agent (must reference ALL files to copy — SKILL.md, references/, templates/, scripts/)
     - A manual install alternative (git clone + cp commands)
   - How it works (overview)
   - What's included (file listing table)
   - Usage examples
   - Security section
   - License

8. **Write .gitignore** — standard template:
   ```
   # Environment and secrets
   .env
   .env.*
   secrets/
   !env.example

   # OS files
   .DS_Store
   Thumbs.db

   # Python
   __pycache__/
   *.pyc
   *.pyo
   .venv/
   venv/
   ```
   Add more entries if the skill generates temp files or contains credential directories.

9. **Sanity-check** — grep the entire new directory for leaked secrets (including `youruser` pattern):
   ```bash
   grep -rn "TAILSCALE\|YOUR_HOSTNAME\|old-hostname\|your_user\|youruser\|your_domain" "$HERMES_SKILLS_REPO_PATH/<public-name>/" --include="*.md" --include="*.py" --include="*.sh"
   ```
   Fix any matches.

10. **Update root README** — three changes required:
    - **Table row**: Add a row to the "Current Skills" table with name, description, pipeline summary, and slash command
    - **Install prompt section**: Add a full "### Install <public-name>" section with the copy-paste install prompt (same as step 7's NL prompt — but as a standalone section in root README, matching the pattern of other skills)
    - **Directory tree**: Add the new skill to the repo structure tree diagram

11. **Peer review (mandatory)** — dispatch ALL THREE mandatory sub-agents: DevSecOps, QA/Consistency, and Technical Writer. Each gets context tailored to their role (see Pipeline Step 7 above for exact prompts). Do NOT skip the Technical Writer — their live source verification catches factual errors that no other reviewer will find. Each reviewer must verify:
    - The sanitised linked files, not just SKILL.md
    - Cross-file consistency between SKILL.md, README.md, and all references
    - That the install prompt covers all files in the directory

12. **Apply fixes from ALL reviews** — wait for all sub-agents to complete, then apply every finding in one batch. Do NOT commit between reviews. Fix all findings (CRITICAL/HIGH/MEDIUM first, then LOW/COSMETIC), re-run syntax checks, then **commit and push**

**Pitfall: missing the Technical Writer on linked files.** If your references/ contain URLs to external sites (gov.uk, council pages, API docs), the Technical Writer must visit each URL in a browser and verify the content is current. The SKILL.md may be factual but the supporting docs stale. This is the most common failure mode of the existing skill pattern.

**Pitfall: forgetting subdirectories.** `cp` will fail silently if the target directory doesn't exist. Always `mkdir -p` references/ templates/ and scripts/ before copying.

**Pitfall: partial install prompts.** If the user's Hermes agent doesn't copy references/ and templates/, the skill loads SKILL.md but the agent can't link to supporting files. The install prompt MUST list every subdirectory.

This is effectively the skill-publishing pipeline but with skill-writer's generation approach for any content that needs writing fresh (README, .gitignore). The source is an existing .hermes skill; the output is a new directory in Hermes-Skills. Do NOT run skill-writer's full 8-step intake — there is no description to intake, the material is already written.

## Configuration Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HERMES_SKILLS_REPO_PATH` | Yes | — | Absolute path to the Hermes-Skills repository |
| `HERMES_SKILLS_REPO_URL` | Yes | — | Git remote URL |
| `SKILL_AUTHOR_NAME` | No | `Your Name` | Attribution name |
| `SKILL_AUTHOR_URL` | No | `https://github.com/your-username` | Attribution URL |
| `PEER_REVIEW_ENABLED` | No | `true` | Run peer review |

## References

- `references/agentskills-io-spec.md` — Key compliance points for the agentskills.io open standard. Load when generating any new skill's frontmatter.