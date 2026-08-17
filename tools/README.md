# Tools

## `pmb_probe.py` — Live PMB verification

Probes each candidate parameter address region we analyzed from `sdram1.bin` and
records which ones respond to a Roland SysEx RQ1 request.

### Setup
```
pip install python-rtmidi
```

### Use
```
# See MIDI ports
./pmb_probe.py --list

# Native-tag probe (fast, targeted)
./pmb_probe.py --port "MC-101"

# Wide scan (5 domain tags × all regions)
./pmb_probe.py --port "MC-101" --scan-all --out pmb_probe.csv

# For MC-707
./pmb_probe.py --port "MC-707" --model mc707
```

The tool sends one RQ1 per candidate and waits 250 ms for a DT1 reply. An
active region echoes a checksum-valid DT1 with data bytes; an inactive one is
silent. Response length reveals the region's size envelope.

### What it verifies

- The 8 track base addresses `0x30000000..0x316E0000` (community-known)
- The partial offsets `+0x2000/2100/2200/2300` per tone
- The RE-only regions from `fn 0x25da`:
  - System block-set A: `0x00110000..0x00112000`
  - System block-set B: `0x00125000` (mask `0xFFF000`)
  - Per-part blocks: `0x00011000/12000/13000/14000`
  - Overlay: `0x00112000`
  - Domain boundary: `0x00200000`

With `--scan-all`, each region is also probed with domain tags `0x00/10/20/30/40`
in case Core-0 uses a different top-byte in its SysEx→UMDW translation than we assumed.

### Caution

Sending RQ1s is read-only and safe. This tool does **not** write anything
to the device — no DT1 messages are ever transmitted.
