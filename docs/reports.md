# Diagnostic reports (`d20-tools report`)

The five reports are read-only decoders for a D-20 Standard MIDI (`.mid` or
`.midi`), raw SysEx (`.syx`), native Sound (`.333`), or native Rhythm (`.444`)
file. They validate every Roland D-20 DT1 frame and checksum before decoding;
native files are validated directly before their data is decoded. They print
to the terminal and never create, change, or transmit a file.

The command structure is intentionally nested:

```text
d20-tools report REPORT INPUT [REPORT-OPTION]
```

`REPORT` is one of the following.

| Command | Input and optional parameter | Terminal output |
| --- | --- | --- |
| `report system INPUT` | No extra option. Requires complete 50-byte area `10H`. | Master tune, global reverb, part reserves/levels/pans, and stored MIDI channels. |
| `report patch INPUT` | `--patch 1..128` is optional; `--showtones` may follow a selected Patch. Requires area `07H`; the selected record must be complete. | Without `--patch`, a populated-patch index. With it, layout, split, both tone assignments, tuning, bender, assign and reverb values. `--showtones` appends both assigned editable Tone configurations. |
| `report timbre INPUT` | `--timbre A-11..A-88` or `--timbre B-11..B-88` is optional; `--showtones` may follow a selected Timbre. Requires area `05H`. | Without `--timbre`, a 128-Timbre index. With it, the complete tone assignment and performance values for that Timbre. `--showtones` appends its assigned editable Tone configuration. |
| `report tone INPUT` | `--tone i01..i64` is optional. Uses permanent `08H`, falling back to temporary `04H`. | Without `--tone`, complete internal/user Tone names. With it, structure, partial activity, wave generator, LFO, TVF and TVA values. |
| `report rhythm INPUT` | No extra option. Requires complete 340-byte area `09H`. | Assigned Rhythm Setup keys (C1–C8), tone, level, pan and reverb. |

Examples:

```sh
d20-tools report system D20BACKUP.mid
d20-tools report patch D20BACKUP.mid --patch 1
d20-tools report patch D20BACKUP.mid --patch 1 --showtones
d20-tools report timbre D20BACKUP.syx --timbre A-26
d20-tools report timbre D20BACKUP.syx --timbre A-26 --showtones
d20-tools report tone D20BACKUP.mid --tone i12
d20-tools report rhythm D20BACKUP.mid
d20-tools report tone MY_SOUNDS.333 --tone i12
d20-tools report rhythm MY_RHYTHMS.444
```

The option follows the input filename. This avoids ambiguity and makes it easy
to paste the command shown by `d20-tools report REPORT --help`.

A `.333` contains Sound/Timbre/Patch/Tone data, so it can be used directly
with `report tone`, `report timbre`, and `report patch` (including
`--showtones`). A `.444` contains Rhythm data, so it can be used directly with
`report rhythm`. A report that asks a file for data it cannot contain gives a
clear "no data" error rather than converting it first.

The Timbre area contains two 64-location **A** and **B** panel banks, each
numbered `11` through `88`. `I` (internal) and `C` (memory card) are a
separate storage-mode choice on the instrument; they are not Timbre-bank
labels, so they are deliberately not accepted as report identifiers.

`--showtones` requires a selected `--patch` or `--timbre`. It embeds the same
detail that `report tone --tone i01` would show for an assigned internal/user
Tone. Preset A/B and Rhythm Tones are fixed content, so their synthesis
settings are not carried in a dump; the report identifies them rather than
inventing a configuration.

## Tone inspection scope

The Tone report exposes only editable internal/user Tones: `i01` through
`i64`, held in permanent area `08H` (or temporary working area `04H` when a
dump has no permanent Tone area). It does **not** decode Preset A or Preset B
Tones. Those are fixed D-20 ROM elements rather than user data in a DT1 dump.
They may appear by name in Patch, Timbre, or Rhythm reports when an editable
record refers to one.

When a Tone partial uses PCM (`P`), its Wave line includes the PCM name from
the D-20 two-bank reference. It uses the manual's one-based Bank and Wave
numbers, rather than exposing the zero-based values stored in the dump. For
example: `Tambourine (PCM Bank 1, Wave 25)`.

Tone and Timbre conversions use the minima and maxima published in the D-20
manuals. In particular, Tone Bias Points retain their `<` or `>` direction,
TVF Bias Level is `-7…+7`, and TVA Bias Levels are `0…-12`. If a bounded
stored value is malformed, the report shows the raw value as invalid rather
than presenting a plausible but incorrect setting. See
[the memory-address reference](memory-map.md#manual-checked-ranges-and-offsets)
for the byte offsets and complete range table.

## Example output

These shortened examples are from `DemoDump.mid`. Actual names and values will
reflect the dump being inspected. Long reports continue for every complete
record or assigned rhythm key.

### System

```text
D-20 Global System Settings (10 00 00)
Master tune: 62
Global reverb: Hall 2 (time 7, level 7)

Part     Reserve  Level  Pan     Stored MIDI channel
Part 1         3    100  Center  1
Part 2         3    100  Center  1
...
Rhythm         6    100  Per-key  1
```

### One Patch and Timbre

```text
Patch 1: Warm Pad Fade
Layout: Whole; split: C1
Level: 100; balance (lower/upper): 50
Reverb: Delay 3; time: 8; level: 7

Parameter         Lower                              Upper
Tone              i17 (Warm Pad)                     i17 (Warm Pad)
Key shift         +0                                 +0
Fine tune         -3                                 +5
...
```

```text
Timbre A-11
Tone: i01 AcouPiano1
Key shift: +0; fine tune: +0
Bender range: 2; assign mode: 1; reverb: ON
```

### One Tone

```text
Internal/user Tone i01: AcouPiano1 (address 08H)
Structure 1/2: 6 (P-P (Mix)); structure 3/4: 1 (S-S (Mix))
Envelope mode: Normal

Partial 1 [P]: ACTIVE
  Wave generator: pitch C3, fine +2, key follow s2, bender ON
  Wave: Acoustic Piano High (PCM Bank 1, Wave 33); pulse width 0; pulse-width velocity +0
  LFO: rate 0, depth 0, modulation 0
  Pitch envelope: depth 1, velocity 0, time key follow 4; times [0, 43, 69, 100]
  TVF: cutoff 0, resonance 0, key follow 3/8, bias <A1 / +0
  TVA: level 100, velocity +45; bias 1 >C4 / -12; bias 2 <G4 / -4
```

### Rhythm Setup

```text
D-20 Rhythm Setup (09 00 00)
Note       Tone                              Level  Pan     Reverb
A1         i11 (LowTomTom1)                  100    Center  OFF
B1         r15 (Bass Drum-1)                 100    Center  OFF
C2         r16 (Bass Drum-2)                 100    Center  OFF
C#2        r25 (Rim Shot)                    100    Center  ON
...
```

## Safe handling of partial transfers

An index report may display records whose individual bytes are complete even
when the overall memory area was transferred in pieces. A selected detailed
record, System report, or Rhythm Setup report refuses to decode unless all of
the bytes it needs are present. Missing data is always an error, never a
silently invented default. See [the memory-address reference](memory-map.md)
for exact record sizes and offsets.
