# Diagnostic reports (`d20-tools report`)

The five reports are read-only decoders for a D-20 Standard MIDI (`.mid` or
`.midi`) or raw SysEx (`.syx`) dump. They validate every Roland D-20 DT1 frame
and checksum before decoding. They print to the terminal and never create,
change, or transmit a file.

The command structure is intentionally nested:

```text
d20-tools report REPORT INPUT [REPORT-OPTION]
```

`REPORT` is one of the following.

| Command | Input and optional parameter | Terminal output |
| --- | --- | --- |
| `report system INPUT` | No extra option. Requires complete 50-byte area `10H`. | Master tune, global reverb, part reserves/levels/pans, and stored MIDI channels. |
| `report patch INPUT` | `--patch 1..128` is optional. Requires area `07H`; the selected record must be complete. | Without `--patch`, a populated-patch index. With it, layout, split, both tone assignments, tuning, bender, assign and reverb values. |
| `report timbre INPUT` | `--slot I-11..I-88` or `--slot C-11..C-88` is optional. Requires area `05H`. | Without `--slot`, a 128-slot index. With it, the complete tone assignment and performance values for that slot. |
| `report tone INPUT` | `--tone 1..64` is optional. Uses permanent `08H`, falling back to temporary `04H`. | Without `--tone`, complete tone names. With it, structure, partial activity, wave generator, LFO, TVF and TVA values. |
| `report rhythm INPUT` | No extra option. Requires complete 340-byte area `09H`. | Assigned Rhythm Setup keys (C1–C8), tone, level, pan and reverb. |

Examples:

```sh
d20-tools report system D20BACKUP.mid
d20-tools report patch D20BACKUP.mid --patch 1
d20-tools report timbre D20BACKUP.syx --slot I-26
d20-tools report tone D20BACKUP.mid --tone 12
d20-tools report rhythm D20BACKUP.mid
```

The option follows the input filename. This avoids ambiguity and makes it easy
to paste the command shown by `d20-tools report REPORT --help`.

## Example output

These shortened examples are from `Awkward.mid`. Actual names and values will
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

### One Patch and Timbre slot

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
Timbre slot I-11
Tone: i01 (AcouPiano1)
Key shift: +0; fine tune: +0
Bender range: 2; assign mode: 1; reverb: ON
```

### One Tone

```text
Tone 1: AcouPiano1 (address 08H)
Structure 1/2: 6 (P-P (Mix)); structure 3/4: 1 (S-S (Mix))
Envelope mode: Normal

Partial 1 [P]: ACTIVE
  Wave generator: pitch C3, fine +2, key follow s2, bender ON
  Wave: PCM bank 0, wave 33; pulse width 0; pulse-width velocity +0
  LFO: rate 0, depth 0, modulation 0
  Pitch envelope: depth 1, velocity 0, time key follow 4; times [0, 43, 69, 100]
  TVF: cutoff 0, resonance 0, key follow 3/8, bias C1 / +0
  TVA: level 100, velocity +45; bias 1 A9 / +4; bias 2 A#3 / +2
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
