# Technical Trainer — Course Creation Skill

> Full lifecycle technical course creation for AI and Linux topics. Market research, fact-checked content, bilingual English/Portuguese production, and B2B packaging — all via parallel sub-agents.

## Install

Copy-paste this prompt to your Hermes agent:

```
Install the technical-trainer skill from the Hermes-Skills repo. Create the directories, copy SKILL.md, copy references/research-summary.md, copy all 4 templates (module-template.md, lab-template.md, video-script-template.md, quiz-template.md), and create a .gitignore. Then set the env var ACADEMY_REPO_PATH to the path of your course repository, and set ACADEMY_REPO_NAME to your repo's name.
```

### Manual Install

```bash
# Clone the Hermes-Skills repo
git clone https://github.com/{{GITHUB_USERNAME}}/Hermes-Skills.git
cd Hermes-Skills/technical-trainer

# Create skill directory in your Hermes profile
mkdir -p ~/.hermes/profiles/your-profile/skills/creative/technical-trainer/{references,templates}

# Copy files
cp SKILL.md ~/.hermes/profiles/your-profile/skills/creative/technical-trainer/
cp references/*.md ~/.hermes/profiles/your-profile/skills/creative/technical-trainer/references/
cp templates/*.md ~/.hermes/profiles/your-profile/skills/creative/technical-trainer/templates/
```

## Setup

After installing, configure your academy repository:

```bash
# Set your course repo path and name
export ACADEMY_REPO_PATH=/path/to/your-academy-repo
export ACADEMY_REPO_NAME=your-academy-repo

# Create the directory structure
mkdir -p $ACADEMY_REPO_PATH/{en,pt,plans,templates,scripts,assets}
```

## How It Works

The skill orchestrates a 6-step pipeline to produce complete, publication-ready course materials:

```
Course Intake → Market Research → Curriculum Design → 
4× Parallel Content Sub-agents → Repository Assembly → Delivery
```

### The 4 Parallel Sub-Agents

| Agent | Role | Output |
|-------|------|--------|
| **Fact Checker** | Verifies every claim against 3 reputable sources | Verified claims table with URLs |
| **Technical Writer** | Writes full course in UK English | Scripts, labs, quizzes, slides |
| **Translator** | Converts to European Portuguese | Same structure, PT language |
| **B2B Specialist** | Creates corporate pricing packages | Per-seat, site license, workshop pricing |

## What's Included

| File | Purpose |
|------|---------|
| `SKILL.md` | Main skill definition with full 6-step pipeline |
| `references/research-summary.md` | Reference data on trainers, pricing, platforms |
| `templates/module-template.md` | Module structure template |
| `templates/lab-template.md` | 3-phase lab design (guided → scaffolded → challenge) |
| `templates/video-script-template.md` | Video script structure (hook → concept → demo → pitfalls → summary) |
| `templates/quiz-template.md` | Assessment template with 5 question types |
| `templates/slide-template.md` | Slide deck structure for module presentations |
| `.gitignore` | Prevents secrets and output from being committed |

## Usage Examples

### Create a new course

> "Load technical-trainer and create a course on Linux command line for security analysts, beginner level, for both B2C and B2B."

The skill will:
1. Ask intake questions (or use defaults)
2. Research market demand
3. Design a complete curriculum
4. Dispatch 4 parallel sub-agents for content creation
5. Assemble everything in your repo with en/ and pt/ directories

### Translate existing materials

> "Load technical-trainer and translate my course on prompt engineering from English to Portuguese."

### Build a B2B package

> "Load technical-trainer and create a B2B packaging proposal for my Linux hardening course."

### Design a learning path

> "Load technical-trainer and design a full learning path from Linux basics to AI deployment."

## Repository Structure

```
your-academy-repo/
├── en/
│   └── {course-slug}/
│       ├── README.md
│       ├── curriculum.md
│       ├── module-01/ (scripts.md, lab.md, quiz.md, slides.md)
│       ├── labs/ (instructions.md, solution.md, starter/)
│       ├── assessments/
│       └── b2b-packaging.md
├── pt/
│   └── {course-slug}/ (same structure, Portuguese)
├── plans/ (business plans per course)
└── templates/ (shared templates)
```

## Bilingual Workflow

1. Write and record in UK English first
2. Add Portuguese subtitles (AI-assisted + human review)
3. Translate written materials (labs, quizzes, slides) to PT
4. Terminal commands and code stay in English throughout

## Pricing Reference

| Tier | B2C | B2B Per-seat | Site License | Live Add-on |
|------|-----|-------------|-------------|-------------|
| Single course | £30–200 | £200–600 | £8k–15k/yr | £800–1,500/day |
| Bundle | £150–400 | £400–800 | £15k–30k/yr | £1,200–2,000/day |
| Cert track | £500–1,500 | £600–1,200 | £20k–50k/yr | £1,500–2,500/day |
| Cohort-based | £500–2,000 | N/A | £30k–100k/yr | Included |

## Security

- No API keys or tokens are stored in this skill
- GitHub operations use the `gh` CLI (your existing auth)
- All course content is version-controlled in your private repo
- Review all AI-generated lab commands before student use

## License

MIT — use, modify, and share freely.
