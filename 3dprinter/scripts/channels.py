#!/usr/bin/env python3
"""channels.py — AD5X material station inventory (3dprinter skill).

Usage:
  channels.py set <1-4> --material PLA|PETG [--color NAME] [--brand NAME] [--remaining PCT]
  channels.py show
  channels.py clear <1-4> --yes

State lives in the skill state file (default ~/3dprinter/state.json; override
with 3DPRINTER_STATE). The file holds printer credentials and is chmod 600.
"""
import argparse
import json
import os
import sys

# State file: override with 3DPRINTER_STATE if set.
STATE = os.environ.get("3DPRINTER_STATE", os.path.expanduser("~/3dprinter/state.json"))
MATERIALS = ["PLA", "PETG", "ABS", "ASA", "TPU", "PLA-CF", "PETG-CF", "OTHER"]


def load_state():
    if not os.path.exists(STATE):
        sys.exit(f"state file not found: {STATE} — answer the install prompt to create it")
    with open(STATE) as fh:
        return json.load(fh)


def save_state(st):
    with open(STATE, "w") as fh:
        json.dump(st, fh, indent=2)
    try:
        os.chmod(STATE, 0o600)  # state holds printer serial + check code
    except OSError:
        pass


def cmd_set(st, ch, material, color, brand, remaining):
    if str(ch) not in st["channels"]:
        sys.exit(f"invalid channel {ch}: use 1-4")
    slot = st["channels"][str(ch)]
    if material:
        slot["material"] = material.upper()
    if color:
        slot["color"] = color
    if brand:
        slot["brand"] = brand
    if remaining is not None:
        slot["remaining_pct"] = remaining
    save_state(st)
    print(f"channel {ch}: {slot}")


def cmd_show(st):
    for ch, slot in sorted(st["channels"].items(), key=lambda kv: int(kv[0])):
        m = slot.get("material") or "—"
        c = slot.get("color") or "—"
        b = slot.get("brand") or "—"
        r = slot.get("remaining_pct")
        r = f"{r}%" if r is not None else "—"
        print(f"  ch{ch}: {m:8} {c:12} {b:12} {r}")


def cmd_clear(st, ch):
    if str(ch) not in st["channels"]:
        sys.exit(f"invalid channel {ch}: use 1-4")
    st["channels"][str(ch)] = {"material": None, "color": None, "brand": None, "remaining_pct": None}
    save_state(st)
    print(f"channel {ch} cleared")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["set", "show", "clear"])
    ap.add_argument("channel", nargs="?")
    ap.add_argument("--material", choices=MATERIALS)
    ap.add_argument("--color")
    ap.add_argument("--brand")
    ap.add_argument("--remaining", type=int)
    ap.add_argument("--yes", action="store_true", help="required to confirm clear")
    a = ap.parse_args()

    if a.cmd == "clear" and not a.yes:
        sys.exit("clear requires --yes (wipes the channel inventory)")

    st = load_state()
    if a.cmd == "set":
        cmd_set(st, a.channel, a.material, a.color, a.brand, a.remaining)
    elif a.cmd == "show":
        cmd_show(st)
    elif a.cmd == "clear":
        cmd_clear(st, a.channel)


if __name__ == "__main__":
    main()
