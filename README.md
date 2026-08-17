# MC-101 SysEx & Protocol Analysis

Analysis of Roland MC-101 firmware v1.82 (build 14423, dated 2023-05-17) for
interoperability purposes. Product internal codename `RPG69` (shared with MC-707).
SoC family: Roland **BMC**.

## Contents of this folder

```
mc101-firmware-re/
├── README.md          this file
├── REPORT.md          full technical report (17 sections, ~30 KB)

├── FEASIBILITY.md     distance estimates for concrete goals — read this
│                      before starting any modding project
├── TODO.md            open questions + concrete next actions
├── LEGAL.md           legal analysis for publishing findings (EU/Germany + US)
├── CONTRIBUTION_PLAN.md  PR opportunities for community repos
├── blog_post.md       concise blog post of findings
│
├── analysis/          static-analysis outputs (our work, not Roland binaries)
│   ├── functions.json   74 string-tagged functions (subset; see functions_full)
│   ├── functions_full.json  3,370 discovered functions (prologue + leaf + thunk, with CFG reachability)
│   ├── string_xrefs.json  per-string owner-function map (455 unique strings referenced)
│   ├── callgraph.json   1,095 BL-target indices
│   ├── pmb_tables.json  decoded PMB parameter-region tables (19 + 11 entries, with names)
│   ├── pmb_probe_live.md  live PMB probe results from a connected MC-101 (domain-tag layer finding + clip-grid scan)
│   └── clip_grid.csv      8×16 clip-grid scan (tone + clip/scene name layers, 256 probes)
│
├── tools/
│   ├── README.md
│   ├── pmb_probe.py          live PMB region verifier (SysEx RQ1 read-only probe)
│   ├── clip_grid_scan.py     map 8×16 clip grid via SysEx RQ1 (tone + clip/scene name layers)
│   ├── dt1_write.py          send DT1 (Data Set 1) writes to MC-101 via SysEx (with RQ1 verify)
│   ├── init_lzs_decode.py   decompress the factory init project (Okumura LZSS)
│   └── discover_functions.py  find functions in sdram1.bin (prologue + leaf + thunk + CFG)
│
├── pmb_probe.csv         native-tag probe log (24 probes)
├── pmb_probe_scanall.csv  wide scan log (120 probes, 5 domain tags)
└── clip_grid.csv         8×16 clip-grid scan (256 probes)
```

**Not in this repo:** Roland firmware binaries and extracted content
(`firmware/`, `extracted/`, `mc707/`, `mc707_v120/`). These are copyrighted
and not redistributed. See "Obtaining the firmware" below.

## Where to start

- **`REPORT.md`** — the full technical report (or the [styled HTML version](https://soobrosa.github.io/mc101-firmware-re/))
- **`FEASIBILITY.md`** — if you have a concrete modding goal, read this *first*. Answers "how close are we to X?" for older-firmware value, custom preset UI, and sidechain, each with realistic time / effort estimates
- **`CROSS_VERSION.md`** — three-way cross-product cross-version analysis (MC-101 v1.82, MC-707 v1.82, MC-707 v1.20). Confirms only 2 files change between versions; all sample/preset content byte-identical
- **`TODO.md`** — open questions ranked by yield-per-effort, plus corrections-applied checklist
- **`tools/pmb_probe.py`** — the one runnable thing here; live PMB region verifier over SysEx

## What lives on the device we can and can't touch

**Can read/analyze offline (with firmware downloaded from Roland):**
- Every plaintext file in `extracted/` (unpack the tar from Roland's update)
- Full disassembly of `sdram1.bin` (Core-1 DSP code — 3.7 MB Thumb-2, ARM Cortex-M4/M7)
- The analyzed UMDW inter-core protocol, factory Test Mode dispatch, WROM directory, PMB parameter address model, boot loader mechanics

**Blocked without a physical device:**
- The encrypted App1_Main payload (C0A) — key not present in firmware updates
- The higher-level SysEx parser (in App1_Main) — determines what external MIDI commands reach the UMDW pipe

**Blocked without a physical MC-101 + MIDI:**
- Verifying PMB region boundaries live (`tools/pmb_probe.py` is ready to do this)

## Obtaining the firmware

This repo does **not** redistribute Roland's firmware binaries. To reproduce
the analysis, download the firmware update from Roland's support site:

- **MC-101 v1.82**: https://www.roland.com/global/support/by_product/mc-101/updates_drivers/
- **MC-707 v1.82**: https://www.roland.com/global/support/by_product/mc-707/updates_drivers/

The download is a zip containing `MC101_UPA_up.bin` (or `MC707_UPA_up.bin`),
which is a GNU tar archive. Untar it to get the four component files
(`RPG69_C0A_up.bin`, `RPG69_C0C_up.bin`, `RPG69_C1A_up.bin`, `RPG69_C1C_up.bin`).
The C0C and C1A containers are plaintext QSPI images that can be unpacked
with `tar xf` to get the individual files (sdram1.bin, init.lzs, PCM banks, etc.).

## Community context

Multiple community projects work on Roland MC-101/MC-707 interoperability — see §12a in REPORT.md.
Notable convergent work: @ajmwagar independently reached identical structural findings on
the sister TR-6S device in August 2026, confirming the shared BMC SoC platform across
MC-101, MC-707, TR-8S, TR-6S, Fantom, and Jupiter-X.

## Legal note

This repository contains **analysis and tools only** — no Roland firmware
binaries, extracted code, or copyrighted content is redistributed.

Analysis was performed on a firmware update file freely distributed by Roland
on their support website. No encryption bypass was attempted; static analysis
of plaintext components and live probing via the device's public MIDI
interface only. Not affiliated with Roland Corporation. For research and
interoperability purposes.

See `LEGAL.md` for a detailed legal analysis of publishing these findings
from Germany/EU and the US, including the EU Software Directive (2009/24/EC),
EULA enforceability, and the idea/expression dichotomy.
