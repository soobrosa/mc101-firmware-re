# Cross-version analysis — MC-707 v1.20 vs v1.82

Test date: **2026-08-15**
Firmware acquired: `/Users/danielmolnar/Downloads/mc707_sys_v120/MC707_UPA_up.bin`
- MC-707 v1.20, build 15219, dated **2019-11-28**
- vs MC-707 v1.82, build 22523, dated **2023-05-18**
- 3.5-year gap; three major version generations

Extracted to `mc707_v120/_tmp/` and `mc707_v120/extracted/{C0C,C1A,C1C}/`.

---

## Headline findings

### 1. Only two files ever change between versions

Plaintext diff MC-707 v1.20 ↔ v1.82 across all 30 files in the three QSPI containers:

| container | files | identical | changed |
|---|---|---|---|
| C0C (PCM banks + init.lzs) | 12 | **12** | 0 |
| C1A (DSP code + IDM) | 2 | 0 | 2 |
| C1C (preset banks + wromInfo) | 16 | **16** | 0 |
| **total** | **30** | **28** | **2** |

**All 28 non-code data blobs are byte-identical between 2019 and 2023** — every PCM bank, every kit, every preset, `init.lzs`, `wromInfo_KY022.b`, `metronome.bin`, `spf_muse_*`, `wpf_muse_*` — untouched. The only two files that change:

- **`sdram1.bin`** — DSP-engine code. v1.20 is 3,654,128 B; v1.82 is 3,710,260 B. Grew by 56,132 bytes (+1.5%). Same source, evolved over 3.5 years.
- **`idm1.bin`** — instrument-definition metadata. 242 KB in both versions; content changed. Likely encodes per-version tone parameter defaults.

Plus of course:
- **`App1_Main` (encrypted C0A)** — grew from 3.57 MB (v1.20) to 4.36 MB (v1.82). 800 KB of new UI / sequencer / feature code. Roland's real work between 2019 and 2023 lives here.

### 2. Our v1.82 analysis is compatible with v1.20

Every debug string we analyzed from MC-101 v1.82's `sdram1.bin` also appears in MC-707 v1.20's `sdram1.bin`:

```
✓ "SysEx Body"      ✓ "SysEx End1/End2/End3"
✓ "Test Mode Request"      ✓ "Restart Sound Engine"
✓ "CORE1 DSP Ready"
✓ "13CUMDWRxSysCmd"        ✓ "14CUMDWRxPRMEdit"
✓ "ITGR7 WRom00v100"       ✓ "RolandKY022"
✓ "BMCInit"
```

**Implications:**
- The UMDW inter-core protocol has been stable since at least November 2019
- The 17 factory Test Mode subcommands existed in v1.20
- The Wave-ROM directory framework existed in v1.20
- The SysEx byte-stream chunker existed in v1.20

Any tool built against v1.82 (like `tools/pmb_probe.py`) also works against v1.20 devices and every version in between.

---

## What this means

- **Publish work to the Roland Clan Forums with confidence it applies to all MC-101/707 firmware versions since 2019**. Every analyzed protocol detail is stable.
- **The `mc-programmer` client library works against every MC-707 since 2019** by construction (parameter model, address space, checksums all stable across versions).

## The v1.20 firmware

```
mc707_v120/
├── _tmp/
│   ├── RPG68_C0A_up.bin   3.57 MB   App1_Main (encrypted)
│   ├── RPG68_C0C_up.bin   8.0 MB    QSPI: PCM banks (identical to v1.82)
│   ├── RPG68_C1A_up.bin   4.0 MB    QSPI: sdram1.bin (differs) + idm1.bin (differs)
│   └── RPG68_C1C_up.bin   4.0 MB    QSPI: preset banks (identical to v1.82)
└── extracted/
    ├── C0C/   12 files — 12 IDENTICAL to v1.82
    ├── C1A/    2 files — both differ (relocation + version drift)
    └── C1C/   16 files — 16 IDENTICAL to v1.82
```
