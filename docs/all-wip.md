# All-file note export (BETA)

```sh
d20-tools all MYBACKUP.111 MYBACKUP-notes.mid --tempo-bpm 120
```

Native `.111` All files include a Song header, event index, and event region
in the same layout used by native `.222` Song files. This BETA command applies
the shared decoder to the Song data in the selected All file and exports its
note events to a Type-1 Standard MIDI file. It does not require a separate
`.222` file or assume that two independently saved files contain the same song.

`--tempo-bpm` is an explicit audition value; the saved tempo has not been
decoded. The output omits expanded rhythm-pattern notes, original channel and
patch routing, and the embedded Sound/Rhythm SysEx domains. `d20-tools inspect`
can inventory those embedded domains. This command is one-way; retain the
original `.111` file. See [Song note export](song-wip.md) for the ROM-backed
record grammar, timing, and BETA validation limits.
