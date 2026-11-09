# All-file note export (BETA)

```sh
d20-tools all MYBACKUP.111 MYBACKUP-notes.mid --tempo-bpm 120
```

Native `.111` All files include a Song header, event index, and event region
in the same layout used by native `.222` Song files. This BETA command applies
the shared decoder to the Song data in the selected All file and exports its
note events to a Type-1 Standard MIDI file with a separate rhythm track
following the embedded Song pattern list. It does not require a separate
`.222` file or assume that two independently saved files contain the same song.

`--tempo-bpm` is an explicit audition value; the saved tempo has not been
decoded. Stored rhythm-pattern hits are expanded on channel 10, with
`--gate-ticks` controlling the provisional note-off length. ROM preset pattern
notes are unsupported: use `--no-rhythm-track` for Song note lanes only if the
chain includes one. The output omits original channel and patch routing and
the embedded Sound/Rhythm SysEx domains. `d20-tools inspect`
can inventory those embedded domains. This command is one-way; retain the
original `.111` file. See [Song note export](song-wip.md) for the ROM-backed
record grammar, timing, and BETA validation limits.
See the [firmware reverse-mapping guide](firmware-reverse-mapping.md) for the
shared Song header, event index, and embedded rhythm offsets.

The embedded writable rhythm patterns can also be exported **one at a time**:
`d20-tools pattern MYBACKUP.111 pattern.mid --pattern-id 0x3f --tempo-bpm 120`.
The `pattern` command does not expand the Song chain. See the
[pattern note export guide](rhythm-converter.md#one-stored-pattern-as-notes-beta)
for the supported IDs and BETA timing limits.
