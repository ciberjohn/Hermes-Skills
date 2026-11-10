# PureGym Peak Planner

Find the genuinely quiet hours at **your** PureGym, from measured attendance
rather than "gyms are quiet at 11am".

PureGym's member API exposes live attendance only — there is no history or
forecast endpoint, and the "how busy will it be" chart in the app is not public.
So this skill samples the live headcount on a schedule, keeps a local SQLite
history, and blends what it has measured with a published-pattern prior. The
result is useful from day one and honest about it: every slot it reports is
labelled `measured`, `emerging`, `early` or `modelled`.

It is built for a Hermes agent (or any scheduler plus an LLM), but the sampler
and the dashboard are ordinary Python and run standalone.

## What you get

- **A sampler** that records one headcount every 20 minutes and never writes a
  fake zero when a gym's door counter goes offline.
- **A brief** for today or tomorrow: the two best windows, the one to avoid, and
  how much data stands behind each claim.
- **An advisor** that ranks non-overlapping two-hour windows by day.
- **A dashboard** (`dashboard/app.py`, stdlib only) with a 7×19 heatmap on
  desktop and day chips plus hour bars on a phone, meant to be published on a
  private network only.
- **A credential layer** that reads your PIN from Infisical, HashiCorp Vault,
  1Password, Bitwarden, SOPS, `pass`, a `0600` file or the environment — your
  choice, never in the repo.

## Prerequisites

- Python **3.10+** with the `requests` package. On a PEP 668 host (Ubuntu
  24.04+, Debian 12+) install it in a venv or with `--break-system-packages`
  rather than fighting the system interpreter. The dashboard needs nothing
  beyond the standard library.
- A PureGym membership: the member email and the PIN you use in the app.
- A secret store or a `0600` file to hold that PIN. See
  [`references/credentials.md`](references/credentials.md).
- Optional: a host on your private network for the dashboard, reachable over
  SSH, plus `rsync`.
- Optional: a scheduler. Hermes cron, systemd timers and plain `cron` all work.

## Installation

Copy the skill into your Hermes skills directory:

```bash
# clone into a fresh directory, not a predictable path in /tmp
src="$(mktemp -d)"
git clone https://github.com/ciberjohn/Hermes-Skills.git "$src"
mkdir -p ~/.hermes/skills/productivity/puregym-peak-planner
cp "$src/puregym-peak-planner/SKILL.md" \
   ~/.hermes/skills/productivity/puregym-peak-planner/
cp -r "$src/puregym-peak-planner/references" \
      "$src/puregym-peak-planner/scripts" \
      "$src/puregym-peak-planner/dashboard" \
      ~/.hermes/skills/productivity/puregym-peak-planner/
chmod +x ~/.hermes/skills/productivity/puregym-peak-planner/scripts/*.sh
cd ~/.hermes/skills/productivity/puregym-peak-planner   # every command below assumes this
```

Or give this prompt to your own Hermes agent and let it do the work:

```text
Install the puregym-peak-planner skill from https://github.com/ciberjohn/Hermes-Skills
into ~/.hermes/skills/productivity/puregym-peak-planner/ — copy SKILL.md, then
the contents of references/ into references/, scripts/ into scripts/ and
dashboard/ into dashboard/, creating those directories if they don't exist,
and chmod +x the .sh files. Then ask me these questions one at a time:
1. What is your PureGym member email? `PUREGYM_EMAIL`
2. How should the PIN be stored — a vault command, Infisical, or a 0600 file?
   If a vault command, ask for the command that prints it: `PUREGYM_SECRET_CMD`.
   If Infisical, ask for `INFISICAL_URL`, `INFISICAL_PROJECT_ID`, `INFISICAL_ENV`,
   `INFISICAL_SECRET_KEY` and a token file, then set `SECRET_BACKEND=infisical`.
   If a file, ask for its path: `PUREGYM_PIN_FILE`.
3. Where should the attendance database live? `PUREGYM_DATA_DIR` (default ~/.local/share/puregym)
When I answer each, write ~/.config/puregym/config.env (or config.env in the
skill directory if $HOME is redirected) with mode 0600, never echo the PIN back
to me, then run 'python3 scripts/puregym.py doctor' and show me the output.
Finally set up two scheduled jobs if I want them: a sampler every 20 minutes
from 05:00 to 23:00 Europe/London, and a brief at 07:00.
```

## Configuration

Everything is environment-driven, optionally seeded from a `0600` file. In order,
the script uses `$PUREGYM_CONFIG`, then `$XDG_CONFIG_HOME/puregym/config.env`,
then `~/.config/puregym/config.env`, then a `config.env` inside the skill
directory. Real environment variables win over the file.

The skill-directory option is the one to use when your agent runtime redirects
`$HOME` (Hermes profiles do) — `config.env` sits next to `scripts/` and is
already ignored by git.

| Variable | Required | Purpose | Example |
|---|---|---|---|
| `PUREGYM_EMAIL` | Yes | Member email used for the token exchange | `you@example.com` |
| `PUREGYM_SECRET_CMD` | One credential source | Command whose stdout is the PIN | `vault kv get -field=pin secret/puregym` |
| `SECRET_BACKEND` | One credential source | `infisical` enables the built-in reader | `infisical` |
| `PUREGYM_PIN` | One credential source | The PIN directly | `12345678` |
| `PUREGYM_PIN_FILE` | One credential source | File containing only the PIN | `~/.config/puregym/pin` |
| `PUREGYM_DATA_DIR` | No | Database, token cache and sampler log | `~/.local/share/puregym` |
| `PUREGYM_GYM_ID` | No | Pin a gym instead of using the home gym | `1234` |
| `PUREGYM_CONFIG` | No | Path to the config file | `~/.config/puregym/config.env` |
| `PUREGYM_USER_AGENT` | No | Client string the API expects | `PureGym/1523 ...` |
| `PUREGYM_SKILL_DIR` | No | Where the wrappers find `puregym.py` | the skill directory |
| `PUREGYM_DASH_HOST` | No | SSH alias of the dashboard host; enables the sync | `dash-host` |
| `PUREGYM_DASH_DIR` | No | Dashboard directory on that host | `/opt/puregym-dash` |
| `PUREGYM_DASH_URL` | No | Published dashboard URL, shown under the brief | `https://dash.example.ts.net:8443/` |
| `GYM_NAME`, `GYM_ID`, `GYM_TZ` | No | Dashboard header, id and timezone | `PureGym`, `1234`, `Europe/London` |

Infisical-specific: `INFISICAL_URL`, `INFISICAL_PROJECT_ID`, `INFISICAL_ENV`,
`INFISICAL_SECRET_KEY`, `INFISICAL_SECRET_PATH`, `INFISICAL_TOKEN` or
`INFISICAL_TOKEN_FILE`.

## Usage

```bash
# prove the configuration works — records no reading, caches no token
python3 scripts/puregym.py doctor

# take one reading
python3 scripts/puregym.py sample

# today's brief, message-ready
python3 scripts/puregym.py report --day today

# ranked windows with confidence
python3 scripts/puregym.py advise --day sat --top 3

# when you actually go
python3 scripts/puregym.py visits --top 10

# raw counts per slot
python3 scripts/puregym.py stats
```

The first `doctor` prints the gym it resolved from your membership, the live
headcount, and where the database will live. If it says `counter offline`, the
API is healthy but that gym's door counter is not — try again later or poll a
nearby gym to confirm.

### Scheduling

```cron
*/20 5-23 * * *  TZ=Europe/London PUREGYM_DATA_DIR=$HOME/.local/share/puregym $HOME/.hermes/skills/productivity/puregym-peak-planner/scripts/puregym-sample.sh
0 7 * * *        TZ=Europe/London PUREGYM_DASH_URL=https://dash.example.ts.net:8443/ $HOME/.hermes/skills/productivity/puregym-peak-planner/scripts/puregym-report.sh
```

Keep `PUREGYM_SECRET_CMD` in the `0600` config file rather than the crontab.

The sampler is silent when nothing is wrong, so wire its output to wherever you
want to be told about failures. It rate-limits itself to one alert per hour and
exits 0 even when a reading is skipped.

## Expected directory structure

```
puregym-peak-planner/
├── SKILL.md
├── README.md
├── .gitignore
├── dashboard/
│   └── app.py                 # stdlib-only single-page dashboard
├── references/
│   └── credentials.md         # every supported way to supply the PIN
├── scripts/
│   ├── puregym.py             # sampler, model, advisor, doctor, visits
│   ├── puregym-sample.sh      # scheduler wrapper, silent on success
│   ├── puregym-report.sh      # scheduler wrapper, prints the brief
│   └── puregym-dashboard-deploy.sh
└── systemd/
    └── puregym-dash.service   # hardened example unit, loopback only
```

Runtime files live outside the skill, in `$PUREGYM_DATA_DIR`:

```
~/.local/share/puregym/
├── puregym.sqlite             # the history — back this up
├── puregym_token.json         # cached bearer token, 0600, ~60 days
├── puregym-sampler.log        # last 2000 lines
└── .sampler-alert-ts          # alert rate-limit stamp
```

## The dashboard

```bash
# on the dashboard host, once
sudo useradd --system --home /opt/puregym-dash --shell /usr/sbin/nologin puregym
sudo mkdir -p /opt/puregym-dash/data
sudo cp systemd/puregym-dash.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now puregym-dash
sudo tailscale serve --bg --https=8443 http://127.0.0.1:8099
```

Edit the unit's `Environment=` lines to set `GYM_NAME`, `GYM_ID` and `DASH_PORT`
first. The service runs as its own unprivileged user with a strict systemd
sandbox, and the app itself refuses to bind anything but loopback.

The unit file must exist on the dashboard host, so copy it there or run the
whole block from a checkout on that host. After that, from the machine that
holds the database:

```bash
export DASH_HOST=dash-host PUREGYM_DASH_URL=https://dash.example.ts.net:8443/
scripts/puregym-dashboard-deploy.sh
```

Set `PUREGYM_DASH_HOST` too if you want the sampler to sync every 20 minutes;
`PUREGYM_DASH_URL` only adds the link to the brief.

**Keep it private.** The dashboard has no login and shows when a named person is
alone in a building. Bind loopback, publish over Tailscale or WireGuard, and
remember that tailnet membership is the only gate — tighten it with Tailscale
ACLs if the tailnet is shared.

## How the model works

- A prior encodes PureGym's published UK pattern — Monday and Tuesday busiest,
  Sunday quietest, weekday peak 17:00–19:30, dead 10:00–15:00 and after 21:30.
- Measured medians are rescaled so the busiest hour seen scores 100, then
  blended: `(measured * n + prior * 3) / (n + 3)`.
- Slots reach `measured` at six readings, which takes about a fortnight at one
  sample every 20 minutes. After four weeks the prior barely moves the answer.

Tune `PRIOR_WEIGHT` to change how quickly measured data takes over.

## Customising

- **A different gym**: set `PUREGYM_GYM_ID`, or leave it unset to use the home
  gym on the membership.
- **Different hours**: `--all-hours` lets 05:00 and 22:00+ starts compete.
- **A different prior**: edit `_WEEKDAY`, `_SAT` and `_SUN` in
  `scripts/puregym.py`; the dashboard has its own copy of the same curves.
- **No dashboard**: ignore `dashboard/` and leave `PUREGYM_DASH_HOST` unset —
  the sampler then only records locally.

## Security notes

- The PIN is a password. It is never printed, never logged, and never belongs in
  the repository; rotate it in the PureGym app if it is ever exposed. A failing
  secret command reports its exit code without echoing its output.
- The bearer token is cached `0600` and is refreshed automatically on 401. The
  data directory is created `0700` and a config or PIN file that is readable by
  group or others draws a warning.
- The dashboard has no authentication and refuses to bind anything but loopback
  unless you set `PUREGYM_ALLOW_REMOTE_BIND=1`. Keep it on a private overlay
  network; do not expose it to the internet.
- `PUREGYM_PIN` in the environment is visible to anything that can read the
  process environment. Prefer the vault command.

## Contributing

Issues and pull requests are welcome at
[ciberjohn/Hermes-Skills](https://github.com/ciberjohn/Hermes-Skills). If
PureGym changes its API, the failing call is almost always in the "Endpoints
that work" section of `SKILL.md` — update that first, then the code.

## License

MIT. Not affiliated with or endorsed by PureGym. Use it on your own membership
and be a decent citizen of their API.
