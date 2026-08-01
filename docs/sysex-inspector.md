# SysEx inspector (`d20-tools inspect`)

This is the compact, read-only summary for standard MIDI (`.mid` / `.midi`),
raw SysEx (`.syx`), and native D-20 files. It validates Roland D-20 DT1
framing and checksums, or identifies a native container from its contents
before listing recognised memory areas and their counts.

```sh
d20-tools inspect D20BACKUP.mid
d20-tools inspect D20BACKUP.syx
d20-tools inspect MY_SOUNDS.333
d20-tools inspect MY_RHYTHMS.444
d20-tools inspect TESTSONG.222
d20-tools inspect TESTALL.111
d20-tools inspect TESTALL.111 --report TESTALL-inspection.html --report-format html
d20-tools inspect D20BACKUP.mid --report inspection.json --report-format json
d20-tools inspect D20BACKUP.mid --report inspection.csv --report-format csv
```

Without `--report`, the command writes its compact summary to the terminal. A
successful report ends with an explicit type
declaration. It distinguishes `ALL (MIDI DUMP)`—a complete transfer containing
the System area—from `ALL (DISK)`—a native `.111` disk container without that
separate System area. A native Song file ends with `This is a SONG file.` Song
recognition uses its fixed size, native type byte, and embedded Rhythm section
marker—not its `.222` filename extension.

For a MIDI, SysEx, Sound, or Rhythm input, the report also contains the source
filename, total number of valid DT1 messages, and a count for every area found,
such as `05H Timbre`, `07H Patch`, `08H Tone`, `09H Rhythm Setup`, and `10H
System`. Native All and Song containers are expanded to the same DT1-equivalent
area summary where their layouts contain those areas; they are not converted or
available to the detailed parameter reports yet. A native Song contains its
embedded Rhythm areas (78 message equivalents). A native All contains embedded
Sound and Rhythm areas (165 message equivalents); its disk layout does not
contain a separate `10H` System area.

Use `--report FILE` for a structured, read-only inventory in Markdown (default),
self-contained HTML (`--report-format html`), JSON, or CSV. JSON stores each
table's title, columns, and rows; CSV uses one `section` column and a stable
superset of the report fields. It includes every recognised
memory area, complete Tone/Timbre/Patch/Rhythm/System records that can be
safely listed, and explicit inventory entries for Pattern, Rhythm Track, and
Sequencer Header. Existing output files are protected unless `--force` is
given. This broader overview complements the nested [`report`](reports.md)
commands, which remain better suited to reading detailed parameters in the
terminal.

The HTML report uses the same compact paired-table approach as the experimental
D-110 validation report: internal Tones are split into `i01-i32` and `i33-i64`,
Timbres into A/B banks, and Patches into `1-64` and `65-128`. Markdown contains
the same tables in sequence. A MIDI or SysEx capture that combines Sound and
Rhythm memory in one track is labelled `MIXED` in both report formats.

For a native Song (`.222`) or an All (`.111`) file, both the compact summary
and structured report include the native Song event-stream region's size and
non-zero-byte count. Tempo and track count are deliberately shown as an
undecoded placeholder; the tool does not interpret event bytes as music yet.
The structured report also records whether the Song's embedded Rhythm data was
expanded to DT1-equivalent areas.

Example native Sound-file result:

```text
D-20 DT1 inspection: TESTSND.333
Valid messages: 87
  05H  Timbre: 4 message(s)
  07H  Patch: 19 message(s)
  08H  Tone: 64 message(s)

Sound memory areas are present.
This is a SOUND file.
```
