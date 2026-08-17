# Inside the Roland MC-101: What's in the Zen-Core Groovebox

## The question

The Roland MC-101 is a 4-track Zen-Core groovebox — same sound engine as the MC-707, in a smaller box. It runs firmware v1.82 (build 14423, May 2023). The firmware update file is a tar archive containing four binaries: an encrypted main app, PCM banks, DSP code, and preset data.

The question was simple: **what's actually in there, and what can we do with it?**

Roland's MIDI Implementation Chart says the MC-101 "does not respond to SysEx requests." The community suspected this was false. We wanted to know what's hidden, what's locked, and what's possible without Roland's permission.

## State of the art (before this work)

Several community projects had already mapped parts of the Zen-Core ecosystem:

- **[mcpoker](https://github.com/Locriana/mcpoker)** (Locriana) — an experimental Python SysEx scanner that discovered the clip-tone base addresses (`0x30xxxxxx`) and documented the 7-bit nibble packing used in Roland's wire format. This was the starting point for external SysEx addressing.

- **[mc-programmer](https://github.com/douglas-carmichael/mc-programmer)** (douglas-carmichael) — a Python + Swift library with 389 named Zen-Core parameters (auto-generated from the Jupiter-X MIDI Implementation document), full sequencer support, dump/restore, and 112 passing tests. The most complete SysEx client library for the platform.

- **[ConvertWithMoss](https://github.com/git-moss/ConvertWithMoss)** (git-moss) — deep documentation of the `.mpj` project file format, including tone/kit/sample records and the LZSS compression used in `init.lzs`. Their `MC707_FORMAT.md` is the authoritative reference for the project container format.

- **[@ajmwagar's TR-6S work](https://github.com/ajmwagar/blog/blob/master/content/post/tr6s-part1.md)** (August 2026) — independently reached identical structural findings on the TR-6S: same tar + `App1_Main` container format, same BMC SoC platform. His work on the BMC SoC family directly complements this MC-101 research.

- **Benedetto Schiavone's ZEN-Core editor** (September 2024) — a commercial Mac/Windows editor that proved the hidden SysEx space is usable, using "MIDI SysEx support that Roland included in the grooveboxes but never documented." The community knew hidden SysEx existed but hadn't mapped it.

What nobody had done: look inside the firmware itself. All community work operated above the encryption boundary — reading/writing parameters via SysEx, parsing project files, documenting the wire format. Nobody had decoded the internal architecture: the dual-core protocol, the parameter address model, the factory test mode, or the encryption scheme.

## What we found

### The firmware is a tar archive with one encrypted file

`MC101_UPA_up.bin` is a GNU tar containing four component updates:
- `C0A` (3.5 MB) — main CPU application, **encrypted** (key not shipped in updates)
- `C0C` (8 MB) — PCM tone banks + factory init project (plaintext)
- `C1A` (4 MB) — DSP code for the second core (plaintext)
- `C1C` (4 MB) — preset metadata + metronome (plaintext)

The encrypted `C0A` (internally called `App1_Main`) contains the UI, the SysEx parser, the sequencer, and the code that decides what external commands reach the internal dispatch. Everything interesting about the user experience lives behind this encryption wall.

### MC-101 and MC-707 share almost everything

Cross-product comparison between MC-101 v1.82 and MC-707 v1.82 (same-day build train, ~1 hour apart) confirmed that all 26 non-code data blobs (PCM banks, presets, init.lzs, wromInfo) are **byte-identical** between the two products. The DSP code (`sdram1.bin`) is the same source recompiled with shifted link addresses. Only `App1_Main` (the encrypted UI layer) meaningfully differs — MC-707 has 8 tracks vs MC-101's 4, more encoders, motor faders.

### The dual-core UMDW inter-core protocol

The BMC SoC has two ARM cores: Core 0 (UI, MIDI, SysEx, parameter engine) and Core 1 (DSP, voice engine). They communicate via a custom protocol we call UMDW (inter-core message words). We decoded 16 message types with subop dispatch tables, including:

- **Subop 0x60: Test Mode Request** — 17 factory test subcommands, including the main test-mode entry at fn 0x75A34. This is Roland's internal factory diagnostic suite. The dispatch table is fully decoded; the external trigger lives in encrypted C0A.
- **Subop 0x48: Model/Device query** — 6 subcommands for identity, firmware version, serial number, wave ROM list.
- **Subop 0x11: Parameter Edit** — the path that external SysEx RQ1/DT1 commands take through the system.

This is the first public documentation of the BMC inter-core protocol. Nobody in the community had identified it before.

### The parameter address model (PMB)

Disassembled the parameter name resolver (fn 0x25da) and decoded two descriptor tables embedded in `sdram1.bin`:
- **Table 1**: 19 parameter regions with Roland's internal debug names (Wr(1), Rd(1), SIO#1, mxmon1, mac0/1, DRAMIO3, etc.)
- **Table 2**: 11 sub-category regions at 0x41110000–0x41138000

The resolver strips the external address top byte and re-tags with 0x41 (Roland's internal namespace), then walks the table to find the matching region. This is the map of every parameter region in the device.

### The factory init project, decoded

`init.lzs` uses textbook Okumura LZSS (4096-byte ring buffer, zero-prefilled, match length `(hi & 0x0F) + 3`, stream at offset 0x20). Per ConvertWithMoss's `MC707_FORMAT.md` §8 — the authoritative spec. Decoded to exactly 8,153,245 bytes: the factory INIT PROJECT with 64 InitTone presets, one InitDrum, and zero user samples.

### The four-layer SysEx address model (live-verified)

Connected an MC-101 via USB MIDI and probed it with read-only RQ1 SysEx. Discovered the external address top byte is a **layer selector**, not just a namespace tag:

| Tag | Layer | Returns |
|-----|-------|---------|
| `0x10` | Project name | `"TriggerFnktn_011"` — the project/pattern name |
| `0x20` | Clip/scene names | Full 8×16 clip grid (INTRO, DROP A, DROP B, DANCE HALL, OUTRO, RHYTHM A/B) |
| `0x30` | Tone names + params | Per-clip tone name + partial data (the only layer community tools use) |
| `0x40` | System metadata | Project-level info (tempo, time signature), same at every address |

The community (mcpoker, mc-programmer, the 2024 ZEN-Core editor) only knew about `0x30`. The `0x20` and `0x10` layers are new — they enable **reading the full project structure over read-only SysEx**.

### DT1 writes work — project backup/restore over SysEx

Proved that DT1 (Data Set 1) writes to the `0x20` and `0x10` layers work. Renamed a clip ("INTRO" → "DROIDTEST") and the project ("TriggerFnktn_011" → "DROIDTEST_01") over SysEx, verified by RQ1 read-back. Writes are surgical — only the name field is overwritten, surrounding binary data is preserved. Name field sizes: clip = 12 bytes, project = 16 bytes.

Combined with the read-only clip-grid scan, this means **full project backup/restore over a USB cable** — no proprietary software, no `.mpj` file needed.

### Built-in ducking, but no true sidechain

Audited the firmware for sidechain compression. Found `TRK1 Duck SW` through `TRK8 Duck SW` — per-track ducking switches in the mixer routing block. But no adjustable parameters (depth, threshold, attack, release, source). The compressor MFX has standard params but no sidechain-key input. The mod matrix has no external audio envelope source.

The MC-101 has a basic built-in ducking feature and supports LFO-based ducking (a community-known technique), but not a true sidechain compressor. For that, use a DAW.

## What's still locked

The encrypted `App1_Main` (C0A) gates everything that modifies the on-device experience:
- The SysEx→UMDW translator (which external commands reach the internal dispatch)
- The test-mode external trigger (does any SysEx command generate subop 0x60?)
- The UI code, sequencer, preset browser
- The boot pipeline, signature verification, update mechanism

The encryption key is not present in any firmware update file. No public method exists to access the encrypted payload across the community.

## Tools

All tools and analysis are in the [repository](https://github.com/soobrosa/mc101-firmware-re):
- `pmb_probe.py` — live PMB region verifier (read-only RQ1)
- `clip_grid_scan.py` — map 8×16 clip grid via SysEx
- `dt1_write.py` — send DT1 writes with RQ1 verify
- `init_lzs_decode.py` — Okumura LZSS decoder for init.lzs
- `discover_functions.py` — ARM Thumb-2 function finder

## Credits

This work builds on and would not have been possible without:
- **Locriana** ([mcpoker](https://github.com/Locriana/mcpoker)) — clip-tone base addresses, nibble packing docs
- **douglas-carmichael** ([mc-programmer](https://github.com/douglas-carmichael/mc-programmer)) — 389 named parameters, SysEx library
- **git-moss** ([ConvertWithMoss](https://github.com/git-moss/ConvertWithMoss)) — `.mpj` format docs, LZSS spec
- **@ajmwagar** ([cowbell](https://github.com/ajmwagar/cowbell), [TR-6S blog](https://github.com/ajmwagar/blog/blob/master/content/post/tr6s-part1.md)) — convergent BMC SoC family analysis, platform identification
- **Benedetto Schiavone** — proving the hidden SysEx space is usable (2024 ZEN-Core editor)
- The **Roland Clan** and **Gearspace** communities — years of questions that framed the problems
