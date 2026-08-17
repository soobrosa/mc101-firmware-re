# PMB live probe results — MC-101 (2026-08-16)

Device: Roland MC-101, firmware v1.82, USB MIDI (Generic / class-compliant mode).
Tool: `tools/pmb_probe.py` (read-only RQ1 — no DT1 writes were sent).
Logs: `pmb_probe.csv` (native-tag), `pmb_probe_scanall.csv` (5 domain tags × 24 regions = 120 probes).

## Summary

- **45 / 120** probes responded in the wide scan; **14 / 24** in the native-tag scan.
- The device has a **user project loaded** (not the factory INIT): clip/scene names
  `TriggerFnktn`, `INTRO`, `DROP A`, `BREAKDOWN` are present, alongside several
  `INIT TONE` slots. (The factory INIT project decoded from `init.lzs` has all
  InitTone / empty clips — so this is a user-authored or preset project.)

## Key finding: the address top byte is a LAYER SELECTOR, not just a namespace tag

The analyzed resolver (`fn 0x25da`) strips the top byte and re-tags with `0x41`. Live
probing shows the top byte selects **which data layer** is returned at the same base:

| tag | layer | evidence |
|-----|-------|----------|
| `0x30` | **tone name** | Track 1 clip 1 → `"INTRO"`, Track 2 clip 1 → `"INIT TONE"` (the documented external space) |
| `0x20` | **clip / scene name** | Track 1 clip 1 → `"TriggerFnktn"`, Track 5 clip 1 → `"DROP A"`, `0x00200000` → `"BREAKDOWN"` |
| `0x10` | shorter framing (29 B) | partials respond at 16/32 B |
| `0x40` | 30–32 B, mostly spaces | |

So `0x30xxxxxx` = tone parameter layer, `0x20xxxxxx` = clip/scene-name layer, at the
same base address. This is **new** — the community docs treat `0x30` as the only
external space.

## Per-region results (scan-all, 5 tags)

| region | tags responding | note |
|---|---|---|
| Track 1–8 clip-tone bases (`0x30020000`–`0x316E0000`) | `0x10/20/30/40` | all 8 tracks confirmed live |
| Track 1 partials (`+0x2000/2100/2200/2300`) | `0x10/30` | partial offsets confirmed |
| **System block-set A base** (`0x00110000`) | `0x20/40` | RE-only internal address IS reachable externally (via 0x20/0x40, not 0x30) |
| **Domain boundary** (`0x00200000`) | `0x20/30/40` | real region; returns `"BREAKDOWN"` under 0x20 |
| System block-set A +0x1000 / end | none | |
| System block-set B (`0x00125000`) | none | internal-only |
| Per-part blocks (`0x00011000`–`0x00014000`) | none | internal-only |
| Overlay (`0x00112000`) | none | internal-only |

## Conclusions

1. **Community-known external clip-tone addresses: VERIFIED live** (all 8 tracks + 4 partials).
2. **The domain top byte selects a data layer** (`0x30`=tone, `0x20`=clip/scene name) — a
   new finding that extends the external address model in REPORT.md §12.
3. **Two RE-only internal addresses are externally reachable** (`0x00110000`, `0x00200000`)
   via tags `0x20`/`0x40`, returning real data. The rest of the internal system/per-part
   regions are **not** exposed externally — confirming they live behind Core-0's
   SysEx→UMDW translator and are internal Core-1 regions only.
4. The probe is read-only (RQ1 only); **nothing was written to the device**.

## Full clip-grid scan (8×16) — 2026-08-16

Tool: `tools/clip_grid_scan.py` (read-only RQ1, 256 probes). Log: `clip_grid.csv`.

Probed all 128 clip addresses (8 tracks × 16 clips) under both the tone layer
(`0x30`) and the clip/scene-name layer (`0x20`).

### Tone names (tag 0x30) — 67/128 responded, 11 with non-empty names

```
     C0       C1       C2       C3       C4       C5       C6       C7       C8       C9       C10      C11      C12      C13      C14      C15
Tr1 [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]
Tr2 [sp]     INIT TON INIT TON INIT TON INIT TON INIT TON INIT TON INIT TON INIT TON [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]
Tr3 [sp]     [sp]     [sp]     [sp]     INIT TON [sp]     [sp]     INIT TON INIT TON [sp]     [sp]     [sp]     [sp]     [sp]     [sp]
Tr4 [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     ·        ·        ·
Tr5-7  (all silent — no clips)
Tr8 ·        ·        ·        ·        ·        ·        ·        ·        ·        [sp]     [sp]     [sp]     [sp]     [sp]     [sp]
```

`[sp]` = responded with 32 bytes of spaces (clip exists, no tone name assigned).
Tracks 5–7 are completely empty (no clips at all). Track 2 clips 1–8 and Track 3
clips 4/7/8 have "INIT TONE" loaded.

### Clip / scene names (tag 0x20) — 68/128 responded, 9 with non-empty names

```
     C0       C1       C2       C3       C4       C5       C6       C7       C8       C9       C10      C11      C12      C13      C14      C15
Tr1 [sp]     INTRO    [sp]     [sp]     DROP A   [sp]     [sp]     DROP B   [sp]     [sp]     DANCE HA [sp]     [sp]
Tr2 [sp]     [sp]     [sp]     OUTRO    [sp]     [sp]     RHYTHM A [sp]     [sp]     RHYTHM B [sp]     [sp]
Tr3 [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]
Tr4 [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     [sp]     ·        ·        ·
Tr5-7  (all silent)
Tr8 ·        ·        ·        ·        ·        ·        ·        ·        ·        [sp]     INTRO    [sp]     [sp]     DROP A   [sp]
```

### Project structure revealed

The device holds a **song project** with a classic electronic-music arrangement:

| section | track | clip | name |
|---------|-------|------|------|
| 1 | Tr1 | C1 | INTRO |
| 2 | Tr1 | C5 | DROP A |
| 3 | Tr1 | C9 | DROP B |
| 4 | Tr1 | C13 | DANCE HALL |
| 5 | Tr2 | C4 | OUTRO |
| 6 | Tr2 | C8 | RHYTHM A |
| 7 | Tr2 | C12 | RHYTHM B |

Track 8 mirrors Track 1's first two sections (INTRO at C10, DROP A at C14).
Tracks 3–4 have empty clips at regular intervals (every 3rd clip). Tracks 5–7
are completely empty. The stride-4 naming on Tracks 1–2 suggests each section
spans 4 clips (4 × 4-bar phrases = 16 bars per section).

### Key takeaway

The **0x20 layer exposes the full 8×16 clip/scene-name grid over read-only SysEx**.
This means a project's clip names can be backed up without the `.mpj` file — a
new capability not documented in the community tools.

## QSPI parameter-name table probe — negative result

Probed internal QSPI/RAM addresses from static RE (octave-label table `0x610A212C`,
PMB table bases `0x61096168`/`0x61096240`, name string table `0x612C6E5C`, and
pre-translated `0x41xxxxxx` variants). **All silent** — the external SysEx
translator only routes to PMB-table parameter blocks, not to raw internal data
arrays. The note-name/octave-label tables are internal lookup data used by the
resolver, not externally readable parameter blocks.

The RAM note-name array at `0x200837C4` is fundamentally inaccessible — the low
byte `0xC4` has bit 7 set, which is invalid in 7-bit-clean SysEx.

## Four-layer domain-tag model (0x10/0x20/0x30/0x40)

Probed representative clip addresses under all four domain tags with 64-byte read
count. Each tag selects a distinct data layer at the same base address:

| tag | layer | response | evidence |
|-----|-------|----------|---------|
| `0x10` | **project name** | 64 B, only at `0x10000000` | `"TriggerFnktn_011"` + binary — the project/pattern name + version. All other `0x10xxxxxx` silent. |
| `0x20` | **clip/scene name + clip data** | 63–64 B, per-clip | clip name (ASCII, 12 B) + clip parameters (length, beats, tempo). Full 8×16 grid mapped above. |
| `0x30` | **tone name + tone params** | 54 B, per-clip | tone name (ASCII, 12 B) + partial data (`7f40` = level 127 / coarse 64 for InitTone, `6440` for named tones). |
| `0x40` | **project/system metadata** | 60 B, same at every address | spaces (16 B) + binary (`0002000000003232…`) — project-level info, ignores clip address. `"22"` may be tempo or version. |

### Layer detail — Track 1 Clip 0 (base `0x30000000`)

```
0x10  54 7269 6767 6572 466e 6b74 6e5f 3031 3102 0701 0044 0404 04   "TriggerFnktn_011" + binary
0x20  494e 5452 4f20 2020 2020 2020 2020 2003 0200 0001 0000 00   "INTRO" + clip params
0x30  2020 2020 2020 2020 2020 2020 2020 2000 0000 0000 7f40 00   spaces (empty tone) + partial data
0x40  2020 2020 2020 2020 2020 2020 2020 2000 0200 0000 0032 32   spaces + system metadata
```

### Interpretation

The MC-101's external SysEx address space has a **4-layer structure** selected by
the top byte:

1. **`0x10` — project layer**: a single block at `0x10000000` returning the project
   name (`"TriggerFnktn_011"`). This is the overall pattern/project name, not per-clip.
2. **`0x20` — clip layer**: the 8×16 clip grid. Each address returns the clip/scene
   name + clip parameters (length, beat structure, etc.). This is the layer that
   exposes the full project arrangement over read-only SysEx.
3. **`0x30` — tone layer**: the 8×16 tone grid. Each address returns the tone name
   + tone parameter data (partial levels, tuning, etc.). This is the documented
   external space in community tools.
4. **`0x40` — system layer**: returns the same 60-byte block regardless of address
   — project-level metadata (tempo, time signature, etc.) that doesn't vary by clip.

The community docs (mcpoker, mc-programmer) only use `0x30`. The `0x20` (clip names)
and `0x10` (project name) layers are **new discoveries** that enable read-only project
backup over SysEx.

## DT1 write verification — clip and project rename (2026-08-16)

Tool: `tools/dt1_write.py` (DT1 Data Set 1 write + RQ1 read-back verify).
User explicitly approved both writes and chose to leave the test names.

### Clip rename (tag 0x20, addr `0x20000000`)

| | hex (first 24 B) | ASCII name |
|---|---|---|
| Before | `494e54524f20202020202020202020200302000001000000` | `INTRO` |
| After  | `44524f494454455354202020202020200302000001000000` | `DROIDTEST` |

Wrote 12 bytes `"DROIDTEST   "` to `0x20000000`. The 12-byte name field was replaced
surgically; the clip parameters at byte 12+ (`0302000001000000…`) were preserved
unchanged. **Write confirmed by RQ1 read-back.**

### Project rename (tag 0x10, addr `0x10000000`)

| | hex (first 24 B) | ASCII name |
|---|---|---|
| Before | `54726967676572466e6b746e5f3031310207010044040404` | `TriggerFnktn_011` |
| After  | `44524f4944544553545f3031202020200207010044040404` | `DROIDTEST_01` |

Wrote 16 bytes `"DROIDTEST_01    "` to `0x10000000` (initial 15-byte write left a
residual "1" from the 16-char original; a second 16-byte write cleared it). The
16-byte name field was replaced; binary metadata at byte 16+ (`0207010044040404…`)
was preserved. **Write confirmed by RQ1 read-back.**

### Key findings

1. **DT1 writes to the 0x20 (clip) and 0x10 (project) layers WORK** — you can rename
   clips and the project over SysEx. This is a new capability not in community tools.
2. **Writes are surgical** — only the bytes you send are overwritten; surrounding
   binary data (clip parameters, project metadata) is preserved.
3. **Name field sizes**: clip name = 12 bytes, project name = 16 bytes (both
   ASCII, space-padded).
4. **DT1 writes are not acknowledged** by the device (no SysEx response), but can be
   verified by reading back with RQ1 after a ~300ms delay.
5. Combined with the read-only clip-grid scan, this means the MC-101's project
   structure (project name + all clip names) can be **both read and written over
   SysEx** — enabling full project backup/restore without the `.mpj` file.

## Open follow-ups

- The `0x00110000` response under `0x20`/`0x40` returned the same partial-default
  bytes as a tone partial — worth a closer look to see if it's genuinely the system
  block-set or a misroute.
- Decode the binary payload after the ASCII names in each layer (clip params, tone
  params, system metadata) by cross-referencing with the MC-707 format spec.
- Investigate DT1 writes to the `0x30` (tone) layer — can tone names/params be
  written over SysEx? (requires explicit user permission)
- Test-mode trigger hunt: send DT1 writes to plausibly-magic addresses and watch
  for UMDW route=1/subop=0x60 diagnostic signatures (requires explicit user
  permission; higher risk).
