---
name: puregym-peak-planner
description: "PureGym quiet hours from live attendance sampling."
license: MIT
metadata:
  version: "1.0.0"
  tags: [puregym, gym, attendance, fitness, scheduling, infisical, vault]
  platforms: [linux, darwin]
  related_skills: [gymcoach]
---

# PureGym Peak Planner

Answer "when is my gym quietest?" from measured data instead of gym folklore.
The PureGym member API publishes live attendance only, so this skill samples the
headcount on a schedule, keeps a local history, and blends it with a
published-pattern prior. Every slot it reports carries a confidence label:
`measured`, `emerging`, `early` or `modelled`.

## When to Use

- "When's the quietest time to go to the gym?" / "is it busy right now?"
- Planning a training slot for today, tomorrow or a named weekday.
- Explaining, adjusting or debugging the daily quiet-hours brief.
- Anything involving PureGym attendance data, the sampler, or its credential.

## Configuration Variables

Set them as environment variables, or in a `KEY=VALUE` file at
`$PUREGYM_CONFIG` (mode `0600`), otherwise the first existing file of
`$XDG_CONFIG_HOME/puregym/config.env`, `~/.config/puregym/config.env` or
`config.env` inside this skill's directory. Real environment variables always
win over the file, and the shell wrappers read the same file, so both halves of
the skill agree on paths.

The skill-directory option exists because agent runtimes sometimes redirect
`$HOME` (Hermes profiles do), which makes `~/.config` point somewhere other
than the human's config. Dropping `config.env` next to `scripts/` keeps the
skill self-contained per profile.

| Variable | Required | Purpose | Example |
|---|---|---|---|
| `PUREGYM_EMAIL` | Yes | Member email, used as the token-exchange username | `you@example.com` |
| `PUREGYM_SECRET_CMD` | Credential source | Shell command whose stdout is the member PIN — the universal vault hook | `vault kv get -field=pin secret/puregym` |
| `SECRET_BACKEND` | Credential source | Set to `infisical` to use the built-in Infisical reader | `infisical` |
| `PUREGYM_PIN_FILE` | Credential source | Path to a `0600` file containing only the PIN | `~/.config/puregym/pin` |
| `PUREGYM_PIN` | Credential source | The PIN directly. Fine for one run, worst for a scheduler | `12345678` |
| `PUREGYM_DATA_DIR` | No | Where the database, token cache and sampler log live | `~/.local/share/puregym` |
| `PUREGYM_GYM_ID` | No | Pin a gym instead of using the member's home gym | `1234` |
| `PUREGYM_CONFIG` | No | Path to the config file | `~/.config/puregym/config.env` |
| `PUREGYM_USER_AGENT` | No | Client string the API expects | `PureGym/1523 CFNetwork/1312 Darwin/21.0.0` |
| `PUREGYM_SKILL_DIR` | No | Where the wrappers find `puregym.py` (defaults to the skill directory) | `/opt/puregym-skill` |
| `PUREGYM_DASH_HOST` | No | SSH alias of the dashboard host; enables the database sync | `dash-host` |
| `PUREGYM_DASH_DIR` | No | Dashboard directory on that host | `/opt/puregym-dash` |
| `PUREGYM_DASH_URL` | No | Published dashboard URL, appended to the brief | `https://dash.example.ts.net:8443/` |
| `GYM_NAME`, `GYM_ID`, `GYM_TZ` | No | Dashboard header, id and timezone (dashboard only) | `PureGym`, `1234`, `Europe/London` |

Only `PUREGYM_EMAIL` plus one credential source is mandatory. See
`references/credentials.md` for concrete commands for Infisical, HashiCorp
Vault, 1Password, Bitwarden, SOPS, `pass` and plain files.

## Credentials — never paste the PIN

The PIN is a password: it must never appear in chat, in a repository, in a
prompt or in a log. The sampler reads it at runtime from whichever backend is
configured, uses it for one token exchange, and stores only the resulting
bearer token (`0600`, 60-day life, auto re-auth on 401).

Any of these are acceptable ways to hand the PIN to the agent, and they are
tried most-secure-first. Code and docs agree on this order:

1. `PUREGYM_SECRET_CMD` — any vault CLI (Infisical, Vault, 1Password, SOPS...).
2. `SECRET_BACKEND=infisical` — the built-in REST reader.
3. `PUREGYM_PIN_FILE` — a `0600` file outside the repository.
4. `PUREGYM_PIN` — an environment variable, last resort.

If more than one is configured the first wins, so a stray exported
`PUREGYM_PIN` cannot quietly shadow the vault. A failing secret command reports
its exit code only — its output is never echoed, because a vault CLI can print
the secret on error.

Pick one, verify it with `puregym.py doctor`, and leave it out of git. For a
scheduled job, prefer a backend that can be read non-interactively without an
unlock step, otherwise the 05:00 sampler will fail while the vault is locked.

## Tools

All commands live in `scripts/` inside this skill. Run them from the skill root
(the directory containing `SKILL.md`), or pass an absolute path.

| Command | Purpose |
|---|---|
| `python3 scripts/puregym.py doctor` | Check config, resolve the PIN, authenticate, read the live count. Records no reading and caches no token |
| `python3 scripts/puregym.py sample` | One live reading into `puregym.sqlite` |
| `python3 scripts/puregym.py report [--day today\|tomorrow\|mon]` | Message-ready brief |
| `python3 scripts/puregym.py advise --day today --top 3` | Ranked windows with confidence |
| `python3 scripts/puregym.py visits [--top 10]` | The member's own recent visits |
| `python3 scripts/puregym.py stats` | Raw per-slot counts, min, max, average |
| `python3 scripts/puregym.py --help` | Usage |

Windows are scored on starts between 06:00 and 21:00 by default (two-hour
windows, so the last ends at 23:00). `--all-hours` adds 05:00 and 22:00 starts.
Set `PUREGYM_DEBUG=1` to see a full traceback when a command fails; without it
you get one clean error line.

Shell wrappers for schedulers:

- `scripts/puregym-sample.sh` — runs one sample, appends to
  `$PUREGYM_DATA_DIR/puregym-sampler.log`, optionally pushes the database to a
  dashboard host, and prints only when something needs a human. Always exits 0.
- `scripts/puregym-report.sh` — prints today's brief; appends the dashboard URL
  when `PUREGYM_DASH_URL` is set.
- `scripts/puregym-dashboard-deploy.sh` — copies the dashboard app and database
  to the dashboard host, restarts it, health-checks it.

Both wrappers locate `puregym.py` from their own path, so they work wherever
the skill is installed.

Suggested cron shape (absolute paths, local timezone):

```cron
*/20 5-23 * * *  TZ=Europe/London /home/you/.hermes/skills/productivity/puregym-peak-planner/scripts/puregym-sample.sh
0 7 * * *        TZ=Europe/London PUREGYM_DASH_URL=https://dash.example.ts.net:8443/ /home/you/.hermes/skills/productivity/puregym-peak-planner/scripts/puregym-report.sh
```

Cron starts in `$HOME`, so a relative path there is a silent no-op. Use a
timezone-aware scheduler: "18:00 peak" means local wall clock, not UTC.

## Auth chain

1. Resolve the PIN in the order above.
2. `POST https://auth.puregym.com/connect/token` with
   `grant_type=password`, `username=<email>`, `password=<PIN>`,
   `scope=pgcapi offline_access`, `client_id=ro.client` and the PureGym
   user agent. The bearer token is good for about 60 days and is cached `0600`
   in `$PUREGYM_DATA_DIR/puregym_token.json`; a 401 forces one re-auth.
3. Call the v2 member API with an `Authorization: Bearer <token>` header.

For the built-in Infisical reader, the extra variables are `INFISICAL_URL`,
`INFISICAL_PROJECT_ID` (or `INFISICAL_PROJECT`), `INFISICAL_ENV` (default
`prod`), `INFISICAL_SECRET_KEY` (default `PureGym`), `INFISICAL_SECRET_PATH`
(default `/`) and `INFISICAL_TOKEN` or `INFISICAL_TOKEN_FILE`. A self-hosted
instance that is only reachable on a private network must be reached over that
network — do not expose it to the internet just to satisfy a sampler.

## Endpoints that work (v2 only)

- `GET capi.puregym.com/api/v2/member` → `HomeGym` (name/id), `MemberStatus`
- `GET capi.puregym.com/api/v2/gyms/` → all gyms (Id, Name, Location, OpeningHours)
- `GET capi.puregym.com/api/v2/gymSessions/gym?gymId=<id>` →
  `{TotalPeopleInGym, TotalPeopleInClasses, AttendanceTime, MaximumCapacity}`
  (`MaximumCapacity` is always 0 — ignore it)
- `GET capi.puregym.com/api/v2/gymSessions/member` → `Summary` plus `Visits[]`
  (`StartTime`, `Duration` in minutes, `Gym`)

Anything on `/api/v1/...` returns 403 (an HTML block page) and
`/api/v2/gyms/<id>` returns 400 UnsupportedApiVersion. Do not retry those.

## Dashboard (optional, private network only)

`dashboard/app.py` is a stdlib-only, single-file HTTP app: a 7×19 heatmap on
desktop, day chips plus hour bars and a bottom detail sheet under 640px. It
reads a read-only copy of the database, so it is as fresh as the last sync — a
view, not a second sampler.

- **It has no authentication.** It refuses any bind address other than
  loopback unless `PUREGYM_ALLOW_REMOTE_BIND=1` is set, so an empty `DASH_HOST`
  cannot silently expose it. Keep it on `127.0.0.1:8099`.
- Publish it over a private network only: `tailscale serve --bg --https=8443
  http://127.0.0.1:8099`, WireGuard, or an authenticated reverse proxy. Never
  bind `0.0.0.0` and never expose it publicly — it shows when a named person is
  alone in a building. Tailnet membership is the gate, not a per-user login;
  tighten it with Tailscale ACLs if the tailnet is shared.
- `systemd/puregym-dash.service` is a hardened example unit: dedicated user,
  `ProtectSystem=strict`, loopback only. Install it before the first deploy.
- `scripts/puregym-dashboard-deploy.sh` copies the app and database, restarts
  the service and health-checks it. Environment: `DASH_HOST` (required, the SSH
  target — a different variable from the app's `DASH_HOST` bind address),
  `DASH_REMOTE`, `DASH_SERVICE`, `DASH_PORT`, `PUREGYM_DASH_URL`. The remote
  account needs `curl` and passwordless sudo for `systemctl restart`.
- The database sync writes a dot-file inside the destination directory, mode
  `600`, then renames it, so the reader never sees a half-written database and
  other local users cannot read the staging copy.
- Set `GYM_NAME` and `GYM_ID` on the dashboard service so the header is right.

## How to answer "when should I train?"

1. Run `python3 scripts/puregym.py report --day today` (or `--day tomorrow`).
2. Quote the two best windows and the one to avoid, and keep the confidence
   wording — do not promote `modelled` to fact.
3. If `stats` shows few readings for that weekday, say so, offer `advise`
   anyway, and name the slots that are still modelled.
4. When the person is about to leave, run `sample` for the current headcount.
5. Run `visits` to see when they actually go; prefer slots they already attend
   over the emptiest ones.

## Model notes / tuning

- Prior = PureGym's published UK pattern (Mon/Tue busiest, Sun quietest,
  weekday peak 17:00–19:30, dead 10:00–15:00 and after 21:30) in
  `_WEEKDAY` / `_SAT` / `_SUN`.
- Blend: `(measured_index * n + prior * PRIOR_WEIGHT) / (n + PRIOR_WEIGHT)`;
  observations are rescaled so the busiest hour seen = 100. Thresholds: n≥6
  `measured`, ≥3 `emerging`, ≥1 `early`.
- Raise `PRIOR_WEIGHT` to trust the prior longer, lower it to trust measured
  data sooner.
- Samples 20 minutes apart grow n by ~3 per week per (weekday, hour) slot, so a
  slot becomes `measured` in about a fortnight and the prior barely matters
  after ~4 weeks.

## Pitfalls

- **`TotalPeopleInGym` can be `null`** when a gym's door counter goes offline;
  the API stays healthy and other gyms report normally. `sample` retries 3×
  (4 s apart), then records a row in `misses` and exits 0. **Never coerce null
  to 0** — a fake zero reads as "empty gym" and poisons the profile. Diagnose a
  suspected outage by polling a neighbouring gym: if it returns numbers, the
  problem is that gym's counter, not the API.
- Transient `ConnectionResetError` and timeouts from PureGym's edge are retried
  (4 attempts, 1.5 s backoff, on connect/read/5xx/429) and, if they still fail,
  logged as one line and skipped with exit 0 — a skipped sample is not an
  incident. Only genuinely uncaught exceptions should make a job shout.
- Alerts are rate-limited to one per hour via
  `$PUREGYM_DATA_DIR/.sampler-alert-ts`: a hard crash or a `WARN:` line (no live
  reading for 3 h+) pings once, then stays quiet.
- Never print the PIN, the vault token or the bearer token. Logs get counts and
  timestamps only, and a failing secret command reports its exit code without
  its output.
- A config or PIN file that is readable by group or others draws a `WARN` on
  stderr — fix the mode; the file can hold a credential.
- One database belongs to one gym. The readings table has no gym column, so
  changing `PUREGYM_GYM_ID` blends two gyms' data in one profile. Start a fresh
  `PUREGYM_DATA_DIR` instead.
- `AttendanceTime` is local wall clock with a trailing `Z`; use `london_now()`,
  not UTC, or every slot shifts by an hour.
- The sampler is silent by design: if no readings appear, read
  `$PUREGYM_DATA_DIR/puregym-sampler.log` (rc plus stderr) before blaming the
  API.
- Deleting `puregym.sqlite` throws away weeks of learning. Back it up, or move
  it aside, rather than removing it.
- The PIN is a password. If it is ever pasted into chat, a repo or a log, treat
  it as burned and change it in the PureGym app before re-seeding the vault.

## References

- `references/credentials.md` — concrete commands for reading the PIN from
  Infisical, HashiCorp Vault, 1Password, Bitwarden, SOPS, `pass`, systemd
  credentials, and a plain `0600` file, plus the trade-offs of each.
