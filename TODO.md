# TODO / Open questions

Ranked by yield-per-effort. High-yield/low-effort at the top.

---

## Software-only (no hardware needed)

### [x] Decompress `init.lzs` with standard Okumura LZSS
- **File:** `extracted/C0C/init.lzs` (969 KB compressed)
- **Done (2026-08-16):** `tools/init_lzs_decode.py` decodes it to exactly 8,153,245 bytes. Key format details that defeated the first attempt: stream starts at file offset 0x20 (32-byte container header before it), ring buffer pre-filled with zeros (not 0x20 spaces), match length `(hi & 0x0F) + 3`, flags LSB-first. Output `extracted/C0C/init_project.mpj` verified: header `0x007E`+`PRJ5`, TOC matches MC707_FORMAT.md §1, content = "INIT PRJ" / 64× InitTone / InitDrum / 0 samples.

### [~] Push callgraph coverage past 90%
- **Partially done (2026-08-16):** `tools/discover_functions.py` now finds **3,370 functions** (up from 1,876): 2,985 push/lr prologue (the old 1,876 was undercounting — it wrongly required R0 in the reglist), + 26 leaf (sub-sp prologue), + 359 PLT thunks (movw/movt/bx + single-B trampolines). Output: `analysis/functions_full.json`.
- **Reachability finding (important):** a recursive-descent CFG from the boot entry (0x20) reaches **0%** of the prologue functions, and from the IPC dispatch entry points (UMDWRxSysCmd 0x1B7D4, read_umdw 0x1B730, ParamAddrToName 0x25DA, CheckWaveROM 0x76B20, RTE 0x214A, dispatch 0x1A74E) reaches only **5.4%** (161/2985). This is expected and informative: the boot entry only calls the loader + shared kernel (at 0x0110xxxx, **outside** sdram1.bin), and most Core-1 functions are dispatched via (a) shared-kernel PLT thunks that jump out of this file and (b) the PIC function-pointer section-init table (REPORT §10.2), which a static CFG cannot follow. So "90% reachability from a single entry" is not achievable from this file alone — the dispatch graph spans Core-0 + the shared kernel image, neither of which is in the update package.
- **Remaining gap to the ~5,000 estimate:** functions with no frame-setup prologue (leaf funcs that start with `sub rX,rY,#imm` / `mov` and never touch SP) are not detectable by prologue scan alone; they need reachability, which is blocked by the out-of-file dispatch. Closing this gap requires the shared-kernel image (0x01100000-0x0113xxxx), which is not shipped.
- **Effort remaining:** blocked on the shared-kernel image; not reachable from sdram1.bin alone.

### [x] Fully expand PMB descriptor tables from static analysis
- **Done (2026-08-16):** the table data IS embedded in `sdram1.bin` (file 0x96168 / 0x96240), not in the C0C QSPI images. Disassembly of resolver fn 0x25da corrected the struct to `{name_ptr, base_addr, size}` (12-byte stride, 19 entries). Table 1: 19 regions at 0x4124/46/44/4A...0x9A (groups of 0x10000/0x3000/0x8000-0x4000), named with Roland internal debug labels (Wr(1), Rd(1), SIO#1, mxmon1, r1, mac0/1, ...). Table 2: 11 sub-category regions at 0x41110000-0x41138000 (0x1000 stride). Full table in `analysis/pmb_tables.json`. See REPORT.md §7.2 (corrected).

### [x] Decode the WROM per-ROM 16-byte hash/capability field
- **Done (2026-08-16):** resolved — it is NOT a hash. The `+0x1c` field is a 16-byte ASCII version string: ITGR7 entries all carry `"ITGR7 WRomNNv100"` (WRom03 is the only `v101`); type=8 entries RolandTEST ROM0 / RolandKY022 carry `"  1.0001MAKE COM"` / `"  1.0001VTW"`; all others are zero. The `+0x0c` field for ITGR7 is a binary per-ROM index/version encoding (byte 10 bit 1 = tens digit, byte 11 = ones digit in a bit-permuted nibble, byte 15 = version patch) — not a cryptographic hash, and there are no hidden feature flags. See REPORT.md §9.1 (corrected).

### [ ] Adapt `douglas-carmichael/mc-programmer` for exhaustive PMB scans
- Their lib has 389 named parameters — use their param table as ground truth
- Cross-verify against our analyzed 19-category tables
- **Effort:** ~4 hours

### [x] Update REPORT with a live decode of `init.lzs`
- **Done (2026-08-16):** REPORT.md §11 note updated with the verified decode (8,153,245 bytes, TOC matches MC707_FORMAT.md, INIT PRJ content). Also corrected §7.2 (PMB struct) and §9.1 (WROM +0x1c field is a version string, not a hash).

---

## Requires physical MC-101 (or MC-707) + USB MIDI

### [x] Run `tools/pmb_probe.py` and log which addresses respond
- **Done (2026-08-16):** live probe against a connected MC-101 (USB Generic mode). 45/120 probes responded. All 8 track clip-tone bases + 4 partial offsets confirmed live. NEW finding: the address top byte is a **layer selector** (`0x30`=tone name, `0x20`=clip/scene name) at the same base. Two RE-only internal addresses are externally reachable (`0x00110000`, `0x00200000` via tags `0x20`/`0x40`); the rest of the internal system/per-part regions are not exposed. Device had a user project loaded (clip names TriggerFnktn/INTRO/DROP A/BREAKDOWN). Read-only — no DT1 writes sent. Results: `analysis/pmb_probe_live.md`, `pmb_probe.csv`, `pmb_probe_scanall.csv`. See REPORT.md §12 (updated).

### [ ] Test-mode trigger hunt
- Our RE found 17 factory Test Mode subcommands at UMDW subop 0x60 (§6.1 in REPORT)
- Community has been asking about the external trigger since 2020
- Approach: fuzz DT1 writes to plausibly-magic addresses; watch UMDW debug pipe (if reachable) for route=1/subop=0x60 signatures; also watch for visible UI/LED reactions
- **Effort:** several hours of trial + error
- **Status:** DT1 write capability now proven (clip/project rename works, see `tools/dt1_write.py`); the trigger hunt can proceed with the connected device. **Requires explicit user permission for each write target.**
- Non-obvious: might be a button-combo at power-on rather than SysEx
- **Effort:** several hours of trial + error

### [x] Read parameter-name lookup tables from QSPI
- **Done (2026-08-16, negative result):** probed internal QSPI/RAM addresses via RQ1 (octave-label table `0x610A212C`, PMB table bases `0x61096168`/`0x61096240`, name string table `0x612C6E5C`, pre-translated `0x41xxxxxx` variants). **All silent** — the external SysEx translator only routes to PMB-table parameter blocks, not raw internal data arrays. The RAM note-name array at `0x200837C4` is fundamentally inaccessible (low byte `0xC4` has bit 7 set, invalid in 7-bit-clean SysEx). See `analysis/pmb_probe_live.md` (QSPI section).

### [ ] Verify BMC↔STM32G0 UART protocol against @ajmwagar's TR-6S findings
- MC-101 should follow the same 115200-baud UART/MIDI convention (TR-6S proved for TR-8S/TR-6S)
- Probe: NoteOn/Off = button events, PolyAT = pad RGB LED, CC = indicator LEDs
- **Effort:** requires opening the enclosure — physical

---

## Publishing / community

### [ ] Post findings to Roland Clan forums (subforum ID 69, coincidentally matches "RPG69")
- Especially: the 17 factory Test Mode subops (long-open community question)
- The complete UMDW protocol
- The PMB tables' locations
- Ping @ajmwagar — his TR-6S work and this MC-101 work are directly complementary; his findings could benefit from our UMDW map

### [ ] Coordinate with `mc-programmer` maintainer
- Cross-reference our analyzed param categories vs their 389 named params
- Contribute back to their param table if we find any they lack

### [ ] Consider a joint effort with @ajmwagar (TR-6S) + douglas-carmichael (MC-101 SysEx)
- Best chance of coordinating BMC SoC family findings across products

---

## Confirmed / done this session (with dates)

- [x] `init.lzs` uses standard Okumura LZSS, not the Roland-specific LZ format
  we analyzed from `sdram1.bin` §11
- [x] App1_Main load address = `0x60000000` (QSPI-XIP) §2
- [x] Roland's SoC is called "BMC" §preamble
- [x] Panel controller is STM32G0 speaking 115200-baud UART/MIDI §preamble
- [x] **MC-101 ↔ MC-707 cross-product findings (2026-08-15)** — all 26 non-code data
  blobs byte-identical. `sdram1.bin` is same source, relocated. Only `App1_Main`
  (encrypted UI) differs meaningfully. See REPORT.md §2.
- [x] **Protocol stable across 3.5+ years (2026-08-15)** — MC-707 v1.20 (Nov 2019)
  has 28/30 data files identical to v1.82. UMDW protocol, TestMode dispatch, WROM
  framework all present in v1.20 — our analysis is compatible with every firmware
  version since 2019. See CROSS_VERSION.md for full three-way analysis.
- [x] **RTOS identified: eSOL μT-Kernel (2026-08-15)** — Roland's own MC-707 owner's
  manual page 2 states: "This Product uses the Source Code of μT-Kernel under
  T-License 2.0 granted by the T-Engine Forum." Bundled inside eSOL's "eParts"
  integrated software platform. Same across all BMC devices (Jupiter-X, Fantom,
  MC-101/707, Boss SY-300, AX-Edge, TR-8S, TR-6S).
- [x] **`init.lzs` decompressed (2026-08-16)** — 969,045 → 8,153,245 bytes (exact match to
  ConvertWithMoss's documented size). The earlier decoder failed because the LZSS stream
  starts at file offset 0x20 (32-byte container header before it), the ring buffer is
  pre-filled with zeros (not 0x20 spaces), and match length is `(hi & 0x0F) + 3`. Output is
  the factory INIT PROJECT (`PRJ5`/`MC77`, "INIT PRJ", 64× InitTone, InitDrum, 0 samples).
  Decoder: `tools/init_lzs_decode.py`. See REPORT.md §11.
- [x] **PMB descriptor tables expanded (2026-08-16)** — the table data is embedded in
  `sdram1.bin` (file 0x96168 / 0x96240), not in the C0C QSPI images. Disassembly of
  resolver fn 0x25da corrected the struct from `{prev_ptr, base, size}` to
  `{name_ptr, base, size}` (12-byte stride, 19 entries). Table 1: 19 regions at
  0x4124/46/44/4A...0x9A with Roland internal debug names (Wr(1), Rd(1), SIO#1, mxmon1,
  r1, mac0/1, ...). Table 2: 11 sub-categories at 0x41110000-0x41138000. Full table in
  `analysis/pmb_tables.json`. See REPORT.md §7.2 (corrected).
- [x] **WROM "hash" field resolved (2026-08-16)** — the ITGR7 `+0x1c` 16-byte field is NOT a
  hash; it is an ASCII version string `"ITGR7 WRomNNv100"` (WRom03 is the only `v101`).
  The `+0x0c` field for ITGR7 is a binary per-ROM index/version encoding (bit-permuted
  nibbles), not a cryptographic hash — no hidden feature flags. See REPORT.md §9.1 (corrected).
- [x] **PMB regions verified live on a connected MC-101 (2026-08-16)** — `tools/pmb_probe.py`
  (read-only RQ1) confirmed all 8 track clip-tone bases + 4 partial offsets respond. NEW
  finding: the SysEx address top byte is a **layer selector** (`0x30`=tone name, `0x20`=clip/
  scene name) at the same base — the community docs treated `0x30` as the only external
  space. Two RE-only internal addresses (`0x00110000`, `0x00200000`) are externally
  reachable via tags `0x20`/`0x40`; the rest of the internal system/per-part regions are
  not exposed. Results: `analysis/pmb_probe_live.md`, `pmb_probe.csv`,
  `pmb_probe_scanall.csv`. See REPORT.md §12.4.
- [x] **Full 8×16 clip-grid scan (2026-08-16)** — `tools/clip_grid_scan.py` (read-only
  RQ1, 256 probes) mapped the complete clip grid under both the tone layer (0x30)
  and clip/scene-name layer (0x20). The 0x20 layer exposes all clip/scene names over
  read-only SysEx — a new capability not in community tools. The device's project
  has 7 named sections (INTRO/DROP A/DROP B/DANCE HALL/OUTRO/RHYTHM A/RHYTHM B) on a
  stride-4 pattern. Results: `analysis/pmb_probe_live.md` (clip-grid section),
  `clip_grid.csv`. See REPORT.md §12.4.
- [x] **QSPI parameter-name table probe (2026-08-16, negative)** — all internal QSPI/RAM
  addresses silent via RQ1; the translator only routes to PMB parameter blocks, not
  raw data arrays. RAM note-name array `0x200837C4` is inaccessible (bit7 set). See
  `analysis/pmb_probe_live.md` (QSPI section).
- [x] **DT1 write verification: clip + project rename (2026-08-16)** — `tools/dt1_write.py`
  confirmed DT1 writes to the `0x20` (clip) and `0x10` (project) layers work. Clip name
  "INTRO" → "DROIDTEST" (12-byte field), project name "TriggerFnktn_011" → "DROIDTEST_01"
  (16-byte field). Writes are surgical (only name field overwritten, binary params
  preserved). DT1 writes are not acknowledged but verifiable by RQ1 read-back. This
  enables full project backup/restore over SysEx without the `.mpj` file. See
  `analysis/pmb_probe_live.md` (DT1 section), REPORT.md §12.4.
