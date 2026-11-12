# Stored program changes (BETA)

SONG (`.222`) and ALL (`.111`) exports preserve recorded `Cx` program changes:
tick-zero programs, later changes, repeats and program-only lanes. Numbers
remain zero-based `0..127`, without General MIDI translation. Missing programs
do not cause a default to be invented.

## ROM-backed grammar

C 1.11 SHA-256:
`7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`.
Addresses use normal `C8/18/18`. The expanded `D20TraceSongRouting.java`
compiled and ran read-only in Ghidra 12.2, exporting machine-byte evidence.

| Function | Confirmed instructions | Consequence |
| --- | --- | --- |
| `6F6A–6FB6` | Reads position and explicit/reused status; `FF` clears running status. | Programs share indexed 192-position intervals; status never crosses `FF`. |
| `6FB9–6FC4` | Tests high nibbles `80`, then `C0`; `C0` returns without adding another data byte. | Explicit `[position,Cx,program]`; running `[position,program]`. |
| `7024–705B` | Recorder writes position, changed status, first data byte; skips second for `80` and `C0`. | Independent confirmation that a program has no stored velocity. |
| `6E2F–6E50` | Mode-gated `Cx` consumer passes program data to display helper `2D4E`. | Program playback handling is separate from instrument loading. |
| `7294–72DC` | Output writes status plus first data byte and skips second for `C0`. | Export as MIDI `program_change`, not a note or controller. |

The decoder retains source offset, absolute tick and lane in a `ProgramEvent`,
separate from `NoteEvent`. MIDI preserves within-lane source order, including
a program before a same-tick note and repeated choices. Counts distinguish
programs from notes. The provisional stored-lane/channel policy is unchanged.

## Stored instrument references

The [loader trace](song-destinations-and-programs.md) distinguishes Patch and
Timbre interpretation. Program-bearing MIDI tracks include text explaining
their dependency on matching stored instruments. SONG may rely on device
memory or a companion Sound file. ALL contains Sound definitions, which can
be located once mode/source are established:

| Internal interpretation | Native ALL offset for zero-based program `p` |
| --- | --- |
| Timbre | `7900 + 8*p` |
| Patch | `7D00 + 38*p` |

Definitions are not proof of the active mode. The exporter does not silently
choose Patch versus Timbre, resolve card references against internal memory,
or remap user Tone/Timbre references to GM instruments.

## Validation

Generated fixtures test both containers, tick-zero and later programs,
same-tick order, repeats, status transitions, offsets and program-only lanes.
An exhaustive fixture exports all 128 numbers on all 16 lane nibbles; this
tests preservation, not validity as an internal D-20 part in every mode.
Malformed payloads and missing status after `FF` stop before output.
Controllers, pitch bend, pressure and internal commands remain unsupported.

`make check` passed: 78 tests, 8 optional skips; Song/pattern statement and
branch coverage 100%, repository 94%. The private Song/All pair contains
2,044 note records and **zero Cx records**; its full MIDI output remains
byte-identical to the previous saved-setup version. Program support is
ROM-backed and fixture-tested, with independent native program recordings
still needed for additional hardware validation.
