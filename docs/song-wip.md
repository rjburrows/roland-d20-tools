# Song note export (BETA)

```sh
d20-tools song MYSONG.222 MYSONG-notes.mid
d20-tools song MYSONG.222 audition.mid --tempo-bpm 120
```

This one-way export reads the native Song container and writes a Type-1 Standard
MIDI file with a conductor track, one track per observed stored-status lane,
and a separate expanded rhythm track by default.
Recorded `Cx` program changes are preserved too, including tick-zero instrument
selection. Numbers remain D-20 references, without a GM sound translation.
See the [program-change evidence and limits](song-program-changes.md).
The note events and relative timing follow the C 1.11 control ROM reader at
`0x6F6A–0x6FDB`, the 192-position storage interval at `0x6ED1`, and the
96-position-per-quarter duration table at `0x5EAA`. Stored one-data-byte `8x`
note-offs become MIDI `9x` messages with zero velocity, matching the ROM's
playback transformation at `0x6FCF`.

The default tempo comes from the saved header byte at `0x36`. The C 1.11
load trace places this byte in `B4D0`, and the ROM computes `40 + 2 × code`
BPM. Valid codes `0x00..0x69` represent 40–250 BPM. Use `--tempo-bpm 4..300`
for an explicit override. An invalid saved code requires an override before
output is written. MIDI text and the terminal result identify which tempo
source was used. Validated
pattern IDs and 1–8 beat lengths in the header produce time-signature changes.
The rhythm track follows the same pattern-ID list, expanding the note triples
of each stored pattern at its recorded position; silent patterns retain their
duration. `--gate-ticks 1..96` sets a provisional note-off length (default one
tick). Automatic Patch/Timbre mode resolution, original channel routing and
the exact device gate remain unresolved. The rhythm notes use MIDI
channel 10, while Song note lanes retain the stored status low nibble
provisionally. Keep the original disk file; this is one-way.

The recognized saved setup pair at header `0x16..0x1B` is preserved as MIDI
text and shown by `inspect`: reverb mode, time, level and rhythm level in native
units. These are not translated into GM controllers. Missing pairs do not
invent defaults; non-seven-bit data in a recognized pair is rejected. Initial
part defaults not recorded as program events remain unverified. See the
[saved-state trace](saved-initial-state.md).

The [routing trace](song-routing-checkpoint.md) confirms that firmware can
conditionally adjust lane 7 and remap statuses through an active channel
table, or select a queue that bypasses that table. The saved flags alone do
not establish every runtime mode. Initial programs, volume and pan are not
invented or emitted from unverified header fields.

Pattern IDs `0x00`–`0x1F` refer to factory presets in the tone ROM. Supply
`--factory-rom TONE_ROM.BIN` to expand them alongside the writable patterns.
The supported 128 KiB image is checked by SHA-256, as documented in the
[factory mapping guide](factory-rhythm-rom-mapping.md). Without that ROM, a
preset selection reports an error. `--no-rhythm-track` exports the Song note
lanes only. A mismatch
between a saved pattern's beat length and the Song duration table also stops
the rhythm expansion. Tempo belongs to the Song header and applies to the
whole export. Individual rhythm patterns carry their own lengths and hits.

The event index must point to separate `FF` boundary bytes and each parsed
record must have a supported `8x`/`9x` note or `Cx` program status. Unsupported or malformed
records cause a clear error before any output is written. The BETA grammar was
validated against a paired Song/All disk capture and the C 1.11 ROM, but other
firmware versions and compositions may contain event types this exporter does
not yet support. Run `d20-tools inspect MYSONG.222` for an inventory.
The [firmware reverse-mapping guide](firmware-reverse-mapping.md) documents
the ROM reader, recorder, and the evidence for the file offsets.

To export a **single saved rhythm pattern** from the Song container as drum
notes, use `d20-tools pattern MYSONG.222 pattern.mid --pattern-id 0x3f
--tempo-bpm 120`. This is separate from the combined Song export above;
it does not follow the Song's pattern-number chain. The provisional note-off
gate, position scaling, and other BETA limits are in the
[pattern note export guide](rhythm-converter.md#one-stored-pattern-as-notes-beta).
