#!/usr/bin/env python3
"""
dt1_write.py — Send a DT1 (Data Set 1) write to the MC-101 via SysEx.

DT1 wire format:
  F0 41 <dev> 00 00 00 <MODEL> 12 <A3 A2 A1 A0> <data...> <CK> F7

All address and data bytes must be 7-bit clean (< 0x80).
The device does not acknowledge DT1 writes — we verify by reading back with RQ1.

Usage:
  ./dt1_write.py --port "MC-101" --addr 0x20000000 --data "DROIDTEST   "
  ./dt1_write.py --port "MC-101" --addr 0x20000000 --hex 44524f494454455354
  ./dt1_write.py --port "MC-101" --addr 0x20000000 --data "DROIDTEST   " --verify
"""
from __future__ import annotations
import argparse
import sys
import time

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from pmb_probe import encode_rq1, decode_dt1, roland_checksum, MidiLink  # noqa: E402

MODEL_ID = 0x5E  # MC-101


def encode_dt1(model_id: int, addr: int, data: bytes, device_id: int = 0x10) -> bytes:
    """Build a DT1 (Data Set 1) SysEx message."""
    # Validate 7-bit clean
    for shift in (0, 8, 16, 24):
        if ((addr >> shift) & 0xFF) & 0x80:
            raise ValueError(f"address 0x{addr:08X} has a byte with bit7 set")
    for i, b in enumerate(data):
        if b & 0x80:
            raise ValueError(f"data byte {i} (0x{b:02X}) has bit7 set — invalid SysEx")

    addr_bytes = [
        (addr >> 24) & 0x7F, (addr >> 16) & 0x7F,
        (addr >> 8) & 0x7F, (addr >> 0) & 0x7F,
    ]
    payload = addr_bytes + list(data)
    msg = [0xF0, 0x41, device_id, 0x00, 0x00, 0x00, model_id, 0x12] + payload
    msg.append(roland_checksum(payload))
    msg.append(0xF7)
    return bytes(msg)


def read_back(link: MidiLink, addr: int, count: int = 64, timeout: float = 0.30):
    """Send RQ1 and return (responded, data_bytes)."""
    try:
        rq = encode_rq1(MODEL_ID, addr, count)
    except ValueError:
        return False, b""
    link.send(rq)
    resp = link.recv_sysex(timeout)
    if resp is None:
        return False, b""
    decoded = decode_dt1(resp, MODEL_ID)
    if decoded is None:
        return True, b""
    _a, data = decoded
    return True, data


def ascii_clean(b: bytes) -> str:
    s = b.decode("ascii", "replace").replace("\x00", " ").rstrip()
    clean = ""
    for ch in s:
        if 32 <= ord(ch) < 127:
            clean += ch
        else:
            break
    return clean.rstrip()


def main() -> int:
    p = argparse.ArgumentParser(description="Send DT1 write to MC-101 via SysEx")
    p.add_argument("--port", required=True, help="substring of MC-101 MIDI port name")
    p.add_argument("--addr", required=True, type=lambda s: int(s, 0),
                   help="target address (e.g. 0x20000000)")
    p.add_argument("--data", default=None, help="ASCII string to write")
    p.add_argument("--hex", default=None, help="hex string to write (no spaces)")
    p.add_argument("--verify", action="store_true",
                   help="read back after writing to confirm")
    p.add_argument("--read-count", type=int, default=64,
                   help="bytes to request in verify RQ1 (default 64)")
    args = p.parse_args()

    if args.data is not None:
        data = args.data.encode("ascii")
    elif args.hex is not None:
        data = bytes.fromhex(args.hex)
    else:
        p.error("must specify --data or --hex")

    print(f"Address:  0x{args.addr:08X}", file=sys.stderr)
    print(f"Data:     {data.hex()} ({len(data)} bytes)", file=sys.stderr)
    print(f"ASCII:    {repr(data.decode('ascii', 'replace'))}", file=sys.stderr)

    # Validate
    try:
        dt1 = encode_dt1(MODEL_ID, args.addr, data)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"DT1 msg:  {dt1.hex()}", file=sys.stderr)

    link = MidiLink(args.port)
    time.sleep(0.1)
    while link.in_port.get_message() is not None: pass

    if args.verify:
        print(f"\n--- READ BEFORE WRITE ---", file=sys.stderr)
        ok, rdata = read_back(link, args.addr, args.read_count)
        if ok and rdata:
            print(f"  Before: {rdata[:24].hex()}  ascii: {repr(ascii_clean(rdata[:16]))}",
                  file=sys.stderr)
        else:
            print(f"  Before: (no response or empty)", file=sys.stderr)

    # Send the DT1 write
    print(f"\n--- SENDING DT1 WRITE ---", file=sys.stderr)
    link.send(dt1)
    # DT1 writes are not acknowledged; wait for the device to process
    time.sleep(0.3)
    # drain any stray messages
    while link.in_port.get_message() is not None: pass
    print(f"  Sent. (DT1 writes are not acknowledged by the device)", file=sys.stderr)

    if args.verify:
        print(f"\n--- READ AFTER WRITE ---", file=sys.stderr)
        time.sleep(0.1)
        ok, rdata = read_back(link, args.addr, args.read_count)
        if ok and rdata:
            print(f"  After:  {rdata[:24].hex()}  ascii: {repr(ascii_clean(rdata[:16]))}",
                  file=sys.stderr)
            # Check if the name appears in the first bytes
            written_name = ascii_clean(data[:16])
            read_name = ascii_clean(rdata[:16])
            if written_name and read_name.startswith(written_name):
                print(f"  ✓ WRITE CONFIRMED — name starts with '{written_name}'",
                      file=sys.stderr)
            else:
                print(f"  ? Write may not have taken effect — expected '{written_name}', "
                      f"got '{read_name}'", file=sys.stderr)
        else:
            print(f"  ? No response after write — cannot verify", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
