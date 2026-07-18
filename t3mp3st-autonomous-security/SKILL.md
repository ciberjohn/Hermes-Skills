---
name: t3mp3st-autonomous-security
description: "Autonomous security operations — install T3MP3ST, automate recon, scanning, CVE hunting, and kill-chain ops with an AI agent. Covers cloning, system setup, MCP integration, daily recon, and watchdog fleet assessment."
license: MIT
author: ciberjohn
metadata:
  version: "1.0.0"
  tags: [security, red-team, recon, scanning, automation, t3mp3st, autonomous, cve, vulnerability, kill-chain, mcp]
  platforms: [linux, darwin]
  related_skills: [devsecops-review, recurring-analysis-cron]
---

# T3MP3ST — Autonomous Security Operations

> ⚠️ **Authorised use only.** This skill runs offensive security tools (nmap, hydra, nikto, sqlmap). Only scan systems you own or have explicit written permission to test. Unauthorised scanning is illegal in most jurisdictions.

> *Autonomous AI-powered security operations — recon, scanning, CVE hunting, exploitation (human-gated), and kill-chain management.*

## Overview

**T3MP3ST** is an autonomous security operations framework installed from `github.com/elder-plinius/T3MP3ST`. It provides full-spectrum offensive and defensive security capability — recon, scanning, vulnerability detection, exploitation (human-gated), and post-exploitation cleanup — backed by an LLM-driven AI agent with 80+ tools.

T3MP3ST integrates with Hermes via MCP (port 3333) and can be dispatched as a delegated task or run autonomously via CLI commands, cron jobs, or its War Room UI.

**Key capabilities:**
- Autonomous target reconnaissance (internal + external)
- CVE hunting and vulnerability scanning
- Full MITRE ATT&CK kill chain (TA0043 → TA0007 → TA0001)
- War Room UI at `http://127.0.0.1:3333/ui/`
- MCP server for Hermes agent integration
- Egress-scope containment (authorized targets only)
- Evidence-led findings with retest verification

## Agent Execution Flow

When the user invokes this skill, follow these steps in order:

1. **Read configuration** — load the `{{VARIABLE}}` table below. If any required vars are unset, ask the user one at a time.
2. **Install T3MP3ST** — clone the repo, run `npm install`.
3. **Create `.env`** — write all environment variables from the config section.
4. **Run `npm run doctor`** — verify the installation. If critical checks fail, install missing dependencies and retry.
5. **Report to user** — show the doctor output, confirm readiness, and give example commands.

## Configuration Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `{{T3MP3ST_PATH}}` | Yes | `~/t3mp3st` | Absolute path where T3MP3ST is installed |
| `{{OPENROUTER_API_KEY}}` | Yes | — | OpenRouter API key for LLM-driven operations |
| `{{T3MP3ST_PORT}}` | No | `3333` | Port for MCP server and War Room UI |
| `{{SCOPE_TARGETS}}` | No | `127.0.0.1` | Comma-separated authorised targets — written to `.env` for T3MP3ST's egress-scope containment |
| `{{FLEET_HOSTS}}` | No | (optional) | Space-separated hostnames or IPs for fleet assessment (NOT JSON — bash array format) |
| `{{HERMES_SCRIPTS_DIR}}` | No | `~/.hermes/scripts` | Scripts directory for cron job scripts |

## Prerequisites

### System Requirements
- **Node.js v22+** and **npm**
- **OpenRouter API key** — get one at https://openrouter.ai/keys
- **External security tools:** `nmap`, `hydra`, `nikto`, `sqlmap`, `whois`, `jq`, `curl`, `wget`, `dig`

  - Debian/Ubuntu: `sudo apt install nmap hydra nikto sqlmap whois jq curl wget dnsutils`
  - macOS: `brew install nmap hydra nikto sqlmap whois jq curl wget bind`
  - Fedora/RHEL: `sudo dnf install nmap hydra nikto sqlmap whois jq curl wget bind-utils`

### Optional Extras
- `nuclei` — high-value vulnerability scanner
- `semgrep` — supply-chain scanner
- `promptfoo` — AI evaluation runner

## How to Use

### 1. Install T3MP3ST

```bash
git clone https://github.com/elder-plinius/T3MP3ST.git {{T3MP3ST_PATH}}
cd {{T3MP3ST_PATH}}
npm install
```

### 2. Configure `.env`

```bash
cat > {{T3MP3ST_PATH}}/.env << 'EOF'
OPENROUTER_API_KEY={{OPENROUTER_API_KEY}}
T3MP3ST_FULL_ARSENAL=false
T3MP3ST_STATE_DIR={{T3MP3ST_PATH}}/state
T3MP3ST_PORT={{T3MP3ST_PORT}}
SCOPE_TARGETS={{SCOPE_TARGETS}}
EOF
chmod 600 {{T3MP3ST_PATH}}/.env
```

> **Security:** The `.env` file contains your API key — `chmod 600` restricts it to file owner only. Never commit this file to version control.

> **Note on `T3MP3ST_FULL_ARSENAL`:** This defaults to `false`, which enables a safe subset of tools (recon, scanning). Set to `true` to enable all 80+ tools including hydra, sqlmap, and credential-based tooling — but only if you understand the risks and have explicit authorisation for every target.

### 3. Verify Installation

```bash
cd {{T3MP3ST_PATH}} && npm run doctor
```

All critical checks must pass (git, node, npm, file, curl, dig, whois, nmap, npm scripts, source files). Optional tool warnings are normal.

**If a critical check fails:** identify the missing dependency, install it with your system package manager, then re-run `npm run doctor`.

### 4. Start MCP Server (for Hermes Integration)

```bash
cd {{T3MP3ST_PATH}} && npm run mcp &
```

This enables agent-to-agent communication so Hermes can dispatch autonomous security tasks directly.

To stop the server later:
```bash
kill $(lsof -t -i :{{T3MP3ST_PORT}}) 2>/dev/null || pkill -f 'npm run mcp'
```

## Core Commands

### Server & UI
```bash
# War Room UI — web interface at http://127.0.0.1:{{T3MP3ST_PORT}}/ui/
cd {{T3MP3ST_PATH}} && npm run server

# MCP server — agent-to-agent communication
cd {{T3MP3ST_PATH}} && npm run mcp

# Production MCP server
cd {{T3MP3ST_PATH}} && npm run mcp:prod
```

### Autonomous Hunting
```bash
# CLI-based autonomous hunt (ideal for cron jobs)
cd {{T3MP3ST_PATH}} && npm run cli-hunt

# Multi-agent swarm mode
cd {{T3MP3ST_PATH}} && npm run swarm
```

### Benchmarks & Verification
```bash
cd {{T3MP3ST_PATH}}
npm run cve:bench              # CVE hunting benchmarks (simulated)
npm run cve:bench:live         # CVE hunting with live targets
npm run cve:bench:adversarial  # Adversarial CVE benchmarks
npm run verify-claims          # Verify benchmark data integrity
```

### System Health
```bash
cd {{T3MP3ST_PATH}}
npm run doctor              # Full system check
npm run arsenal:smoke       # Verify all 80+ tools
npm run field:drill         # End-to-end mission simulation
npm run exploit:smoke       # Exploit chain smoke test
```

## Daily Recon Pattern

### Step 1: Health Check
```bash
cd {{T3MP3ST_PATH}} && npm run doctor
```

### Step 2: Start MCP
```bash
cd {{T3MP3ST_PATH}} && npm run mcp &
```

### Step 3: Run Autonomous Hunt
```bash
cd {{T3MP3ST_PATH}} && npm run cli-hunt
```

### Step 4: Review Output
```bash
ls -la {{T3MP3ST_PATH}}/output/
```

### Step 5: Verify State
```bash
cd {{T3MP3ST_PATH}} && npm run doctor
```

## The Kill Chain

T3MP3ST implements a six-phase autonomous kill chain. Phases 3+ require **human confirmation** — the agent pauses, emits a confirmation request (via CLI prompt, War Room UI, or Hermes chat), and waits for explicit approval before proceeding. This is not a soft check — without approval, the phase does not execute.

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Reconnaissance | ✅ Active | Active scanning, service discovery, port enumeration, DNS recon |
| 2. Scanner | ✅ Active | Vulnerability scanning, CVE matching, service enumeration |
| 3. Exploiter | ⚠️ Human-gated | Exploit chain construction, vulnerability verification — requires explicit approval |
| 4. Infiltrator | ⚠️ Human-gated | Persistence assessment, lateral movement paths — requires explicit approval |
| 5. Exfiltrator | 🔴 Inactive | No data extraction. Evidence collection (nmap logs, scan results) is handled by Phases 1–2 |
| 6. Ghost | 🔴 Inactive | Post-exploitation cleanup — manual Captain-only operation. Not available for autonomous use |

**Key safety rules:**
- Phase 3+ requires explicit human approval — the agent will not proceed without it
- Egress-scope containment — operations are denied against off-scope targets
- No raw secrets, credentials, or private keys copied into evidence
- All findings require evidence and retests before becoming confident claims
- Retest is performed by re-running the relevant scanner against the target

## MCP Integration

Once T3MP3ST's MCP server is running, Hermes agents can call tools directly:

```bash
# Via heredoc (cleaner than inline JSON escaping)
cd {{T3MP3ST_PATH}}
cat <<'JSONRPC' | npm run mcp 2>/dev/null
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"security_recon","arguments":{"target":"{{SCOPE_TARGETS%%\,*}}","scan_type":"quick"}}}
JSONRPC
```

> **Note:** `2>/dev/null` suppresses MCP server logs. Remove it to debug.

The MCP server exposes the `security_recon` tool on stdio transport with target validation and command allowlisting.

## Fleet Assessment (Cron)

For users managing multiple hosts, T3MP3ST supports a silent-watchdog fleet assessment cron job. The script scans all defined hosts with nmap ping checks and only reports when hosts are unreachable.

### Create the Script

Create this file at `{{HERMES_SCRIPTS_DIR}}/t3mp3st-fleet-assessment.sh`:

```bash
#!/bin/bash
# Silent-watchdog fleet assessment — output only when issues are found
# ⚠️ Security: ensure {{FLEET_HOSTS}} only contains valid hostnames/IPs.
#   Shell metacharacters (;, `, $()) in host values create command injection risk.
set -euo pipefail

T3MP3ST_PATH="{{T3MP3ST_PATH}}"
HOSTS=( {{FLEET_HOSTS}} )
REPORT="$T3MP3ST_PATH/output/fleet-assessment-$(date +%Y-%m-%d).md"
ISSUES=0

for HOST in "${HOSTS[@]}"; do
  # Validate hostname/IP (basic check — only alphanumerics, dots, hyphens)
  if ! echo "$HOST" | grep -qE '^[A-Za-z0-9._-]+$'; then
    echo "⚠️  Invalid host format, skipping: $HOST"
    ISSUES=$((ISSUES + 1))
    continue
  fi

  # Ping check with timeouts to prevent hangs
  UP=$(nmap -sn -n --host-timeout 30s --max-retries 1 "$HOST" 2>/dev/null | grep -c "1 host up" || true)
  if [ "$UP" -eq 0 ]; then
    ISSUES=$((ISSUES + 1))
    echo "❌ Unreachable: $HOST"
  else
    echo "✅ Reachable: $HOST"
  fi
done

if [ "$ISSUES" -gt 0 ]; then
  {
    echo "# Fleet Assessment — $(date)"
    echo ""
    echo "Issues detected on $ISSUES host(s)."
  } > "$REPORT"
  exit 1  # Triggers cron notification (non-zero exit = alert)
fi
```

### Cron Configuration

```yaml
name: T3MP3ST Fleet Assessment — Daily Security Scan
schedule: "0 6 * * *"
script: t3mp3st-fleet-assessment.sh
# mode: no_agent means the script runs directly without LLM — zero tokens, silent on success
mode: no_agent
deliver: origin  # Sends report back to your Hermes chat
```

## Output Structure

Findings are saved to `{{T3MP3ST_PATH}}/output/`:

```
output/
├── findings-<date>.json           # Structured findings
├── recon-<date>.json              # Reconnaissance results
├── scan-<date>.json               # Scan results
├── evidence/                      # Evidence files
│   ├── nmap-<target>-<date>.txt
│   └── ...
└── logs/                          # Detailed operation logs
```

### Finding Structure

```json
{
  "finding_id": "T3MP3ST-<date>-<seq>",
  "severity": "Critical | High | Medium | Low | Info",
  "confidence": "Confirmed | Likely | Possible",
  "target": "<hostname/IP>",
  "port_service": "<port>/<service>",
  "cve": "<CVE-ID>",
  "description": "Human-readable finding",
  "impact": "What this means",
  "recommendation": "Fix or mitigate",
  "retest": "Passed | Failed | Pending"
}
```

> **Retest:** Performed by re-running the relevant scanner against the target. Status reflects the most recent retest attempt.

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|------|
| `npm run doctor` fails — API health | Server not running (optional check) | Run `npm run server` or ignore if tool-related checks pass |
| `npm run doctor` fails — missing tool | Tool not installed | `sudo apt install <pkg>` (Linux) or `brew install <pkg>` (macOS) |
| `SCOPE DENIED` errors | Target not in authorized scope | Verify target authorisation; check `SCOPE_TARGETS` in `.env` |
| MCP server won't start | Port `{{T3MP3ST_PORT}}` already in use | `ss -tlnp \| grep {{T3MP3ST_PORT}}` or `fuser {{T3MP3ST_PORT}}/tcp` to find the process |
| `OPENROUTER_API_KEY` not found | `.env` not configured | Check `{{T3MP3ST_PATH}}/.env` exists with valid key and permissions (`chmod 600`) |
| Hermes `terminal()` returns empty results | `$HOME` override in profile isolation | Prefix commands with `HOME=/home/<your-username>` (the real user home, not the profile's isolated home). Verify with `echo $HOME` |
| Orphaned MCP server processes | Background server never stopped | `pkill -f 'npm run mcp'` or `kill $(fuser {{T3MP3ST_PORT}}/tcp 2>/dev/null)` |

## Safety Rules

1. **No third-party target without explicit authorisation** — unauthorised scanning is illegal.
2. **No production writes without named approval** — Phase 3+ requires human confirmation.
3. **No copying raw secrets, tokens, credentials, or private keys into evidence.**
4. **All findings require evidence and retests before becoming confident claims.**
5. **`T3MP3ST_FULL_ARSENAL=false` by default** — set to `true` only if you understand the full risk.

## References

- T3MP3ST source: `https://github.com/elder-plinius/T3MP3ST`
- OpenRouter API: `https://openrouter.ai/keys`
- MITRE ATT&CK: `https://attack.mitre.org/`

---

> *Autonomous security operations — always verify, never trust without evidence.*
