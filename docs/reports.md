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

## Safe handling of partial transfers

An index report may display records whose individual bytes are complete even
when the overall memory area was transferred in pieces. A selected detailed
record, System report, or Rhythm Setup report refuses to decode unless all of
the bytes it needs are present. Missing data is always an error, never a
silently invented default. See [the memory-address reference](memory-map.md)
for exact record sizes and offsets.
