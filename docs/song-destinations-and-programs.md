# Song destinations and D-20 program selection

This extends the [routing checkpoint](song-routing-checkpoint.md). Evidence is
from executed Ghidra 12.2 scripts, the owned C 1.11 and interleaved A/B 1.12
images, the installed Ghidra Z180 processor definition, and the D-20 Service
Notes schematics printed pp.17 and 19. Export behavior is unchanged.

## Output destinations now identified

| Routing choice | C firmware queue path | Transmitter | Board destination |
| --- | --- | --- | --- |
| Lane flag bit 6 clear | `69EA` maps lane through `B448`; `7294` writes `8844`; `4932/4955` drain into `8834`; `431C` also appends to this final buffer. | `08AD–08E7` consumes via `8836` and writes port `06` at `08C9`. | ASCI0/TXA0, external MIDI OUT. |
| Lane flag bit 6 set | `69EA` is bypassed; `7294` writes `8848`; `49BB/49F5` drain into `883D`; `19D2` also appends to this final buffer. | `0935–0970` consumes via `883F` and writes port `07` at `0951`. | ASCI1/TXA1, main-board processor link. |

The installed `Ghidra/Processors/Z80/data/languages/z180.pspec` names I/O
`0006` as `TDR0` and `0007` as `TDR1`. This independently identifies the
transmit registers used by the instruction listings.

On printed p.17, CPU IC7 TXA0 pin 45 reaches CN1 pin 2, while TXA1 pin 48
reaches CN1 pin 5. On printed p.19, main-board CN1 pin 2 reaches the MIDI OUT
driver (IC17 and the output resistors), and CN1 pin 5 reaches main CPU IC16
P2.5 pin 39. CN1 pin 6 is the reverse link from P2.6 to RXA1. The connector's
MIDI IN/OUT labels differ between the two board drawings: follow pin numbers
and the actual wires, not the label alone. MIDI input is also wired to both
processors; do not assume every A/B MIDI parser is the CPU-link receiver.

**Confirmed consequence:** bit 6 selects an internal-part route versus an
external MIDI route. It is not merely a choice of output channel number.
Both validation files have bit 6 set in every lane flag. Conditional on the
previously traced playback mode and header-load path, these are internal-part
events. Copying their low nibble into a MIDI channel remains an export policy.
The external route requires the runtime channel table, whose complete saved
source has not been established.

Both transmitters implement running-status compression: repeated channel
status bytes are skipped; system-common statuses clear the remembered status;
realtime bytes are sent without replacing it. An empty queue disables the
corresponding transmit interrupt through status port `04` or `05`.

## What the C-side program handler really does

`C:2D4E–2D58` checks `8824.bit0`, stores the program byte in `8879`, copies it
to B and jumps to `2D44`. That writes a prefix to the display buffer `8990`
and calls `45B2`. `45B2–45EC` writes characters including `I`/`C`, `-`,
`A`/`B`, and formatted panel digits. This is **program-label display work**,
not the sound-record loader. The adjacent `2D36` path also stages program
status/data at `B484`; do not conflate its entry with `2D4E`.

`6D65` can still forward the actual program event through the selected output
queue. Its mode gates and the A/B receiver must be followed separately from
the display update.

## A/B event dispatch and instrument records

A/B addresses below distinguish fixed addresses from the bank-2 window. The
script also creates a separately named **candidate** bank-3 overlay, mapping
file `C000–FFFF` to CPU `8000–BFFF`; this is not a universal flat CPU view.
Bank writes and matching entry vectors support the candidate, but the gate
array has not been independently simulated. No conclusions below rely on
calling a bank-3 candidate routine the program loader.

| Address / state | Instruction evidence | Meaning and limits |
| --- | --- | --- |
| Fixed `1D94–1E82` | Reads/writes `SBUF`; RX appends through `RW9A`, TX consumes through `RW8C`; maintains running status. | Main-CPU hardware UART service, physically associated with the DIN wiring. This is not proof of CPU-link reception. |
| Bank 2 `83FB` onward | Consumes bytes through `RW98`; assembles data under running status `RA5`. At `855E–8569`, `status & E0 == C0` selects one-data-byte completion. | UART MIDI parser. Further checks distinguish channel modes and status families. |
| Bank 2 `86E6–871B` | Uses state-indexed enable table `871D`; on the allowed path combines program data with a stored high bit and calls `55FA`. Success calls `2A97`; another result queues a `C0` triple with zero data through `5ACE`. | Patch-selection branch of the UART parser. Not a universal per-part program handler. |
| Fixed `55FA–5600` | Calls `3F27`, then `5FEF` to restore bank 2. | Patch-load wrapper. |
| Fixed `3F27–3F73` | Selects bank `21`, writes current index to `C9BC/BFB0`, reads from `8400 + 38*index`, masks each byte to seven bits, and scatters 38 bytes through destination table `419C`. | Internal Patch record load. The 38-byte stride corroborates the implemented `07H` / native Sound Patch layout. |
| Fixed `3F74–4000` | High-bit alternative checks card state and reads bank `30/31` headers/pointers before joining the scatter loop. | Separate card/source branch; do not treat a high-bit index as another internal Patch number. |
| Fixed `6132–6263` | Dequeues three-byte events with `61AC/61B5`; dispatches through `6264`. One branch matches `CA0C + part_stride` receive-channel entries; another derives a part stride from status low nibble, rejecting values 9 and above. | Shared event consumer with channel-based and part-index-based branches. The complete producer path for CPU-link events remains to be closed. |
| Table `6264` | `8x→62E5`, `9x→63DE`, `Ax→63D6`, `Bx→7E87`, `Cx→6319`, `Dx→2188`, `Ex→62F0`, `Fx→629C`; `6262` branches through the selected address. | Confirms a distinct program-change handler. `Dx` also participates in proprietary command dispatch; this is not an instruction to export every internal command as MIDI channel pressure. |
| Fixed `6319–635C` | Rejects bit-7-set part strides. `R68.bit3=1` calls `4002` and `5A11`; the alternative passes `R46` with a source flag into `4013`, then updates status/UI fields. | Mode-dependent program application. `R68.bit3` is refreshed from `C9AB.bit0` in the consumer. An internal C0 event does not always call the global Patch loader. |
| Fixed `4002–4012` | Calls `3F18` and `3B9C` for part strides `00` and `10`. | Two-part refresh. This routine itself does not select a 38-byte Patch by its event data. |
| Fixed `4013–4061` | With the ordinary internal-source branch, selects bank `21`; stores the per-part program reference; copies eight bytes from `8000 + 8*program` to `C000 + part_stride`, masking to seven bits; calls `3F18` and `3B9C`. | Per-part Timbre load. Eight-byte stride agrees with `05H` / native Sound Timbres. Further tone application occurs in `3B9C`. |
| Fixed `4062–407B`, `407D–40FA` | Additional state selects bank `28`, base `9000`, masked index, or a card header/pointer path. | Distinct factory/card sources, not a reason to use the internal Timbre formula on every branch. |

Thus a D-20 program number can select a Patch or a per-part Timbre, depending
on mode and source. It is not automatically a General MIDI instrument number.
The existing Sound-file tables make the record formats available, but do not
prove which initial program reference a particular standalone Song saved.

## Additional atomic functions discovered

These are recorded even where not needed for current MIDI output.

| Function | Instruction-supported operation |
| --- | --- |
| C `431C–4334` | Append one byte to the ASCI0 final transmit ring; enable its transmit interrupt. |
| C `19D2–19DE` | Append one byte via `4A88` to the ASCI1 final ring; enable its transmit interrupt. |
| C `08AD–08E7`, `0935–0970` | Parallel ring consumers with running-status suppression, system-status handling and empty-ring interrupt shutdown. |
| A/B `5FEF–5FF7` | Write constant program bank `02` through shadow `R69` and external register `0100`. |
| A/B `5A51–5A5A` | Nested decrement delay using `R21=2D` and input R20. No wall-clock duration inferred. |
| A/B `5ACE–5AEE` | Enqueue status/data triple into `FA00` ring via `RW3E`, wrap at `FBFE`, invoke overflow helper when write catches read. |
| A/B `61AC–61D8` | Return zero if read/write pointers match; otherwise dequeue three bytes, update sign-derived flags and wrap the read pointer. |
| A/B `5A5B–5A9E` | Wait for UART ring capacity, enqueue status and one/two data bytes, commit write pointer and request TX service. The width test groups `Cx/Dx` together. |
| A/B `3F18–3F26` | Zero-extend part byte `C004 + stride`, multiply by `02AB`, store word at `CA00 + stride`. Musical scaling interpretation remains to be checked against callers. |
| A/B `2A97–2AAE`, `5F34–5F4A` | Use a pointer table indexed by twice the decremented input, then copy up to 32 bytes; on the first high-bit source byte, fill the remaining destination with spaces. Label/name-copy path; table bank context remains caller-qualified. |
| Candidate bank 3 `83B3–83D3` | Enqueue one byte through `RW8E` with masked wrap; retry on full ring; request service using `RA2/INT_PEND`. Candidate overlay qualification applies. |

## Reproduction and remaining limits

Run the expanded `D20TraceSongRouting.java` on the mapped C research copy,
and `D20TraceABProgramDispatch.java` on the interleaved A/B research copy:

```sh
analyzeHeadless /path/to/projects RoutingTrace \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceSongRouting.java /tmp/d20-song-destinations-evidence.txt
analyzeHeadless /path/to/projects ABPatternTrace \
  -process AB-interleaved-1.12.bin -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceABProgramDispatch.java /tmp/d20-ab-program-evidence.txt
```

Both scripts verify source hashes and export instruction bytes. The A/B script
also exports the dispatch table and 38 scatter destinations. Raw opcode
search hits remain explicitly unclassified. Candidate-bank listings and
nearby instructions are not automatically new confirmed functions. Analysis
changes are discarded on exit; source ROMs and native inputs are unchanged.

The two queue endpoints and the two ordinary record-loader strides are now
established. Remaining work is to close CPU-link reception into the event
consumer, identify which initial part/program/routing state is persisted by
each native file type, and test mode changes with independent saves. The
card branches, later tone application, and every CC handler are not fully
reconstructed. No new channels, GM programs, volume or pan are invented for
the validated exporter in this research-only change.
