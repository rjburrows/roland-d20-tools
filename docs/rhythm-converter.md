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

`--tempo-bpm` is mandatory for individual pattern export because patterns
contain relative timing. The Song/All commands can read their container
tempo when exporting the whole arrangement. MIDI
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
Standalone Rhythm note export requires an explicit tempo. The saved Song/All
tempo reader applies to their arrangement exports.
A factory preset selection (`0x00`–`0x1F`) requires the supported tone ROM
through `--factory-rom`. The command reports a missing-ROM error when that
source is needed. The existing default
`d20-tools rhythm RHYTHM.444 RHYTHM.mid` still exports the reversible SysEx
representation; `--notes` selects the new note-event output.

See the [firmware reverse-mapping guide](firmware-reverse-mapping.md) for the
A/B editor trace, saved pattern layout, and evidence for the timing conversion.

## Factory presets from the tone ROM (BETA)

```sh
d20-tools pattern RHYTHM.444 preset.mid --pattern-id 0x17 --factory-rom TONE_ROM.BIN --tempo-bpm 120
d20-tools rhythm RHYTHM.444 all-patterns.mid --notes all --factory-rom TONE_ROM.BIN --tempo-bpm 120
d20-tools rhythm RHYTHM.444 rhythm-track.mid --notes track --factory-rom TONE_ROM.BIN --tempo-bpm 120
d20-tools song MYSONG.222 song.mid --factory-rom TONE_ROM.BIN
d20-tools all MYBACKUP.111 all.mid --factory-rom TONE_ROM.BIN
```

IDs `0x00..0x1F` are P-11–P-48, and IDs `0x20..0x3F` are P-51–P-88.
`--factory-rom` accepts the supported 131,072-byte tone ROM whose SHA-256 is
`ae4aa5a80b5e5aba9584db6906707ea9d74fb04936a917e6e62585a4529782a1`.
The file is validated locally. Supply the tone ROM separately from the A/B
program ROMs and the PCM waveform ROMs. The package contains the extractor.

With the ROM supplied, `--notes all` writes 64 pattern tracks plus the
conductor. Without it, this mode writes the 32 writable pattern tracks.
All pattern tracks start at zero and can be soloed individually. MIDI
end-of-track events preserve the complete beat length, including empty
patterns and rests after the last hit. Notes use the native file's raw
Rhythm Setup metadata and default to MIDI channel 10.

A saved rhythm chain may mix factory and writable IDs. Each selection uses
its own beat length, and Song/All checks that length against the Song duration
table. The user-selected note gate and the previously documented BETA timing
assumptions also apply to factory patterns. See the
[factory mapping guide](factory-rhythm-rom-mapping.md) for ROM evidence.
