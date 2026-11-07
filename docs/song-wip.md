# Song note export (BETA)

```sh
d20-tools song MYSONG.222 MYSONG-notes.mid --tempo-bpm 120
```

This one-way export reads the native Song container and writes a Type-1 Standard
MIDI file with a conductor track and one track per observed stored-status lane.
The note events and relative timing follow the C 1.11 control ROM reader at
`0x6F6A–0x6FDB`, the 192-position storage interval at `0x6ED1`, and the
96-position-per-quarter duration table at `0x5EAA`. Stored one-data-byte `8x`
note-offs become MIDI `9x` messages with zero velocity, matching the ROM's
playback transformation at `0x6FCF`.

The selected audition tempo is **not read from the Song file**. `--tempo-bpm`
is required to prevent accidental claims about the saved tempo. Validated
pattern IDs and 1–8 beat lengths in the header produce time-signature changes;
unverified chain data produces no time-signature events. Channels retain the
stored status low nibble provisionally. The converter does not expand rhythm
patterns, assign original track routing or patches, decode saved tempo, or
convert back to a native `.222` file. Keep the original disk file.

The event index must point to separate `FF` boundary bytes and each parsed
record must have a supported `8x` or `9x` note status. Unsupported or malformed
records cause a clear error before any output is written. The BETA grammar was
validated against a paired Song/All disk capture and the C 1.11 ROM, but other
firmware versions and compositions may contain event types this exporter does
not yet support. Run `d20-tools inspect MYSONG.222` for an inventory.
