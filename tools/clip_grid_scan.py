#!/usr/bin/env python3
"""
clip_grid_scan.py — Map the MC-101 project clip grid (8 tracks × 16 clips) over SysEx.

Read-only RQ1 probe. Sends NO writes (no DT1). Reuses SysEx encode/decode
from pmb_probe.py.

The live probe (2026-08-16) discovered the address top byte is a LAYER SELECTOR:
  0x30xxxxxx → tone name layer
  0x20xxxxxx → clip / scene name layer
at the same base address. This tool scans all 128 clip addresses under both tags
to produce the full 8×16 grid of tone names and clip/scene names.

Address model:
  Track base:  0x30000000 + track_index * 0x220000   (tracks 0..7)
  Clip offset: clip_index * 0x20000                   (clips 0..15)
  Full addr:  track_base + clip_offset
  Tag 0x20:   replace top byte with 0x20
  Tag 0x30:   keep 0x30

Usage:
  ./clip_grid_scan.py --port "MC-101" --out clip_grid.csv
"""
from __future__ import annotations
import argparse
import csv
import sys
import time
from typing import Optional

# Reuse SysEx machinery from the sibling probe tool
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from pmb_probe import encode_rq1, decode_dt1, MidiLink  # noqa: E402

MODEL_ID = 0x5E  # MC-101

TRACK_STRIDE = 0x220000
CLIP_STRIDE  = 0x20000
N_TRACKS    = 8
N_CLIPS     = 16


def clip_addr(track: int, clip: int, tag: int) -> int:
    """Return the SysEx address for track/clip under the given domain tag."""
    base = 0x30000000 + track * TRACK_STRIDE + clip * CLIP_STRIDE
    return (tag << 24) | (base & 0x00FFFFFF)


def probe(link: MidiLink, addr: int, count: int = 32, timeout: float = 0.20):
    """Send RQ1, return (responded, data_bytes)."""
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
        return True, b""  # got something but not a clean DT1
    _a, data = decoded
    return True, data


def ascii_clean(b: bytes) -> str:
    """Decode bytes as ASCII, strip NULs and trailing spaces."""
    s = b.decode("ascii", "replace")
    s = s.replace("\x00", " ").rstrip()
    return s


def main() -> int:
    p = argparse.ArgumentParser(description="Map MC-101 clip grid via SysEx RQ1 (read-only)")
    p.add_argument("--port", required=True, help="substring of MC-101 MIDI port name")
    p.add_argument("--out", default=None, help="write CSV to this path")
    p.add_argument("--timeout", type=float, default=0.20, help="per-probe timeout (s)")
    args = p.parse_args()

    link = MidiLink(args.port)
    # drain
    time.sleep(0.1)
    while link.in_port.get_message() is not None: pass

    out_file = None
    writer = None
    if args.out:
        out_file = open(args.out, "w", newline="")
        writer = csv.writer(out_file)
        writer.writerow(["track", "clip", "tag", "addr", "responded",
                         "resp_len", "data_hex", "ascii"])

    results = {}  # (track, clip, tag) -> (responded, data)

    for tag_label, tag in [("tone 0x30", 0x30), ("clip 0x20", 0x20)]:
        print(f"\n{'='*72}")
        print(f"  Layer: {tag_label}")
        print(f"{'='*72}")
        header = "     " + "".join(f"Clip {c:<2d} " for c in range(N_CLIPS))
        print(header)
        for t in range(N_TRACKS):
            row_cells = []
            for c in range(N_CLIPS):
                addr = clip_addr(t, c, tag)
                ok, data = probe(link, addr, 32, args.timeout)
                results[(t, c, tag)] = (ok, data)
                name = ascii_clean(data[:16]) if ok and data else ""
                # compact cell: first 8 chars of name or "·"
                cell = name[:8] if name else "·"
                row_cells.append(f"{cell:<8s}")
                if writer:
                    writer.writerow([t, c, f"0x{tag:02X}", f"0x{addr:08X}",
                                     int(ok), len(data), data[:16].hex(), name])
                time.sleep(0.03)
            print(f"Tr{t+1} " + "".join(row_cells))

    # Summary grid
    print(f"\n{'='*72}")
    print("  TONE NAMES (tag 0x30)")
    print(f"{'='*72}")
    print("     " + "".join(f"C{c:<2d}      " for c in range(N_CLIPS)))
    for t in range(N_TRACKS):
        cells = []
        for c in range(N_CLIPS):
            ok, data = results.get((t, c, 0x30), (False, b""))
            name = ascii_clean(data[:16]) if ok and data else ""
            cells.append(f"{name[:8]:<8s}")
        print(f"Tr{t+1} " + "".join(cells))

    print(f"\n{'='*72}")
    print("  CLIP / SCENE NAMES (tag 0x20)")
    print(f"{'='*72}")
    print("     " + "".join(f"C{c:<2d}      " for c in range(N_CLIPS)))
    for t in range(N_TRACKS):
        cells = []
        for c in range(N_CLIPS):
            ok, data = results.get((t, c, 0x20), (False, b""))
            name = ascii_clean(data[:16]) if ok and data else ""
            cells.append(f"{name[:8]:<8s}")
        print(f"Tr{t+1} " + "".join(cells))

    # Count hits
    tone_hits = sum(1 for k, v in results.items() if k[2] == 0x30 and v[0])
    clip_hits = sum(1 for k, v in results.items() if k[2] == 0x20 and v[0])
    total = N_TRACKS * N_CLIPS
    print(f"\nTone layer:  {tone_hits}/{total} clips responded")
    print(f"Clip layer:  {clip_hits}/{total} clips responded")

    if out_file:
        out_file.close()
        print(f"\nCSV written: {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
