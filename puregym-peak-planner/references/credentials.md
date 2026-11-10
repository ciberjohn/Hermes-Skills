# Supplying the PureGym PIN

The sampler needs the member's PIN exactly once per token exchange, and a token
lasts about 60 days. The PIN is a password: it must never be written into
`SKILL.md`, a README, a chat message, a git commit, a cron definition or a log
line. `puregym.py doctor` resolves it and prints only its **length**.

The skill deliberately does not care which secret manager you use. It supports
four shapes, in this order of preference:

| Shape | Variable | Good for |
|---|---|---|
| A command that prints the PIN | `PUREGYM_SECRET_CMD` | Any vault with a CLI |
| Infisical's REST API | `SECRET_BACKEND=infisical` | Self-hosted Infisical |
| A `0600` file | `PUREGYM_PIN_FILE` | A locked-down host, or CI |
| An environment variable | `PUREGYM_PIN` | A one-off run in a shell you control |

> **Rule of thumb:** if a value can be read by `ps e`, `env`, `docker inspect`
> or a process dump, it is not a secret store. Use the command hook and let the
> vault do the authorising.

## The universal hook: `PUREGYM_SECRET_CMD`

The command is run with `sh -c`, its **stdout** is used as the PIN, and its
stderr is only surfaced (truncated) if it fails. First line of stdout wins, so
CLI noise on stderr is harmless.

```bash
# HashiCorp Vault (KV v2)
export PUREGYM_SECRET_CMD='vault kv get -field=pin secret/puregym'
# needs VAULT_ADDR and VAULT_TOKEN (or a token helper) in the scheduler's env

# 1Password CLI
export PUREGYM_SECRET_CMD='op read op://Private/PureGym/pin'

# Bitwarden CLI (unlocked, session in BW_SESSION)
export PUREGYM_SECRET_CMD='bw get password "PureGym PIN"'

# SOPS + age
export PUREGYM_SECRET_CMD="sops -d --extract '[\"puregym\"][\"pin\"]' ~/secrets/apps.yaml"

# pass
export PUREGYM_SECRET_CMD='pass show puregym/pin'

# AWS Secrets Manager
export PUREGYM_SECRET_CMD='aws secretsmanager get-secret-value --secret-id puregym/pin --query SecretString --output text'

# 1Password item stored as JSON, or any tool that needs jq
export PUREGYM_SECRET_CMD='op item get PureGym --format json | jq -r .fields[] | select(.id=="pin") | .value'
```

Put the export in the `0600` config file rather than in the crontab, which is
world-readable on most systems:

```bash
install -d -m 700 ~/.config/puregym
cat > ~/.config/puregym/config.env <<'EOF'
PUREGYM_EMAIL=you@example.com
PUREGYM_SECRET_CMD=vault kv get -field=pin secret/puregym
EOF
chmod 600 ~/.config/puregym/config.env
```

The file is parsed as `KEY=VALUE` with optional surrounding quotes; values are
not shell-expanded. `PUREGYM_SECRET_CMD` is the one value that is later run,
through `sh -c`, exactly as written. Real environment variables beat the file,
and if several credential shapes are configured the first in the table wins, so
a leftover exported `PUREGYM_PIN` cannot shadow the vault.

### Scheduled runs and locked vaults

A scheduled job cannot type a master password. Whatever backend you choose must
be readable non-interactively at the moment the cron fires — an AppRole/
token/API key for Vault, a service-account token for 1Password, an unlocked
keyring for the desktop agents. If your vault locks overnight, the 05:00 sample
will fail; either unlock it before that window, or give the agent a credential
scoped to reading this one secret.

## Built-in Infisical reader

`SECRET_BACKEND=infisical` reads the PIN over Infisical's REST API:

```bash
PUREGYM_EMAIL=you@example.com
SECRET_BACKEND=infisical
INFISICAL_URL=https://vault.example.com
INFISICAL_PROJECT_ID=<project uuid>
INFISICAL_ENV=prod
INFISICAL_SECRET_KEY=PureGym
INFISICAL_SECRET_PATH=/
INFISICAL_TOKEN_FILE=~/.infisical-auth
```

`INFISICAL_TOKEN_FILE` may hold either a bare token or `KEY=VALUE` lines that
include `INFISICAL_TOKEN` (the format `infisical` itself writes). `INFISICAL_TOKEN`
in the environment wins over the file. The token needs read access to that
project and environment only.

If your Infisical is reachable only on a private network, reach it over that
network — Tailscale Serve, WireGuard, an SSH tunnel — rather than exposing the
instance publicly. A tunnel opened by hand is fine:

```bash
ssh -fN -L 18080:127.0.0.1:8080 you@vault-host
INFISICAL_URL=http://127.0.0.1:18080
```

## Plain file, or plain environment

```bash
install -m 600 /dev/null ~/.config/puregym/pin
printf '%s' '12345678' > ~/.config/puregym/pin    # no trailing newline needed
export PUREGYM_PIN_FILE=~/.config/puregym/pin
```

`PUREGYM_PIN` in the environment works for a single run, but it is visible to
anything that can read the process environment. Use it for a first test, not
for the sampler's permanent configuration.

## Rotation

The PIN is changed in the PureGym app (or on the website), not in this skill.
After changing it:

1. Update the secret in whichever backend you use.
2. Delete the cached bearer token: `rm "$PUREGYM_DATA_DIR/puregym_token.json"`
   (the skill's data directory, by default `~/.local/share/puregym`).
3. Run `python3 scripts/puregym.py doctor` and confirm the PIN resolves and a
   live count comes back.

If the PIN was ever pasted into chat, a commit or a log, rotate it first and
clean up second — assume it is compromised.
