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
user Tone (`08H`), Timbre (`05H`), and Rhythm Setup (`09H`) areas. The output is
raw D-110 SysEx and a report can be Markdown (default), HTML, JSON, or CSV.
Open Markdown with a Markdown previewer; open an HTML report directly in a browser.
When `--report` is supplied, the command writes the full comparison to that
file and prints only a short completion summary to the terminal. Without
`--report`, the Markdown comparison is printed to the terminal.

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
the D-110's documented MIDI bulk-transfer facility. The experimental report
lists the exact destination blocks and every non-direct substitution. It
contains two 32-row shared D-20/D-110 Tone tables (`i01-i32` and `i33-i64`),
then all 128 Timbres as A and B tables (`A-11` through `A-88`, then `B-11`
through `B-88`). The HTML version places each pair of tables side by side.
Each Timbre shows its common Tone
reference/name, copied parameters, and the explicit `D-20 reverb → D-110
output` change. The Rhythm-key comparison lists all 85 keys (MIDI notes
24-108) and uses one shared Tone reference/name because those values are
identical on both units. Internal `i01-i64` names come from the transferred
Tone data; preset `r`, `a`, and `b` names use the built-in reference tables.
JSON includes `tones`, `timbres`, and `rhythm`; CSV contains rows from all
three sections.

Not converted: D-20 Patches, Rhythm patterns, Rhythm track, and sequencer
header. The D-110's eight-part Patch architecture is not equivalent to D-20
Patch memory, so no approximation is made.
