# Native saved initial-state checkpoint

The save/load investigation identifies four sound settings in both native
SONG (`.222`) and ALL (`.111`) headers. The BETA exporter now preserves them
as conductor-track text, and `inspect` reports them. Initial per-part program
references and active MIDI channel assignments remain unverified.

## Confirmed saved fields

All offsets are zero-based. The supported record pair is:

| Offset | Stored byte | A/B source / interpretation |
| --- | --- | --- |
| `16` | `88` | First setup record tag. This is a device protocol record, not a sequencer note-off. |
| `17` | Reverb mode | `C995` |
| `18` | Reverb time | `C996` |
| `19` | `89` | Second setup record tag. |
| `1A` | Reverb level | `C997` |
| `1B` | Rhythm level | `C9C6`, applied to the rhythm part's level through `3A67`. |

The values are native device units. They are not GM program numbers or a
justification for emitting CC7, CC10 or CC91. The exporter inserts text only;
it does not change note velocities, channels, note-offs, tempo or timing.
Seven-bit payload values are preserved without guessing a conversion or
silently clamping them to a supposed musical range.

When the exact `88 ... 89 ...` pair is absent, no setup is invented and the
existing note export remains available. A recognized pair with a non-seven-bit
payload reports an error before output. Inspection describes absent or invalid
setup separately from tempo and event decoding.

## Save, reply and replay evidence

C addresses marked **disk** use `85/18/08`, mapping CPU `5000–7FFF` to C ROM
file `D000–FFFF`. C source SHA-256 is
`7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`.
A/B SHA-256 is
`283cda5527d3b21cc39093cdcb0f982f0399466585b871b9fa77ac3ae855f2ca`.
A/B bank-2 window addresses require bank 2; they are not a universal flat view.

| Function / table | Executed instruction evidence | Consequence |
| --- | --- | --- |
| C disk `55A8–55B1` | Initializes receive staging, sends command `D8 59` via `585D`, and calls `602A`. | Requests the initial setup before saving the sequencer-bearing containers. |
| C disk `55B4–55DB` | Sets DE=`8016`, B=2. Accepts a tag of `88` or `89`, then reads two more bytes with `5E5B`; stores all three, twice, with error exits on missing data or invalid tag. | Captures six bytes at the header offsets, not an eight-program array. The reply handler establishes the normal ordered pair. |
| C disk `55F7–5600` | Copies 32 bytes `8000→9A00`. | The captured bytes belong to the staged first header block. The first-allocation origin and matching load copy are established by the [tempo trace](song-tempo-load-checkpoint.md). |
| A/B fixed `2188–21A9` | Restores bank 2 with `5FEF`, indexes status table `A3AA` by `2*(status-C0)`, then doubles the first data byte before indirect dispatch. | Table entry `A3DA` for `D8` points to `2801`. |
| A/B fixed `2801–2810` | For command bit 6 set, subtracts `80` from the doubled command and indexes table `8DCE` under bank 2. | Command `59` selects word `8E00`, which is `8AF0`. |
| A/B bank 2 `8AF0–8B17` | Queues `88,C995,C996`, increments status, then queues `89,C997,C9C6`; both data words are masked with `7F7F`. | Independently identifies the four fields and expected tag order from their actual source state. |
| C disk `5CBC–5CD4` | For a sequencer-bearing file, points HL at `8016`; when its first byte is `88`, sends exactly six bytes through `5865`, then calls vector `0014`. | Restores the saved setup protocol before the normal tempo/state refresh. |
| A/B bank 2 `86A6–86DE` | The UART parser's special `88`/`89` branches restore `C995/C996` and `C997/C9C6`; reverb writes are gated by `C9AB==0`, while `89` restores `C9C6` and calls `3A67` with part stride `80`. | Corroborates field roles, but replay depends on mode. This UART branch alone does not close every byte of CPU-link reception. |
| A/B fixed `3A67–3A74` | When the part stride has bit 7 set, copies `C9C6` into `C008 + stride`. | Rhythm-part level application; agrees with the existing part-level/Rhythm Setup mapping. |

The Patch loader's scatter table `419C` independently maps Patch bytes
16, 17 and 18 to `C995`, `C996`, `C997`. The existing Patch report identifies
those fields as reverb mode/time/level. This cross-check is stronger than
assigning meanings solely from the specimen values.

## What each file carries

| Data | SONG `.222` | ALL `.111` | Remaining limit |
| --- | --- | --- | --- |
| Setup pair at `16–1B` | Present in validation save | Present in validation save | Other or older header shapes remain unsupported as setup metadata. |
| Tempo and saved lane flags | Shared Song-header layout | Shared Song-header layout | Flags select destinations; they are not MIDI channel numbers. |
| Song events and indexed timing | Yes | Yes | Current BETA decoder accepts notes, recorded programs, controllers and pitch bend; see the [event guide](song-controller-pitch.md). |
| Stored Rhythm data | Embedded | Embedded | Includes Rhythm Setup and pattern/track records. |
| Sound library | Not in the traced section list | Additional Sound section | Stored Patch/Timbre definitions do not establish which initial program a part selects. |
| Initial part programs / active channel table | Not established | Not established | No defaults or GM programs are emitted. Absence has not been proven for every possible record or firmware version. |

C disk lists `5807` and `580C` are `01 02 03 04 00` and `01 02 04 00`;
standalone Sound and Rhythm lists at `5810/5812` are `03 00` and `04 00`.
`5A5E` selects these lists by type; `5E49` advances the class iterator.
Thus the difference is the Sound class, not an independently identified System
settings snapshot. The implemented native boundaries agree with this split.

Do not reinterpret the eight initializer bytes `B715–B71C = 01..08` as program
assignments. Their semantics are not established by the initialization alone.
Raw operand searches also hit a pointer table and the immediate word `B71A`
in position-index arithmetic, so a two-byte match is not necessarily a data
reference. Likewise, `B4CC/B4CE` participate in 24-bit remaining-space
arithmetic at `65A0–65BF`; they are not demonstrated program fields.

The previously identified active channel table `B448–B450` is below the
first Song-data transfer destination `B4BA`. The traced header transfer does
not directly overwrite it. This narrows the search; it does not exclude a later
command or callback that might populate it.

## Further atomic functions and evidence limits

| Function | Observation |
| --- | --- |
| C disk `5E49–5E5A` | Preserve HL, read next class through `8AC6`, increment the pointer, update `8AC0` only for a nonzero class. |
| C disk `5CDA–5CEB` | Load DMA destination ports `25/24/23` from the three bytes at `8002/8001/8000`. |
| C disk `5D20–5D2E` | Write header end pointer `03:7FF0` to `8003–8005`, then call vector `006C`. No program-list interpretation. |
| A/B fixed `62E5–62EF` | Set or clear `R68.bit0` according to status bit 0. The internal `8x` dispatch is a mode switch here, not a generic MIDI note-off handler. |

## Validation and reproduction

Run `D20TraceSavedInitialState.java` on the mapped C copy and the expanded
`D20TraceABProgramDispatch.java` on the A/B copy, both with `-noanalysis
-readOnly` and a local evidence output path. Both scripts verify source hashes;
the C script creates its disk overlay transiently if missing. No owned ROM,
native file, generated listing or specimen-derived event data is committed.

Public generated fixtures cover both containers, absent/mismatched tags,
seven-bit boundaries, corrupt recognized payloads, inspection output and MIDI
metadata. The export regression checks every non-meta MIDI message and tick
against the previous behavior, and verifies that no program/CC events are
invented. Optional private tests confirm `0,7,7,99` in the local pair. Both real
full exports retain the same five tracks, note messages and duration as the
previously auditioned files; inputs remain unchanged.

The next initial-program evidence must come from locating persisted part
references or program events and closing their load/replay path. A stored
library and this four-parameter setup snapshot are insufficient to infer an
eight-part performance setup.
