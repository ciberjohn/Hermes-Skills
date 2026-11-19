# Credentials: the three-shape ladder

The setup needs three values. The gateway itself reads two of them: the auth token and
the PIN. The third, the account SID, is used only by `doctor.py` for its live check,
and it is not a secret in the way the other two are.

Resolve in this order. The order is not cosmetic: the first shape that works wins,
so a stray exported variable cannot shadow the vault.

## 1. Command hook (preferred)

```bash
export PHONE_AGENT_TWILIO_AUTH_TOKEN_CMD='vault kv get -field=auth_token secret/twilio'
```

Works with anything that can print a secret to stdout: HashiCorp Vault, Infisical,
1Password (`op read`), Bitwarden (`bw get`), SOPS (`sops -d`), `pass`, or a cloud
secret manager's CLI. No vendor SDK, no vendor-specific code path.

Rules the implementation must follow:

- Take stdout and strip it. Trailing newlines from a CLI are a common breakage.
- On a non-zero exit, report the **exit code only**. Never print the command's
  stdout or stderr: a vault CLI will happily put the secret in an error message, and
  that message lands in a scheduler log, which then gets relayed somewhere.
- Give the command a timeout. A hung vault call must not hang a live phone call.

## 2. Native reader for one backend (convenience, needs a code change)

If you run a specific vault, a native reader saves spawning a process per request.
It is not implemented in the starter: edit `read_secret()` and put the vendor call at
the top of that function. Keep the command-hook branch beneath it, so anyone without
your vault still has a working path.

If you add one, every value must still come from configuration: URL, project id,
token file path. Nothing belonging to the author of this skill belongs in your config.

Cache the result with a short TTL. Do not keep a last-known-good value past that TTL:
after a token is revoked because it leaked, a stale cache keeps validating signatures
against the dead credential and the rotation quietly fails while looking successful.
Fail closed on a vault error instead, and if availability forces a fallback, bound it
to minutes and log loudly that stale authentication is in use.

## 3. A 0600 file (minimum acceptable)

```bash
install -m 600 /dev/null ~/.config/phone-agent/auth_token
printf '%s' "$TOKEN" > ~/.config/phone-agent/auth_token
export PHONE_AGENT_TWILIO_AUTH_TOKEN_FILE=~/.config/phone-agent/auth_token
```

Better than an environment variable because it survives process listings and can be
tightened independently. The gateway warns when the mode is group- or
other-readable, and `doctor.py` prints the mode it found.

## 4. Environment variable (last)

Visible to `ps e`, to `/proc/<pid>/environ`, and to anything that dumps the process
environment. Acceptable for a test, not for something that stays up.

## What to check before you call it done

```bash
python3 scripts/doctor.py
```

It prints, for each secret: its length (never the value), and which shape resolved
it. Then it makes one live API call with your account SID and token pair, because
the only proof that a credential works is a 200 from the far side.

If the live check returns 401, the pair does not belong together or the token is
stale. If it returns 404, the account SID is wrong. Those are different problems and
the message says which.

## Rotation

- **PIN:** rotate after any exposure. It is the only thing between a caller and the
  agent.
- **Auth token:** rotate if it appeared in a chat window, a screenshot, a log, or a
  commit. Rotating means the old one stops signing immediately, which is exactly the
  behaviour you want.
- **Test after rotating.** A rotated token that the gateway cannot read produces the
  same symptom as a wrong region: callers hear a rejection, and nothing else.
