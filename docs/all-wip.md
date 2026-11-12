# All-file note export (BETA)

The shared header's recognized saved reverb and rhythm-level record pair is
included as MIDI text metadata and in inspection reports. This does not infer
initial part programs from the embedded Sound library or translate settings
to GM controllers. See the [saved-state trace](saved-initial-state.md).

```sh
d20-tools all MYBACKUP.111 MYBACKUP-notes.mid
d20-tools all MYBACKUP.111 audition.mid --tempo-bpm 120
```

Native `.111` All files include a Song header, event index, and event region
in the same layout used by native `.222` Song files. This BETA command applies
the shared decoder to the Song data in the selected All file and exports its
note events to a Type-1 Standard MIDI file with a separate rhythm track
following the embedded Song pattern list. It does not require a separate
`.222` file or assume that two independently saved files contain the same song.

Recorded `Cx` programs retain their original numbers, ticks and order. The
embedded Sound library can supply referenced instruments, but the exporter
does not assume Patch/Timbre mode or convert references to GM sounds.
See the [program-change guide](song-program-changes.md).

The saved tempo at header offset `0x36` is used by default, with the same
validated code range and ROM formula as Song export. `--tempo-bpm 4..300`
overrides it. An invalid saved code requires an override. Stored
rhythm-pattern hits are expanded on channel 10, with
`--gate-ticks` controlling the provisional note-off length. Supply
`--factory-rom TONE_ROM.BIN` to expand factory presets in the chain using the
supported owned tone ROM. See the [factory mapping guide](factory-rhythm-rom-mapping.md).
`--no-rhythm-track` exports the Song lanes without the rhythm track. The output
uses provisional lane channels and does not infer Patch/Timbre mode or include
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
