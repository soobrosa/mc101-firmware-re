# Contribution Plan — PRs to Community Repos

Based on our analysis findings (4-layer SysEx model, clip-grid scan, DT1 write proof,
PMB parameter tables, Duck SW discovery, UMDW protocol).

---

## Repo assessment

### 1. mc-programmer (douglas-carmichael) — Best PR candidate

**Repo:** https://github.com/douglas-carmichael/mc-programmer
Python + Swift, MIT, 389 named params, 112 tests, actively maintained (last
commit April 2026). Two contributors: douglas-carmichael and Locriana (mcpoker
author).

**Their stated gaps (from README):**

> "Pending — drum kit tone parameters, scene-level 'Part' parameters, per-MFX-type
> parameter labels, Looper / Sample-Edit metadata. All addressable in principle but
> need either an MC-specific reference or hardware exploration via hack_tools.py to
> find the SysEx addresses."

**What we can contribute:**

- **The 0x20 clip/scene-name layer** — directly fills their "scene-level parameters"
  gap. We proved the full 8×16 clip grid is readable/writable over SysEx at
  `0x20xxxxxx`. They have scene/clip *selection* via Program Change but not clip
  *naming*.
- **The 0x10 project-name layer** — they have project save/restore but not project
  *renaming* over SysEx.
- **The Duck SW parameters** (TRK1-8 Duck SW) — 8 new system-level mixer parameters
  they don't have.
- **The PMB parameter tables** (`analysis/pmb_tables.json`) — cross-verification of
  their 389 params against our analyzed 19-category + 11-subcategory tables from the
  firmware.
- **The 4-layer address model** — their address map only covers `0x30`. Adding
  `0x10`/`0x20`/`0x40` would make the library complete.

**PR shape:** Add clip-name and project-name read/write to both the Python and Swift
libraries, using the verified addresses and field sizes (clip=12 bytes, project=16
bytes). Add the Duck SW parameters to the system block. Add the 4-layer model to the
docs.

**Effort:** Medium (code in Python + Swift)

---

### 2. mctools_basic (Locriana) — Strong PR candidate

**Repo:** https://github.com/Locriana/mctools_basic
4 stars, 3 commits, MIT, Python. 4 files: `hack_tools.py`, `midi_if.py`,
`sys_ex_comm.py`, `zen_core_tools.py`. Last commit June 2026. This is the active
follow-up to mcpoker.

**What they already have:**

- `zen_core_tools.py` — hardcodes the 8 track base addresses
  (`0x30000000`–`0x316E0000`) and clip stride (`0x20000`). Only works with the `0x30`
  tone layer. Has a `coarse_tune_rmw` (read-modify-write) function — so they already
  do DT1 writes.
- `hack_tools.py` — has a `dump_settings` function that dumps from `0x00000000`–
  `0x00000030` AND `0x10000000`–`0x10001000`. **Locriana already knows about the
  `0x10` address space** — they're dumping it. But the dump is raw bytes with no
  interpretation of what's there.
- `sys_ex_comm.py` — full RQ1/DT1 implementation with checksum, model ID detection,
  nibble packing. Also has `trk_col_addr` addresses (`0x10000819` etc.) — they've
  found track color parameters in the `0x10` space.
- The `dump` function skips addresses where `address & 0x80808080 != 0` — they know
  about the 7-bit-clean constraint.

**What they're missing (our findings):**

1. **The 4-layer model** — they dump `0x10` raw but don't know it's the "project name"
   layer, or that `0x20` is clip/scene names, `0x40` is system metadata. They have the
   data but not the interpretation.
2. **The 0x20 clip/scene-name layer** — they only work with `0x30` (tone). The `0x20`
   layer (clip names, 8×16 grid) is completely absent from their code.
3. **Name field sizes** — clip name = 12 bytes, project name = 16 bytes. They dump
   raw but don't know the field boundaries.
4. **The Duck SW parameters** — 8 per-track ducking switches in the system block.
5. **The PMB parameter tables** — 19+11 region descriptors with Roland's internal
   debug names.

**PR shape:** Two options:

- **Documentation PR** — add the 4-layer model, field sizes, and the clip-grid scan
  results to the README. Low effort, high value.
- **Code PR** — add a `clip_name_read`/`clip_name_write` function to
  `zen_core_tools.py` using the `0x20` layer, and a `project_name_read`/
  `project_name_write` using `0x10`. Medium effort, directly useful.

**Effort:** Low–medium

---

### 3. cowbell (ajmwagar) — Good for a docs PR

**Repo:** https://github.com/ajmwagar/cowbell
Rust, MIT, 2 stars, 3 commits. Early-stage TR-6S RE with fw-analyze/fw-extract
CLIs. Has `docs/architecture-questions.md` (open questions log).

**What we can contribute:**

- **UMDW protocol** — their `docs/architecture-questions.md` asks about the
  inter-core architecture. Our decoded UMDW protocol (16 message types, test-mode
  dispatch) directly answers this for the BMC SoC family.
- **PMB parameter model** — the 19+11 region tables map every parameter region in
  the BMC SoC.

**PR shape:** Add a `docs/bmc-family-findings.md` documenting the UMDW protocol
summary and the PMB parameter model, cross-referencing our REPORT. Or contribute
to their existing `docs/architecture-questions.md`.

**Caveat:** This is a TR-6S project, not MC-101. The findings transfer (same BMC
SoC) but the PR should frame the contribution as "convergent BMC family findings"
rather than MC-101-specific.

**Effort:** Low (docs only)

---

### 4. mcpoker (Locriana) — Skip

**Repo:** https://github.com/Locriana/mcpoker
11 stars, 8 commits, Unlicense, single Python file. Experimental POC.

The README says "Please see the updated version in my follow-up project:
mctools_basic." The author considers this repo superseded. PR against
mctools_basic instead.

---

### 5. ConvertWithMoss (git-moss) — Weakest fit

**Repo:** https://github.com/git-moss/ConvertWithMoss
Java, LGPL-3.0, 423 stars, 659 commits, very active (last commit 17 hours ago).
A multisample format converter. They have `MC707_FORMAT.md` which documents the
`.mpj` project file format.

**What we can contribute:**

- Our `init.lzs` decode verified byte-exact against their `MC707_FORMAT.md` spec. We
  could add a note confirming the spec is correct.
- The 4-layer SysEx model is about live device communication, not file format
  conversion. Not directly relevant to their use case.
- If they ever add SysEx-based project transfer (currently they only do file-based
  conversion), the 4-layer model would be useful.

**PR shape:** Probably not worth a PR. The projects operate in different domains
(file format conversion vs. live SysEx). At most, a documentation note in their
`MC707_FORMAT.md` confirming the init.lzs spec is verified.

**Effort:** Low but low value

---

## Summary table

| Repo | Fit | What to PR | Effort |
|------|-----|-----------|--------|
| **mc-programmer** | **Strong** | 0x10/0x20 layer read/write, Duck SW params, PMB cross-verification | Medium (Python + Swift) |
| **mctools_basic** | **Strong** | 4-layer model docs + clip/project name read/write functions | Low–medium |
| **cowbell** | Good | UMDW protocol, PMB parameter model, BMC architecture docs | Low (docs only) |
| **mcpoker** | Skip | — | Archived, PR to mctools_basic instead |
| **ConvertWithMoss** | Weak | init.lzs verification note | Low but low value |

---

## Recommended order

1. **mctools_basic** — Locriana already has the `0x10` data but doesn't know what it
   is. A PR that adds the 4-layer interpretation + clip-name read/write to their
   existing code would be immediately useful and is a natural extension of what they
   already built. It's also a good relationship to build — Locriana is a contributor
   to both mcpoker and mc-programmer, so a good PR here could flow into mc-programmer
   too.

2. **mc-programmer** — our findings directly fill their stated gaps (scene-level
   parameters, clip naming). Most impactful but most work (code in both Python and
   Swift). Do this after the mctools_basic PR establishes the relationship.

3. **cowbell** — just docs (UMDW protocol + PMB model), and @ajmwagar is actively
   working on the same BMC family so the findings are immediately useful. Low effort,
   good community signal.

4. **ConvertWithMoss** — only if there's a natural opportunity. Not worth forcing.
