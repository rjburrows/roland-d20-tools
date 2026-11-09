# Song note export (BETA)

```sh
d20-tools song MYSONG.222 MYSONG-notes.mid --tempo-bpm 120
```

This one-way export reads the native Song container and writes a Type-1 Standard
MIDI file with a conductor track, one track per observed stored-status lane,
and a separate expanded rhythm track by default.
The note events and relative timing follow the C 1.11 control ROM reader at
`0x6F6A–0x6FDB`, the 192-position storage interval at `0x6ED1`, and the
96-position-per-quarter duration table at `0x5EAA`. Stored one-data-byte `8x`
note-offs become MIDI `9x` messages with zero velocity, matching the ROM's
playback transformation at `0x6FCF`.

The selected audition tempo is **not read from the Song file**. `--tempo-bpm`
is required to prevent accidental claims about the saved tempo. Validated
pattern IDs and 1–8 beat lengths in the header produce time-signature changes.
The rhythm track follows the same pattern-ID list, expanding the note triples
of each stored pattern at its recorded position; silent patterns retain their
duration. `--gate-ticks 1..96` sets a provisional note-off length (default one
tick). Original channel routing and patches, saved tempo, the exact device
gate and ROM preset notes remain unresolved. The rhythm notes use MIDI
channel 10, while Song note lanes retain the stored status low nibble
provisionally. Keep the original disk file; this is one-way.

Pattern IDs `0x00`–`0x1F` refer to ROM presets whose note data is not yet
decoded. If a Song chain contains one, export stops with a clear error. Use
`--no-rhythm-track` to export only the Song note lanes in that case. A mismatch
between a saved pattern's beat length and the Song duration table also stops
the rhythm expansion. The pattern does not store a tempo; `--tempo-bpm` remains
an explicit audition choice.

The event index must point to separate `FF` boundary bytes and each parsed
record must have a supported `8x` or `9x` note status. Unsupported or malformed
records cause a clear error before any output is written. The BETA grammar was
validated against a paired Song/All disk capture and the C 1.11 ROM, but other
firmware versions and compositions may contain event types this exporter does
not yet support. Run `d20-tools inspect MYSONG.222` for an inventory.

To export a **single saved rhythm pattern** from the Song container as drum
notes, use `d20-tools pattern MYSONG.222 pattern.mid --pattern-id 0x3f
--tempo-bpm 120`. This is separate from the combined Song export above;
it does not follow the Song's pattern-number chain. The provisional note-off
gate, position scaling, and other BETA limits are in the
[pattern note export guide](rhythm-converter.md#one-stored-pattern-as-notes-beta).
