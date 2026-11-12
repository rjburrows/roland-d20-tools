# SONG command and edit-path audit

This completes the next bounded pass after the [input-producer checkpoint](song-input-producers.md):
all entries in the normal-view input dispatch tables are inventoried, and all
nine direct calls to serializer `6FDC` in normal C ROM are accounted for.
The pass finds no additional stored musical event family that warrants a
decoder change. This is a static reachability result, not proof of every
possible file, bank state or indirect execution path.

C 1.11 SHA-256:
`7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`.
All addresses below are normal `C8/18/18` CPU addresses. The executed
`D20TraceSongCommands.java` verifies both the owned reference hash and equality
of the mapped normal half before decoding table targets. It exports tables,
bounded instruction listings, decoded writer calls, and raw operands separately.

## Command states: actual dispatch, not MIDI pressure

ASCI1 `14CE` maps `D0..DF` to states `0E..1D`. The next byte is dispatched
through table `1260`, not through a generic MIDI pressure writer.

| Input status | State | Handler | Confirmed behavior |
| --- | --- | --- | --- |
| `D0` | `0E` | `14EA` | If `8820.bit0` is clear, store B at `886C`. |
| `D1` | `0F` | `14F5` | Same gate; store B at `886D`. |
| `D2` | `10` | `1500` | Same gate; store B at `886E`. |
| `D3` | `11` | `150B` | Update `886F`; a recording-state branch combines input bits `70` with existing bits `06`. |
| `D4` | `12` | `14E5` | Store B at `886B`. |
| `D5..D8` | `13..16` | `12AE` | Reset ASCI1 parser state and return. |
| `D9` | `17` | `1528` | Clear remaining-data count; either store B with bit 7 set at `8861`, or call the active callback at `88B8` with A=B. |
| `DA..DC` | `18..1A` | `12AE` | Reset parser state and return. |
| `DD` | `1B` | `154B` | Set `8826.bit2`, then enter program handler `2D36`. |
| `DE` | `1C` | `153F` | Clear `8826.bit2`, then enter `2D36`. |
| `DF` | `1D` | `1557` | For B=`1E`, jump to `07E4`; otherwise use callback pointer `8828`. |

These are command operations on the processor link. In particular, the fact
that `Dx` has a following byte does not establish stored channel pressure.
`DD/DE` feed the already identified program path, rather than define another
native musical record. UI meanings of `886B..886F` remain unassigned.

The full 39-entry data-state table (`1260`, states `00..26`) groups as follows:

| State(s) | Handler(s) | Role established by instructions |
| --- | --- | --- |
| `00`, `13..16`, `18..1A` | `12AE` | Reset ASCI1 parser. |
| `01`, `03`, `05`, `08`, `09`, `0B`, `0D`, `24..26` | `172E` | Byte assembly/completion, with state-specific branches before recording. Not every completion calls the recorder. |
| `02` | `13C0` | CC-number classification; routes modulation, sustain, pan, volume and channel-mode cases through distinct states/gates. |
| `04` | `0DE1` | Clears the ASCI0 state byte `8814`; retain this cross-parser target as observed, without inventing a purpose. |
| `06`, `21..23` | `1594`, `15AF`, `15B9`, `15D4` | Forwarded or addressed memory-transfer setup and byte writes. |
| `07`, `0A` | `1692`, `16B7` | Select display/status destination, append received bytes via `884D`. |
| `0C` | `186E` | Channel-mode state and gated completion. |
| `0E..12`, `17`, `1B..1D` | Table above | `Dx` command callbacks and state updates. |
| `1E`, `1F` | `12C1`, `12CB` | Special `8x`-derived command handlers. Their broader protocol roles remain open. |
| `20` | `1729` | Forward B through output byte helper `431C`. |

## System handling is separate from stored events

The ASCI1 system table at `1240` has 16 entries, indexed by the low status
nibble. `F0` selects `158B`; `F1/F2` reset through `12AE`; `F3/F4` start
three-byte protocol packets (`15DD/163D`); `F5` finishes a display/status
transfer (`16C0`); `F6` starts one (`1689`); `F7` ends forwarding or a memory
transfer (`16E5`). `F8`, `FB`, `FD..FF` return through `12B2`; `F9`, `FA`,
and `FC` select `1712`, `1715`, and `1718` respectively.

`172E` intercepts completed states `08` and `24` for `15EB` and `164D`
before its general recording branch. Those paths update addressed sequencer
RAM/status and transfer pointers. They do not declare additional native MIDI
record formats. Transfer data can populate device memory; that is different
from storing the protocol status itself as a timed event.

For ASCI0, `F0` starts a header filter: subsequent bytes must match `41`, a
value below `20`, and `16` (`0EE8/0EF6/0F04`). On success, `0F04` flushes the
staged header via `107C` and forwards the matching byte through `1006`; state
9 then forwards bytes until `F7`. This path is a processor-link forwarding
path, not an identified Song SysEx stream. Realtime handlers at `0F25` onward
perform transport/clock work independently. The exporter must continue
rejecting unsupported `Fx` records rather than reinterpret native `FF`
interval boundaries as MIDI reset events.

## Callbacks and tempo: what is, and is not, established

Observed immediate installs of parameter callback `88B8` select:

| Target | Confirmed effect | Consequence |
| --- | --- | --- |
| `1ADF` | Return. | Disabled callback. The `4001–400F` reset block loads DE=`1ADF` and writes it to three callback pointers. |
| `418A` | Scale seven-bit input through `4561` with B=`6A`, then `41A1` checks `B4B0.bit0`, stores A in `B4D0`, programs timer ports `0E/0F` using table `43B6`. | Runtime tempo update; matches the saved-header tempo source already mapped. No timed tempo-event write is identified here. |
| `3524` | Scale seven-bit input with B=2; update mode/output/display state via `42F4`, `4706`, `4D19`. | Mode callback; no new musical record at this entry. |
| `3493` | Scale seven-bit input with B=8, update `8860` and display buffer. | Parameter/UI callback; musical label remains provisional. |

The `8828` callback has observed targets `027C`, `0846`, `1ADF`, `1C17`,
`20D2`, `209A`, `2063`, `2040`, `3DF0`, `423D`. They include startup
acknowledgment, no-op and UI state transitions. `027C` clears `885C` only for
A=`1F`; `0846` and `1ADF` return. Some UI handlers call other installed
callbacks, so this inventory does not prove every indirect path terminates or
cannot affect recording. It closes the immediate dispatch destinations, not
the entire UI state machine. No decoder extension is justified by these
pointers alone.

The current exporter still uses the saved initial tempo. This audit neither
finds a timed tempo-change encoding nor proves that no other firmware path
can persist one. A controlled recording remains the useful test.

## Every normal-view direct serializer call

| Call site(s) | Source path | Representation reaching `6FDC` |
| --- | --- | --- |
| `6920` | Recording helper `68DD` | Staged status/data, subject to headroom and recording-state gates. |
| `6D61` | Decoded-event copy `6D55` | Copies `B439..B43B` into writer fields. It preserves decoded data; it is not a family validator. |
| `70CB` | Index/interval helper `70B1` | Append current 24-bit pointer to index and write `FF` delimiter. |
| `7B6D` | Position-list reconstruction `7B55` | Index entry and `FF` delimiter. |
| `7BB3` | Current-position scratch list `7B90` | Position/status/data1/data2 repacked through the existing serializer. |
| `7BD9`, `7C03` | Scratch release/remainder flush `7BBD` | Status/data1 with zero data2, then full scratch events. |
| `7C2E` | Scratch triple flush `7C10` | Status/data1/data2 at the selected position. |
| `7E93` | Interval fill `7E80` | Index pointer and `FF` delimiter. |

All nine raw little-endian references to `6FDC` in the normal 32 KiB half
match these decoded CALL operands. The same comparison accounts for all nine
direct recording-helper `68DD` calls: `66E1`, `6701`, `676C`, `6817`, `6830`,
`6885`, `68D7`, `7533`, `758B`. This excludes alternate-bank and indirect
entries; it is deliberately not a whole-firmware completeness claim.

## Scratch producers and further atomic functions

| Address | Instruction-supported mapping | Limits / dependencies |
| --- | --- | --- |
| `70B1–70CE` | Append 24-bit event pointer through `B408`, set status `FF`, call serializer. | Atomic interval/index writer. |
| `70CF–70EB` | Advance index pointer by three and 24-bit event pointer by one. | Atomic pointer advance, not a musical event. |
| `74F0–7536` | If sustain state is set for lane 8 or selected lane, construct `Bx,40,7F` and call `68DD`. | Sustain-on seed in the existing CC64 grammar. |
| `7537–758E` | If sustain state was set, clear it, construct `Bx,40,00`, call `68DD`. | Sustain-off seed. |
| `758F–75DB` | For an active lane sustain bit, construct CC64 zero through the internal/remapped output queue and call `7294`. | Output cleanup, not a direct storage write. |
| `75DC–75E8` | Clear `B4B8` and lane-8 sustain bit `B4B9.bit0`. | Atomic sustain-state reset. |
| `7EC0–7F5E` | Restore input/output pointers, reset status state, derive phase lengths from `B49D`, install scratch bases, mark each list `FE`, call `792E` and `6F40`. | Edit reconstruction setup. User-facing edit name not yet assigned. |
| `7A5C–7A8E` | Compare decoded position against phase boundaries; return zero or `FF`. | Atomic partition predicate, with caller-managed phase state. |
| `7A8F–7ABC` | Advance positions with `C0` wrap handling, increment phase modulo four. | Atomic phase advance; do not infer a new tempo unit. |
| `7ABD–7B54` | Choose phase lists and invoke `7B90/7BBD`; phase 3 also flushes delimiter/triple lists. | Scratch-list coordinator. Producers are the append helpers in the prior checkpoint. |
| `4561–4569` | Multiply A by B using `MLT`, shift the product left and return its high byte. For seven-bit A this implements `floor(A × B / 128)`. | Atomic parameter scaling, not clamping. B=`6A`, 8 and 2 produce tempo codes `0..105`, values `0..7`, and values `0..1` respectively. |
| `456A–4571` | Decrement A when `E.bit0` is clear, increment otherwise. | Atomic directional step; no bounds applied. |
| `4572–457B` | Compare A with C and then B+1; substitute B/C outside those comparisons, increment B during the test. | Atomic range-wrap helper for caller-supplied limits. |
| `459E–45A8` | Send `80` through `19D2`, clear `881E.bit6`, return. | Atomic processor-link prefix/state reset, not a stored note-off record. |
| `0C17–0C1D` | Preserve BC, run a 40-count `DJNZ` loop, restore BC, return. | Atomic delay helper, found during callback review. No elapsed-time estimate without CPU/wait-state evidence. |

`7EC0` installs these bases, closing the origin of the pointer-based edit
queues previously left open:

| Field | Scratch base | Producer / role |
| --- | --- | --- |
| `B41C` | `9A00` | `7D3F` appends note-on triples; `7C10` flushes them. |
| `B41E/B420/B422/B424` | `9E00/A000/A200/A400` | `7CC6/7D2B` choose and append note-off pairs. |
| `B426/B428` | `A600/A800` | `7D6A/7D90/7DAE` append other position/status/data events. |
| `B42A` | `B42C` | `7CB8` appends delimiter markers; `7B55` rebuilds intervals. |

Scratch `FE` sentinels and fixed-width queue entries are internal structures.
They must not be substituted for native variable-width Song records.

## Validation and export decision

```sh
analyzeHeadless /tmp/ghidra-projects RolandD20-Control \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceSongCommands.java /tmp/song-commands.txt
```

The final script compiled and executed successfully in Ghidra 12.2, with
read-only analysis discarded. Source ROMs, private native inputs and generated
listings remain outside git. No runtime code changes require new unit tests.
Existing malformed/unsupported-family tests continue to define exporter limits.

The supported normal musical paths remain notes (`8x/9x`), controllers (`Bx`),
programs (`Cx`) and pitch bend (`Ex`). This pass does not establish an additional
stored pressure, SysEx or timed-tempo grammar. The next priority is a controlled
native recording covering those supported events; original routing and any
tempo-change persistence remain explicit BETA validation gaps.
