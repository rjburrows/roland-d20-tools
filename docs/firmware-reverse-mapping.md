# Roland D-20 firmware reverse mapping

The [recording admission checkpoint](song-record-admission.md) reconstructs
the mode/channel gates and staged program/note seeds, distinguishes recording
CC64 filtering from playback filtering, and maps further atomic helpers.

The [controller and pitch-bend checkpoint](song-controller-pitch.md) adds
ROM-backed `Bx`/`Ex` extraction and the atomic record-state/headroom helpers
`68DD`, `6924` and `6945`, with dependencies and unresolved branches.

The [program-change guide](song-program-changes.md) records matching reader,
recorder and output evidence for one-data-byte `Cx` records. Song/All export
now preserves those recorded references alongside notes. Initial programs are
not inferred when no program event exists.

The [saved initial-state trace](saved-initial-state.md) follows setup request
`D8 59` to the `88/89` reply, six-byte header capture and load-time replay.
Song/All MIDI and inspection now preserve the four confirmed setup values;
initial part program references remain unverified.

The [destination and program trace](song-destinations-and-programs.md) follows
both serial output queues through the board wiring and distinguishes the
38-byte Patch loader from the 8-byte per-part Timbre loader. Initial saved
program references and full CPU-link reception remain open.

The [song-routing checkpoint](song-routing-checkpoint.md) adds the executed
lane/channel mapper, its inverse, the two output queues, saved routing flags,
program/CC handlers and sustain-state helper. Output mode and peripheral
endpoints remain unresolved; the exporter still uses provisional lane channels.

This is the address and reproduction guide for the D-20 sequencer, rhythm editor, and floppy traces. The investigation used Ghidra 12.2 and owned ROM dumps. Addresses are hexadecimal unless stated otherwise. **Confirmed** means an instruction or table was observed in the identified ROM and bank view. **Correlated** means bytes in saved containers agree with the ROM layout. **Provisional** means the BETA exporter makes a choice that hardware playback has yet to establish.

## Set up the ROM views

| Image | Ghidra language | Address convention | SHA-256 |
| --- | --- | --- | --- |
| C 1.11, 64 KiB | `z180:LE:16:default` | Import as raw binary at zero. Treat the initial flat addresses as file offsets. | `7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2` |
| A/B 1.12, 32 KiB per chip | `MCS96:LE:16:default` | Interleave `B[0], A[0], B[1], A[1], …`. Import the resulting 64 KiB raw image at zero. | Interleaved `283cda5527d3b21cc39093cdcb0f982f0399466585b871b9fa77ac3ae855f2ca` |

The D-20 Service Notes identify A/B at mainboard IC14/IC13 and the 8097BH at mainboard IC16 (printed p.19). The CPU board has the C ROM at IC16 (pp.16–17). A/B addresses below refer to the interleaved image and must be interpreted separately from C CPU addresses. The paired-chip hashes, older A/B 1.00 relocation, and known byte-lane order are checked by the A/B probe.

1. Import C into a Ghidra project with auto-analysis disabled. Preserve that import and use **Save As** to create a program named `D20-C-1.11-banked-analysis`. Run `D20SetupRuntimeMap.java` on the copy. It verifies the ROM hash, keeps all 64 KiB in `ROM_FILE_REFERENCE`, maps CPU `0000–7FFF` as executable ROM, and marks `8000–FFFF` as uninitialized RAM in the normal `C8/18/18` view. The reference block is a file-offset view.
2. Run `D20TraceSongPlayback.java` and the bounded normal-bank exporters. Start at the reset vector `0080` and follow known call targets, CPU state, memory references, and DMA staging addresses. Keep a record of where each trace switches views. `3CF6` writes MMU `85/18/08` and `3D08` restores `C8/18/18` (CBAR/CBR/BBR).
3. Run `D20ProbeAlternateBanks.java` once on the research copy. It overlays file `A000–FFFF` at CPU `2000–7FFF` (`82/18/08`) and file `D000–FFFF` at CPU `5000–7FFF` (`85/18/08`). Upper ROM file `8000–9FFF` is fill. Seed the disk entry stubs and follow callback words at `615A`, then use the disk exporters. These static overlays model selected MMU states. Check the service schematic and compare reference bytes before interpreting an overlay as a hardware selection.
4. Import interleaved A/B into its own Ghidra program. Trace the startup copy and pointer table first. The slot selector leads to the editor reader and serializer, which establish the record grammar independently of any saved rhythm file. Compare controlled native files with the probes after tracing the instructions.

From the repository root, use Ghidra's script manager or the headless runner. Here `GHIDRA_HOME` is the Ghidra installation and `PROJECT_DIR` is the folder containing the prepared project.

```sh
"$GHIDRA_HOME/support/analyzeHeadless" "$PROJECT_DIR" D20Research \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20ExportSongPlaybackEvidence.java /tmp/d20-song-playback.txt

python3 research/ghidra/probe_ab_rom_patterns.py A.BIN B.BIN --rhythm RHYTHM.444
python3 research/ghidra/probe_pattern_records.py RHYTHM.444 --events-id 0x3f
python3 research/ghidra/probe_pattern_records.py SONG.222
python3 research/ghidra/probe_pattern_records.py BACKUP.111
```

To build the interleaved file for import, pass the two owned dumps to this command in A, B order. Run `D20TraceABPatternReader.java` on the resulting program with an output path as its argument.

```sh
python3 - A.BIN B.BIN AB-interleaved.bin <<'PY'
from pathlib import Path
import sys

a, b = (Path(name).read_bytes() for name in sys.argv[1:3])
assert len(a) == len(b) == 32768
rom = bytearray(65536)
rom[::2], rom[1::2] = b, a
with Path(sys.argv[3]).open('xb') as output:
    output.write(rom)
PY
```

## C 1.11 normal-bank function map

| Function / span | Confirmed instructions | Dependencies / callers | Confidence and open branch |
| --- | --- | --- | --- |
| `0x018C–0190` | Initializes `B4D0` to `0x28`. | Startup. | Confirmed RAM write; 120 BPM interpretation corroborated by `0x7690`. |
| `0x4191–41BD` | Bounds editable `B4D0` to `0..0x69`, reads a word from `0x43B6+2*code`, outputs timer reload to Z180 ports `0E/0F` when state permits. | Tempo UI, `B4B0` gate. | Confirmed; bank/UI entry path still not fully traced. |
| `0x4B7C–4BA0` | Consumes `B40A` position counter; on selected branch calls `6A81`, `6ED1`, `5E06`. | Main loop `4B25`; MIDI F8 route `0D86→0F25→4D3D→50E8→512F` adds 4 to `B40A`. | Confirmed instructions; state flags and alternate branch unresolved. |
| `0x4C86–4C9D` | If `B4B0` bit 0 is clear, increments `B497` and, on every fourth count, passes `F8` to `1DF0`. | Called from main playback loop `4B87`, before pattern length/chain routine `5E06`. | Confirmed **atomic F8 output scheduler** relative to `B497`; physical destination of `1DF0` and musical tick scale require trace. This routine does not access pattern note triples. |
| `0x5B13–5BB1` | Initializes current event pointer and chain pointer `B3FE` from `B4DE` or `B4E0` according to flags. | Calls `7199`, `5CE8`, `6021`, `5C0D`, `5BDC`. | Confirmed alternatives; exact user mode for each remains inferred. |
| `0x5E06–5EA0` | Reads pattern ID at `[B3FE]`; looks up `B6D5[id]`; selects duration word from `5EAA` (0, 96, ..., 768); on boundary advances chain and resets position `B3FC`, tests `FF` end. | Called from `4BA0`; calls `5F82`, `5FFA`, `5F54`, `5EF3`. | Confirmed chain timing. No drum-note data read in this routine. |
| `0x47F4–4823` | Reads the current rhythm chain ID via `4824`, renders `P-` plus two digits via `482F` for IDs below `0x40`, displays `P-**` for other non-`FF` IDs and `END` for `FF`. | Display path; `4824` reads `B4DE + (B402-1)`. | Confirmed pattern-ID **display renderer**; this supports the valid `00..3F` range but does not identify the block-note reader. |
| `0x4824–4840` | `4824` reads a pattern ID from the current chain slot. `482F` converts that ID to two ASCII digits: `(id >> 3 & 7)+1` and `(id & 7)+1`. IDs `3E/3F` thus render `P-87/P-88`. | Called from `47F4`; formatter also called from `45D8`. | Confirmed **atomic pattern-ID to displayed-number conversion**. The corresponding stored note block remains a sample-supported inference. |
| `0x5726–5773` | Sums `B6D5[id]` from `B4E0` to current chain pointer and computes an offset via `7717` and `5EAA`. | Playback navigation. | Confirmed arithmetic; semantics of returned `FF/00` conditional require caller trace. |
| `0x7654–76CC` | Sums pattern lengths until `FF`, multiplies by 60, converts `B4D0` using `40+2*value`, performs long division and stores derived time values at `B4A9–B4AB`. | Calls `76F5`, `772F`, `7717`. | Confirmed tempo arithmetic. The saved-header load path and timer reapplication are traced in the tempo checkpoint. |
| `0x7717–772E` | 16-step shift/subtract integer division. | Called at `5757`, `76A9`, `76B5` and others. | Confirmed **atomic arithmetic routine**, even though it does not read pattern notes. |
| `0x772F–7763` | Multi-byte shift/subtract division using `IX` buffer and `DE` divisor. | Called at `769D` and elsewhere. | Confirmed **atomic arithmetic routine**; output layout must be tracked at each caller. |
| `0x76F5–7716` | Z180 `MLT`-based multi-byte multiplication. | Called from `7680`, `55AB`. | Confirmed **atomic arithmetic routine**. |
| `0x6021–6056` | Converts current song/pattern count into display-oriented value `B406`; calls BCD helper `6001`. | `5FFA`, startup/navigation. | Confirmed counter formatting; does not fetch drum steps. |
| `0x6001–6020` | Repeated shift and decimal adjust into three bytes `AB08–AB0A`. | `6021`. | Confirmed **atomic binary-to-BCD style routine**; exact input/output range should be unit checked. |
| `0x295F–299D` | Builds display command at `8900` and calls UI helpers `477D`, `47F4`. | `5FFA`. | Confirmed display path; previously considered as a possible drum emitter and ruled out. |
| `0x6F6A–6FDB` | Reads stored sequencer note records with optional running status; `8x` offs converted to `9x` velocity zero. | Song event stream `6F40`; recording mirror `6FDC`. | Confirmed for note lanes; no evidence this is also the rhythm-pattern step reader. |
| `0x3CF6–3D07` | Writes `0x85,0x18,0x08` to Z180 MMU registers `3A/38/39`, with interrupts masked during the switch. | Startup and disk-related calls. | Confirmed **atomic bank switch** to an alternate C ROM view; interpreting targets requires bank context. |
| `0x3D08–3D19` | Writes `0xC8,0x18,0x18` to the same MMU registers with interrupts masked. | Normal-bank restoration. | Confirmed **atomic bank restore**. |
| `0x077B–0793` | Initializes 32 bytes starting at `B6D5` to `04`, then overrides `B6EC=03`, `B6F0=08`, `B6F1=08`. | Startup/default setting; read by `5E06`, `5726`. | Confirmed initializer. It sets only the lower half of the indexed table; `3E/3F` reach `B713/B714`. The test SONG stores `08/08` at the corresponding candidate offsets. |
| `0x15EB–163C` | On the `882A` flag branch, writes the edited byte `8818` to `B4E0 + (882A & 7FFF)` and calls `166C`. On the other branch, adds `8818` to base `B6D5` and writes `8819 + 1` to the indexed byte; IDs `>=50` take a separate low-nibble result path at `1636`. | Editor input state `8818/8819/882A`; `166C` gates an optional display call `299E`. | Confirmed **atomic per-ID duration updater** at `1622–1635`. This is an independent instruction-level explanation of the sample's `header + 1` relationship, although the provenance of `8819` in file bytes still needs an input trace. |
| `0x57E0–587B` | Writes `F4` to `B442`, packs `(B402-3)` into two seven-bit position bytes at `B443/B444`, loads `F3` at `57FF` then writes it to `B445`, selects a chain ID from `B4DE+(B402-1)` or an adjacent slot, reads `B6D5[id]`, and stores `0x4F+length` at `B446`; sets `B447` to `01` or `02` on branches. | Called from `5312` and other navigation/start paths; callers send this six-byte buffer via `19DF`. | Confirmed **rhythm position/length command constructor** and **atomic indexed duration-to-command-byte helper** at `586E–587B`. The six-byte command includes the selected pattern's *duration*, but no obvious selected pattern ID or note triples; it alone does not prove an external pattern expansion handoff. The first disassembly incorrectly labeled immediate byte `5800` as `DI`; verified raw bytes `57FF: 3E F3` and corrected research listing show `LD A,F3`. |
| `0x19DF–19F8`, `0x19D2–19DE`, `0x4A88–4A97` | Conditional buffer sender starts at `B442`, sends count `A` bytes to `19D2` (call `4A88`), which pushes each byte into a ring at `(883D)` and sets bit 0 on Z180 port `05`. | `5225–525A` sends an `F4` three-byte position message; `5DA1–5E05` sends two such messages with one high-bit flag; `57E0` prepares the six-byte form. | Confirmed **atomic command buffer sender and queue writer**; physical receiver and whether it expands patterns into notes remain unresolved. |
| `0x70EC–7132` | Starts at RAM `B71D`, writes 2,000 (`07D0`) consecutive **three-byte** values from the 24-bit state `B4DB–B4DD`, incrementing that state by one per entry. | Startup `77FA`, navigation reset `4F68`; calls `620B`, `658F`, `7399` afterward. | Confirmed pointer/index-table **initializer**, not a pattern step reader; use and persistence of individual entries require trace. |
| `0x7399–7434` | Loads 24-bit values from `B45D–B45F` and `B460–B462` into Z180 ports `20–25`, sends a transfer count through ports `26/27`, mode from `A` through `B478` to port `31`, and starts transfer through port `30`. Splits transfers into `0x80`-byte chunks and decrements the 24-bit remaining count `B463–B465`. | Used by `70EC` after filling the three-byte table, and by `6573`, `6F63`, `700C`, `707E`, `715C`. | Confirmed **atomic hardware-transfer launcher**; source/destination register direction and exact DMA controller semantics need device-level confirmation. Do not equate it with the rhythm note reader. |
| `0x776F–7777`, `0x7854–7879` | Set initial 24-bit address `B451–B453=02:4E95`; later initialize `B715–B71C` to bytes `01..08`. | Startup `7764–7803`. | Confirmed adjacent defaults; all eight values align with the test SONG's proposed RAM image. |
| `0x6339–634C` | Writes zero through `(HL)` for `BC` bytes, preserving `HL` and `BC`; caller must supply a nonzero count. | Clears `AC00` for `0480` bytes at `60AF` and `77EE` and other buffers. | Confirmed **atomic buffer-clear routine**. |

### Song playback and recording details

| Function / span | Observation |
| --- | --- |
| `0D7B–0D9A`, `0F25–0F35`, `4D19–4D40`, `50E8–5149` | State-gated MIDI realtime dispatch. The F8 path `0D86 → 0F25 → 4D3D → 50E8 → 512F` adds four to `B40A` after its checks. The playback loop consumes those positions, supporting 96 positions per quarter from 24 MIDI clocks. |
| `6EAC–6ECD` | Adds the decoded record width `B48F` to the 24-bit read pointer and fetches again. |
| `6ED1–6F03` | Advances recording position `B479`. Wraps at `C0` (192) and conditionally calls `70B1` to record a boundary. A storage interval need not coincide with a musical bar. |
| `6F40–6F69` | Copies four bytes from the 24-bit `B454–B456` pointer to DMA physical `0x02343C` (normal RAM `B43C`), then invokes the decoder. |
| `6F6A–6FDB` | Tests first byte `FF` as a separate marker, resets `B439/B48C`, and sets width one. Otherwise stores position in `B436`, accepts explicit status or reuses `B48C`. At `6FCF–6FD8`, stored `8x` note-off becomes `9x` with velocity zero. |
| `6FDC–7097`, `7098–70B0` | Writes position first, includes status when changed, then note/program data and optional velocity. Normalizes zero-velocity note-on on the recording side. |
| `70B1–70CE` | Writes the 24-bit event pointer to the index and appends the `FF` boundary byte. |
| `7764–776C`, `43B6` | Startup writes timer reload `0x0516` via ports `0E/0F`, matching table entry 40. Reload values for codes 0, 39, 40, 105 are 3906, 1324, 1302, 625. |
| `780A–7834` | Initializes `B448–B450` to channels `0..7,9`. Saved routing from disk remains unverified. |

## Candidate alternate bank `85/18/08`: floppy transport codec

Physical ROM offsets `D000–FFFF` are mapped to CPU `5000–7FFF` in the Ghidra research overlay; the byte equivalence is checked by the scripts. This ROM selection is consistent with the D-20 Service Notes p.17 IC16 address wiring and the MMU writes, as documented in the prior Song-save checkpoint; exact runtime transitions remain to be checked per caller. These routines belong to the floppy path because caller `6F36` reads controller ports `E0–E3` and caller `70C0` writes a controller-bound buffer. They do **not** establish a rhythm pattern-record format.

| Function / span | Confirmed instructions | Dependencies / callers | Confidence and open branch |
| --- | --- | --- | --- |
| `85/18/08:757F–758F` | Masks input to five bits, indexes the 32-byte table at `75AD`, stores one encoded byte at `(DE)`, increments `DE`. Table at ROM file `F5AD` begins `AA AB AD AE AF B5` and ends `FA FB FD`. | Called eight times by `7521`. | Confirmed **atomic 5-bit-symbol encoder**. |
| `85/18/08:7521–757E` | Slices five source bytes at `(HL)` into eight five-bit symbols and calls `757F` for each. | Called by `74F3`, `51` times for the first 255 source bytes and once more for a five-byte trailer. | Confirmed packing; byte field meanings still need disk-record trace. |
| `85/18/08:749A–74E7` | Reads one byte at `(DE)`, finds it in one of four eight-byte table windows, returns its five-bit index, increments `DE`; sets carry on invalid symbol. | Called eight times per group by `743F`. | Confirmed **atomic symbol decoder**. |
| `85/18/08:743F–7499` | Reassembles eight decoded five-bit symbols into five bytes at `(HL)`; advances `HL`. | Called by `73EF`, 51 times followed by trailer. | Confirmed inverse bit packing. |
| `85/18/08:7590–75AC` | Reads three initial bytes then iterates 253 times, shifting and XORing a three-byte state. | `73EF`, `74F3`; result compared against bytes `98D7–98D9` on read and written there on write. | Confirmed **atomic three-byte rolling check**; exact polynomial/semantics not yet independently calculated. |
| `85/18/08:73EF–743E` / `74F3–7520` | Decode / encode `0x33` groups of five source bytes, process one five-byte trailer, verify / append check bytes and `58` marker. | Read wrapper `73DD` called from `6F2D`; write wrapper `74E9` called from `6FC5`, `70B3`. | Confirmed disk transfer framing in candidate bank, contingent on physical mapping. |
| `85/18/08:6129–6159` | Reads slot `8AB8`, waits for countdown `8AB9` to expire, then dispatches through little-endian words at ROM `615A`: slot 8→`58C3`, 9→`5895`, 10→`5A5E`; slot 6→`53B5` (save path). | Disk front end, call targets below. | Confirmed **atomic indirect callback dispatcher**; particular file type is selected later by `8AC8`. |
| `85/18/08:58C3–5917`, `59B1–5A5D` | Disk checks, directory/name selection, and schedules callback slot 10 at `5A58–5A5D`. The ROM display record at `63DC` reads `Disk Load`. | Callback slot 8 after load selection. | Confirmed load-path entry and branch edges; errors return to menu. |
| `85/18/08:5A5E–5CB0` | Selects dispatch-list pointer by `8AC8`, reads its bytes through `5E49`, branches at `5B00` on type `<3` vs `>=3`; on the `>=3` path with flag bit 4 set it copies 16 bytes `9A00→8010`; on the `<3` path with that bit set it copies 32 bytes `9A00→8000` at `5BCC`. The latter path then sets DMA address ports `22/25=02`, `23/24=34BA`, transferring chunks via `5E14`. A separate branch sends staged bytes at `(HL)` via `5865`. | Disk load slot 10; status, directory, and response handlers `6658`, `5CEC`. | Confirmed instruction path and type split. The programmed destination `0x0234BA` is consistent with normal-bank RAM `B4BA` (and Song candidate file offset `0x20`) under the MMU address relationship also seen at `6F40→B43C/0x02343C`; **a file-to-RAM copy including offset zero is not yet proven**. |
| `85/18/08:5807–5813`, `5E49–5E5A` | Four short byte lists selected by `8AC8` and consumed by `5E49`, skipping zero bytes when updating `8AC0`. | Used in `5A5E` and `5B81`; raw ROM bytes exported by `D20TraceDiskLoadCallbacks`. | Confirmed **atomic dispatch-list reader**; list-byte meanings are not established. |
| `85/18/08:5865–5872`, `5E14–5E3F` | First routine writes byte to port `07` and waits on status from port `05`. The latter programs DMA address/count via ports `20/21` or `23/24`, `26/27`, starts via `30`, and waits for status. | Load path `5B66–5B74` sends bytes with `5865`; `5BF3–5C95` invokes `5E14`. | Confirmed **atomic port-transmit and DMA-start routines**; peripheral direction and any decoding performed downstream still unresolved. |

### Disk save path and directory handling (85/18/08)

| Function / span | Observation |
| --- | --- |
| `5372` | Copies ten bytes from `9BC0` to `8016` and conditionally to `8006`. Schedules slot 6 with `8AB8` and countdown `8AB9` via `604D`. |
| `53B5–53F1` | Slot 6 runs disk/status checks via `6606`, `6008`, `6054`. Branches to Insert Disk callback `53E7` or directory search. |
| `53F1–5467`, `5468` | Formats a directory name via `5E6D` and calls `6785`. The continuation displays Disk Saving and schedules slot `0E`. |
| `553F–5580` | Checks free space and status. Uses `8AC8` and `8AC6`. `5214/5202` write type values 2/1, but the menu callback-to-file-type association still requires a trace. |
| `55F7–5600`, `5602–576A`, `56D2–56E8` | Stages 32 bytes `8000 → 9A00` for type below 2, otherwise 16 bytes `8010 → 9A00`. Transfer chunks use `0xC00` or `0xB00`. These copies and receive calls occur during Save and do not by themselves establish a payload write. |
| `5E20`, `5E40`, `5F80`, `5E5B`, `5814` | Programs DMA address/count, starts control `60`, initializes receive ring `8300` and sends `D8` on port 7. `5E5B` consumes bytes via `8839/883B` and `5814` copies up to 256 bytes with retry. |
| `6653`, `66C5`, `65B6`, `6841` | `6653` stores a pointer to `8B14`. `66C5` manages a 32-byte directory/allocation entry via `8B12`, free slots at `9516`, and helpers `65B6/6841`. It marks the allocation byte and stages directory data at `8B10`. |

## A/B 1.12 mainboard function map

| Function / span | Confirmed MCS-96 instructions | Dependencies / open branch |
| --- | --- | --- |
| `0x1230–125D` | Masks `REA` to 3 bits, multiplies by 6, adds ROM `1B99` to select one of eight empty six-byte rhythm templates; conditional calls `1CB4` send bytes from template. | Confirms relocated address `1B99` is executable reference; entry state and exact protocol not yet traced. |
| `0x1882–1891` | Writes consecutive 16-bit RAM pointers beginning `9740` to RAM pointer table at `9700`, increasing destination by `0x126` (294) per entry. | Loop counter is set upstream of this export; 32 entries corroborated by table placement and adjacent 32-slot initializer. |
| `0x1894–18C0` | Sets `R20=0x20` slots and `R21=0x62` triples per slot, ROM source `RW22=1BC9`, RAM destination `RW24=9740`; copies three bytes per iteration; if first byte is `FF`, rewinds source by three. | **Confirmed 32-slot, 294-byte RAM pattern initialization** using the 13-hit ROM record then repeated `FF 80 00` terminators. Slot 31 begins `BADA`, final slot ends `BBFF`. This ROM record is a startup template, not a singled-out preset. |
| `0x18C3–18E0` | Writes `0x0040` at RAM `BC00`, then writes incrementing index-shaped bytes in a loop. | Atomic initialization of another rhythm-adjacent structure; exact role requires its consumers. |
| `0x16ED–173B` | Tests pattern ID bit 6 to select one of eight ROM empty templates at `1B99`; otherwise bit 5 chooses `B000` or `9700`; writable branch masks ID to `0..31`, doubles it, reads word from `9700`, then fetches the first byte of the record. | **Confirmed header selector**, including `3F→slot31`. Caller `4A58` queues 32 writable pattern headers; this path does not itself play notes. The factory bank selector and tone-ROM records are traced in the [factory guide](factory-rhythm-rom-mapping.md). Caller-mode flags remain partly unresolved. |
| `0x4A58–4A80` | Iterates pattern IDs `20..3F`, queues `F3`, ID, and the header byte returned from `16ED`, then sets bank selector register to `02`. | Confirmed atomic **writable-pattern header report**; a response/control route, not yet a playback event path. |
| `0x16A2–16DA` | Queues `F4` followed by a packed two-byte position, updates a rhythm-list byte at `BC02+index` from `C9CF`, then queues `F3`, selected ID and the header fetched through `16ED`. | Confirmed **rhythm-list edit and position/header reporting**. This path stores a pattern number in the list; it does not emit the pattern's note/velocity triples. |
| `0x1301–1318`, `0x1538–155F`, `0x15FC–161E` | Construct and queue `F4` plus a packed position from `RWE8` or `RW24`; `1538` also stores an ID to `BC02+index`, while `15FC` updates a position word at `EC56`. | Confirmed **position command senders**; no note-off/gate or timed hit dispatch in their exported spans. |
| `0x13BD–1406` | Queues `F4`, `40`, `01`; initializes position/list state at `EC5E`, `BC00`, `BC02`, and `EC60`, with a flag-gated store to `D2F3`. | Confirmed **atomic rhythm-list initialization and position command**; flag semantics at `RFA` require caller trace. |
| `0x1A6D–1AE0` | Computes `9740+(id&1F)*0x126`; reads header and count; indexes raw duration table `1B91` with `header+1`; for up to 96 triples, tests `FF`, checks position, multiplies position by 16, and loads note and velocity bytes into an eight-slot-per-position grid at `E000`. | **Instruction-confirmed record layout and field order** `[position,note,velocity]` and 24 raw positions per beat. Editor grid import, not proven MIDI playback emitter; trace overflowing event and grid branches. |
| `0x1AE5–1B8F` | Clears 3,072 bytes of step-grid RAM `E000–EBFF` to `80 00`, chooses a source from banked pointer/count metadata at `8034/8036`, selects bank `30` or `31`, loads header and count, then interprets the same triplets into the 16-byte-per-position grid; terminates scan on `FF` or after 96 triples. | Confirmed **banked-source pattern-to-editor-grid loader**, separate from writable-slot importer `1A6D`. Physical source behind bank selectors and downstream playback remain unknown; its out-of-range branch into `1C65` needs validation. |
| `0x1910–19C3` | Writes record header, count and reserved zero; walks `E000` step grid in ascending time, emits `[time,note,velocity]` triples for occupied slots; fills remaining room with `FF 80 00` and terminates full-count branch with `FF 00 00`. | Confirmed atomic **editor grid-to-pattern serializer**, complementary to `1A6D`. The count bound is 96; exact output note-off rules remain open. |
| `0x6DAC–6E0F` | Reads bounded slot count `<=32` from banked metadata, multiplies by `0x93` (147) two-byte iterations, copies source bank `31` data into bank `21` RAM at `9740`; then transfers additional data to `BC00`. | **Confirmed bulk pattern-bank import**; at count 32 copies `32*294=9408` bytes. Bank `30/31` backing store and trigger need hardware trace; do not equate with disk load yet. |
| `0x6E56–6E88`, `0x6E89–6EAC` | Alternates source and destination bank selectors through port `100`, copies two bytes per iteration via indirect pointers, reads back each destination byte and returns error code `09` on mismatch. Helpers select bank values `20`, `21`, `30`, and `31`. | Confirmed atomic banked-copy primitive and bank selector helpers; physical medium behind selectors still unresolved. |
| `0x55D3–55F9` | Writes queued bytes into a 512-byte ring at `F800`, waits if its producer would meet consumer pointer `RW94`, wraps writer pointer `RW96`. | Confirmed **atomic output ring writer**, used by `1D06`, `4759`, and other paths. The downstream receiver and relation to voice triggering are unresolved. |
| `0x1CB4–1CD9`, `0x1CEB–1CFC` | Atomically enqueues a byte into a circular buffer and updates a one-byte output register, respectively. | Used by the empty-template selector and lookup branches; receiver and protocol unresolved. |

### A/B tables and ROM revision cross-check

| Item | A/B 1.12 address | A/B 1.00 address or relationship |
| --- | --- | --- |
| Duration lookup, 24 positions per beat for 1–8 beats | `1B91–1B98` | Shifted by `+0x2A` |
| Eight six-byte empty meter templates | `1B99` | `1BC3`. `1239` uses the relocated immediate. |
| 13-hit startup template for writable slots | `1BC9` | `1BF3`. Startup source load is at `189E` in 1.12 and `18C8` in 1.00. |
| Writable slot pointer table and data in A/B RAM | `9700`, `9740` | `32 × 294` bytes through `BBFF`. `BC00/BC02` are adjacent list state. |
| Editor grid | `E000–EBFF` | 192 positions with 16 bytes per position. |

An independent comparison aligns the first 340 interleaved bytes with the saved `09H` Rhythm Setup. The high match rate, valid relocated opcodes, and independent template bytes support the interleave order. The C `5E06` scheduler selects a chain entry and duration. The A/B editor reader and writer independently establish the note-record grammar. The bridge from the timed playback path to A/B voice or MIDI output is still open.

## Native file mappings and MIDI interpretation

File ranges in this section use an exclusive end. These alignments describe the compared native saves and what the exporter checks.

| Region | File offsets | Evidence and interpretation |
| --- | --- | --- |
| Embedded pattern payload | `.444` `0100`, `.222` `3B00`, `.111` `9000` | Matched saved payloads. Thirty-two records of `0x126` bytes span 9,408 bytes across the combined packed `0AH` and `0BH` areas. The nominal boundary at `.444` `2100` crosses slot 27. |
| Rhythm mirror and setup | Relative to payload base: mirror `2900:2F00` must match `1D00:2300`. Setup `2700:2854`. | Mirror checked before decoding. Four raw `09H` bytes for each used note 24–108 are retained as MIDI text. The exporter leaves device parameters uninterpreted. |
| Record header and slots | `base + (id - 0x20) × 294` for IDs `20..3F` | `[beats − 1, count, 00]`, up to 96 `[position, note, velocity]` triples, then `FF 80 00` or `FF 00 00` padding. The A/B editor confirms the RAM stride and fields. Saved duration entries agree with all 32 slot headers in the paired saves. |
| Standalone Rhythm chain | `.444` count word `2600:2602`, IDs from `2602` | Count interpretation is specimen-supported. Trailing entries can be stale. This list can differ from the Song list even when both reference identical pattern payloads. |
| Song chain and lengths | `.222` / `.111` `0044:023B` terminated by `FF`, length table `023B:027B` | Correlates with `B4DE/B4E0` and `B6D5`. IDs `3E` and `3F` map to `P-87` and `P-88`. Compare the saved length against each selected record header. Empty slots still advance time. |
| Song header candidates | `.222` / `.111` `0036`, `003F`, `0041:0044` | Proposed base `B49A + file offset` aligns tempo with `B4D0`, active-lane mask with `B4D9`, and the 24-bit event base with `B4DB`. ROM formula `40 + 2 × B4D0` gives tempo in BPM. The first-allocation reader, header copy, DMA, and completion callback establish the tempo-byte path. Other header interpretations still require independent traces. |
| Song index and events | `.222` / `.111` index `0283:1A00`, event region `1A00:3A02` | Candidate RAM index base `B71D`. Subtract the header's 24-bit base from each little-endian pointer and add file offset `1A00`. Pointer targets are separate `FF` markers. Index entries increase strictly. A full index can run to its region limit. |
| Song record | `[position, optional status, first data, optional second data]` | Each `FF` clears running status. Position is `0..191` in a 192-position storage interval. Export accepts `8x`/`9x` notes, `Bx` controllers, `Cx` programs and `Ex` pitch bend. Programs and stored `8x` have one data byte; other supported families have two; status low nibble determines the provisional MIDI channel. |

The normal-bank MMU relationship `B43C → 02343C` also makes the disk-load DMA address `0234BA` consistent with RAM `B4BA` and proposed Song offset `0020`. This supports the `B49A` alignment. The executed [tempo-load trace](song-tempo-load-checkpoint.md) follows the first allocation to `9A00`, the header copy and DMA transfer, and the completion call through vector `0014` to `41BE`. The byte at offset `0036` lands at physical `0234D0` and is read as `B4D0` for timer reapplication.

For BETA MIDI, map a rhythm hit to `pattern start + 4 × position` on a 96 PPQ timeline. The C duration words (`5EAA`) and A/B step table (`1B91`) support this ratio. Device scheduling has yet to confirm it. Song/All tempo is read from the saved header by default, with an explicit override available. Standalone pattern and Rhythm exports use an explicit audition tempo. The rhythm note-off gate is an audition choice because the record stores no gate. Factory IDs `00..1F` can be read from the owned tone ROM with `--factory-rom`. The [factory mapping guide](factory-rhythm-rom-mapping.md) traces the selector and shared editor reader. Timed hardware output and gate policy remain unresolved.

## Trace script and evidence index

Scripts are in [research/ghidra](../research/ghidra/). Use an output path argument for each trace that writes a report. Setup and entry scripts modify the research program's analysis or memory map. The bounded exporters can be run with `-readOnly` after setup. Exported listings, factory ROMs, saved disk images, and local event CSVs stay local.

| Script | Main coverage |
| --- | --- |
| `D20ExportAudit.java`, `D20SetupRuntimeMap.java` | Audit the import and create the hash-checked normal ROM and RAM view. The audit takes a directory argument. |
| `D20ProbeAlternateBanks.java`, `D20TraceEntries.java` | Create the two candidate overlays and seed bounded diagnostic and disk entry points. |
| `D20TraceSongPlayback.java`, `D20ExportSongPlaybackEvidence.java` | Seed and export the normal playback and recording spans. The exporter includes `077B`, `0D7B`, `0F25`, `4B7C`, `4D19`, `4F51`, `50E8`, `5529`, `5726`, `5B13`, `5E06`, `69EA`, `6D55`, `6EAC`, `6F04`, `6FDC`, `70EC`, `7399`, `7764`, `780A`, and duration words `5EAA–5EBB`. |
| `D20TraceTempoAndRhythm.java`, `D20TraceRhythmPattern.java` | Timer writes, MIDI clock, display and pattern timing. Additional surrounding spans include `0368`, `07A8`, `04CA`, `1DF0`, `418A`, `4191`, `419A`, `41A1`, `4B25`, `4C86`, `5D28`, `5F3C`, `5540`, `5FFA`, `6ED1`, `7654`, `772F`, and `7764`. Nearby decoded instructions do not establish a separate function's purpose. |
| `D20TraceSongRamLayout.java`, `D20TracePatternIds.java`, `D20TracePatternRouting.java` | Normal-bank pattern IDs and display, duration-table update and references, RAM index initialization, hardware transfer, and command queue. `57FF: LD A,F3` consumes the byte at `5800`. |
| `D20TraceSongSave.java`, `D20TraceDiskLoadCallbacks.java`, `D20TraceDiskSymbolCodec.java` | Candidate disk bank. Save and load callbacks, type dispatch, buffer and DMA helpers, and symbol codec. |
| `D20TraceABPatternReader.java` | A/B startup, empty templates, pointer and slot tables, editor decode/encode, alternate grid loader, banked copy, and position/header commands. |
| `probe_ab_rom_patterns.py`, `probe_pattern_records.py` | ROM hashes, interleave and relocated template checks, saved record bounds, optional event ledger, and Song duration cross-check. |

## Unresolved and reproducible next checks

1. Cross-check the traced tempo byte at `0036` with controlled saves at different tempos when hardware is available. The [tempo-load checkpoint](song-tempo-load-checkpoint.md) records the executed load and completion trace, including new allocation and sector-reader function mappings.
2. Compare the decoded factory presets and controlled empty, single-hit, and simultaneous-hit patterns with MIDI output to identify the hardware time conversion and gate. The preset bank and record lookup are now documented in the [factory mapping guide](factory-rhythm-rom-mapping.md).
3. Follow the disk type callbacks and receive/staging branches through the sector write command. Keep directory allocation and the five-bit floppy codec separate from the musical records.
4. Verify saved channel routing, non-note statuses, and cross-device behavior against additional independent native saves. See the [memory map](memory-map.md), [Song export](song-wip.md), [All export](all-wip.md), and [Rhythm export](rhythm-converter.md) for the implemented interfaces.

The [factory rhythm guide](factory-rhythm-rom-mapping.md) extends this map with the executed preset selector and shared editor import, the external bank helpers, display label formatter, and the memory-test helper discovered during the pointer search.
