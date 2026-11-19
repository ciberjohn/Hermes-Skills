#!/usr/bin/env python3
"""Pre-flight for the phone gateway. Prints facts, writes nothing.

Run this before you expose anything and after every credential change. It shows
which backend answered, how long each secret is (never the value), and whether
Twilio accepts the account SID and token pair with one live API call.

A 200 proves the pair is valid for the REST API. It does not prove the token signs
webhooks, because an account can hold more than one valid token. Replay a captured
request to prove signing (SKILL.md step 5).

    python3 doctor.py
Exit codes: 0 all checks passed, 1 something is wrong, 2 incomplete (nothing to test)
"""
from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REQUIRED = ["PHONE_AGENT_TWILIO_AUTH_TOKEN", "PHONE_AGENT_PIN"]
OPTIONAL = ["PHONE_AGENT_TWILIO_ACCOUNT_SID", "PHONE_AGENT_ALLOWLIST", "PHONE_AGENT_PUBLIC_URL"]


def resolve(name: str) -> tuple[str, str]:
    """Return (value, how) using the same order as the gateway."""
    cmd_var = f"{name}_CMD"
    if os.environ.get(cmd_var):
        try:
            proc = subprocess.run(shlex.split(os.environ[cmd_var]), capture_output=True,
                                  text=True, timeout=20, shell=False)
        except subprocess.TimeoutExpired:
            return "", "command hook timed out"
        except (OSError, ValueError) as exc:
            return "", f"command hook could not run ({exc.__class__.__name__})"
        if proc.returncode != 0:
            # Exit code only. A vault CLI can put the secret in its error text.
            return "", f"command hook failed (exit {proc.returncode})"
        return proc.stdout.strip(), "command hook"

    file_var = f"{name}_FILE"
    if os.environ.get(file_var):
        path = Path(os.environ[file_var]).expanduser()
        if not path.exists():
            return "", f"file missing ({file_var})"
        mode = path.stat().st_mode & 0o777
        return path.read_text().strip(), f"file, mode {oct(mode)}"

    if os.environ.get(name):
        return os.environ[name].strip(), "environment variable"
    return "", "not set"


def main() -> int:
    print("phone-agent-front-door doctor")
    print("-" * 52)
    data = Path(os.environ.get("PHONE_AGENT_DATA", "~/.local/share/phone-agent")).expanduser()
    print(f"data dir   : {data}{'' if data.exists() else ' (will be created)'}")

    failures = 0
    incomplete = False
    values: dict[str, str] = {}

    for name in REQUIRED:
        value, how = resolve(name)
        values[name] = value
        print(f"{name:<34}{f'{len(value)} chars' if value else 'EMPTY':<13}{how}")
        if not value:
            failures += 1

    for name in OPTIONAL:
        value, _ = resolve(name)
        values[name] = value
        print(f"{name:<34}{'set' if value else 'unset':<13}")

    pin = values.get("PHONE_AGENT_PIN", "")
    if pin and not (pin.isdigit() and 6 <= len(pin) <= 10):
        print("  ERROR: the PIN must be 6 to 10 digits, because the keypad gather "
              "collects exactly that many")
        failures += 1

    # Accept a lax file mode as a finding even when the value resolved: the gateway
    # refuses it, so reporting it here saves a confusing failed start.
    for name in REQUIRED:
        mode_how = resolve(name)[1]
        if mode_how.startswith("file, mode 0o") and not mode_how.endswith("0o600") \
                and not mode_how.endswith("0o400"):
            print(f"  ERROR: {name} file {mode_how}; chmod 600 it (the gateway refuses it)")
            failures += 1

    allow = values.get("PHONE_AGENT_ALLOWLIST", "")
    if not allow and os.environ.get("PHONE_AGENT_ALLOW_ANY") != "1":
        print("  ERROR: no allowlist, so the gateway will refuse to start; anyone who "
              "found the number would otherwise reach the menu")
        failures += 1

    token = values.get("PHONE_AGENT_TWILIO_AUTH_TOKEN", "")
    sid = values.get("PHONE_AGENT_TWILIO_ACCOUNT_SID", "")
    if not sid:
        print("\nlive check : NOT RUN, PHONE_AGENT_TWILIO_ACCOUNT_SID is unset")
        incomplete = True
        print(f"\nresult     : {failures} problem(s)" if failures
              else "\nresult     : incomplete, the signing token was never tested")
        return 1 if failures else 2
    if not token:
        print("\nlive check : NOT RUN, no auth token")
        print("\nresult     : 1 problem(s)")
        return 1

    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.load(resp)
        print(f"\nlive check : HTTP 200, account {body.get('status')} ({body.get('type')})")
        print("             the pair is valid for the REST API")
        print("             signing is NOT proven by this; replay a captured request")
    except urllib.error.HTTPError as exc:
        print(f"\nlive check : HTTP {exc.code}")
        if exc.code == 401:
            print("             the token and account SID do not belong together, "
                  "or the token is stale")
        elif exc.code == 404:
            print("             the account SID is wrong")
        failures += 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nlive check : failed ({exc.__class__.__name__})")
        failures += 1

    print(f"\nresult     : {'ready' if not failures else f'{failures} problem(s)'}")
    if not failures and incomplete:
        return 2
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
