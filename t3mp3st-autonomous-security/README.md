# T3MP3ST Autonomous Security — Hermes Skill

Autonomous security operations framework for Hermes Agent. Installs, configures, and operates **T3MP3ST** — an LLM-driven AI security agent that performs recon, scanning, CVE hunting, exploitation (human-gated), and kill-chain management with 80+ tools.

> ⚠️ **Authorised use only.** This skill runs offensive security tools. Only scan systems you own or have explicit written permission to test. Unauthorised scanning is illegal in most jurisdictions.

## What It Does

- **Autonomous recon** — nmap/DNS/whois scanning against authorised targets
- **CVE hunting** — vulnerability detection with live or simulated benchmarks
- **Kill chain ops** — six-phase MITRE ATT&CK chain (recon → scanner → exploiter → infiltrator → exfiltrator → ghost)
- **MCP integration** — Hermes agents dispatch security tasks directly via JSON-RPC
- **War Room UI** — web interface at `http://127.0.0.1:{{T3MP3ST_PORT}}/ui/`
- **Fleet assessment** — silent-watchdog cron job for multi-host security scanning
- **Swarm mode** — parallel autonomous agents covering different phases simultaneously

## Prerequisites

- **Node.js v22+** and **npm**
- **Security tools:** `nmap`, `hydra`, `nikto`, `sqlmap`, `whois`, `jq`, `curl`, `wget`, `dig`

**Optional:** OpenRouter API key (https://openrouter.ai/keys) — only if you want T3MP3ST to run fully autonomously. Without it, Hermes drives operations using your existing model.

## Installation

Copy and paste **one prompt** — your Hermes agent will do the rest:

> "Install the t3mp3st-autonomous-security skill from github.com/ciberjohn/Hermes-Skills into ~/.hermes/skills/security/t3mp3st-autonomous-security/SKILL.md. First, clone T3MP3ST from https://github.com/elder-plinius/T3MP3ST.git into a directory I specify, run npm install in it, and verify it installed correctly. Then ask me these questions one at a time:
> 1. Where should T3MP3ST be installed? `{{T3MP3ST_PATH}}` (default ~/t3mp3st)
> 2. What port should the MCP server use? `{{T3MP3ST_PORT}}` (default 3333)
> 3. What comma-separated targets should be in my daily recon scope? `{{SCOPE_TARGETS}}` (default: 127.0.0.1)
> 4. What hosts should the fleet assessment scan? `{{FLEET_HOSTS}}` (space-separated hostnames or IPs, optional)
> 5. Do you have an OpenRouter API key for T3MP3ST's internal AI? `{{OPENROUTER_API_KEY}}` (optional — leave blank to use Hermes's existing model instead)
> When I answer each, create the `.env` file with all the env vars — write the API key if provided, leave it empty otherwise — set permissions to `chmod 600`, run `npm run doctor` to confirm everything is working, show me the doctor output, then tell me the skill is ready and show me an example: '/t3mp3st-autonomous-security run a quick recon against my local targets'."

### Alternative: Manual Setup

```bash
# 1. Clone and setup T3MP3ST
git clone https://github.com/elder-plinius/T3MP3ST.git ~/t3mp3st
cd ~/t3mp3st
npm install

# 2. Configure .env (API key is optional — leave empty to use Hermes instead)
cat > ~/t3mp3st/.env << 'EOF'
OPENROUTER_API_KEY=             # optional — leave blank for Hermes-driven ops
T3MP3ST_FULL_ARSENAL=false
T3MP3ST_STATE_DIR=~/t3mp3st/state
T3MP3ST_PORT=3333
SCOPE_TARGETS=127.0.0.1
EOF
chmod 600 ~/t3mp3st/.env

# 3. Verify
npm run doctor
```

## Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `{{T3MP3ST_PATH}}` | Yes | `~/t3mp3st` | Absolute path where T3MP3ST is installed |
| `{{OPENROUTER_API_KEY}}` | No | (none) | Only needed for T3MP3ST's internal AI. Without it, Hermes drives operations using your existing model. |
| `{{T3MP3ST_PORT}}` | No | `3333` | Port for MCP server and War Room UI |
| `{{SCOPE_TARGETS}}` | No | `127.0.0.1` | Comma-separated authorised targets for egress-scope containment |
| `{{FLEET_HOSTS}}` | No | (optional) | Space-separated hostnames or IPs for fleet assessment |
| `{{HERMES_SCRIPTS_DIR}}` | No | `~/.hermes/scripts` | Scripts directory for cron job scripts |

## Directory Structure

```
Hermes-Skills/
└── t3mp3st-autonomous-security/
    ├── SKILL.md          # Full skill instructions
    └── README.md         # This file
```

## How to Use

Once installed, invoke via slash command:

```
/t3mp3st-autonomous-security run daily recon
/t3mp3st-autonomous-security scan target example.com
/t3mp3st-autonomous-security cve-benchmark live
/t3mp3st-autonomous-security setup fleet assessment for my servers
```

Or describe what you want naturally, and Hermes will auto-load the skill:

> "Run a quick security scan against my local infrastructure"

## Core Workflow

```bash
# Health check
cd {{T3MP3ST_PATH}} && npm run doctor

# Start MCP for Hermes integration
cd {{T3MP3ST_PATH}} && npm run mcp &

# Autonomous hunt
cd {{T3MP3ST_PATH}} && npm run cli-hunt

# Review findings
ls -la {{T3MP3ST_PATH}}/output/
```

## Output Files

| File | Contents |
|------|----------|
| `{{T3MP3ST_PATH}}/output/findings-<date>.json` | Structured findings with severity, confidence, evidence |
| `{{T3MP3ST_PATH}}/output/recon-<date>.json` | Reconnaissance results |
| `{{T3MP3ST_PATH}}/output/scan-<date>.json` | Scan results |
| `{{T3MP3ST_PATH}}/output/evidence/` | Raw evidence files (nmap, whois, dig outputs) |

## Safety

- **Phase 3+ (exploiter, infiltrator) requires human approval** — the agent pauses and waits for explicit confirmation
- **Egress-scope containment** — operations are denied against off-scope targets
- **No raw secrets or credentials in evidence** — finding documentation only
- **All findings require evidence and retests** before confident claims
- **`T3MP3ST_FULL_ARSENAL=false` by default** — safe subset for recon only

## Customising

- **Recon scope** — set `{{SCOPE_TARGETS}}` to your own infrastructure
- **Fleet hosts** — define `{{FLEET_HOSTS}}` for multi-host scanning in cron
- **MCP port** — change `{{T3MP3ST_PORT}}` if port 3333 is already in use
- **Arsenal level** — set `T3MP3ST_FULL_ARSENAL=true` for full 80+ tools (hydra, sqlmap, etc.) — understand the risks first

## Security

This skill is sanitised for public use:

- ✅ No secrets, tokens, or credentials
- ✅ All paths configurable through `{{VARIABLE}}` placeholders
- ✅ T3MP3ST source points to the public repo (`elder-plinius/T3MP3ST`)
- ✅ Dangerous capabilities default to `false`

## License

MIT — use freely, adapt as needed. Attribution appreciated but not required.

## Related

- [T3MP3ST source repo](https://github.com/elder-plinius/T3MP3ST) — the autonomous security framework
- [OpenRouter](https://openrouter.ai/keys) — API keys for LLM-driven operations
- [Hermes-Skills](https://github.com/ciberjohn/Hermes-Skills) — more skills for your Hermes agent
