# phone-agent-front-door

Give your own AI agent a telephone number.

You dial, a menu answers in under a second, and pressing a digit gets you either a
cached answer or a conversation with your agent behind a six-digit PIN. The agent can
read; it cannot send, delete or restart anything, because those functions were never
written.

Includes a working gateway you can adapt, a pre-flight that proves your credentials
without writing anything, and the four failures that cost a working day between them.

## Prerequisites

**1. A Twilio account with voice credit.** Not SMS. A trial account adds a trial
message to calls and restricts inbound, so test with a funded account.

**2. A phone number, bought in the region your account serves.** This matters more
than any other step. A number provisioned outside the account's region can be
configured perfectly and still never receive a PSTN call, with no inbound record and
no error anywhere. Buy it in the console, tick Voice. See
`references/twilio-gotchas.md` before you debug anything.

**3. Somewhere safe to keep the credentials.** Strongly advised: a secrets manager
(Infisical, HashiCorp Vault, 1Password, Bitwarden, SOPS, `pass`). Minimum acceptable:
a `0600` file on the host. Do not put the auth token in a committed config file and
do not paste it into a chat window. The gateway talks to any of these through a
command hook, so you are not locked into a vendor.

You also need an HTTPS URL that Twilio can reach. A reverse proxy on a VPS, or a
tunnel from a machine behind NAT. The tunnel needs no open port.

## Installation

Copy the skill into your Hermes skills directory:

```bash
git clone https://github.com/ciberjohn/Hermes-Skills.git /tmp/hermes-skills
mkdir -p ~/.hermes/skills/devops/phone-agent-front-door/{references,scripts,templates}
cp /tmp/hermes-skills/phone-agent-front-door/SKILL.md \
   ~/.hermes/skills/devops/phone-agent-front-door/
cp /tmp/hermes-skills/phone-agent-front-door/references/* \
   ~/.hermes/skills/devops/phone-agent-front-door/references/
cp /tmp/hermes-skills/phone-agent-front-door/scripts/* \
   ~/.hermes/skills/devops/phone-agent-front-door/scripts/
cp /tmp/hermes-skills/phone-agent-front-door/templates/* \
   ~/.hermes/skills/devops/phone-agent-front-door/templates/
```

### Install with your agent instead

```text
> "Install the phone-agent-front-door skill from github.com/ciberjohn/Hermes-Skills.
> Clone the repo, copy SKILL.md into ~/.hermes/skills/devops/phone-agent-front-door/,
> the contents of references/ into .../references/, the .py files from scripts/ into
> .../scripts/ and templates/ into .../templates/. Create the subdirectories if they
> do not exist. Then ask me these questions one at a time:
> 1. What is your Twilio account SID? `PHONE_AGENT_TWILIO_ACCOUNT_SID`
> 2. What is the COMMAND that prints your auth token, for example
>    `op read op://Private/Twilio/auth_token`? Do not ask me for the token itself, and
>    stop me if I start typing one. `PHONE_AGENT_TWILIO_AUTH_TOKEN_CMD`
> 3. Which phone numbers may reach the menu? `PHONE_AGENT_ALLOWLIST`
> 4. What HTTPS URL will Twilio call, hostname only? `PHONE_AGENT_PUBLIC_URL`
> Do not ask me for the PIN. Generate one locally instead:
> `python3 -c "import secrets;print(''.join(str(secrets.randbelow(10)) for _ in range(6)))"`,
> write it straight to a 0600 file, and set `PHONE_AGENT_PIN_FILE` to that path. Show me
> the path, never the digits. Then write a .env with chmod 600 for the non-secret
> values, run 'cd ~/.hermes/skills/devops/phone-agent-front-door && set -a && . ./.env
> && set +a && python3 scripts/doctor.py', show me the output, and never print a secret
> value back to me. Then tell me it is ready and what to set as the number's Voice
> webhook."
```

## Variables

Resolution order for every secret: `<NAME>_CMD`, then `<NAME>_FILE`, then `<NAME>`.

| Variable | Required | Description | Example |
|---|---|---|---|
| `PHONE_AGENT_TWILIO_AUTH_TOKEN` | Yes | The token that signs webhooks | via `_CMD` or `_FILE` |
| `PHONE_AGENT_TWILIO_ACCOUNT_SID` | Yes | Account that owns the number | `ACxxxxxxxx…` |
| `PHONE_AGENT_PIN` | Yes | 6 to 10 digits; the keypad collects exactly this many | via `_CMD` or `_FILE` |
| `PHONE_AGENT_ALLOWLIST` | Yes | Allowed callers, E.164, comma separated | `+15550000001` |
| `PHONE_AGENT_PUBLIC_URL` | Advised | HTTPS hostname Twilio calls, no path | `https://voice.example.com` |
| `PHONE_AGENT_ALLOW_ANY` | No | `1` runs with no allowlist, deliberately | `1` |
| `PHONE_AGENT_DATA` | No | Attempt and lockout state | `~/.local/share/phone-agent` |
| `PHONE_AGENT_PORT` | No | Loopback port | `8097` |
| `PHONE_AGENT_HOST` | No | Bind address; non-loopback refused | `127.0.0.1` |
| `PHONE_AGENT_PIN_TRIES` | No | Failures before lockout | `3` |
| `PHONE_AGENT_LOCKOUT_SECONDS` | No | Lockout duration | `3600` |
| `PHONE_AGENT_VOICE` | No | Text-to-speech voice | `Polly.Amy-Neural` |
| `PHONE_AGENT_LANGUAGE` | No | Speech language | `en-GB` |

## Directory structure

```text
phone-agent-front-door/
├── SKILL.md                    # the build order and the pitfalls
├── README.md                   # this file
├── .gitignore
├── references/
│   ├── credentials.md          # the four-shape secrets ladder
│   └── twilio-gotchas.md       # failure catalogue with the check for each
├── scripts/
│   ├── gateway_starter.py      # working FastAPI + TwiML gateway
│   └── doctor.py               # pre-flight, writes nothing
└── templates/
    └── env.example
```

## How to use

```bash
pip install fastapi uvicorn

# Preferred: a command hook, so the token never lives in a file or the environment.
export PHONE_AGENT_TWILIO_AUTH_TOKEN_CMD='your-vault-cli read -name TWILIO_AUTH_TOKEN'
export PHONE_AGENT_TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export PHONE_AGENT_ALLOWLIST=+15550000001
export PHONE_AGENT_PUBLIC_URL=https://voice.example.com
export PHONE_AGENT_PIN_FILE=~/.config/phone-agent/pin   # chmod 600, 6-10 digits

python3 scripts/doctor.py           # credential lengths, backend used, one live API call
python3 scripts/gateway_starter.py  # listens on 127.0.0.1:8097
```

For a local test you may keep the values in a `.env` instead, but that is the last
rung of the ladder: `cp templates/env.example .env && chmod 600 .env`, fill it in,
then `set -a; . ./.env; set +a`. Do not use it for anything exposed to the internet.

Put HTTPS in front of it and set the number's **Voice webhook** to
`https://<your-host>/voice`, method `POST`.

Then wire your agent into `answer()` in `gateway_starter.py`. That function is the
only place the call reaches a model, and it is behind the PIN by construction.

## Output files

| File | What it is |
|---|---|
| screen output | `doctor.py`: credential lengths, backend used, one live API result |
| `~/.local/share/phone-agent/attempts.json` | PIN attempt counters and lockout timestamps, mode 0600 |
| TwiML responses | what the caller hears; nothing is persisted |

## Customising

- **The menu.** Add digits in `menu()`. Keep every new digit on the fast path; only
  one should be slow.
- **The voice.** `PHONE_AGENT_VOICE` and `PHONE_AGENT_LANGUAGE`.
- **The gate.** The PIN is a shared secret. If you need per-person identity, this is
  the wrong primitive; use a signed link or a real authentication step instead of
  inventing a cleverer PIN.
- **The agent.** `answer()` takes a string and returns a string. Keep the tool surface
  read-only, and keep any write capability out of this process entirely.

## Contributing and licence

MIT. Issues and pull requests welcome at
[github.com/ciberjohn/Hermes-Skills](https://github.com/ciberjohn/Hermes-Skills).

Nothing in this skill contains a hostname, domain, phone number or credential. If you
adapt it, keep it that way: the point of publishing the pattern is that your estate
stays yours.
