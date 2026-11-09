# Rhythm converter (`d20-tools rhythm`)

Converts Roland D-20 Rhythm disk files (`.444`) to Standard MIDI or raw SysEx,
and reconstructs a `.444` file from complete compatible MIDI/SysEx data.

```sh
d20-tools rhythm RHYTHM.444 RHYTHM.mid
d20-tools rhythm RHYTHM.syx RHYTHM.444
```

| Input | Valid output |
| --- | --- |
| `.444` | `.mid`, `.midi`, `.syx` |
| `.mid`, `.midi`, `.syx` | `.444` |

When writing a `.444`, its embedded D-20 filename is derived from the output
filename: it is uppercased and limited to the first 10 printable ASCII
characters of the filename stem. Existing output files are protected; add
`--force` only to replace a file intentionally.

Example terminal result:

```text
Converted TESTRHY.444 (TESTRHY) to TESTRHY.syx: 78 DT1 messages.
```

The native file is exactly 12,288 bytes. Pattern Memory and Rhythm Track data
are nibble-packed (low nibble first); Sequencer Header and Rhythm Setup are
stored directly. The converter validates all four required areas, Roland DT1
checksums, 7-bit SysEx values, and the required native mirror region.

## One stored pattern as notes (BETA)

```sh
d20-tools pattern RHYTHM.444 pattern.mid --pattern-id 0x3f --tempo-bpm 120
d20-tools pattern MYSONG.222 song-pattern.mid --pattern-id 0x3f --tempo-bpm 120
d20-tools pattern MYBACKUP.111 all-pattern.mid --pattern-id 0x3f --tempo-bpm 120
```

This separate, one-way command reads one of the 32 writable pattern records
(IDs `0x20`–`0x3F`, corresponding to P-51–P-88) embedded in a native Rhythm,
Song, or All file. It writes Type-1 MIDI containing one note-on per saved
`[position, note, velocity]` hit and a provisional note-off for audition.
The saved 1–8 beat pattern length becomes a MIDI time signature; the saved
position is one of 24 positions per quarter note and is scaled to 96 MIDI
ticks per quarter. Concurrent hits remain concurrent. The source file is not
modified, and existing output requires `--force`.

`--tempo-bpm` is mandatory because the saved tempo is not decoded. MIDI
channel 10 is the default drum channel; `--channel 1..16` selects another.
`--gate-ticks 1..96` chooses the note-off length, defaulting to one tick:
**there is no stored gate in the pattern hit record**. Neither the exact
playback gate nor the actual real-time position-scaling instruction has been
verified in ROM. These are explicit BETA audition choices, not extracted
values. A pattern is exported by ID; the Song/Rhythm chain is not expanded.

For every note used within the 24–108 Rhythm Setup range, a MIDI text event
contains its four original `09H` bytes. Their device-specific meanings are
not interpreted as MIDI program, controller, or kit changes. The stored hit
triples have no such additional fields. The existing `d20-tools rhythm` command
exports the native Rhythm SysEx data, which is distinct from this playable
note-event export.

### Rhythm-file note export (BETA)

```sh
d20-tools rhythm RHYTHM.444 one-pattern.mid --notes pattern --pattern-id 0x3f --tempo-bpm 120
d20-tools rhythm RHYTHM.444 all-patterns.mid --notes all --tempo-bpm 120
d20-tools rhythm RHYTHM.444 rhythm-track.mid --notes track --tempo-bpm 120 --gate-ticks 12
```

`--notes pattern` exports one stored ID. `--notes all` writes **32 separate MIDI
tracks**, one per writable ID P-51–P-88, aligned at tick zero so tracks can be
soloed or imported separately. An empty pattern still has a named track. Each
track's name gives its pattern length; the conductor does not impose a single
meter on patterns with different lengths. `--notes track` follows the counted
pattern-ID list in the native `.444` Sequencer Header, appends each selected
pattern in sequence, preserves silent selections, and marks each selection.
Its conductor track records meter changes at pattern boundaries.

All three modes require `--tempo-bpm 4..300`; `--gate-ticks 1..96` controls
the provisional note length (default one tick), and `--channel 1..16` sets the
output channel (default 10). The selection list and pattern note bytes are
separate from the `09H` Rhythm Setup; the pattern does not store a tempo.
The saved-tempo field has not been established well enough to use automatically.
If the selection list includes a ROM preset ID (`0x00`–`0x1F`), track expansion
reports an error: the preset notes are not yet decoded. The existing default
`d20-tools rhythm RHYTHM.444 RHYTHM.mid` still exports the reversible SysEx
representation; `--notes` selects the new note-event output.
