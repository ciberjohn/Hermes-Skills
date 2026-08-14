# ciberjohn-no-slop — Hermes Agent Skill

A general-purpose writing constraint set that produces human-sounding text by eliminating statistically detectable AI patterns. Platform-neutral, voice-agnostic: use it for articles, social posts, emails, scripts, reports, documentation, or anything that must not read as AI-generated.

Merges two proven rule sets: the anti-ai-slop-writing directive by Jalaaldeen (MIT) and the detection checklist distilled from the medium-story publishing pipeline. Ships with a verification script (`no_slop_check.py`) that scans your text for violations before you ship it.

## Quick Install

Copy and paste this to your Hermes agent (any profile):

```text
Install the ciberjohn-no-slop skill into my Hermes agent. Clone
github.com/ciberjohn/Hermes-Skills to a temporary directory and copy
ciberjohn-no-slop/SKILL.md into ~/.hermes/skills/creative/ciberjohn-no-slop/SKILL.md.
If creative/ doesn't exist, create it. Then copy the contents of
ciberjohn-no-slop/references/ into ~/.hermes/skills/creative/ciberjohn-no-slop/references/
and the contents of ciberjohn-no-slop/scripts/ into
~/.hermes/skills/creative/ciberjohn-no-slop/scripts/. Create the subdirectories
if they don't exist. This skill has no configuration questions. Finally, show me
an example of how to invoke it: '/ciberjohn-no-slop' or 'write this and make it
sound human'.
```

## Prerequisites

- **Hermes Agent**: installed and configured (`pip install hermes-agent` or via [Nous Research](https://hermes-agent.nousresearch.com))
- **Python 3**: for the optional verification script (standard library only, no dependencies)

## Installation

1. Copy `SKILL.md` to your Hermes skills directory:
   ```bash
   cp ciberjohn-no-slop/SKILL.md ${SKILLS_DIR:-~/.hermes/profiles/default/skills/creative}/ciberjohn-no-slop/SKILL.md
   ```

2. Copy the supporting files:
   ```bash
   mkdir -p ${SKILLS_DIR:-~/.hermes/profiles/default/skills/creative}/ciberjohn-no-slop/references
   mkdir -p ${SKILLS_DIR:-~/.hermes/profiles/default/skills/creative}/ciberjohn-no-slop/scripts
   cp ciberjohn-no-slop/references/banned-words.md ${SKILLS_DIR:-~/.hermes/profiles/default/skills/creative}/ciberjohn-no-slop/references/
   cp ciberjohn-no-slop/scripts/no_slop_check.py ${SKILLS_DIR:-~/.hermes/profiles/default/skills/creative}/ciberjohn-no-slop/scripts/
   ```

3. Or install via the Skills Hub CLI:
   ```bash
   hermes skills tap add ciberjohn/Hermes-Skills
   hermes skills install ciberjohn/Hermes-Skills/ciberjohn-no-slop
   ```

No configuration variables are required. The skill works out of the box.

## How to Use

The skill activates automatically when you ask your agent to write anything and the output must sound human. You can also invoke it directly:

- "/ciberjohn-no-slop": apply the constraints to the next piece of writing
- "Write this tweet and make it sound human"
- "Draft the email, then run it through the no-slop check"

The bundled checker verifies any text file before shipping:

```bash
python3 scripts/no_slop_check.py path/to/file.md
```

It reports banned vocabulary, banned phrases, banned openers, em dash overuse, exclamation spam, ellipsis abuse, and checklist patterns with line numbers, and exits non-zero when violations are found.

## What It Enforces

| Category | Examples |
|----------|----------|
| Structural rules | no rule of three, no uniform sentence length, no parataxis, no hedging seesaw, no passive voice |
| Punctuation discipline | max one em dash per 500 words, max one exclamation per 1,000 words, max one ellipsis per piece |
| Banned vocabulary | delve, tapestry, testament, vibrant, pivotal, leverage, utilize, seamless, and 50+ more |
| Banned phrases | "In today's [X]", "It's worth noting", "Here's the thing", "Not just X, but Y", and 35+ more |
| Banned openers | "Moreover,", "Furthermore,", "As an AI...", "With over N years of experience...", and 16+ more |
| Accuracy rules | no invented data, no fabricated quotes, real verifiable names and dates |
| Voice calibration | match the audience's dialect and register; consistency beats uniformity |

## Directory Structure

```
ciberjohn-no-slop/
├── SKILL.md                    # Core rules and self-check
├── references/
│   └── banned-words.md         # Full banned vocabulary, phrases, openers
└── scripts/
    └── no_slop_check.py        # Verification script (stdlib only)
```

## Attribution

Adapted from [jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) (MIT, author Jalaaldeen) and the anti-slop checklist in the [medium-story](https://github.com/ciberjohn/Hermes-Skills/tree/main/medium-story) skill. Detection research basis: Carnegie Mellon (2025), Wikipedia "Signs of AI writing", Buffer 52M post analysis.

## License

MIT. Use freely, adapt as needed. Attribution appreciated but not required.
