# UK Business Consultant — Hermes Agent Skill

> **Structured business advisory for UK micro-businesses and startups.** Two-mode framework covering side hustles (£500–£2k/month) and full-time ventures (£3k–£8k/month). Includes viability scorecard, financial modelling, UK tax/regulations, and low-cost marketing playbook — calibrated for startup capital under £1,000.

## Install

Copy-paste this to your Hermes agent (any profile):

```text
Install the uk-business-consultant skill into my Hermes agent. Clone
github.com/ciberjohn/Hermes-Skills, copy uk-business-consultant/SKILL.md
into ~/.hermes/skills/creative/uk-business-consultant/SKILL.md, the
references/ folder into ~/.hermes/skills/creative/uk-business-consultant/references/,
and templates/ into ~/.hermes/skills/creative/uk-business-consultant/templates/.

Then ask me:
1. What email address should business reports be sent from?
   {{BUSINESS_CONSULTANT_EMAIL_ADDRESS}}
2. What is the full path to my email sending script?
   {{BUSINESS_CONSULTANT_EMAIL_SCRIPT}}
3. What is your city/town/region for localised advice?
   {{BUSINESS_CONSULTANT_LOCATION}}
4. What is your local council name?
   {{BUSINESS_CONSULTANT_LOCAL_COUNCIL}}

Store my answers, then show me an example query.
```

Or install manually:

```bash
# Clone the skills repo
git clone https://github.com/ciberjohn/Hermes-Skills.git ~/Hermes-Skills

# Copy skill and supporting files
cp -r ~/Hermes-Skills/uk-business-consultant ~/.hermes/skills/creative/
```

## How it Works

The skill operates as a persona — when loaded, your Hermes agent becomes **Hikaru Sulu**, a Senior Business Consultant with UK-specific knowledge of tax, regulations, and local markets in South Wales / Rhondda Cynon Taf.

### Two Modes

| Mode | Target Income | Time Commitment | Typical Capital |
|------|--------------|----------------|-----------------|
| **Side Hustle** | £500–£2,000/month | 5–15 hrs/week | £0–£200 |
| **Full-Time Venture** | £3k–£8k/month | 30–40 hrs/week | £500–£1,000 |

The skill automatically detects which mode to use based on your question, or asks if it's unclear.

### Assessment Framework

1. **Understand** — What's the goal, capital, and available time?
2. **Scorecard** — 10-factor viability assessment (market demand, founder fit, margin potential, scalability, etc.)
3. **Model** — 3-scenario financial projection (worst/base/best)
4. **Recommend** — Clear recommendation with next steps
5. **Deliver** — Professional advisory report (text or email)

## What's Included

| File | Purpose |
|------|---------|
| `SKILL.md` | Full skill definition — frameworks, regulations, marketing playbook |
| `README.md` | This file — install guide and overview |
| `.gitignore` | Excludes local config and secrets |
| `references/quick-start.md` | Step-by-step usage guide |
| `references/uk-home-food-business-regulations.md` | UK food business rules for home kitchens |
| `references/uk-micro-startup-guide.md` | Starting a UK micro-business with £500–£1,000 |
| `references/south-wales-business-opportunity-research.md` | Local market gaps in RCT / South Wales Valleys |
| `references/marketing-guide-south-wales-food-business.md` | Low-cost marketing for Welsh food businesses |
| `templates/viability-report.md` | Structured email report template |

## UK Knowledge Covered

- **Legal structure**: Sole trader vs limited company at different income levels
- **Tax**: 2026/27 thresholds, NI, VAT at £84k+ turnover, expenses
- **Food regulations**: Home kitchen registration, EHO inspections, allergen labelling, street trading licences in RCT
- **Local knowledge**: Rhondda Cynon Taf council contacts, Business Wales, Welsh Government support programmes
- **Marketing**: Google Business Profile, Facebook groups, market stall sampling — zero/low-cost channels

## Usage

Once installed, invoke the skill through your Hermes agent:

- _"I need a side hustle idea. I'm good at organising things."_
- _"I want to leave my job. Target £4,000/month. Wife can bake. We have £800 to start."_
- _"Walk me through what we need legally to sell homemade cakes in the UK."_
- _"Give me a financial model for a weekend baking business."_

The skill responds in-character as Sulu — concise, structured, actionable.

## Security

- No secrets, tokens, or API keys in the skill itself
- Email credentials stored separately (in your Hermes config or vault)
- `{{VARIABLE}}` placeholders for all user-specific values
- Publicly sanitised — no paths, hostnames, or personal data

## License

MIT — see [LICENSE](../LICENSE)
