# Rhythm converter (`d20-tools rhythm`)

Converts Roland D-20 Rhythm disk files (`.444`) to Standard MIDI or raw SysEx,
and reconstructs a `.444` file from complete compatible MIDI/SysEx data.

```sh
d20-tools rhythm RHYTHM.444 RHYTHM.mid
d20-tools rhythm RHYTHM.syx RHYTHM.444 --name RHYTHM
```

| Input | Valid output |
| --- | --- |
| `.444` | `.mid`, `.midi`, `.syx` |
| `.mid`, `.midi`, `.syx` | `.444` |

`--name` is required only when writing a `.444` and must be 1–10 printable
ASCII characters. Existing output files are protected; add `--force` only to
replace a file intentionally.

Example terminal result:

```text
Converted TESTRHY.444 (TESTRHY) to TESTRHY.syx: 78 DT1 messages.
```

The native file is exactly 12,288 bytes. Pattern Memory and Rhythm Track data
are nibble-packed (low nibble first); Sequencer Header and Rhythm Setup are
stored directly. The converter validates all four required areas, Roland DT1
checksums, 7-bit SysEx values, and the required native mirror region.
