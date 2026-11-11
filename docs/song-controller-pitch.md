# Recorded controllers and pitch bend (BETA)

SONG (`.222`) and ALL (`.111`) export recorded `Bx` control changes and `Ex`
pitch bend alongside notes, programs and the separate expanded rhythm track
in one Type-1 MIDI file. Both containers use the same decoder. Events retain
stored values, position, order within each lane, repeated values and the status
low nibble as a provisional MIDI channel. Controller-only and bend-only lanes
are retained. No default controllers or bend resets are added.

## Record grammar and MIDI representation

| Family | Explicit record | Reused status | MIDI output |
| --- | --- | --- | --- |
| `Bx` | position, status, controller, value | position, controller, value | `control_change`, both data bytes `0..127` |
| `Ex` | position, status, LSB, MSB | position, LSB, MSB | `pitchwheel`, signed value `(MSB << 7 \| LSB) - 8192` |

Position is `0..191` within a 192-position indexed storage interval; export
uses 96 PPQ. Every `FF` interval boundary resets running status. All data bytes
must be seven-bit; truncated records, unknown families or invalid positions
stop conversion before output is written, including with `--force`.

Controller numbers and values are preserved without GM remapping: this includes
CC1 modulation, CC7 volume, CC10 pan and CC64 sustain. Repeated sustain messages
and values on either side of the conventional 64 threshold remain separate
messages. The exporter does not simulate the D-20's live suppression rules.
Pitch center is 0, with endpoints -8192 and 8191; the original two bytes round
trip exactly. Bend range, RPN state and pitch in semitones are not inferred.
The four saved header setup values remain native text metadata, independently
of recorded controller messages; see [saved initial state](saved-initial-state.md).

## ROM evidence and atomic function map

C 1.11 SHA-256:
`7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`.
Addresses below use the normal `C8/18/18` CPU view. The executed, bounded
`D20TraceSongRouting.java` trace verifies this hash before reporting instructions.

| Address | Confirmed instructions / dependency | Interpretation and limits |
| --- | --- | --- |
| `6705–6731` | Classifies status high nibbles `90`, `C0`, `E0`, `B0` as 1–4. | Supports controller and bend families in the sequencer path. The later `FF` comparison after masking with `F0` is unreachable; it does not prove system-message support. |
| `6F6A–6FCA` | Reads position and optional status; only `80` and `C0` bypass the second data byte. | Stored `Bx` and `Ex` each have two data bytes. `FF` clears status. |
| `7049–705B` | Recorder masks status and skips `B483` only for `80` or `C0`. | Independent writer corroboration of the two-byte grammar. |
| `7294–72DC` | Queues status and `B47C`; queues `B47D` except for `C0`/`Fx`. | Preserves both raw data bytes on the controller/bend output path. It does not prove support for stored `Fx` records. |
| `6E51–6E87` | Mode-gated `Bx` handling on the selected lane or lane 8; CC10 calls `48FF`, CC7 calls `4915`. | Some controllers also affect internal state. Runtime flags and hardware effects remain mode dependent. |
| `74A5–74EF`, caller `6DBE` | CC64 compares data bit 6 with per-lane state at `B4B8`; unchanged state returns zero. | Firmware sustain suppression is conditional. Export retains every stored event rather than applying this live filter. |
| `68DD–6923` | Calls `6945`, returns on nonzero; updates record/lane flags, optionally calls `6924`, then calls writer `6FDC`. | Recording gate and state update, not a note-data conversion. Flag meanings beyond traced use remain provisional. |
| `6924–6944` | Indexes `B4D1` by `B481 & 0F`, ORs `60`, reads lane mask from `AB00`, calls `33F2`. | Atomic lane-record-state helper. Downstream `33F2` semantics remain unresolved. |
| `6945–6985` | Compares 24-bit `B454:456` against `B4DB:DD + 3C`; below threshold sets `B4AF.bit4`, `B4B1.bit7`, `B4B7.bit7`, returns `FF`; otherwise zero. | Atomic 60-byte headroom guard. No musical-unit interpretation is assigned to this threshold. |

Reproduce on the mapped research copy after `D20SetupRuntimeMap.java`:

```sh
analyzeHeadless /tmp/ghidra-projects RolandD20-Control \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceSongRouting.java /tmp/song-routing.txt
```

The setup script modifies the research copy; the trace above is read-only.
Keep the original import and owned ROM bytes outside git. The
[overall reverse map](firmware-reverse-mapping.md) records other discovered
functions and bank views.

## Validation and remaining work

Generated fixtures exercise both file types, all 128 controllers on all 16
stored lanes, every one of the 16,384 pitch values on each file type, running
status, interval resets, mixed same-tick ordering, repeated sustain, event-only
lanes, inspection counts and malformed-input/output preservation. The Song
and pattern modules have 100% statement and branch coverage in `make check`.
The existing private Song/All pair has no recorded controllers or pitch bends;
its full MIDI exports are compared byte-for-byte with the preceding exporter.
No private files, ROM bytes or generated MIDI are committed.

The grammar is ROM-backed and fixture-tested; independent native recordings
containing sustain, modulation and wheel motion are still needed for musical
validation. Polyphonic pressure (`Ax`), channel pressure (`Dx`) and system or
internal (`Fx`) records remain unsupported. Original active channel routing,
Patch/Timbre mode and any unrecorded initial part state remain unresolved.
