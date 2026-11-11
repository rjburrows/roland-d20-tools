# Song routing: executed C ROM checkpoint

The later [destination and program trace](song-destinations-and-programs.md)
resolves the two queue endpoints and identifies Patch/Timbre loaders. Endpoint
uncertainties below describe this earlier checkpoint; runtime/save-state
limitations remain.

This records static instruction evidence from C 1.11, SHA-256
`7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`.
Addresses are CPU addresses in normal `C8/18/18`. No exporter routing or
controller behavior changes are included in this checkpoint.

## Confirmed control flow

`6F6A–6FDB` decodes position to `B436`, status to `B439`, and data to
`B43A/B43B`. The state-gated scheduler `6A81–6B50` can send the result to
record/copy helper `6D55` or output handler `6D65`. These are different paths.

On the `B4B0.bit4=0` branch, `6D77` copies status to `B49A` and `AB0B`.
On the other branch, `6E2F`, `6E51` and `6E88` additionally process programs,
controllers and lane 8. The event bytes alone do not select the mode branch.

The common output path `6DC5–6DF8` saves the original low nibble, calls `6E19`
to conditionally adjust lane 7 to lane 8, and tests bit 6 of
`B4D1 + original_lane` through `5A9F`. If set, it sets `B4B1.bit5` and copies
the adjusted status to `B47B`. Otherwise it clears `B4B1.bit5`, calls `69EA`
on the adjusted status and stores the mapped result in `B47B`. It copies
event data to `B47C/B47D`, then calls `7294`. Another state branch can first
send a special status through the same dispatcher.

`69EA` computes `(status & F0) | (B448[status & 0F] & 0F)`, preserving BC/DE.
The stored low nibble therefore is not universally the transmitted channel.

`7294` writes to queue `8848` when `B4B1.bit5=1`, or `8844` otherwise.
It writes status plus one data byte for `Cx`, two for ordinary channel
messages, and only status on its special `Fx` path. It calls `7324` for
note-state filtering and `72DD` for space checks. `4932` drains the
`8844/8846` queue; `49BB` drains `8848/884A` into another downstream buffer.
The external-MIDI versus internal-generator endpoint assignment remains open.

## Active channels and saved flags

| State | Confirmed instructions | Limit |
| --- | --- | --- |
| `B448–B450` | `780A–7834` initializes nine active entries to `00,01,02,03,04,05,06,07,09`. | Runtime defaults, not saved-channel proof. This table is below the traced song-data destination `B4BA`. |
| `12E1–1303` | Selector `8818` below 9 writes input B into `B448 + selector`, then calls `1B43`. | Proves the active table can change. Command framing and source remain unresolved. |
| `1B6E–1B8A` | Walks nine entries; skips bit-5-set entries; writes reverse part indices at `8700 + channel`. | Channel-to-part dispatch, not a disk offset. |
| `B4CF.bit0` | Selects active entry 8 instead of 7 for the eighth stored lane in `6E19`, `4533` and `69AC`. | Native SONG/ALL byte `35` under the traced contiguous header transfer. Other bits remain open. |
| `B4D1–B4D8` | Eight lane flags. Bit 6 chooses bypass/remap in `5A9F`; bit 7 is tested by `6A02` and `3565`. | Native bytes `37–3E` under that transfer. These are flags, not channel numbers. Musical mute/record labels still need mode/UI evidence. |

Both local validation containers have `byte35=01` and flags
`70 70 40 40 40 40 40 60`. All eight flags have bit 6 set. If these values
reach the traced playback branch unchanged, they select the bypass queue and
adjust lane 7 to 8. This is a **conditional prediction**, not a hardware
capture. Listening validation does not resolve these mode-dependent details.
The exporter continues using its documented provisional stored-lane channels.

The existing `10H` System report contains stored channel fields. This trace
does not prove they are interchangeable with the active `B448` table.

## Function inventory

| Address | Instruction-supported function | Dependency / unresolved behavior |
| --- | --- | --- |
| `69AC–69E9` | Inverse matcher: search first seven active entries, then entry 7 or 8 according to `B4CF.bit0`; return lane status with carry on success, zero/no carry otherwise. | Called at `66E8`. Separate from output mapper `69EA`. |
| `69EA–6A01` | Replace low status nibble through active channel table. | Input bounds rely on callers. |
| `5A9F–5AB1` | Return bit 6 of the indexed lane flags in carry; preserve BC/HL. | Selects output queue/remapping. |
| `6A02–6A16` | Return lane flag bit 7 in carry, restoring input status in A. | Scheduler state-gated. |
| `6E19–6E2E` | Increment status when low nibble is 7 and `B4CF.bit0=1`; preserve BC. | Also used by note/controller cleanup paths. |
| `4533–4548` | Return active channel entry, applying the same 7-to-8 selection. | Queue cleanup calls at `4A21`, `4A5B`. |
| `6705–6731` | Classifies masked high nibble: `90→1`, `C0→2`, `E0→3`, `B0→4`, otherwise `FF`. Also contains an `FF→5` comparison after `AND F0`, which cannot succeed for a byte input. | Recognizes note, program, pitch-bend and controller families; not proof of every disk record type. |
| `6E2F–6E50` | For `Cx` on selected lane or lane 8, pass data to `2D4E`. | Actual program/instrument selection still needs `2D4E` trace. |
| `6E51–6E87` | For `Bx` on selected lane or lane 8, controller 10 calls `48FF`, controller 7 calls `4915`. | Mode branch at `6D68`; does not identify initial saved pan/volume. |
| `48FF–4914`, `4915–492A` | State-gated parameter construction at `8960`/`8990`, prefixes `C8`/`CC`, tail-call `4883`/`4870`. | Proprietary downstream paths, not proven direct CC-to-GM conversion. |
| `6E88–6EAB` | Substitute `B490` for lane 8, otherwise preserve status; store at `B49A`/`AB0B`. | Only on `B4B0.bit4` branch. |
| `6D55–6D64` | Copy decoded event to `B481–B483` and call serializer `6FDC`. | Record/copy operation, not output. |
| `72DD–7323` | Check selected queue space for up to four bytes; service queues through `492B` while insufficient. | Atomic space helper; no dynamic blocking-time claim. |
| `74A5–74EF` | For CC64, compare value bit 6 with per-lane state `B4B8`, update changed state, return zero if unchanged; other events return `FF`. | Sustain-state deduplication helper. Caller `6DBE` can suppress repeated sustain messages. |

The service schematic printed p.19 places the A/B-programmed 8097BH and MIDI
DIN connections on the main board, with separate TXD/RXD and MIDI signals at
the CPU-board connector. Multiple hardware communication paths are consistent
with the code; the schematic alone does not assign the two software queues.
The [memory reference](memory-map.md) documents separately known System,
Timbre and Rhythm Setup fields. Those fields are not a General MIDI mapping.

## Reproduce and next unresolved branches

```sh
analyzeHeadless /path/to/projects RoutingTrace \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceSongRouting.java /tmp/d20-song-routing-evidence.txt
```

The script verifies the ROM hash, exports bytes and bounded instruction
listings, and inventories selected direct operands separately as possible
code/data. It compiled and executed in Ghidra 12.2 on a freshly mapped copy,
then ran again read-only. Generated listings and native inputs remain local.
No source ROM bytes changed. The original old scratch project had missing
metadata, so this trace used a separate fresh project rather than its database.

Next follow `2D4E` to instrument selection; trace both queues to transmitters;
trace the `12E1` writer's command source; resolve both `6D65` mode branches.
Only then change export channels or emit initial program/volume/pan events.
Additional native saves or a device MIDI capture can test the conditional
lane-7 prediction. No new hardware validation is claimed here.
