# Feasibility — concrete goals, real distances

Practical answers to "how close are we to X?" for specific modding goals.
References: `REPORT.md` (analysis findings), `TODO.md` (open work).

---

## Q: How would older MC-101 firmware help us?

**Bottom line:** useful for cross-version diffing of the unencrypted components. The encrypted App1_Main remains inaccessible regardless of version.

### High-value uses

1. **Cross-version diff of unencrypted components.** `sdram1.bin` (DSP code), PCM banks, and preset data are all unencrypted. Diffing older vs newer versions highlights what changed between firmware updates — useful for understanding feature additions.

2. **Cross-product diff — confirmed (this session).** MC-101 v1.82 and MC-707 v1.82 share all 26 non-code data blobs (PCM banks, presets, init.lzs, wromInfo) byte-identical. `sdram1.bin` DSP code is the same source recompiled with shifted link addresses. Only `App1_Main` (encrypted UI) meaningfully differs.

3. **Feature bisection.** If scale-modes appeared in v1.6, diffing v1.5 vs v1.6 highlights the new region of code in the unencrypted components.

4. **Init/factory data changes.** `init.lzs` (Okumura LZSS, 4 KB ring buffer) may have been simpler in earlier versions.

### Low / no value

- **Rollback recovery for a bricked device** — yes but you'd only need it *if* you were already flashing custom firmware, which isn't possible without hardware access.
- **Accessing the encrypted App1_Main** — no. The encryption scheme is consistent across all known versions.

### What to actually chase

Roland deletes old firmware from their download server when they release new versions. Options for obtaining older MC-101 firmware:
- Support ticket to Roland ("I want to downgrade before upgrading to v1.82; please send v1.7x")
- Community backups on Roland Clan Forums (forum ID 69), Gearspace, Reddit r/rolandmc101
- @ajmwagar has an open Roland support ticket for TR-6S v1.51 — same tactic applies
- **Alternative that's already actionable:** grab MC-707 v1.82 (Roland's current download) and diff against our MC-101 v1.82 — same-era cross-product test with zero additional acquisition effort.

---

## Q: Change the UI on accessing presets — how far are we?

**Two paths — one impossible today, one 100% doable today.**

### Path 1: Modify the on-device UI (blocked)

The preset-picker screen, encoder handling, and list display all live in **App1_Main** (encrypted C0A). The encryption key is not present in any firmware update file — it lives in the BMC SoC's internal boot ROM, which is not shipped in updates. No public method exists to access this key across the community.

**Realistic estimate:** blocked without hardware access to the BMC SoC.

### Path 2: External UI via SysEx (available today)

Point the MC-101 at a laptop / iPad app that shows *your* UI and reads/writes preset data over USB MIDI:

| # | Step | Status |
|---|---|---|
| 1 | SysEx wire format | ✓ known (`REPORT.md` §12, cross-verified via mcpoker) |
| 2 | Preset addressing | ✓ known: `0x30000000` + track/clip offsets |
| 3 | Client library | ✓ [`douglas-carmichael/mc-programmer`](https://github.com/douglas-carmichael/mc-programmer) — Python + Swift, 389 named parameters, 112 passing tests |
| 4 | Read a preset (RQ1 → parse DT1, unpack nibbles) | ✓ done in library |
| 5 | Write a preset (DT1 with checksum) | ✓ done in library |
| 6 | Your custom UI | needs writing — normal app work |

**Realistic estimate:** a weekend to a week for a full custom preset browser, depending on how polished you want the UI. Zero firmware modding required.

### Limitation of Path 2

The MC-101's own screen still shows Roland's UI. Your custom UI is on the laptop / iPad, not on-device. You *can* trigger scene / clip switches from your app so the device follows along, but the built-in display can't be replaced without modifying App1_Main.

### Recommended approach

Start with Path 2 today. It solves 80% of "I want a better preset browser" without a single byte of firmware modding. Path 1 is blocked without hardware access to the BMC SoC.

---

## Q: Sidechain — how far are we?

Depends on which flavor of sidechain you mean.

### Option A: LFO-based ducking (available today, no work needed)

Use an LFO synced to the kick track, targeting master or bus level. This is a common MC-101 technique — search "MC-101 sidechain trick" for tutorials. Not true sidechain, but sounds close for pumping / EDM effects. Documented workflow, zero work.

### Option B: Native sidechain compressor in the existing effect chain

**Audited (2026-08-16).** Grepped all effect banks (`spf_muse_*`, `wpf_muse_*` in
`extracted/C1C/`) and the full `sdram1.bin` string table for sidechain-related terms.

**Result: the MC-101 has a built-in per-track ducking system, but not a full sidechain compressor.**

Found in `analysis/strings.txt`:

```
TRK1 Duck SW    (0x002ce644)
TRK2 Duck SW    (0x002ce654)
...
TRK8 Duck SW    (0x002ce6b4)
```

These are per-track "Duck Switch" parameters — one per track, sitting in a block of
mixer routing switches alongside "Cue SW" and "Asgn SW". When enabled, a track's
level ducks (reduces) under another signal — the classic sidechain pumping effect.

**However:**
- No "Duck Depth", "Duck Threshold", "Duck Attack", "Duck Release", or "Duck Source"
  parameter strings were found. The ducking appears to be a simple on/off switch with
  fixed parameters (likely tied to the rhythm/kick pattern), not a full sidechain
  compressor with adjustable threshold/ratio/attack/release.
- No "Sidechain", "Key Input", "External Key", or "Detector Source" parameter strings
  exist in the firmware.
- The compressor MFX (`11CFspMfxCOMP`) has standard parameters (Threshold, Ratio,
  Attack, Release, Knee, Output Gain) but no sidechain-key input.
- The mod matrix (MCTL1-4, each with 4 destinations) has no "external audio envelope"
  source type.

**Community confirmation:** Reddit (Feb 2022) — "I couldn't find a way to do any real
Side Chain Compression even though it's possible to automate a pumping effect."
Elektronauts (Mar 2022) — "It's more of a volume duck than a mute."

**Conclusion:** The MC-101 has a basic built-in ducking feature (per-track on/off switch),
but NOT a true sidechain compressor with a key-input source. The ducking is likely
sufficient for EDM pumping effects but lacks the parameter control needed for
transparent sidechain compression. For that, use Option A (LFO ducking) or Option D
(computer-based sidechain).

**Follow-up:** the Duck SW parameters could be probed live via SysEx to find their
addresses and test toggling them. They are system-level mixer parameters, likely in
the 0x00110000 system block-set range (confirmed externally reachable via tag 0x20/0x40).

### Option C: Add sidechain by modifying the DSP effect graph

Means adding a new DSP module (or modifying an existing compressor) in `sdram1.bin`. We *can* modify sdram1.bin (it's unencrypted), but the boot loading pipeline is gated by the encrypted App1_Main (C0A). Even with perfect DSP code, we can't get a modified image verified and loaded because the boot pipeline is gated by C0A.

**Realistic estimate:** not viable in current state.

### Option D: External sidechain via computer

Route MC-101 audio out to a computer, apply sidechain there, route back. Live production workflow, not a device mod. **100% available today** with any DAW.

---

## Summary matrix

| Goal | Distance | Path |
|---|---|---|
| Older firmware for cross-version diff | useful for unencrypted components | grab MC-707 v1.82 for cross-product diff; open Roland ticket for older MC-101 fw |
| On-device preset UI change | blocked | encrypted App1_Main, key not in updates |
| **Custom preset UI on laptop / iPad** | **days of app work** | `mc-programmer` + your UI framework of choice |
| LFO ducking / fake sidechain | today | existing device feature |
| True in-device sidechain | blocked | same encrypted App1_Main wall |
| Sidechain in your production | today | any DAW |

The consistent story: **anything that modifies the device firmware is blocked** (encrypted App1_Main, key not in updates), while anything treating the MC-101 as a black-box MIDI slave is fully achievable now with mcpoker / mc-programmer as starting points.

---

## Immediate next actions (if you want to actually build any of this)

1. **Custom preset UI**: clone `douglas-carmichael/mc-programmer`, plug it into a small SwiftUI (Mac / iPad) or web (React / htmx) frontend. First MVP: list, load, save, favourite, group. ~1 weekend.
2. ~~**Cross-product diff**~~ — **DONE this session** (see above).
3. **Native sidechain audit**: `strings extracted/C1C/spf_muse_cmn.bin | grep -i "side\|key\|ext"` — five minutes to confirm presence/absence.
4. **Firmware acquisition**: file a Roland support ticket for MC-101 v1.7x, framed as "want a backup before upgrading."
5. **MC-707 cross-product opportunity**: MC-101 and MC-707 share App1_Main code family. Any analysis progress on the MC-707 UI would translate directly to MC-101.
