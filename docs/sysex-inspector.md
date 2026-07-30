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
```

`INPUT` is the only parameter. The command creates no output file and writes
its report to the terminal. A successful report ends with an explicit `ALL`,
`SOUND`, `RHYTHM`, `MIXED`, or `UNKNOWN` declaration. A native Song file ends
with `This is a SONG file.` Song recognition uses its fixed size, native type
byte, and embedded Rhythm section marker—not its `.222` filename extension.

For a MIDI, SysEx, Sound, or Rhythm input, the report also contains the source
filename, total number of valid DT1 messages, and a count for every area found,
such as `05H Timbre`, `07H Patch`, `08H Tone`, `09H Rhythm Setup`, and `10H
System`. Native All and Song containers are expanded to the same DT1-equivalent
area summary where their layouts contain those areas; they are not converted or
available to the detailed parameter reports yet. A native Song contains its
embedded Rhythm areas (78 message equivalents). A native All contains embedded
Sound and Rhythm areas (165 message equivalents); its disk layout does not
contain a separate `10H` System area.

It is useful whether the dump came from MIDI Data Transfer or was produced by
one of the file converters. It never changes the input file. It is not a
parameter-by-parameter decoder: use the nested [`report`](reports.md) commands
for the detailed System, Patch, Timbre, Tone, and Rhythm Setup reports.

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
