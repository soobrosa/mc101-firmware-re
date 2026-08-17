#!/usr/bin/env python3
"""
init_lzs_decode.py — Decompress the MC-101/MC-707 factory init project.

Format (authoritative source: ConvertWithMoss `documentation/design/MC707_FORMAT.md` §8):
  textbook Okumura LZSS:
    - 4096-byte ring buffer, pre-filled with ZEROS
    - write position starts at 0xFEE (= N - F = 4096 - 18)
    - flag bytes LSB-first: 1 = literal, 0 = match
    - match = u8 lo, u8 hi  ->  12-bit ABSOLUTE ring offset lo | (hi & 0xF0) << 4,
                                length (hi & 0x0F) + 3
    - the LZSS stream starts at file offset 0x20 (first 32 bytes are a container header)
    - decompresses to 8,153,245 bytes (the INIT PROJECT, 243 bytes short of the full
      8,153,488-byte canonical project; the missing tail is the repeating empty
      looper directory + 16-byte empty USDa, completable from any preset project)

Output is the raw .mpj project container (PRJ5/MC77). See MC707_FORMAT.md §1 for the
section layout (PRJa/STPa/SYSa/USRa/LPPa/LPDa/USDa).

Usage:
    ./init_lzs_decode.py                       # decode extracted/C0C/init.lzs -> init_project.mpj
    ./init_lzs_decode.py -o out.mpj             # custom output path
    ./init_lzs_decode.py --inspect              # decode + print section TOC + first bytes
"""
from __future__ import annotations
import argparse
import os
import sys

N = 4096          # ring buffer size
F = 18            # max match length (lookahead)
START_OFFSET = 0x20   # LZSS stream begins at file offset 0x20
EXPECTED_OUT = 8_153_245


def decompress_lzss(stream: bytes) -> bytes:
    """Okumura LZSS, LSB-first flags, zero-prefilled ring, absolute match offset."""
    ring = bytearray(N)          # pre-filled with zeros
    r = N - F                    # 0xFEE
    out = bytearray()
    flags = 0
    count = 0                    # bits remaining in current flag byte
    i = 0
    n = len(stream)
    while i < n:
        if count == 0:
            flags = stream[i]
            i += 1
            count = 8
        bit = flags & 1
        flags >>= 1
        count -= 1
        if bit:                  # literal
            if i >= n:
                break
            c = stream[i]
            i += 1
            out.append(c)
            ring[r] = c
            r = (r + 1) & (N - 1)
        else:                    # match
            if i + 1 >= n:
                break
            lo = stream[i]
            hi = stream[i + 1]
            i += 2
            offset = lo | ((hi & 0xF0) << 4)      # 12-bit absolute ring offset
            length = (hi & 0x0F) + 3              # min 3, max 18
            for k in range(length):
                c = ring[(offset + k) & (N - 1)]
                out.append(c)
                ring[r] = c
                r = (r + 1) & (N - 1)
    return bytes(out)


SECTIONS = ("PRJa", "STPa", "SYSa", "USRa", "LPPa", "LPDa", "USDa")


def inspect(data: bytes) -> None:
    """Print the .mpj file header + TOC."""
    if len(data) < 16:
        print("output too short", file=sys.stderr)
        return
    toc_off = int.from_bytes(data[0:2], "little")
    tag = data[2:6]
    print(f"Header: u16 0x{toc_off:04X}  tag={tag.decode('ascii', 'replace')!r}")
    print(f"Output size: {len(data)} bytes  (expected {EXPECTED_OUT})")
    print()
    print("TOC (7 x 16-byte entries at 0x10):")
    print(f"  {'TAG':4s}  {'PLAT':4s}  {'OFFSET':>10s}  {'SIZE':>10s}")
    for i in range(7):
        base = 0x10 + i * 16
        if base + 16 > len(data):
            break
        stag = data[base:base + 4].decode('ascii', 'replace')
        plat = data[base + 4:base + 8].decode('ascii', 'replace')
        off = int.from_bytes(data[base + 8:base + 12], "little")
        size = int.from_bytes(data[base + 12:base + 16], "little")
        print(f"  {stag:4s}  {plat:4s}  0x{off:08X}  0x{size:08X}")
    print()
    print(f"First 32 bytes: {data[:32].hex(' ')}")


def main() -> int:
    p = argparse.ArgumentParser(description="Decompress MC-101/MC-707 init.lzs -> init_project.mpj")
    here = os.path.dirname(os.path.abspath(__file__))
    default_in = os.path.normpath(os.path.join(here, "..", "extracted", "C0C", "init.lzs"))
    p.add_argument("input", nargs="?", default=default_in, help=f"init.lzs path (default: {default_in})")
    p.add_argument("-o", "--output", default=None, help="output .mpj path (default: beside input, init_project.mpj)")
    p.add_argument("--inspect", action="store_true", help="print TOC + header after decoding")
    args = p.parse_args()

    if not os.path.exists(args.input):
        print(f"input not found: {args.input}", file=sys.stderr)
        return 1

    with open(args.input, "rb") as f:
        raw = f.read()
    if len(raw) < START_OFFSET:
        print(f"file too short ({len(raw)} bytes); expected >= 0x20 header", file=sys.stderr)
        return 1
    stream = raw[START_OFFSET:]
    out = decompress_lzss(stream)

    out_path = args.output or os.path.join(os.path.dirname(os.path.abspath(args.input)), "init_project.mpj")
    with open(out_path, "wb") as f:
        f.write(out)
    print(f"decompressed {len(raw)} -> {len(out)} bytes  (expected {EXPECTED_OUT})", file=sys.stderr)
    print(f"written: {out_path}", file=sys.stderr)

    if args.inspect:
        inspect(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
