#!/usr/bin/env python3
"""
discover_functions.py — Find functions in sdram1.bin (Core-1 DSP, ARM Thumb-2).

Three discovery passes, merged + deduped:

  1. Prologue scan (the baseline 1,876 from REPORT §16):
       - Thumb-1  push {..., lr}   :  byte[1]==0xB5 and reglist bit 8 (LR) set
       - Thumb-2  stmdb sp!, {..., lr} :  2D E9 xx xx with bit 14 (LR) in reglist
  2. Leaf functions with no frame push:
       - Thumb-1  sub sp, #imm      :  B0 xx (0xB0..0xB7, sub sp, #imm*4)
       - Thumb-2  sub.w sp, sp, #imm :  2D ED xx xx (SUB SP, immediate, T2)
       Only counted if preceded by something that looks like a call boundary
       (a BL/B/POP/BX to this address, or a preceding function's end).
  3. Tail-call-via-B thunks: short sequences (movw/movt/bx or a lone b) that
       exist between discovered functions and are reached by a B from elsewhere.

  4. Recursive-descent CFG: start from the boot entry (0x20) and the reset
       vector, follow every BL and conditional/unconditional B target, marking
       reachable code. Reports coverage = reachable / total discovered.

Output: analysis/functions_full.json  (all discovered functions with bounds)
        + a coverage summary on stderr.

Usage:
    ./discover_functions.py                 # full scan
    ./discover_functions.py --cfg           # also do recursive-descent reachability
    ./discover_functions.py --out file.json # custom output
"""
from __future__ import annotations
import argparse
import json
import os
import sys

try:
    import capstone
except ImportError:
    print("pip install capstone", file=sys.stderr)
    sys.exit(1)

# Thumb-2 prologue opcodes
STMDB_SP = bytes([0x2D, 0xE9])   # stmdb sp!, {...}  (push) — first two bytes


def is_thumb1_push_lr(off, d):
    """Thumb-1 push {..., lr}: 0xB5xx  -> 1011 0101 rrrr rrrr ; the 0xB5 opcode
    already encodes L=1 (LR pushed). byte[1]==0xB5 is sufficient."""
    if off + 1 >= len(d):
        return False
    return d[off + 1] == 0xB5


def is_thumb2_stmdb_lr(off, d):
    """Thumb-2 stmdb sp!, {...}: 2D E9 xx xx ; LR is bit 14 of the 16-bit reglist."""
    if off + 3 >= len(d):
        return False
    if d[off] != 0x2D or d[off + 1] != 0xE9:
        return False
    reglist = (d[off + 2]) | (d[off + 3] << 8)
    return (reglist & 0x4000) != 0   # bit 14 = LR


def is_thumb1_sub_sp(off, d):
    """Thumb-1 sub sp, #imm: 0xB0xx (1011 0000 0iii iiii) -> sub sp,sp,#imm*4."""
    if off + 1 >= len(d):
        return False
    return d[off + 1] == 0xB0 and (d[off] & 0xC0) == 0x00   # top 2 bits of imm == 0 -> sub


def is_thumb2_sub_sp(off, d):
    """Thumb-2 sub.w sp, sp, #imm: 2D ED xx xx (SUB SP, immediate, T2)."""
    if off + 3 >= len(d):
        return False
    # Encoding T2 of SUB (immediate): 1110 1101 0x xx 0110 ... ; we match 2D ED
    return d[off] == 0x2D and d[off + 1] == 0xED


def find_end(off, d, md, max_size=0x20000):
    """Disassemble forward from `off` until a return/epilogue or next prologue.
    Capped at max_size bytes so a function with no clear epilogue doesn't scan
    to end of file."""
    p = off
    limit = min(off + max_size, len(d))
    while p + 2 < limit:
        # stop if next prologue starts (function boundary)
        if p != off and (is_thumb1_push_lr(p, d) or is_thumb2_stmdb_lr(p, d)):
            return p
        hw = d[p] | (d[p + 1] << 8)
        # Thumb-1 POP {..., pc}: 0xBDxx (1011 1101 rrrr rrrr), bit8=PC
        if (hw & 0xFF00) == 0xBD00 and (hw & 0x0100):
            return p + 2
        # Thumb-1 BX LR: 47 70
        if hw == 0x4770:
            return p + 2
        # Thumb-2 POP.W {..., pc}: BD E8 xx xx with bit15 (PC) set
        if d[p] == 0xBD and d[p + 1] == 0xE8 and p + 3 < limit:
            reglist = d[p + 2] | (d[p + 3] << 8)
            if reglist & 0x8000:
                return p + 4
        p += 2
    return min(p, limit)


def discover(d):
    """Return a dict addr->end for all prologue-detected functions."""
    funcs = {}
    # Pass 1: push/lr prologues (the baseline)
    for off in range(0, len(d) - 1, 2):
        if is_thumb1_push_lr(off, d) or is_thumb2_stmdb_lr(off, d):
            if off not in funcs:
                end = find_end(off, d, None)
                funcs[off] = end
    return funcs


def _is_plt_thunk(d, off, md):
    """PLT thunk: movw ip,#lo ; movt ip,#hi ; bx ip  (12 bytes) — REPORT §4 pattern."""
    if off + 12 > len(d):
        return False
    ins = list(md.disasm(d[off:off + 12], off))
    if len(ins) >= 3:
        m = [i.mnemonic for i in ins]
        if m[0] in ("movw", "mov.w") and m[1] in ("movt", "movt.w") and m[2] == "bx":
            return True
    # single unconditional B to a far target (tail-call trampoline)
    hw = d[off] | (d[off + 1] << 8)
    if (hw & 0xF800) == 0xE000:
        return True
    return False


def _branch_targets(d, start, end, md):
    """Disassemble [start,end) and yield (target, is_call) for BL/BLX/B targets."""
    if start >= len(d):
        return
    chunk = d[start:min(end, len(d))]
    for ins in md.disasm(chunk, start):
        mn = ins.mnemonic
        is_call = mn in ("bl", "blx")
        is_b = mn in ("b", "b.w") or (mn.startswith("b") and mn not in
                ("bic", "bkpt", "bic.w", "bfi", "bfc", "bfx"))
        if not (is_call or is_b):
            continue
        op = ins.op_str.strip()
        if op.startswith("#"):
            try:
                tgt = int(op.lstrip("#"), 0)
            except ValueError:
                continue
            yield (tgt & ~1, is_call)


def cfg_discover(d, seeds, prologue_funcs, md):
    """Recursive-descent from seed addresses, following BL (calls) and B
    (tail-calls). Intra-function B targets (loops/conditionals) are NOT new
    functions — only a B that exits the current function's [start,end) is a
    tail-call to another function.

    Returns reached_prologue, leaves, thunks, all_reached_blocks.
    """
    reached_blocks = set()
    reached_prologue = set()
    leaves = {}
    thunks = {}
    stack = [(s, None) for s in seeds]   # (target, enclosing_func_end)
    while stack:
        s, enc_end = stack.pop()
        if s in reached_blocks or s < 0 or s >= len(d):
            continue
        reached_blocks.add(s)

        if s in prologue_funcs:
            end = prologue_funcs[s]
            reached_prologue.add(s)
        elif is_thumb1_sub_sp(s, d) or is_thumb2_sub_sp(s, d):
            end = find_end(s, d, md)
            leaves[s] = end
        elif _is_plt_thunk(d, s, md):
            end = min(s + 0x10, len(d))
            thunks[s] = end
        else:
            # reached code that is not a function start (mid-function jump target
            # or data) — give it a small window so we still follow its branches
            end = min(s + 0x40, len(d))

        for tgt, is_call in _branch_targets(d, s, end, md):
            if not (0 < tgt < len(d)):
                continue
            if tgt in reached_blocks:
                continue
            if is_call:
                # BL = call -> always a new function candidate
                stack.append((tgt, end))
            else:
                # B = jump. If it stays inside this function, it's a loop/conditional
                # (not a new function). If it exits, it's a tail-call.
                if s in prologue_funcs and s <= tgt < end:
                    continue   # intra-function branch
                if enc_end is not None and enc_end > 0 and tgt < enc_end and tgt >= s:
                    continue
                stack.append((tgt, end))
    return reached_prologue, leaves, thunks, reached_blocks


def main():
    ap = argparse.ArgumentParser(description="Discover functions in sdram1.bin")
    here = os.path.dirname(os.path.abspath(__file__))
    default_in = os.path.normpath(os.path.join(here, "..", "extracted", "C1A", "sdram1.bin"))
    default_out = os.path.normpath(os.path.join(here, "..", "analysis", "functions_full.json"))
    ap.add_argument("input", nargs="?", default=default_in)
    ap.add_argument("-o", "--out", default=default_out)
    ap.add_argument("--cfg", action="store_true", help="also run recursive-descent reachability")
    args = ap.parse_args()

    d = open(args.input, "rb").read()
    n = len(d)
    print(f"sdram1.bin: {n} bytes (0x{n:X})", file=sys.stderr)

    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)

    base = discover(d)
    print(f"pass 1 (push/lr prologue):  {len(base)} candidate functions", file=sys.stderr)

    # --- True reachability from the boot entry alone (coverage metric) ---
    rp_boot, lf_boot, tk_boot, rb_boot = cfg_discover(d, [0x20], base, md)
    coverage = len(rp_boot) / len(base) if base else 0
    print(f"pass 2a (CFG from 0x20):    {len(rp_boot)}/{len(base)} prologue "
          f"reached = {coverage:.1%}", file=sys.stderr)

    # --- Reachability from the known Core-1 IPC/dispatch entry points. The boot
    #     entry only calls the loader + shared kernel (outside this file); the
    #     2,985 Core-1 functions are invoked via the UMDW IPC dispatcher, so the
    #     real "main" seeds are the receiver tasks (per REPORT §6/§8/§9). ---
    ipc_seeds = [0x20, 0x1B7D4, 0x1B730, 0x25DA, 0x76B20, 0x214A, 0x1A74E]
    ipc_seeds = [s for s in ipc_seeds if s < n]
    rp_ipc, lf_ipc, tk_ipc, rb_ipc = cfg_discover(d, ipc_seeds, base, md)
    ipc_cov = len(rp_ipc) / len(base) if base else 0
    print(f"pass 2b (CFG from IPC seeds): {len(rp_ipc)}/{len(base)} prologue "
          f"reached = {ipc_cov:.1%}", file=sys.stderr)

    # --- Broader discovery: seed from every prologue start too, so leaves/thunks
    #     reachable from any real function are found (not just from boot). ---
    seeds = [0x20] + sorted(base)
    rp_all, leaves, thunks, rb_all = cfg_discover(d, seeds, base, md)
    print(f"pass 2c (CFG, all seeds):   leaves={len(leaves)}  thunks={len(thunks)}", file=sys.stderr)

    all_funcs = dict(base)
    all_funcs.update(leaves)
    all_funcs.update(thunks)
    total = len(all_funcs)
    reached_any = rp_all | set(leaves) | set(thunks)
    print(f"TOTAL functions:            {total}  (prologue {len(base)} + leaf {len(leaves)} "
          f"+ thunk {len(thunks)})", file=sys.stderr)
    print(f"reachable from boot 0x20:    {len(rp_boot)}/{len(base)} prologue = {coverage:.1%}",
          file=sys.stderr)
    print(f"reachable from IPC seeds:    {len(rp_ipc)}/{len(base)} prologue = {ipc_cov:.1%}",
          file=sys.stderr)
    print(f"reachable from any seed:      {len(reached_any & set(base))}/{len(base)} prologue",
          file=sys.stderr)

    out = []
    for s in sorted(all_funcs):
        e = all_funcs[s]
        kind = "push_lr" if s in base else ("leaf" if s in leaves else "thunk")
        out.append({"addr": f"0x{s:x}", "start": s, "end": e, "size": e - s,
                    "kind": kind, "reachable_from_boot": s in rp_boot,
                    "reachable_from_ipc": s in rp_ipc,
                    "reachable_from_any": s in reached_any})
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"written: {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
