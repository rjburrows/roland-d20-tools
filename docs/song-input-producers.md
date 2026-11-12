# SONG input producers and edit queues

This extends the [recording admission checkpoint](song-record-admission.md).
It closes the source of `B47E–B480` and identifies the two staged controller
records. It adds evidence and function mappings, with no decoder changes.

Evidence: executed Ghidra 12.2 `D20TraceSongInputs.java`, C 1.11 normal
`C8/18/18`, SHA-256
`7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`.
The trace verifies the reference hash and exports bounded instructions,
channel-dispatch tables and separately labelled raw operand candidates.

## Receive source and recording path

| Receive path | Producer and consumer | Parser and recorder |
| --- | --- | --- |
| ASCI0 | Interrupt `0870`, read port `08` at `0883`; ring producer `8830`, consumer `8832`; `0568` returns next byte in B/carry. | `0542–054A` calls `0D20`; accepted messages assemble at `8810`. Conditional `105A–1065` copies three bytes to `B47E` and calls `65C0`. |
| ASCI1 | Interrupt `0904`, read port `09` at `0917`; ring producer `8839`, consumer `883B`; `0578` returns next byte in B/carry. | `054C–0553` calls `11DB`; accepted messages assemble at `8817`. Conditional `17B2–17BD` copies three bytes to `B47E` and calls `65C0`. |

Installed Ghidra `z180.pspec` independently names I/O `08/09` as `RDR0/RDR1`.
The [destination/schematic checkpoint](song-destinations-and-programs.md)
identifies ASCI0 as the DIN communication path and ASCI1 as the processor-link
path using Service Notes pp.17/19. The ASCI1 receive code is therefore a
separate protocol parser, not automatically a second Standard MIDI parser.
Neither static receive availability nor a three-byte copy proves recording:
the mode/lane gates in `65C0/665B/66E5` still apply.

ASCI0 discards realtime bytes at the interrupt when `B4B0.bit0` is clear.
ASCI1 discards `F8` before queueing. These are receive policies, not saved
Song events. Error/overflow branches reset their parser state and ring indices.

## Why pressure cannot be added from a status-nibble guess

`0D20` distinguishes data, channel status, system status and realtime status.
For channel messages, table `0DB9` is indexed by the high nibble. `11DB` uses
its own channel table `1232`; its system table is separate.

| Family | ASCI0 table `0DB9` | ASCI1 table `1232` | Consequence |
| --- | --- | --- | --- |
| `8x` | `0DE6` | `12B3` | Different parser states. ASCI0 completion converts note-off to `9x` with zero velocity at `10A2`. |
| `9x` | `0DF4` | `137C` | Note-state and recording gates apply. |
| `Ax` | `0DE1` | `138F` | ASCI0 clears parser state (drop). ASCI1 selects state `0D`; completion calls `1893`, rewriting status to `9x`, then `189B` note-state handling. This is not preserved polyphonic pressure. |
| `Bx` | `0E02` | `13A4` | Controller assembly, with subsequent mode/channel/CC filters. |
| `Cx` | `0E9E` | `14B1` | Two-byte total message assembly; acceptance can depend on `881E/881F` flags. |
| `Dx` | `0DE1` | `14CE` | ASCI0 drops it. ASCI1 derives parser state as `0E + low_nibble` and expects one subsequent byte: a command selector, not a demonstrated recorded channel-pressure value. |
| `Ex` | `0EBC` | `1565` | Three-byte total message assembly; bend enable/mode flags remain relevant. |

At `0DE1–0DE5`, A is cleared and stored in `8814`, disabling subsequent
running-data assembly. `Fx` does not enter that channel table from `0D20`:
`0D71` separately handles `F0/F7`; `0D7B` separately handles realtime bytes.
The table's eighth word must not be used to claim every `Fx` message is dropped.
System handlers perform protocol/transport work; this trace does not identify
a native SysEx or pressure record grammar.

`1893–189A` sets status bit 4 and clears bit 5 at `8817`; for `Ax` this yields
`9x`. `189B` uses the two data bytes as note-state inputs, with zero/nonzero
third-byte handling, before `172E` can copy to the recorder. Applying Standard
MIDI pressure semantics before that transformation would misidentify events.
These findings support keeping `Ax`, `Dx` and `Fx` unsupported in export; they
do not prove impossibility for every edit path, firmware version or file.

## Confirmed staged programs and controllers

`44C8–4523` constructs a `Cx` status and seven-bit program from `8879`.
Depending on recording flags, it writes the status/data word at `B47E` and
calls `65C0`, or stages it at `B484`. This closes a producer of the program
seed traced at `6732/6770`. It is not a saved eight-part program array.

`144E–14B0` builds `B0,0A,value` at `B486–B488` unless selector `8818` equals
7; that alternative builds `B0,07,value` at `B489–B48B`. Value comes from
`8819`. The existing `6801` helper forces lane 8 on these nonempty stages
before recording. These are pan and volume controller seeds; they are separate
from native header reverb/rhythm-level metadata. Other references clearing the
stages are not additional musical event definitions.

## Atomic helpers and edit/copy mappings

| Address | Confirmed operation | Dependencies / limits |
| --- | --- | --- |
| `0568–0577`, `0578–0587` | Read one ring byte to B; advance low-byte consumer; set carry. Empty ring returns with carry clear. | ASCI0 and ASCI1 respectively. |
| `08E8–0902`, `0970–0992` | Drain receive byte when entered on that error branch, clear selected control bits, reset parser/ring state, set notification bits at `8A6E`. | Distinct error/overflow entry points; exact physical error causes depend on hardware flags. |
| `1006–101D` | Wait for processor-link TX ring space, append B, enable ASCI1 TX interrupt. | Atomic byte enqueue; wait time unresolved. |
| `101E–1043` | Append B to `8810`, decrement remaining count, dispatch completed parser state. | Recording through `1045` is conditional, not automatic. |
| `10DF–111C` | Map channel through `8700`, index note bitmap under `8710`, set/clear bit according to velocity. | Uses bit-mask table `111D`; state maintenance, not pressure conversion. |
| `1151–1180`, `1181–11A7`, `11A8–11BF` | Under recording gates, clear status bit 5, set velocity zero, scan bitmap, build note number and call `65C0` for each active bit. | Release-generation setup, scan and per-bit callback. No new native family. |
| `1893–189A` | Set bit 4 and clear bit 5 of status at `8817`. | Atomic status normalization; `Ax → 9x` on the traced completion path. |
| `189B–18CA` | Update note presence and packed lane state for nonzero data; zero data clears only a present bit and returns carry for accepted changes. | Calls `18CB` and `18E9`; unmatched zero-data return can stop recording. |
| `18CB–18E8` | Derive bitmap byte from note `8818 >> 3` under `87A0`, return mask from `111D`. | Atomic note bit-address helper. |
| `18E9–18FA` | Derive packed lane byte under `87B0` from `8818 >> 1`; return note parity in carry. | Atomic nibble-address helper. |
| `18FB–1911`, `1912–1918`, `1919–1926`, `1927–1979` | Scan active-note bitmap, issue a conditional `D8,4E` pair through `42F4`, enumerate set bits, clear each and construct zero-velocity note messages for output through `431C/19D2`. | Cleanup scan, command helper, byte scan and per-note release. Not a general SysEx exporter. |
| `197A–199A` | Reinitialize ASCI1 running-data counters; states 9/26 become 2 before indirect data dispatch at `1220`. | Atomic parser restart helper, distinct from native `FF` reset. |
| `7B55–7B79` | Iterate position list until `FE`, set stored status `FF`, call `7B7A` and serializer, then reset list marker. | Interval/index reconstruction path. `FE` is a scratch-list sentinel, not a new native delimiter. |
| `7B7A–7B8F` | Append 24-bit `B4DB:DD` at index pointer `B408`, advance pointer by three. | Atomic event-index pointer writer. |
| `7B90–7BBC` | Consume `[position,status,data1,data2]` scratch entries matching `B4A3`, serialize, retain advanced source pointer. | No new event-family conversion locally. Source construction still matters. |
| `7BBD–7C0F` | Serialize `[status,data1]` entries with zero data2 at current position, then serialize remaining four-byte scratch entries; use `FE` list markers. | Note releases can normalize to native `8x`; not a native two-byte grammar for every status. |
| `7C10–7C39` | Serialize `[status,data1,data2]` scratch entries from `9A00` at current position, reset `FE` marker. | Repacking scratch triples, not validating new native types. |
| `7C3A–7C79` | Advance decoded stream with `6EAC`, stage earlier events through `7C7A`, set boundary phase/position state. | Edit partition path; UI operation name remains provisional. |
| `7C7A–7CB7` | Dispatch delimiter to `7CB8`; selected nonzero-velocity `9x` to `7D3F`; selected zero-velocity `9x` to `7CC6`; others to `7D6A`. | Per-lane mask `AB00` and `B4A1` select specialized note handling. |
| `7CB8–7CC5` | Append `FF` then `FE`, update `B42A`. | Atomic scratch delimiter append. |
| `7CC6–7D2A`, `7D2B–7D3E` | Pick one of four lists using note phase `(AA00[note] + B49C) & 3`; append status/data1 plus `FE`. | Note-off partition selector and atomic pair append. |
| `7D3F–7D69` | Append status/data1/data2 plus `FE`; set note phase at `AA00 + note` to `3-B49C`. | Atomic note-on staging and phase update. |
| `7D6A–7D8F`, `7D90–7DAD`, `7DAE–7DCB` | Select alternating phase list; append position/status/data1/data2 plus `FE`. | Phase selector and two atomic four-byte append helpers. These scratch fields are not native record sizes. |
| `7E38–7E7F`, `7DCC–7E37` | Transfer/inspect ten trailing bytes for all-`FF`; set/clear `B4B4.bit6`; conditional backward one-byte transfer scan updates `B475:477`. | Tail-padding probe and scan. Bounds depend on caller/data; no dynamic termination guarantee. |
| `7E80–7EA0` | Compute length to `03:7FF0`, repeatedly write index pointer and an `FF` serializer event, decrement remaining count. | Interval fill helper. Not a MIDI reset-event writer. |

## Validation and remaining branches

Run on the mapped research copy:

```sh
analyzeHeadless /tmp/ghidra-projects RolandD20-Control \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceSongInputs.java /tmp/song-inputs.txt
```

The hash-checked script compiled and executed read-only; changes to analysis
were discarded. Original ROM/native bytes and generated evidence stay local.
Documentation-only changes require no new runtime tests; the unsupported
pressure/system regression cases remain in the suite.

Still unresolved: the complete ASCI1 command and data-handler tables, all UI
labels for recording flags, and every producer of edit scratch queues. The
next useful step is a systematic inventory of the ASCI1 command states and
remaining direct serializer callers, followed by native capture validation.
