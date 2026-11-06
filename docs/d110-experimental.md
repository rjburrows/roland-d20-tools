# Experimental D-20 to D-110 converter

`d20-tools d110` is an **experimental, opt-in, one-way** converter. It never
changes the input, and it does not alter the existing D-20 Sound or Rhythm
converters. Review the generated report before sending its SysEx to a D-110.
The file format is validated, but this project does not yet include a
documented D-110 hardware load, power-cycle, bulk-dump, and byte-for-byte
read-back test. Keep a backup of the target's memory and treat hardware use as
an experimental verification step.

```sh
d20-tools d110 D20BACKUP.mid D110-SNDRHY.syx --report D110-SNDRHY.md
```

For a browser-ready table, request a self-contained HTML report:

```sh
d20-tools d110 D20BACKUP.mid D110-SNDRHY.syx --report D110-SNDRHY.html --report-format html
```

The source must be a complete D-20 MIDI or raw SysEx dump containing permanent
user Tone (`08H`), Timbre (`05H`), and Rhythm Setup (`09H`) areas. The output
is raw D-110 SysEx. Reports may be Markdown (default), HTML, JSON, or CSV;
open Markdown in a previewer and HTML directly in a browser. With `--report`,
the full comparison is written to that file and the terminal receives only a
short completion summary. Without it, the Markdown comparison is printed to
the terminal.

| D-20 source | D-110 destination | Handling |
| --- | --- | --- |
| User Tones `08H` | Internal Tone Memory `08 00 00` | copied to matching `i01-i64` slots |
| Timbres `05H` | Internal Timbre Memory `05 00 00` | copied, except per-Timbre reverb switch becomes `MIX` output assignment |
| Rhythm Setup `09H` | Rhythm Setup bulk block `03 01 10` | tone, level, and pan copied; reverb switch becomes `MIX` output assignment |

### D-110 Tone record compatibility

Each D-20 Tone record occupies 256 bytes, while the D-110 documents only the
first 246 bytes as active Tone parameters. During conversion the final ten
bytes of every Tone record are written as zero. They are not part of the
named Tone or its active synthesis settings, so this prevents D-20-only or
undefined trailing data from being sent to the D-110.

The D-110 Rhythm Setup is battery-backed internal memory and is included in
the D-110's documented MIDI bulk-transfer facility. The report lists the
destination blocks and every non-direct substitution. It has two 32-row shared
D-20/D-110 Tone tables (`i01-i32` and `i33-i64`) and all 128 Timbres in A and
B tables (`A-11` through `A-88`, then `B-11` through `B-88`). HTML places each
pair side by side. Timbre and Rhythm rows show a Tone identifier and Tone name;
internal `i01-i64` names come from transferred data, while preset `r`, `a`,
and `b` names use built-in reference tables. The Rhythm comparison covers all
85 keys (MIDI notes 24-108). JSON has `tones`, `timbres`, and `rhythm`; CSV
contains rows from all three sections.

### HTML report excerpt

The browser report presents the A and B Timbre tables side by side. A Timbre
row looks like this (the values below are representative):

| Timbre | Tone | Tone name | Shift | Fine | Bend | Assign | Reverb → output | Status |
|---|---|---|---:|---:|---:|---:|---|---|
| A-11 | a01 | AcouPiano 1 | +0 | +0 | 2 | 1 | ON → MIX | D-20 reverb replaced |
| A-12 | i01 | TouchPiano | +0 | +0 | 2 | 1 | OFF → MIX | Direct fields copied |

Not converted: D-20 Patches, Rhythm patterns, Rhythm track, and sequencer
header. The D-110's eight-part Patch architecture is not equivalent to D-20
Patch memory, so no approximation is made.

## Explicit destination initialization

Permanent Timbres are built from a complete eight-byte baseline before the six
shared D-20 fields are copied. Output assignment is explicitly written as MIX
(0); the dummy byte is explicitly zero. The converter does not inherit either
byte from the source's reserved data or the destination's current memory.
Rhythm output assignment is also explicitly MIX. All 246 active Tone bytes
are transferred, including muted partials; the ten padding bytes are zeroed.
Common and partial parameters are range-validated before output is written.
Source reverb switches must be 0 or 1 before substitution.

Reference: [Roland D-110 Owner's Manual](https://cdn.roland.com/assets/media/pdf/D-110_OM.pdf),
printed pp.117–118, tables 5-1, 5-3 and 5-4. These tables establish parameter
ranges and MIX encoding, **not a verified factory INIT snapshot**. MIX is the
current explicit conversion baseline, not a claim of verified INIT equivalence.
A hardware INIT dump is still needed to verify that equivalence. When Patch
conversion is implemented, it must start from a verified complete D-110 INIT
Patch and overlay mapped fields; unverified defaults must block that conversion.
Patch conversion remains unsupported and does not write Patch or System memory.

Hardware read-back and listening validation remain outstanding.
