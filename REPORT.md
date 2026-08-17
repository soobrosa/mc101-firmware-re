# Roland MC-101 Firmware v1.82 — Interoperability Analysis Report

Subject: `MC101_UPA_up.bin` (Roland MC-101 firmware update, version 1.82, build 14423, dated 2023-05-17)

Product internal codename: **RPG69** (Zen-Core platform, shared with MC-707)
Product hardware SKU: **KY022**
SoC family: **Roland BMC** (custom BGA — shared with MC-707, TR-8S, TR-6S, Fantom, Jupiter-X)
Panel controller: **STM32G0** (Cortex-M0+, 115200-baud UART speaking MIDI byte stream)
External MIDI model ID: **0x5E** (MC-707 = 0x5D)

---

## 1. File layout

`MC101_UPA_up.bin` is a **GNU tar archive**, not a raw binary. Inside are four component update files for the RPG69 Zen-Core platform:

| File | Size | Content | Format |
|---|---|---|---|
| `RPG69_C0A_up.bin` | 3.5 MB | `App1_Main` — main CPU application | **Encrypted** |
| `RPG69_C0C_up.bin` | 8 MB | PCM tone banks + `init.lzs` | Plaintext QSPI container (12 files) |
| `RPG69_C1A_up.bin` | 4 MB | `idm1.bin` + `sdram1.bin` (DSP code) | Plaintext QSPI container (2 files) |
| `RPG69_C1C_up.bin` | 4 MB | Preset metadata + metronome | Plaintext QSPI container (16 files) |

Each ends with an ASCII tag: `Roland RPG69_C0<A|C|X> VER.1.82-BLD.14423 0517 22 <mm> <ss>`.

**Naming convention:**
- `C0` = Core 0 (main ARM CPU, UI/MIDI/SysEx/parameter engine)
- `C1` = Core 1 (DSP / voice engine)
- `A` = application (executable)
- `C` = content (data, samples, presets)

## 2. Encrypted App1_Main (C0A) — container format

### Container header (plaintext, 0x60 bytes)
```
0x00  "App1_Main"                       (16-byte name)
0x10  "2023/05/17 22:54"                (build timestamp)
0x20  "0.010001"                        (payload version)
0x30  TOC slot (empty, 0xFF-filled)
0x40  TOC slot (empty)
0x50  TOC slot (empty)
0x60  START OF ENCRYPTED PAYLOAD, size 0x003565B0 (8- and 16-aligned)
end-100  4-byte checksum: 97 EF F5 0B
end-48   ASCII tag "Roland RPG69_C0A VER.1.82-BLD.14423 0517 22 54 58"
```

The payload is encrypted and not shipped in a readable form. The decryption key is not present in any firmware update file.

**Load address:** `0x60000000` (QSPI-XIP region) — this is where the decrypted App1_Main lands at runtime. Consistent with the "internal address 0x60xxxxxx" pointers we see everywhere in `sdram1.bin`.

### MC-101 ↔ MC-707 cross-product findings (this session)

Cross-checked MC-101 v1.82 (`RPG69`) against MC-707 v1.82 (`RPG68`) — same-day build train (2023-05-17 22:54:58 vs 2023-05-18 00:00:21, ~1 hour apart):

- **All PCM tone banks, kit banks, preset banks, `init.lzs`, `wromInfo_KY022.bin`, metronome samples — byte-identical** (26 files across C0C and C1C containers). Every non-code data blob is shared. The products differ only in codename tag (`RPG68` vs `RPG69`) and container header size.
- **`sdram1.bin` (Core-1 DSP code) — same source, different link addresses.** 86% of bytes differ, but the diff is dense single-byte changes at Thumb-2 BL target-offset positions — the classic signature of same source recompiled with slightly shifted layout. MC-707's is 536 bytes larger; the extra bytes at the tail are a pointer/relocation table.
- **`idm1.bin` differs** — this is instrument-definition metadata, small (242 KB), likely encodes per-device track/pad counts.
- **`App1_Main` differs by ~25%** (MC-101: 3.5 MB, MC-707: 4.4 MB) — MC-707 has 8 tracks vs MC-101's 4, more encoders, encoder ring LEDs, motor faders — extra UI code adds up.

**Practical implication:** the DSP engine and all sample/preset content are effectively one product across MC-101 and MC-707. Only the UI layer (encrypted App1_Main) meaningfully differs.

## 3. QSPI container format (C0C, C1A, C1C)

Same structure across all three plaintext images:

| offset | size | field | description |
|---|---|---|---|
| 0x00 | 4 | total_size | — |
| 0x20 | 4 | magic | "QSPI" + 4 spaces |
| 0x24 | 4 | base_offset | =0x20 |
| 0x28 | 4 | base_offset | =0x20 |
| 0x2C | 4 | file_count | number of file entries |
| 0x30 | 28 per entry | file entries | (file_count x 28-byte entries, see below) |
| 0x1000+ | — | payload files | page-aligned |

Each file entry (28 bytes):

| offset | size | field | description |
|---|---|---|---|
| +0x00 | 16 | name | NUL-padded, 16-char cap (Roland's limit) |
| +0x10 | 4 | offset | relative to container start |
| +0x14 | 4 | size | — |
| +0x18 | 4 | crc16 | stored as 32-bit (top 16 bits zero) |
| +0x1C | 4 | reserved | — |

Contents:

**C0C — PCM tone/kit banks (12 files, ~7.7 MB)**
- `tone_pcmx_cmn.bi[n]`, `tone_pcmEx_ky022.bin`, `tone_pcmEx_rpg68.bin`, `tone_pcmEx_slgnd.bin`, `tone_pcmEx_snsyn.bin`, `tone_pcmEx_i5080.bin`
- `kit_pcmx_cmn.bin`, `kit_pcmx_rpg68.b[in]`, `inst_pcmx_cmn.bin`, `inst_pcmx_rpg68.[bin]`
- `qspi_ver_def.h` — plaintext version stamps
- `init.lzs` — factory-init container (see §7)

**C1A — DSP code + init (2 files)**
- `idm1.bin` (242 KB) — instrument-def metadata
- `sdram1.bin` (3.7 MB) — **Core-1 DSP executable** (the primary target of this RE)

**C1C — Preset banks (16 files, ~1.3 MB)**
- `wromInfo_KY022.b[in]` — 64-byte device-ID stub
- `tone_pcmx_test.b[in]`, `metronome.bin`, `kit_pcmx_metro.b[in]`, `inst_pcmx_metro.[bin]`
- `spf_muse_*` (5 files) — SuperNATURAL preset format banks
- `wpf_muse_*` (5 files) — Wave/patch format banks
- `qspi_ver_def.h`

Version stamp inside both `qspi_ver_def.h`: `TARGET=PCM-EX`, `PRM_VER=0.039`, `QSPI_DATA=0.058`.

## 4. sdram1.bin — Core-1 DSP firmware

### Basics
- **CPU:** ARM Cortex-M4/M7 (Thumb-2 only). Confirmed by LDR from `0xE000ED88` (CPACR — Cortex-M SCB coprocessor register)
- **Load base:** `0x00000000` (in the code-image address space)
- **Size:** 3,709,724 bytes = 0x389B1C
- **Debug symbols:** intact printf-style format strings throughout (~7,400)
- **Discovered functions:** 1,876 by prologue scan; 385+ PLT thunks

### Memory map (deduced)
```
0x00000000 — 0x00389B1C   sdram1.bin (Core-1 code, this file)
0x01100000 — 0x0113_xxxx  Shared kernel / RTOS blob (NOT SHIPPED HERE — probably in Core-0)
0x20000000 — 0x201x_xxxx  SDRAM (.data/.bss/heap/task queues)
0x40000000 — 0x40xx_xxxx  Peripherals (GPIO, timers)
0x41100000                QSPI indirect-read controller
0x60000000 — 0x611x_xxxx  QSPI-XIP (wave-ROM directory, parameter tables, boot helpers)
0xE0000000+               Cortex-M System Control / NVIC
```

### PLT thunk table
Range **0x7D474 — 0x7D5xx** (385+ entries). Each entry is a 3-instruction PLT thunk: load a 32-bit address into the ip register (via two 16-bit immediate moves), then branch to it.
Every `bl 0x7DXXX` from Core-1 code is really jumping to a shared-kernel function at `0x0110xxxx`-`0x0113xxxx`. This is why most utility calls (logger, DMA, ring-buffer, sync, `printf`) converge on the 0x7Dxxx range. The shared kernel isn't in this update package.

Selected thunks (resolved):
```
0x7D47E → 0x01102301   printf/log core
0x7D488 → 0x01102351   log flush
0x7D4F6 → 0x011212A1   UMDW-send / signal
0x7D500 → 0x01120D6D   UMDW-flush
0x7D50A → 0x01129531   formatter used by every debug-print site
0x7DDB6 → 0x01120ED5   ★ PRM-Edit apply (this is where parameter changes go)
0x7DC3A → 0x01129C27   buffer clear
```

## 5. UMDW inter-core protocol

Roland's internal **Universal MIDI Datalink Word** — a 32-bit packed message format used for all IPC between Core-0 (main app) and Core-1 (DSP). Every SysEx byte, every parameter edit, every mute command, every DSP error, flows through this pipe.

### Word layout (32-bit LE)

| bits | field | meaning |
|---|---|---|
| 0–3 | msg_type | 16-way dispatch (see table below) |
| 4–7 | route | 0 = default, 1 = PRM-Edit, 7 = SysCmd (alias for 0) |
| 8–11 | channel | MIDI channel (0..15) for channel-scoped msgs, sub-opcode for system msgs |
| 12–15 | (extended) | usually unused |
| 16–23 | data1 | note#, CC#, patch#, SysEx byte, error id, ... |
| 24–31 | data2 | velocity, CC value, aftertouch, SysEx byte, ... |

### 16-type dispatch (from trace fn 0x1a74e)

| type | meaning | debug print |
|---|---|---|
| 0, 3, 15 | `<undef>` | `Block Edit %02Xh` |
| 1 | system message | (subop-dispatched — see §5.1) |
| 2 | MIST Ctrl (RPN/NRPN?) | `Mist Ctrl Dev%3d Num%3d Val%5d` |
| 4 | SysEx body chunk | `SysEx Body %02X %02X %02X` |
| 5 | SysEx end (1 residual byte) | `SysEx End1 %02X` |
| 6 | SysEx end (2 residual bytes) | `SysEx End2 %02X %02X` |
| 7 | SysEx end (3 residual bytes) | `SysEx End3 %02X %02X %02X` |
| 8 | Note Off | `Ch%2d Note Off   %s %3d` |
| 9 | Note On (vel=0 → NoteOff) | `Ch%2d Note On    %s %3d` |
| 10 | Poly Aftertouch | `Ch%2d Poly After %s %3d` |
| 11 | Control Change | `Ch%2d Control Change ...` |
| 12 | Program Change | `Ch%2d Program Change      %3d` |
| 13 | Channel Aftertouch | `Ch%2d Ch Aftertouch       %3d` |
| 14 | Pitch Bend | `Ch%2d Pitch Bend        %5d` (signed 14-bit) |

SysEx is transported at 3 bytes/word (type 4); when F7 arrives with N residual bytes still in the accumulator, a type 5/6/7 word flushes them (N = 1/2/3).

### 5.1 Type-1 system messages (subops)

| subop | printed message | probable meaning |
|---|---|---|
| 0x0E | `CORE1 Error ID=%3d Info=%3d` | RTE (real-time error) report |
| 0x10 | `CORE1 DSP Level Mon Sw: %d` | metering on/off |
| 0x11 | `CORE1 Requested to start Mute Off Sequence` | unmute begin |
| 0x12 | `CORE1 Requested to start Mute On Sequence` | mute begin |
| 0x40 | `CORE1 DSP Ready` | boot-complete signal |
| 0x41 | *(silent)* | ack |
| 0x42 | `CORE1 Mute On Sequence Done` | mute complete |
| 0x43 | `CORE1 Mute Off Sequence Done` | unmute complete |
| **0x60** | **`Test Mode Request`** | **factory-service entry** |
| **0x61** | `Test Mode Reply '%c'` | factory-service reply |
| **0xFE** | `Restart Sound Engine` | force DSP restart |
| ≥0x80 | `Block Edit %02Xh` | parameter-block edit |

## 6. SysCmd receiver (13C UMDWRxSysCmd) — fn 0x1B7D4

Full receiver task loop. ~600 bytes of Thumb-2 at **0x1B7D4**. Reads UMDW words from queue at RAM `0x2008394C` via `read_umdw()` at `0x1B730`.

### Dispatch logic

The receiver reads 8-byte UMDW words from a queue. The top nibble of byte 0 is the **route**:

- **Route 1** → PRM-Edit: forwards the word to the parameter-edit handler via a PLT thunk at `0x7DDB6` (→ shared kernel `0x01120ED5`), using a parameter context at RAM `0x2009D1B8`.
- **Route 0 or 7** → SysCmd dispatch: byte 1 is the **subop**, dispatched via a switch table.
- **Other routes** → dropped.

Subop dispatch table:

| subop | description |
|---|---|
| 0x10 | config: sets flag bit at context+0xF0 |
| 0x11 | handler at `0x1406` |
| 0x12 | handler at `0x13DE` |
| 0x13 | 11-way sub-dispatch on byte 2 (TBB at `0x1B8FE`) |
| 0x20 | bulk/dump-related, calls fn `0x25D6A` with byte 3 |
| 0x48 | 6-way Model/Device query (TBB at `0x1B8A0`) |
| 0x4D | handler at `0x2DCAA` (audio-format command) |
| 0x4F | three sub-calls: `0x2A7A2`, `0x2A7B2`, `0x2B3E4` |
| 0x60 | 17-way Test Mode dispatch (TBB at `0x1B976`) |

### 6.1 Test Mode subcommands (subop 0x60) — 17 entries

| subcmd | dispatch tgt | handler fn |
|---|---|---|
| 0x00 | 0x1B988 | 0x75A34 — main test-mode entry (large) |
| 0x01–0x04 | 0x1BA06 | fallthrough / no-op |
| 0x05 | 0x1B9B4 | 0x2080C |
| 0x06 | 0x1B9BC | 0x20990 |
| 0x07–0x0A | 0x1B9C4 | 0x20A5A |
| 0x0B | 0x1B9CE | 0x20B26 |
| 0x0C | 0x1B9D6 | 0x20BE0 |
| 0x0D | 0x1B9DE | 0x20CAA |
| 0x0E | 0x1B9E6 | 0x20DB0 |
| 0x0F | 0x1B9EE | 0x20E6A |
| 0x10 | 0x1B9F6 | 0x20EA2 |

**This is the Roland factory test suite.** Community has been asking about the trigger for years (see Roland Clan Forum thread "Factory Test Program - how to activate?", 2020) — the *dispatch table* is here; the *external trigger* is in encrypted C0A.

### 6.2 Model/Device query subcommands (subop 0x48) — 6 entries

| subcmd | handler fn | (called with `r0 = 0x200A05A8` = device-info descriptor obj) |
|---|---|---|
| 0x00 | (self) | — |
| 0x01 | 0x1BA80 | — |
| 0x02 | 0x2B3E4 | probably Identity Reply |
| 0x03 | 0x2B826 | firmware version |
| 0x04 | 0x2B8CE | serial# or boot version |
| 0x05 | 0x2B96A | wave-ROM list / device ID |

## 7. Parameter address model (PMB)

### 7.1 Resolver: fn 0x25DA — `ParamAddrToName`

Human-readable pretty-printer for any parameter address. Dispatches on `type` (0..9) via `TBB [pc, r1]` at 0x25E4.

The 32-bit address's top byte is a **domain tag** and gets normalized:
The resolver masks the address to keep only the lower 24 bits, then ORs in `0x41000000` (Roland's internal namespace tag).

### 7.2 Category tables in QSPI

Two **19-entry descriptor tables**. Each entry is 12 bytes `{name_ptr, base_addr, size}` (corrected from an earlier `{prev_ptr, ...}` guess by disassembling the resolver at fn `0x25da`: it loads `[entry+4]` as base, `[entry+8]` as size, and on a match loads `[entry+0]` as the name pointer passed to the debug formatter). The table data is embedded in `sdram1.bin` as static init content (same pattern as the WROM name table) — it does not need to be read live from QSPI.

| RAM address | purpose | file offset (sdram1.bin) |
|---|---|---|
| `0x61096148` | 32-byte descriptor header; 19 entries begin at `0x61096168` | header `0x96148`, entries `0x96168` |
| `0x6109622C` | sub-categories header; 11 valid entries begin at `0x61096240` | header `0x9622C`, entries `0x96240` |

The 0x20-byte header at `0x61096148` holds a CRC16 (`0x89DF` at +0x00), a count (`0x03` at +0x14), a QSPI sub-pointer (`0x6108C8A4` at +0x10), and a debug-string pointer (`0x612C6DD8` at +0x1C). Iterated linearly to find which region owns a requested address. Full decoded table in `analysis/pmb_tables.json`.

**Table 1 (primary, 19 entries):** bases step through the `0x41` namespace in groups of three — a `0x10000`-size region, a `0x3000`-size region, and a `0x8000`/`0x4000`-size sub-region. The `0x10000`/`0x3000` entries carry Roland internal debug names (`Wr(1)`, `Rd(1)`, `SIO#1`, `mxmon1`, `r1`, `mac0/1`, `r2`, `mxmon3`, `r3`, `SIO#5`, `n4`, `r7`); the `0x8000`/`0x4000` sub-region entries are unnamed (their name field points into a debug-print string region). Bases: `0x4146/44/4A`, `0x4156/54/5A`, `0x4166/64/6A`, `0x4176/74/7A`, `0x4186/84/8A`, `0x4196/94/9A`, plus a final `0x4124` region.

**Table 2 (sub-categories, 11 entries):** `0x1000`-stride regions at `0x41110000`–`0x41138000` (the "system block-set A" range), named `r7`, `Wr(0)`, `r0`, `fnc1`, `mxmon2`, `DRAMIO3`, `IO4`, `mxmon0`, `@mode2`, etc. Entries 11+ are padding.

The name strings live in a packed 8-byte (NUL-padded) table at runtime `0x612C6E5C` (file `0x2C6E5C`): `Wr(0) Rd(1) Wr(1) SIO#0 DPC0 IPG0 PRG0 DRAMIO0 mac0 fnc0 mxmon0 r0 x0 SIO#1 ...`. These are Roland's internal codenames, not user-facing parameter names.

### 7.3 Special address ranges seen in the resolver

```
0x00110000 — 0x00112000    block-set A
0x00125000                 block-set B  (mask 0xFFF000)
0x00011000, 0x00012000     per-part blocks
0x00013000, 0x00014000     per-part blocks
0x00112000                 overlay block
0x00200000                 domain boundary
```

### 7.4 Failure messages

- `"Program N/A  %-4s %08lXh"` — addr not in any table
- `"Ill Inst %-4s Idx%2d %08lXh"` — illegal instrument index

## 8. Parameter Edit path (14C UMDWRxPRMEdit)

Handled by shared-kernel fn at **`0x01120ED5`** (called via PLT thunk `0x7DDB6`).

Signature (deduced):
`PRMEdit_Apply` takes a parameter context pointer (RAM `0x2009D1B8`) and the UMDW word, and applies the parameter edit.

The full UMDW word is passed in; the actual parameter value is encoded in its data1/data2/data3 bytes.

### 8.1 RTE (Real-Time Error) reporter — fn 0x214A

When a parameter operation fails, this fn builds a UMDW word with:
- byte 0: `route=1, type=1` (system on PRM channel)
- byte 1: `0x0E` (RTE opcode)
- byte 2: `error_id` (0..4 — from the `cmp r1, #5` throttling check)
- byte 3: `param_addr >> 24` (top byte of failing address — domain tag)

Sends via UMDW pipe back to Core-0. After 5 RTE errors in a row, `str.w r1, [r2, #0x180]` writes to **`0xE000E188`** = NVIC ICPR (Interrupt Clear-Pending Register) — defensive throttle disables the source interrupt.

## 9. Wave-ROM (WROM) system

### 9.1 Directory structure

Two paired tables in QSPI:

- **Name table** at RAM `0x612BA22C` — 32 × 48-byte entries
- **Instance table** at RAM `0x612BA82C` — 24 × 8-byte entries

**WromNameEntry** (48 bytes per entry, at QSPI `0x612BA22C`):

| offset | size | field | description |
|---|---|---|---|
| +0x00 | 2 | csum | CRC16 |
| +0x02 | 2 | reserved | — |
| +0x04 | 4 | type_flags | 8=Roland, 12=KY019-legacy, 16=ITGR, 32=third-party |
| +0x08 | 4 | data_size | 16 or 32 (bytes of content) |
| +0x0c | 16 | name | type=8: ASCII brand/name; type=16 (ITGR): binary per-ROM index/version encoding |
| +0x1c | 16 | version | ASCII version/identifier string (NOT a hash) |
| +0x2c | 4 | qspi_addr | QSPI address of ROM data |

**WromInstance** (8 bytes per entry, at QSPI `0x612BA82C`):

| offset | size | field | description |
|---|---|---|---|
| +0x00 | 2 | lo | bank index low |
| +0x02 | 2 | hi | bank index high |
| +0x04 | 4 | addr | QSPI address of instance data |

### 9.2 The 30 catalogued ROM banks (from file offset 0x2BA250)

| # | type | brand/name | version/note | qspi_addr |
|---|---|---|---|---|
| 0 | 8 (Roland) | `RolandPCMX     ` | — | 0x612D5FC4 |
| 1 | 8 (Roland) | `RolandPCM-EX   ` | — | 0x612D5E28 |
| 2–17 | 16 (ITGR) | `ITGR7 WRom00v100` … `WRom15v100` | +0x1c is the ASCII version string `ITGR7 WRomNNv100` (WRom03 is the only `v101`); +0x0c is a binary per-ROM index/version encoding, not a hash | 0x612D5E04..0x612D604C |
| 18 | 32 (3rd) | `SB06 ROM17 008 ` | — | 0x612D5FB8 |
| 19 | 8 (Roland) | `RolandTEST ROM0 ` | `1.0001MAKE COM` | 0x612D600C |
| 20 | 8 (Roland) | `RolandKY022    ` | `1.0001VTW    ` | 0x612D5F3C |
| 21 | 8 (Roland) | `RolandVDN_BMC  ` | — | 0x612D5FA0 |
| 22–24 | 12 (KY019) | `ndKY019 EXP0010/0020/0030` | — | 0x612D5FA8..5FEC |
| 25–26 | 32 (3rd) | `SuperiorGrd CD00/MI00` | — | 0x612D5F44/5F90 |
| 27 | 8 (Roland) | `RolandRPG68    ` | — | 0x612D5FE4 |
| 28 | 8 (Roland) | `RolandVEXP_760EP` | — | 0x612D5FDC |
| 29 | 8 (Roland) | `RolandPCMEX SNAP` | — | 0x612D5F88 |

**KY019** was a predecessor product (JD-Xi family); the MC-101 firmware still carries slots to load KY019 expansion banks. **ITGR7** = Integra-7-derived ROM series. **SB06** = Roland internal ROM series. **SuperiorGrd** = Superior Grand piano sample bank. **V-EXP** = Virtual Expansion.

### 9.3 Validator loop — fn 0x76B20

**CheckWaveROM** (fn at `0x76B20`): Iterates 24 wave-ROM banks. For each bank, reads the instance directory at QSPI `0x612BA82C`, resolves the ROM ID from the instance address via `WROM_GetIdFromAddr` (fn `0x768A8`), and looks up the name entry at QSPI `0x612BA22C`. Valid banks (ID 0-31 with non-empty name) are counted and their IDs stored in a bank→ID map at RAM `0x200A7708`. Prints progress and a final valid-count summary.

### 9.4 QSPI indirect-read peripheral (used by validator)

**Register block base: `0x41100000`**

| offset | name | function |
|---|---|---|
| +0xE0 | ADDR | write address to read |
| +0xE4 | STAT | bit 31 = BUSY |
| +0xE8 | DATA | read 16 bits (auto-increments address) |

Manually unrolled 5× polling loop for performance.

### 9.5 Sample descriptor arrays (from fns 0x76C84 / 0x76C9A)

**WROM_GetSampleByIdx**: Returns a pointer to sample data at QSPI `0x61700000` + idx × 40 (40-byte stride). Caps at 1000 entries. An alternate variant caps at 500 (0x1F4) — likely a different category (user samples).

**QSPI `0x61700000` + `idx*40`** = per-sample descriptor. Up to 1000 samples per bank.

## 10. Boot / init sequence

### 10.1 Entry

**_reset** (at file offset 0x0020): Calls the local loader function, then calls a PLT thunk at `0x7D474` which jumps to the shared kernel main entry at `0x011004D7`. Never returns.

### 10.2 PIC section-init loader (0x0028)

**loader**: Reads a section table at file offset 0x54 (relative to the section table start). Each 16-byte entry contains: source address, destination address, destination end, and a function pointer. The function pointer is decoded as either a PIC offset (if bit 0 is set, subtracted from an anchor) or an absolute Thumb address. Each entry's function is called with (src, dst, dst_end) to copy/initialize a section. The loop continues until the cursor reaches the end marker.

### 10.3 Built-in copy functions

- **`0x62`** — Roland-LZS decompressor (see §11)
- **`0xB8`** — fast 16-byte-block memcpy (LDM/STM `{r3,r4,r5,r6}`)

Additional copy fns for boot live in QSPI at **`0x610000xx`** (see sample sections below).

### 10.4 Sample sections from the table

| src | dst | size | copy fn |
|---|---|---|---|
| `0x01138748` | `0x20080000` | 140 B | `0x61000098` (QSPI) |
| `0x011387D4` | `0x2008008C` | ~23 KB | `0x6100003C` (QSPI, LZS?) |
| `0x0113B04C` | `0xE0043000` | 56 B | `0x61000098` (into System Control!) |
| `0x61389B14` | `0x61400000` | 4 B | `0x61000098` |
| `0x61389B18` | `0x617FFFFC` | 4 B | `0x61000098` (poke QSPI-XIP end) |
| `0x0113B04C` | `0x20085BBC` | ~144 KB | `0x61000098` |

Sources span the shared kernel image and QSPI; destinations include RAM, a peripheral (System Control at 0xE0043000), and even QSPI-XIP config pokes.

## 11. Roland-LZS decompressor — fn 0x62

Reverse-engineered from the Thumb-2 code at file offset 0x62:

```
per token byte T:
  lit_len   = T & 7            (if 0, extended by next byte)
  copy_raw  = T >> 4           (if 0, extended by next byte)
  copy (lit_len - 1) literal bytes from src to dst
  if T & 8:  read dist byte,  copy (copy_raw + 2) bytes from dst-dist
  else:      write copy_raw zero bytes
```

**Note on `init.lzs` inside C0C:** per ConvertWithMoss's `MC707_FORMAT.md` §8, `init.lzs` uses **textbook Okumura LZSS with a 4096-byte ring buffer** (the classic 1989 Haruhiko Okumura algorithm), not the Roland-specific variant we analyzed from `sdram1.bin` §11. The earlier decoder failed because the LZSS stream starts at **file offset 0x20** (the first 32 bytes are a container header, not the stream), the ring buffer is pre-filled with **zeros** (not 0x20 spaces), and the match length is `(hi & 0x0F) + 3`. A working decoder is in `tools/init_lzs_decode.py`. **Decompression verified (2026-08-16):** 969,045 bytes → exactly **8,153,245 bytes** (matching ConvertWithMoss's documented size), header `0x007E` + `PRJ5`, TOC matches the documented layout byte-for-byte (`PRJa`@0x80/0x634090, `STPa`@0x634110/0x210, `SYSa`@0x634320/0x210, `USRa`@0x634530/0x191420, `LPPa`@0x7C5950/0x810, `LPDa`@0x7C6160/0x820, `USDa`@0x7C6980/0x10). Content confirmed as the factory INIT PROJECT: project name `"INIT PRJ"`, 64× `"InitTone"`, `"InitDrum"`, 0 user samples. Output written to `extracted/C0C/init_project.mpj`.

## 12. External SysEx (from community RE, corroborated)

### 12.1 Wire format

Standard Roland DT1/RQ1 over MIDI:

```
F0 41 10 00 00 00 <MODEL> 11 <A3 A2 A1 A0> <S3 S2 S1 S0> <CK> F7    ← RQ1 read
F0 41 10 00 00 00 <MODEL> 12 <A3 A2 A1 A0> <data...>       <CK> F7    ← DT1 write

MODEL:  MC-101 = 0x5E     MC-707 = 0x5D
CK:     128 - (sum_of_addr_and_data % 128)
```

All bytes after F0 are 7-bit clean. **Multi-byte values are nibble-packed**: a 4-byte value ships as 4 bytes each carrying 4 bits.

### 12.2 External address map (mcpoker.py, verified via dumps)

MC-101 clip-tone bases (16 clips per track × 0x20000 stride + 1 track sound):
```
Track 1: 0x30000000    Track 5: 0x31080000
Track 2: 0x30220000    Track 6: 0x312A0000
Track 3: 0x30440000    Track 7: 0x314C0000
Track 4: 0x30660000    Track 8: 0x316E0000
```

Per-tone offsets:
- `+0x0018` — coarse tune (16..112)
- `+0x2000/2100/2200/2300` — Partial 1..4 bases
- `+0x0020` from partial base — waveform-L index (0..16383, 4-byte nibble-packed)

### 12.3 How external SysEx maps to our internal RE

- Model ID **`0x5E`** ↔ internal hardware SKU **`KY022`** — same product.
- External address `0x30xxxxxx` → Core-0 translates → UMDW word with route-nibble 1 (PRM-Edit) → shared-kernel fn `0x01120ED5`.
- The `bic addr, #0xFF000000` / `orr #0x41000000` in the internal resolver strips the SysEx domain tag `0x30` and re-tags with `0x41` (Roland manufacturer namespace).
- Nibble packing explains the `ubfx r0, r4, #0x10, #8` / `ubfx r3, r4, #0x18, #8` bit-field extracts in every UMDW handler — the value arrives in 4-bit chunks and has to be reassembled.

### 12.4 Live verification on a connected MC-101 (2026-08-16)

`tools/pmb_probe.py` was run against a connected MC-101 (USB Generic / class-compliant mode, model ID `0x5E`). Read-only RQ1 only — no DT1 writes were sent. 45/120 probes responded across 5 domain tags. Full results in `analysis/pmb_probe_live.md`.

**Confirmed live:** all 8 track clip-tone bases (`0x30020000`–`0x316E0000`) and the 4 partial offsets (`+0x2000/2100/2200/2300`).

**New finding — the address top byte is a layer selector, not just a namespace tag.** Probing the same base under different top bytes returns different data layers:
- `0x30xxxxxx` → **tone name** layer (e.g. Track 1 clip 1 → `"INTRO"`, Track 2 clip 1 → `"INIT TONE"`)
- `0x20xxxxxx` → **clip / scene name** layer (e.g. Track 1 clip 1 → `"TriggerFnktn"`, Track 5 clip 1 → `"DROP A"`, `0x00200000` → `"BREAKDOWN"`)
- `0x10` / `0x40` → shorter alternate framings (29–32 B)

The community docs treat `0x30` as the only external space; live probing shows `0x20` exposes a parallel clip/scene-name layer at the same bases.

**Internal regions:** two RE-only internal addresses are externally reachable — `0x00110000` (System block-set A) and `0x00200000` (domain boundary), via tags `0x20`/`0x40`. The rest of the internal system/per-part regions (`0x00125000`, `0x00011000`–`0x00014000`, `0x00112000`) are **not** exposed externally — confirming they live behind Core-0's SysEx→UMDW translator as internal Core-1 regions.

**Full clip-grid scan:** `tools/clip_grid_scan.py` probed all 128 clip addresses (8 tracks × 16 clips) under both layers. The 0x20 layer exposes the **full clip/scene-name grid** over read-only SysEx — a new capability not in community tools. The device's project has 7 named sections (INTRO → DROP A → DROP B → DANCE HALL → OUTRO → RHYTHM A → RHYTHM B) on a stride-4 pattern across Tracks 1–2, with Track 8 mirroring Track 1. Tracks 5–7 are completely empty. The 0x30 layer returns tone names (11 clips with "INIT TONE", rest empty/spaces). Results in `analysis/pmb_probe_live.md` and `clip_grid.csv`.

**QSPI parameter-name tables:** probed internal QSPI/RAM addresses (octave-label table, PMB table bases, name string table) — all silent. The external SysEx translator only routes to PMB-table parameter blocks, not raw internal data arrays. The RAM note-name array at `0x200837C4` is fundamentally inaccessible (low byte `0xC4` has bit 7 set, invalid in 7-bit SysEx).

**Four-layer domain-tag model:** systematic probing under all four tags (0x10/0x20/0x30/0x40) with 64-byte reads reveals a clean 4-layer structure:
- `0x10` — **project name** layer: single block at `0x10000000`, returns `"TriggerFnktn_011"` (project name + version)
- `0x20` — **clip/scene name + clip data** layer: per-clip 8×16 grid (mapped above)
- `0x30` — **tone name + tone params** layer: per-clip (the documented external space)
- `0x40` — **project/system metadata** layer: same 60-byte block at every address (tempo, time signature, etc.)

The community tools (mcpoker, mc-programmer) only use `0x30`. The `0x20` and `0x10` layers are new discoveries enabling read-only project backup over SysEx.

**DT1 write verification:** `tools/dt1_write.py` confirmed that DT1 writes to the `0x20` (clip) and `0x10` (project) layers work — clip names and the project name can be renamed over SysEx. Writes are surgical (only the name field is overwritten; surrounding binary data is preserved). Name field sizes: clip = 12 bytes, project = 16 bytes (ASCII, space-padded). DT1 writes are not acknowledged by the device but are verifiable by RQ1 read-back after ~300ms. Combined with the read-only clip-grid scan, the MC-101's project structure can be **both read and written over SysEx** — enabling full project backup/restore without the `.mpj` file.

## 12a. Community landscape (convergent RE efforts)

Cross-referenced August 2026. Multiple independent projects work around the same firmware, each choosing to focus on external SysEx or backup-file editing instead of the encrypted App1_Main. **No public documentation exists for the encrypted payload's contents** across the community.

| Project | Author | Scope | Firmware crypto? |
|---|---|---|---|
| [`mc-programmer`](https://github.com/douglas-carmichael/mc-programmer) | douglas-carmichael | 389 named ZEN-Core params (auto-gen from Jupiter-X MIDI Impl), full sequencer, dump/restore, Python + Swift, ~112 tests | no — SysEx only |
| [`mcpoker`](https://github.com/Locriana/mcpoker) | Locriana | Experimental Python SysEx scanner; discovered clip-tone base addresses; nibble-packing docs | no |
| [`Roland-Structured-Storage`](https://github.com/DrKnackeratorStrikesAgain/Roland-Structured-Storage) | DrKnackerator | JS library for MC/SH-4d/Fantom project-file container format | no |
| [`Roland-ZenCore-file-format`](https://github.com/DrKnackerator/Roland-ZenCore-file-format) | DrKnackerator | Format docs across Zenology/MC/Jupiter-X/Fantom/Juno X | no |
| [`ConvertWithMoss`](https://github.com/git-moss/ConvertWithMoss) `MC707_FORMAT.md` | git-moss | Deep .mpj project format docs, tone/kit/sample records, LZSS decode of init.lzs | no |
| [`tr-format` / `tr-studio`](https://github.com/ajmwagar/cowbell) | ajmwagar | Rust: TR-6S / TR-8S user data (Script.xml-driven) | no |
| [`Awesome-MC-707`](https://github.com/ricardofeynman/Awesome-MC-707) | ricardofeynman | Community index of MC-707/101 tips & tools | n/a |

**Convergent independent finding**: @ajmwagar's [TR-6S Part 1](https://github.com/ajmwagar/blog/blob/master/content/post/tr6s-part1.md) (August 2026) reached identical conclusions on the TR-6S — same tar + `App1_Main` container format. He additionally identified:
- **BMC SoC** is the shared platform across MC-101/707/TR-8S/TR-6S/Fantom/Jupiter-X
- **STM32G0 panel** controller communicates via 115200-baud UART speaking MIDI byte streams
- **AIRA Compacts (T-8, J-6, E-4) use a different `E4E` SoC** — separate product family

**Community open request**: firmware v1.51 for TR-6S is being held back by Roland (they delete old versions on release). Same policy affects MC-101 — only latest firmware is publicly downloadable.

## 13. What we contributed beyond the existing community RE

| Finding | Community had? |
|---|---|
| Model ID 0x5E, DT1/RQ1 wire format, nibble packing | ✔ |
| Clip-tone base addresses 0x30xxxxxx | ✔ (partial) |
| Per-partial parameter offsets | ✔ (dozens) |
| **19-category PMB tables at 0x61096148 / 0x6109622C** | ✘ new |
| **Full UMDW inter-core protocol (16 types + sub-op set)** | ✘ new |
| **Factory Test-Mode dispatch (17 subcmds under UMDW 0x60)** | ✘ new — long-open community question |
| **Model/Device query dispatch (6 subcmds under UMDW 0x48)** | ✘ new |
| **Wave-ROM directory + 30 catalogued banks** | ✘ new |
| **Roland-LZS decompressor algorithm** | ✘ new |
| **`RolandVEXP_760EP`, `SuperiorGrd`, `SB06 ROM17 008` in ROM table** | ✘ new |
| **PLT thunk table → shared kernel at 0x01100000+** | ✘ new |
| **Address-space & memory map** | ✘ new |
| **Boot/init loader mechanics + section table format** | ✘ new |

## 14. Files on disk

```
mc101-firmware-re/
├── analysis/          static-analysis outputs (our work, not Roland binaries)
│   ├── functions.json     discovered functions (prologue + leaf + thunk)
│   ├── string_xrefs.json  per-string owner-function map
│   ├── callgraph.json     BL-target indices
│   └── pmb_tables.json    decoded PMB parameter-region tables
├── tools/             SysEx probes and analysis scripts
└── REPORT.md          this document
```

## 15. Practical next steps

1. **Live-verify PMB tables** — point `mcpoker.py`'s `dump()` scan at each of the 19 category-table regions we identified. Should give instant confirmation of the parameter map.
2. **Test-mode trigger hunt** — send DT1 writes to plausibly-magic addresses and watch UMDW for route=1/subop=0x60 signatures. If any address triggers Test Mode Request, users unlock factory diagnostics for the first time.
3. **Publish** — the Roland Clan Forum "documenting roland file formats" thread is the natural venue.

## 16. Session tooling notes

- Disassembler: Capstone (Python) with `CS_ARCH_ARM | CS_MODE_THUMB`
- Function discovery: prologue-scan for `push {..., lr}` (Thumb-1: `xx B5`) and Thumb-2 `stmdb sp!, {..., lr}` (`2D E9 xx xx` with bit 14 set in reglist)
- String xref resolution: recursive-descent from each prologue, tracking ADR (PC-relative) and LDR-lit (pool loads) — pure u32 pool scan misses ~90% of refs because most strings are non-4-aligned and addressed via ADR
- TBB (Table Branch Byte): pattern `DF E8 0m F0` — table starts at PC+4, entries are 1-byte offsets (×2 for real branch delta)
- PLT thunk detection: `movw ip, #lo` / `movt ip, #hi` / `bx ip` triplet

Total session tool calls: ~30 Bash/disasm runs. Total artifacts written: this file plus 4 JSON indices.
