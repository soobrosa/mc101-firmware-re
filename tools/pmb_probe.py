#!/usr/bin/env python3
"""
pmb_probe.py — Live-verify the MC-101 PMB (parameter address model) regions
found via static RE of sdram1.bin.

Requires:
    pip install python-rtmidi
Optional:
    pip install rich    (nicer terminal output)

Usage:
    ./pmb_probe.py --list                       # show MIDI devices
    ./pmb_probe.py --port "MC-101"              # probe with default region set
    ./pmb_probe.py --port "MC-101" --scan-all   # scan every candidate region
    ./pmb_probe.py --port "MC-101" --out csv    # append results to pmb_probe.csv

Model IDs:
    MC-101 = 0x5E     MC-707 = 0x5D

Address model — cross-referenced from:
    - static RE of sdram1.bin fn 0x25da (param name resolver)
    - external addresses seen in mcpoker.py + community dumps
    - the internal→external translation (top-byte swap: 0x41 ↔ 0x30/other)

The RE found 19-entry region descriptor tables in QSPI at RAM 0x61096148 and
0x6109622C. Each entry is {prev_ptr, base_addr, size}. On-device those hold
the true address boundaries; we can't read them without a live device.
This tool probes each candidate region base to see which addresses respond
with a DT1 (evidence that a parameter block exists there).

An "empty" region returns no response; a valid region echoes a DT1 within
~200ms with header + data. Presence + response length reveals the region's
size envelope.
"""
from __future__ import annotations
import argparse
import csv
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import rtmidi
    from rtmidi.midiutil import list_input_ports, list_output_ports
except ImportError:
    print("Missing dependency. Install with:  pip install python-rtmidi", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# PMB region catalogue (from static RE of sdram1.bin)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Region:
    """A candidate parameter address region to probe."""
    name: str
    addr: int
    probe_size: int = 16
    note: str = ""


# External addresses (top byte = 0x30-0x31 space, seen from community RQ1 dumps)
# These are known to work via SysEx.
KNOWN_EXTERNAL: list[Region] = [
    Region("Track 1 clip 1 tone",   0x30000000, 32, "verified: mcpoker"),
    Region("Track 1 clip 2 tone",   0x30020000, 32, "clip-N stride = 0x20000"),
    Region("Track 1 clip 16 tone",  0x301E0000, 32, "16 clips per track"),
    Region("Track 2 clip 1 tone",   0x30220000, 32, "track stride = 0x220000 for T2-T4"),
    Region("Track 3 clip 1 tone",   0x30440000, 32),
    Region("Track 4 clip 1 tone",   0x30660000, 32),
    Region("Track 5 clip 1 tone",   0x31080000, 32, "T5-T8 base +0x01000000 (MC-707 only)"),
    Region("Track 6 clip 1 tone",   0x312A0000, 32),
    Region("Track 7 clip 1 tone",   0x314C0000, 32),
    Region("Track 8 clip 1 tone",   0x316E0000, 32),
    Region("Track 1 tone, partial 1", 0x30002000, 32, "+0x2000 = P1 base"),
    Region("Track 1 tone, partial 2", 0x30002100, 32),
    Region("Track 1 tone, partial 3", 0x30002200, 32),
    Region("Track 1 tone, partial 4", 0x30002300, 32),
]

# Internal addresses recovered from the resolver at fn 0x25da (special-cased ranges).
# These are analyzed from disassembly — untested externally. We probe them assuming
# the standard external→internal top-byte translation: 0x00XXXXXX might be routed
# without prefix mangling (system parameter block), or map to 0x00XXXXXX external.
INTERNAL_CANDIDATES: list[Region] = [
    Region("System block-set A base",   0x00110000, 32, "RE: special-cased at 0x25da"),
    Region("System block-set A +0x1000",0x00111000, 32),
    Region("System block-set A end",    0x00111FFF, 16, "boundary probe"),
    Region("System block-set B",        0x00125000, 32, "RE: mask 0xfff000"),
    Region("Per-part block 0x11000",    0x00011000, 32, "RE: per-part regions"),
    Region("Per-part block 0x12000",    0x00012000, 32),
    Region("Per-part block 0x13000",    0x00013000, 32),
    Region("Per-part block 0x14000",    0x00014000, 32),
    Region("Overlay 0x00112000",        0x00112000, 32),
    Region("Domain boundary",           0x00200000, 32, "RE: domain-tag switch"),
]

# Also probe with alternate top-byte tags in case internal 0x00 maps externally
# to 0x00, 0x10, 0x20, 0x30, 0x40 etc. This is the "domain tag" the resolver
# strips with `bic addr, #0xff000000; orr #0x41000000`.
DOMAIN_TAGS = [0x00, 0x10, 0x20, 0x30, 0x40]


# ─────────────────────────────────────────────────────────────────────────────
# SysEx encoding / decoding
# ─────────────────────────────────────────────────────────────────────────────

def roland_checksum(payload_bytes: list[int]) -> int:
    """Standard Roland checksum: 128 - (sum mod 128)."""
    return (128 - (sum(payload_bytes) % 128)) & 0x7F


def encode_rq1(model_id: int, addr: int, count: int, device_id: int = 0x10) -> bytes:
    """Build an RQ1 (Data Request 1) SysEx message.

    F0 41 <dev> 00 00 00 <MODEL> 11 <A3 A2 A1 A0> <S3 S2 S1 S0> <CK> F7
    All bytes between the header and F7 must be 7-bit clean.
    """
    if any(((addr >> shift) & 0xFF) & 0x80 for shift in (0, 8, 16, 24)):
        raise ValueError(f"address 0x{addr:08X} has a byte with bit7 set — invalid SysEx")
    payload = [
        (addr >> 24) & 0x7F, (addr >> 16) & 0x7F,
        (addr >> 8)  & 0x7F, (addr >> 0)  & 0x7F,
        (count >> 24) & 0x7F, (count >> 16) & 0x7F,
        (count >> 8)  & 0x7F, (count >> 0)  & 0x7F,
    ]
    msg = [0xF0, 0x41, device_id, 0x00, 0x00, 0x00, model_id, 0x11] + payload
    msg.append(roland_checksum(payload))
    msg.append(0xF7)
    return bytes(msg)


def decode_dt1(msg: bytes, model_id: int) -> Optional[tuple[int, bytes]]:
    """Decode a DT1 (Data Set 1) SysEx from the device. Returns (addr, data) or None."""
    if len(msg) < 15 or msg[0] != 0xF0 or msg[-1] != 0xF7:
        return None
    if msg[1] != 0x41 or msg[6] != model_id or msg[7] != 0x12:
        return None
    addr = (msg[8] << 24) | (msg[9] << 16) | (msg[10] << 8) | msg[11]
    # Data runs from [12] to [-3] (last two = checksum + F7)
    data = bytes(msg[12:-2])
    # Verify checksum: sum(addr_bytes + data) + checksum ≡ 0 (mod 128)
    payload = list(msg[8:-2])
    if (sum(payload) + msg[-2]) & 0x7F != 0:
        return None  # bad checksum — probably garbled
    return addr, data


# ─────────────────────────────────────────────────────────────────────────────
# MIDI I/O
# ─────────────────────────────────────────────────────────────────────────────

class MidiLink:
    def __init__(self, port_substring: str):
        self.in_port = rtmidi.MidiIn()
        self.out_port = rtmidi.MidiOut()

        in_names = self.in_port.get_ports()
        out_names = self.out_port.get_ports()

        in_idx = next((i for i, n in enumerate(in_names) if port_substring in n), None)
        out_idx = next((i for i, n in enumerate(out_names) if port_substring in n), None)

        if in_idx is None or out_idx is None:
            print(f"\nMIDI ports containing {port_substring!r} not found.", file=sys.stderr)
            print(f"\nInputs available:")
            for i, n in enumerate(in_names): print(f"  [{i}] {n}", file=sys.stderr)
            print(f"\nOutputs available:")
            for i, n in enumerate(out_names): print(f"  [{i}] {n}", file=sys.stderr)
            sys.exit(2)

        self.in_port.open_port(in_idx)
        self.out_port.open_port(out_idx)
        # SysEx must not be filtered out
        self.in_port.ignore_types(sysex=False, timing=True, active_sense=True)
        self._in_name  = in_names[in_idx]
        self._out_name = out_names[out_idx]
        print(f"MIDI  → out: {self._out_name}", file=sys.stderr)
        print(f"      ← in:  {self._in_name}",  file=sys.stderr)
        # small drain
        time.sleep(0.1)
        while self.in_port.get_message() is not None: pass

    def send(self, msg: bytes) -> None:
        self.out_port.send_message(list(msg))

    def recv_sysex(self, timeout: float = 0.25) -> Optional[bytes]:
        """Return the first complete SysEx message received within `timeout` seconds."""
        deadline = time.time() + timeout
        buf: list[int] = []
        while time.time() < deadline:
            evt = self.in_port.get_message()
            if evt is None:
                time.sleep(0.005)
                continue
            data, _dt = evt
            if not data: continue
            if data[0] == 0xF0:
                buf = list(data)
            else:
                buf.extend(data)
            if buf and buf[-1] == 0xF7:
                return bytes(buf)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Probe
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Result:
    region: Region
    tag: int              # domain-tag byte we tried (top byte of address)
    probed_addr: int
    responded: bool
    resp_len: int = 0
    first_data_hex: str = ""


def probe_region(link: MidiLink, model_id: int, region: Region, tag: int,
                 timeout: float = 0.25) -> Result:
    """Send one RQ1 to (tag << 24) | (region.addr & 0x00FFFFFF) and record the response."""
    probed_addr = (tag << 24) | (region.addr & 0x00FFFFFF)
    try:
        rq = encode_rq1(model_id, probed_addr, region.probe_size)
    except ValueError:
        return Result(region, tag, probed_addr, False, 0, "SKIP (bit7)")
    link.send(rq)
    resp = link.recv_sysex(timeout)
    if resp is None:
        return Result(region, tag, probed_addr, False, 0, "")
    decoded = decode_dt1(resp, model_id)
    if decoded is None:
        return Result(region, tag, probed_addr, True, len(resp), f"non-DT1: {resp[:12].hex()}")
    _addr, data = decoded
    return Result(region, tag, probed_addr, True, len(data), data[:16].hex())


def run_probes(link: MidiLink, model_id: int, regions: list[Region],
               tags: list[int], out_writer: Optional[csv.writer]) -> list[Result]:
    results: list[Result] = []
    print(f"\nProbing {len(regions)} regions × {len(tags)} domain tags "
          f"= {len(regions)*len(tags)} candidates\n", file=sys.stderr)
    print(f"{'ADDRESS':>10s}  {'RESP':>4s}  {'LEN':>4s}  DATA[0:16]                            NAME")
    print(f"{'-'*10}  {'-'*4}  {'-'*4}  {'-'*40}  ----")
    for region in regions:
        for tag in tags:
            r = probe_region(link, model_id, region, tag)
            results.append(r)
            marker = "✓" if r.responded else "·"
            print(f"  0x{r.probed_addr:08X}  {marker:>4s}  {r.resp_len:>4d}  "
                  f"{r.first_data_hex:<40s}  {region.name}  {region.note}")
            if out_writer:
                out_writer.writerow([f"0x{r.probed_addr:08X}", int(r.responded),
                                     r.resp_len, r.first_data_hex,
                                     region.name, region.note])
            time.sleep(0.05)  # gentle pace
    return results


def summarize(results: list[Result]) -> None:
    hits = [r for r in results if r.responded]
    print(f"\n\n═══ SUMMARY ═══", file=sys.stderr)
    print(f"Total probes:      {len(results)}",     file=sys.stderr)
    print(f"Responded:         {len(hits)}",         file=sys.stderr)
    print(f"Silent (no reply): {len(results)-len(hits)}", file=sys.stderr)
    if hits:
        print(f"\nActive addresses (first 20):", file=sys.stderr)
        for r in hits[:20]:
            print(f"  0x{r.probed_addr:08X}  → {r.resp_len:>4d} B  ({r.region.name})", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(
        description="Probe MC-101/MC-707 parameter address regions via SysEx RQ1")
    p.add_argument("--list", action="store_true", help="list MIDI ports and exit")
    p.add_argument("--port", type=str,
                   help="substring of the MC-101/707 MIDI port name")
    p.add_argument("--model", choices=["mc101","mc707"], default="mc101")
    p.add_argument("--device-id", type=lambda s: int(s,0), default=0x10,
                   help="Roland device ID (default 0x10)")
    p.add_argument("--scan-all", action="store_true",
                   help="scan external + internal candidate regions across all domain tags")
    p.add_argument("--out", type=str, default=None,
                   help="write CSV log to this path (appends)")
    p.add_argument("--timeout", type=float, default=0.25,
                   help="per-probe reply timeout in seconds (default 0.25)")
    args = p.parse_args()

    if args.list:
        list_input_ports(); print()
        list_output_ports()
        return 0

    if not args.port:
        p.print_help()
        return 1

    model_id = {"mc101": 0x5E, "mc707": 0x5D}[args.model]
    print(f"Model:  {args.model.upper()}  (SysEx model ID = 0x{model_id:02X})", file=sys.stderr)

    link = MidiLink(args.port)

    # Pick region + tag set
    if args.scan_all:
        regions = KNOWN_EXTERNAL + INTERNAL_CANDIDATES
        tags = DOMAIN_TAGS
    else:
        regions = KNOWN_EXTERNAL + INTERNAL_CANDIDATES
        # Only probe with each region's native tag first
        tags = None  # signal below

    out_writer = None
    out_file = None
    if args.out:
        out_file = open(args.out, "a", newline="")
        out_writer = csv.writer(out_file)
        if out_file.tell() == 0:
            out_writer.writerow(["addr", "responded", "resp_len", "data_hex", "name", "note"])

    if tags is None:
        # Native-tag mode: probe each region at its declared address
        results: list[Result] = []
        for region in regions:
            native_tag = (region.addr >> 24) & 0xFF
            r = probe_region(link, model_id, region, native_tag, args.timeout)
            results.append(r)
            marker = "✓" if r.responded else "·"
            print(f"  0x{r.probed_addr:08X}  {marker}  len={r.resp_len:3d}  "
                  f"{r.first_data_hex[:32]:<32s}  {region.name}")
            if out_writer:
                out_writer.writerow([f"0x{r.probed_addr:08X}", int(r.responded),
                                     r.resp_len, r.first_data_hex,
                                     region.name, region.note])
            time.sleep(0.05)
        summarize(results)
    else:
        results = run_probes(link, model_id, regions, tags, out_writer)
        summarize(results)

    if out_file:
        out_file.close()
        print(f"\nCSV written: {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
