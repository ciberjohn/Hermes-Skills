---
name: phone-agent-front-door
description: "Twilio voice IVR in front of your AI agent: build or debug."
license: MIT
metadata:
  version: "1.1.0"
  platforms: "linux, darwin"
  tags: "telephony, twilio, ivr, voice, agents, security"
  related_skills: "skill-publishing"
---

# Phone Agent Front Door

Give your own agent a telephone number. The caller hears a menu in under a second,
presses a digit, and reaches your agent only if they asked for it and passed a gate.
Everything else is answered from a cache.

This skill is the build order, the trust model, and the four failures that cost a
day. Read it before writing code: the failures are cheap to avoid and expensive to
diagnose, because a broken phone call tells you almost nothing.

## When to Use

- You want to ask your agent something while walking, driving, or away from a screen.
- You already run a server, a homelab, or a VPS with your agent on it.
- You want a menu in front of an agent rather than an agent answering a phone blind.
- You are debugging one you already built: callers hear a rejection, the number never
  rings, or the signature check fails while your own tests pass.
- You are rotating the auth token, the PIN, or the number itself.

Not for: outbound alerting calls (different problem, different design), or anything
where the caller must be identified to a legal standard. Caller ID is not identity.

## Prerequisites

Three, in this order. Each one has a failure mode that looks like someone else's fault.

**1. A Twilio account with voice credit.** Not SMS. A trial account can call out but
places limits on inbound and plays a trial message, so use a funded account for a
fair test.

**2. A phone number, bought in the region your account actually serves.** This is the
one that wastes a day. Region and realm are not cosmetic: a number provisioned
outside the account's own region can be configured perfectly and still never receive
a PSTN call. Nobody will tell you this. Symptoms and the check are in
`references/twilio-gotchas.md`.

Buy the number in the console, tick Voice, and do not configure it by hand yet. The
gateway sets the webhook later.

**3. Somewhere safe for the credentials.** A secrets manager is strongly advised:
a self-hosted vault, a cloud secret store, 1Password, SOPS, `pass`. Failing that, a
`0600` file on the host. What you must not do is put the auth token in a config file
committed to a repository, or paste it into a chat window. The gateway resolves every
value through three interchangeable shapes: a command hook, a `0600` file, then the
environment. See `references/credentials.md`.

You also need one thing that can reach the internet over HTTPS, because Twilio must
fetch instructions from a URL. That can be a VPS with a reverse proxy, or a tunnel
from a machine behind NAT. Both work; the tunnel avoids opening a port.

## Configuration Variables

Set these in the environment, or point the `_CMD`/`_FILE` variants at a secrets
backend. Resolution order per variable: `<NAME>_CMD`, then `<NAME>_FILE`, then
`<NAME>`.

| Variable | Required | Description | Example |
|---|---|---|---|
| `PHONE_AGENT_TWILIO_AUTH_TOKEN` | Yes | The auth token that **signs the webhooks** | via `_CMD` or `_FILE` |
| `PHONE_AGENT_TWILIO_ACCOUNT_SID` | Yes, for `doctor` | The account SID that owns the number | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `PHONE_AGENT_PIN` | Yes | 6 to 10 digits; the keypad collects exactly this many | via `_CMD` or `_FILE` |
| `PHONE_AGENT_ALLOWLIST` | Yes | E.164 numbers allowed to reach the menu | `+15550000001` |
| `PHONE_AGENT_PUBLIC_URL` | Advised | The HTTPS **hostname** Twilio calls, no path | `https://voice.example.com` |
| `PHONE_AGENT_ALLOW_ANY` | No | Set to `1` to run with no allowlist, deliberately | `1` |
| `PHONE_AGENT_DATA` | No | Where attempts and lockout state live | `~/.local/share/phone-agent` |
| `PHONE_AGENT_PORT` | No | Loopback port for the gateway | `8097` |
| `PHONE_AGENT_HOST` | No | Bind address; non-loopback is refused | `127.0.0.1` |
| `PHONE_AGENT_PIN_TRIES` | No | Failures before lockout (default 3) | `3` |
| `PHONE_AGENT_LOCKOUT_SECONDS` | No | Lockout duration (default 3600) | `1800` |
| `PHONE_AGENT_VOICE` | No | Text-to-speech voice | `Polly.Amy-Neural` |
| `PHONE_AGENT_LANGUAGE` | No | Speech language | `en-GB` |

Nothing in this skill names a host, a domain, or a number. Fill those in your own
environment and keep them out of the skill directory.

## Step 0: Decide the trust boundary before the menu

Write down what a caller may do before you write a line of TwiML. A phone call is a
low-trust channel: caller IDs are trivially spoofed, and a keypad code proves the
caller knows a code, not that they may act in your name.

The rule that holds up in practice:

- **Reads are fine, after the gate.** Status, a calendar, a mailbox search.
- **Drafts are fine.** Writing a draft for a human to review is recoverable.
- **Sends, deletes, restarts and deploys are not.** Not "discouraged": absent.

Enforce it by not writing the function. A prompt can be argued with; a missing code
path cannot. If the phone process has no `send` function, no sentence unlocks one.

**Decide where the gate sits, and be honest about it.** In the starter, digits 1 and 2
are answered before the PIN, behind the allowlist only. That is fine for liveness text
("everything is reporting normally") and wrong for anything personal. If you wire a
calendar or a mailbox to a pre-PIN digit, you have published it to anyone who can
spoof a caller ID. Either move the PIN in front of every content branch, or keep those
digits to non-sensitive facts.

## Step 1: Get the number right, and tell the difference between the failures

Learn the four distinct sounds. They point at four different causes, and mixing them
up is what turns an hour into a day:

| What the caller hears | What it means |
|---|---|
| The network says the number is incorrect or invalid | The DID is not routable: wrong region, or not provisioned for inbound |
| "Goodbye." immediately, before anything else | Your gateway rejected the request, usually the signature |
| "This line is private." | Signature fine; the caller is not on the allowlist |
| A menu | Everything before the agent is working |

Log which branch fired, with the caller number, and you will never guess wrong
again. Full catalogue in `references/twilio-gotchas.md`.

## Step 2: Put the credential where it can be rotated

The auth token is the thing that proves a request came from Twilio. It must be
readable by the gateway and by nothing else.

Use the command-hook shape even if you run one specific vault, because it keeps the
gateway vendor-neutral:

```bash
export PHONE_AGENT_TWILIO_AUTH_TOKEN_CMD='your-vault-cli read -path secret/twilio -field auth_token'
```

The hook runs as an argv, not through a shell. It takes stdout, and on a non-zero exit
it reports the exit code and drops the output entirely, because a vault CLI can print
the secret in an error message and that text ends up in a log. A hang returns empty
rather than raising, for the same reason: an exception's message can contain the
command.

Confirm with `python3 scripts/doctor.py`, which prints each secret's **length** and
never its value.

## Step 3: Expose exactly one URL

Twilio fetches instructions from a public HTTPS URL within seconds of the call
arriving. It cannot reach a private network, so something must be reachable.

Keep the gateway bound to loopback and put one of these in front of it:

- A reverse proxy on a VPS you already run.
- A tunnel from a machine behind NAT (no inbound port, no firewall change).

Publish one hostname for this service. The gateway rebuilds the URL from forwarded
headers to check the signature, so pass `X-Forwarded-Proto` and `Host` through
faithfully. `PHONE_AGENT_PUBLIC_URL` is the hostname only: a path prefix there will
not appear in the rebuilt URL and every signature will fail.

**The loopback refusal only covers the documented entry point.** `python3
gateway_starter.py` refuses a non-loopback `PHONE_AGENT_HOST`, but running
`uvicorn gateway_starter:app --host 0.0.0.0` bypasses that check. If you use uvicorn
directly, keep the host argument on loopback yourself.

## Step 4: Build it menu first, model second

Answer in under a second. A caller reads two seconds of silence as a dropped line.

- Digits 1 and 2 serve cached or locally-read answers. No model.
- Digit 4 is the conversation, and it is explicitly opt-in.
- The model never runs inside a webhook. The starter says "One moment.", redirects, and
  serves the answer on a second request once the worker finishes.

`scripts/gateway_starter.py` is a working version of all of this: signature check,
closed allowlist, PIN with an enforced lockout, prompts inside the gather, a session
token so `/ask` cannot be reached without passing the PIN, and a single `answer()`
function for you to wire your agent into.

`status_text()` and `second_text()` are stubs that say "not configured yet" on
purpose. Replace them before exposing the number: a confident-sounding placeholder is
indistinguishable from a real answer, which is the worst possible outcome.

Run it:

```bash
pip install fastapi uvicorn
python3 scripts/doctor.py          # prove the credentials first
python3 scripts/gateway_starter.py # binds 127.0.0.1:8097
```

Point the number's Voice webhook (HTTP POST) at `https://<your-host>/voice`.

## Step 5: Verify without dialling

Dialling is the slowest, least informative test you have.

```bash
python3 scripts/doctor.py
```

A 200 from the live check proves the account SID and token pair is valid. It does
**not** prove the token signs webhooks, because an account can hold more than one
valid token. Signing is proven by replay, and replay needs one real request.

To get one: place a call, then take the request from the Twilio console's request
inspector, or enable capture in your proxy for a single request. Replay it with its
own `X-Twilio-Signature` against `/voice` only. A gateway that accepts the replayed
bytes and rejects the same bytes with one character changed is correct; one that
accepts your hand-built request proves only that the code agrees with itself.

**A captured request is a credential.** A valid Twilio signature carries no timestamp
or nonce, so a captured body replays forever. Keep it at mode `0600`, replay only
`/voice`, and delete it once the test passes.

**Never capture or log `/pin` or `/ask`.** Their bodies contain the caller's digits and
their words. If you must inspect them, redact `Digits`, `SpeechResult` and `Confidence`
first, and log key names and lengths rather than values.

## Step 6: Make the call, then read the log

Place the call. Then look at what the gateway logged, not at what you expected:

- Which branch fired (signature, allowlist, menu, PIN).
- How long the agent took.
- Whether any write-shaped tool appeared in the trace.

If the agent path is slow, that is the number to fix. If a tool you did not intend
appeared, the boundary is wrong and no prompt change will make it right.

## Step 7: Keep it alive

- Run the gateway under a supervisor that restarts it (systemd, s6, a container
  policy). A phone call at 2am is exactly when a crashed process is discovered.
- Refresh whatever feeds your cached answers on a timer. A stale cache is worse than
  no cache, because it sounds confident.
- Rotate the PIN after any exposure, and rotate the auth token if it ever appeared
  in a chat window, a log, or a screenshot. Then restart: a cached token survives
  revocation and your next test will lie to you.
- Know the lockout's limit. It is keyed on the caller's number, which is spoofable, so
  someone determined can lock you out of your own line. That is a denial of your
  channel, not a compromise of it. If it matters, add an out-of-band unlock (rotate
  the PIN, or a one-time code to your own device).

## Pitfalls

- **A number bought outside your account's region can never receive a call.** The
  config looks perfect, the console shows the webhook set, and callers get "incorrect
  number" from the network itself. There is no inbound call record because the call
  never arrives. Fix the region, then re-test.
- **A token that authenticates is not necessarily the token that signs.** One account
  can hold more than one valid token, and only one of them signs webhooks. Checking
  the token against the REST API proves it is valid and proves nothing about
  signing. Verify against a captured request, not against the API.
- **Blank parameters are part of the signature.** A real inbound POST carries
  parameters with empty values. Python's `parse_qs` drops them unless you pass
  `keep_blank_values=True`, and then every signature check fails while a hand-built
  test passes. The starter script sets it; keep it if you rewrite.
- **The signature covers the full URL, query string included.** Strip the query when
  rebuilding and every redirect in your flow fails validation.
- **A proxy can report the wrong scheme.** The origin often sees plain `http` for a
  call the caller made over `https`. Test the small set of readings rather than one,
  which is what `candidate_urls()` does.
- **A self-closing `<Gather/>` plays nothing.** The prompt must be nested inside it,
  or the caller gets seconds of silence after your greeting.
- **A `<Say>` placed after a `<Gather>` is dead.** When the caller presses a key, Twilio
  posts to the action URL and never plays the rest of the document.
- **The gather's `numDigits` must equal the PIN length.** A six-digit gather can never
  collect a seven-digit PIN, and the caller loops on "not right" forever.
- **An empty allowlist must not mean "everyone".** Treating it as no restriction
  publishes the menu to the whole PSTN. Refuse to start instead.
- **A lockout checked only where the PIN is requested is not a lockout.** Check it on
  every submission, including the one inside the PIN loop.
- **Never hold the webhook open for the model.** Answer immediately and fetch the
  result afterwards, or the provider times out mid-call.
- **Do not log the caller's content.** Read the transcript if you must debug, then
  delete it. The audit log should carry events and durations, not what your calendar
  says.

## References

- `references/credentials.md`: the three-shape secrets ladder and why the order matters.
- `references/twilio-gotchas.md`: the failure catalogue, with the exact check for each.
- `scripts/gateway_starter.py`: working gateway to adapt.
- `scripts/doctor.py`: pre-flight that writes nothing.
- `templates/env.example`: copy to `.env`, fill in, `chmod 600`.
