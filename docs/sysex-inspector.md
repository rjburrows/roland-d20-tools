# SysEx inspector (`d20-tools inspect`)

This is the compact, read-only summary for standard MIDI (`.mid` / `.midi`),
raw SysEx (`.syx`), native Sound (`.333`), or native Rhythm (`.444`) D-20
files. It validates Roland D-20 DT1 framing and checksums, or validates the
native container before listing recognised memory areas and their counts.

```sh
d20-tools inspect D20BACKUP.mid
d20-tools inspect D20BACKUP.syx
d20-tools inspect MY_SOUNDS.333
d20-tools inspect MY_RHYTHMS.444
```

`INPUT` is the only parameter. The command creates no output file and writes
its report to the terminal. A successful report contains the source filename,
total number of valid DT1 messages, and a count for every area found, such as
`05H Timbre`, `07H Patch`, `08H Tone`, `09H Rhythm Setup`, and `10H System`.

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
```
