# All-file note export (BETA)

```sh
d20-tools all TESTALL.111 TESTALL-notes.mid --tempo-bpm 120
```

Native `.111` All files contain the same Song header, event index and event
region as a `.222` Song file. This BETA command uses the shared Song decoder
to export note events to a Type-1 Standard MIDI file. The `TESTALL.111` and
`TESTSONG.222` validation pair yield identical notes and time signatures.

`--tempo-bpm` is an explicit audition value; the saved tempo has not been
decoded. The output omits expanded rhythm-pattern notes, original channel and
patch routing, and the embedded Sound/Rhythm SysEx domains. `d20-tools inspect`
can inventory those embedded domains. This command is one-way; retain the
original `.111` file. See [Song note export](song-wip.md) for the ROM-backed
record grammar, timing, and BETA validation limits.
