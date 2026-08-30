#!/usr/bin/env python3
"""ff_print.py — FlashForge AD5X printer control (3dprinter skill).

Usage:
  ff_print.py status
  ff_print.py list [--tail N]
  ff_print.py upload <gcode-file> [--start]
  ff_print.py cancel --yes

Connection comes from state.json (printer.host / serial / check_code).
NOTE: the AD5X HTTP API (8898) is not served on some AD5X firmware in LAN mode;
file listing falls back to the TCP M-code path, but uploads require the HTTP
API and will fail until the printer's LAN/remote-control mode or check code is
verified.
"""
import argparse
import asyncio
import json
import os
import sys

# State file: override with 3DPRINTER_STATE if set.
STATE = os.environ.get("3DPRINTER_STATE", os.path.expanduser("~/3dprinter/state.json"))


def load_state():
    if not os.path.exists(STATE):
        sys.exit(f"state file not found: {STATE} — answer the install prompt to create it")
    with open(STATE) as fh:
        return json.load(fh)


async def _connect(st):
    from flashforge import FlashForgeClient
    p = st["printer"]
    return FlashForgeClient(p["host"], p["serial"], p["check_code"])


async def cmd_status(st):
    c = await _connect(st)
    try:
        await c.init_control()
        fl = await c.files.get_file_list()
        print(f"file_count: {len(fl) if fl else 0}")
        try:
            status = await c.get_printer_status()
            print("status:", getattr(status, "machine_state", status))
        except Exception as e:
            print("status_error (TCP):", e)
    finally:
        await c.dispose()


async def cmd_list(st, tail):
    c = await _connect(st)
    try:
        await c.init_control()
        fl = await c.files.get_file_list() or []
        for f in fl[-tail:]:
            print(f)
        print(f"(total {len(fl)} files)")
    finally:
        await c.dispose()


async def cmd_upload(st, gcode, start):
    if not os.path.exists(gcode):
        sys.exit(f"gcode not found: {gcode}")
    c = await _connect(st)
    try:
        await c.init_control()
        ok = await c.job_control.upload_file(gcode, start_print=start, level_before_print=start)
        print("upload:", "OK" if ok else "FAILED (HTTP API likely unavailable)")
    finally:
        await c.dispose()


async def cmd_cancel(st):
    c = await _connect(st)
    try:
        await c.init_control()
        ok = await c.job_control.cancel_print_job()
        print("cancel:", "OK" if ok else "FAILED")
    finally:
        await c.dispose()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "list", "upload", "cancel"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--start", action="store_true", help="start printing immediately after upload")
    ap.add_argument("--yes", action="store_true", help="required to confirm cancel")
    ap.add_argument("--tail", type=int, default=15)
    a = ap.parse_args()

    if a.cmd == "upload" and not a.arg:
        sys.exit("upload requires a gcode file: ff_print.py upload <file.gcode> [--start]")
    if a.cmd == "cancel" and not a.yes:
        sys.exit("cancel requires --yes (stops the current print job)")

    st = load_state()
    if a.cmd == "status":
        asyncio.run(cmd_status(st))
    elif a.cmd == "list":
        asyncio.run(cmd_list(st, a.tail))
    elif a.cmd == "upload":
        asyncio.run(cmd_upload(st, a.arg, a.start))
    elif a.cmd == "cancel":
        asyncio.run(cmd_cancel(st))


if __name__ == "__main__":
    main()
