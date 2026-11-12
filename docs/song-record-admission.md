# Song recording admission checkpoint

The later [input-producer checkpoint](song-input-producers.md) closes the two
receive paths, identifies staged CC7/CC10, and maps edit/copy queues.

This checkpoint follows the [controller/bend export](song-controller-pitch.md).
It changes no decoder behavior. Pressure (`Ax`/`Dx`) and system/internal (`Fx`)
records remain unsupported: a permissive serializer is not proof of their
stored meaning or of a complete load/playback path.

Evidence is from the executed `D20TraceSongAdmission.java` script on C 1.11,
SHA-256 `7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`,
normal `C8/18/18` view. It verifies the owned reference block before tracing.
Direct-operand matches are candidates until decoded as instructions.

## Reconstructed recording paths

`65C0` is a mode-gated entry. With `B4B0.bit7` clear, flags in `B4B3` and
`B4B4` can return early; the startup branch proceeds only when classifier
`6705` returns 1 (the `9x` family). It calls `5C6D` and `5BDC`, sets
`B4B0.bit7`, emits `FA` or `FB` through `1DF0`, then calls `6732` before
joining `6648`. This is a conditional recording-start path, not a rule that
all stored events must be notes. The meanings of every mode/UI flag and the
complete upstream MIDI receiver remain unresolved.

`6648–665A` calls `665B` only when `B4B1 & C0 == 0` and `B4B2.bit2` is set.
At `665B` the flow splits:

| Branch | Data handling | Gate before writer |
| --- | --- | --- |
| `B4B3.bit0 = 0` | `B47E` status becomes lane 8 when `B4AF.bit3` is set, otherwise the lane from `B490`; copies `B47F/B480` into `B482/B483`. A `9x` classification additionally updates note state. | Calls `7435`; zero returns early. Further tests of `B4B0.bit1`, `B4B3.bit7`, `B4B2.bit6` can stop the call to `68DD`. |
| `B4B3.bit0 = 1` → `66E5` | Calls `69AC` to inverse-match the active channel table, then `6A02` to test the matched lane flag bit 7. Copies the resulting status and two data bytes. | Either carry-clear result returns early; success calls `68DD`. This branch does not call `7435` locally. |

Both paths can reach `68DD → 6945 → 6FDC`; `6945` is the previously mapped
headroom guard. The classifier at `66A8` selects additional note-state work;
its non-note result goes to `66C5`, **not** an unconditional rejection.
The channel-matching branch similarly does not establish a global event-family
whitelist. Consequently, this trace does not prove that pressure can never
occur in native files, nor that it is safe to export it yet.

`6FDC` normalizes zero-velocity `9x` through `7098`, then serializes one data
byte for `8x`/`Cx` and two for other families on this path. In particular, that
second rule cannot be silently equated with Standard MIDI's one-data-byte
`Dx` channel pressure. `FF` is a stored interval delimiter; it is not evidence
of recorded MIDI reset or SysEx support. Other direct writer callers in the
edit/copy paths remain to be traced independently.

## Sustain recording differs from playback filtering

`7435–74A4` returns `FF` for non-CC64 events. For CC64, data bit 6 selects
pressed/released state. Lanes other than 8 use mask `AB00[lane]` in `B4B8`;
lane 8 uses `B4B9.bit0`. An off event with no recorded on state returns zero;
an on event sets the state and returns `FF`, including repeated on values.
Thus this recording helper suppresses an unmatched release, rather than
suppressing every duplicate state. The previously mapped playback helper
`74A5–74EF` has a different rule. Export continues to preserve every stored
CC message without reproducing either stateful filter.

## Additional atomic function map

| Address | Confirmed operation and dependencies | Interpretation / unresolved work |
| --- | --- | --- |
| `33F2–33F8` | Complements input A, ANDs with `8A40`, writes it back, returns. Called by `6924` with `AB00[lane]`. | Atomic clear-mask helper: `8A40 &= ~mask`. The musical meaning of `8A40` is unresolved. |
| `6732–676F` | Calls `6770`; if staged status `B484` is nonzero, optionally changes its lane to 8, copies status/data to `B481/B482`, calls `68DD`. | Staged one-data-byte event seed. Its traced producer selects `Cx`; it is not proof of an eight-part saved-program header. |
| `6770–67C7` | When `B4AF.bit3` is set and `B484` is empty, examines current `B439` or fetches lookahead through `67C8`; accepts `Cx` only when `67F2` reports equal positions and the lane matches `B490`, then stages the status/data word at `B484`. | Conditional same-position program seed from current/lookahead events. Broader initialization sources remain open. |
| `67C8–67F1` | Programs transfer source from `B454:456`, destination `02:343C`, length 4, mode 2 through `7399`; returns `B43E`. | Atomic four-byte lookahead transfer wrapper. Peripheral register direction relies on the existing transfer map; this is not a four-byte native record declaration. |
| `67F2–6800` | Compares `B436` with `B479`; returns zero on equality, otherwise `FF`. | Atomic position-equality predicate. |
| `6801–6833` | For nonzero staged statuses at `B486` and `B489`, preserves each high nibble, sets lane 8, copies the following data word, calls `68DD`. | Two staged event seeds. Their producers and event-family restrictions remain unresolved. |
| `6834–68AD` | Saves/restores a `90`-byte region using `7399` around repeated `63AC` calls over `B300`; takes velocities from `B280 + returned note`, constructs `9x` for selected lane or lane 8, calls `68DD` until `63AC` returns `FF`. | Active-note reseeding loop. Detailed `63AC` bitmap semantics remain unresolved. |
| `68AE–68DC` | Repeats `63AC`, constructs the same `9x` lane with velocity zero, calls `68DD` until `FF`. | Active-note release loop; serializer subsequently normalizes these to stored `8x`. |
| `7435–74A4` | CC64 state update and unmatched-release filter described above. | Recording-side filter, distinct from playback helper `74A5`. |

## Reproduce and next trace

After setup of the research copy, run:

```sh
analyzeHeadless /tmp/ghidra-projects RolandD20-Control \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceSongAdmission.java /tmp/song-admission.txt
```

The script compiled and ran successfully in Ghidra 12.2; read-only processing
discarded analysis changes. ROMs and generated listings stay outside git.
No runtime code changes or new unit tests are needed for this research-only
checkpoint; existing exporter coverage and unsupported-family tests remain.

The next bounded trace should close the input producers feeding `B47E–B480`,
the producers of `B486/B489`, and direct writer calls in edit/copy routines.
Then compare the allowed families against replay dispatch and any independent
native pressure/system recording before expanding the decoder.
