# Saved Song tempo load checkpoint

This checkpoint follows the C 1.11 disk-load instructions already exported during the firmware investigation. The new bounded script is prepared for a fresh Ghidra run. That run was interrupted by loss of the laptop execution connection, so this checkpoint records static dataflow and the remaining evidence gates.

ROM SHA-256 is `7c8d2aecbb74bf939661d3fd904c691a4c7c749a374cb804c0247b64b649e1c2`. Disk addresses below use the candidate `85/18/08` overlay, where CPU `5000–7FFF` corresponds to ROM file `D000–FFFF`. Normal-bank addresses use `C8/18/18`.

## First-block dataflow

| Address | Existing instruction evidence | Consequence |
| --- | --- | --- |
| `5A5E–5A8E` | Type values 1 and 2 select byte lists at `5807` and `580C`. Both start with class 1. The caller reads the first class with `5E49`, ORs `10`, and stores the result at `8AC0`. | Both selections enter the class-below-3 path with the first-block flag set. Their menu-to-file-type association still requires verification. |
| `5AF7–5B02`, `5BAE–5BB0` | Masks the class to its low nibble, tests class below 3, and tests bit 4 of the original value. | Selects the header-copy and initial DMA setup branch. |
| `5BB2–5BC9` | Writes zero to DMA mode port `31`, high bytes `02` to address ports `22/25`, and destination word `34BA` to `24/23`. | The programmed destination is physical `0234BA`. |
| `5BCC–5BD5` | `HL=9A00`, `DE=8000`, `BC=0020`, then `LDIR`. | Copies the first 32 staging bytes. After the copy, `HL=9A20`, `DE=8020`, and `BC=0`. |
| `5BD7–5BDE` | Exchanges DE and HL, sets BC to `0BE0`, loads the remaining-length word from `8011`, and joins `5BE9`. | The first data source is CPU `9A20`. The length check can reduce the first transfer below `0BE0`. |
| `5BE9–5C03` | Subtracts the requested count from the remaining length, branches on borrow or completion, and invokes `5E14`. | For the inspected native header length `19C8`, the first transfer uses the full `0BE0` bytes. |
| `5E14–5E1E`, `5E2A–5E3F` | Loads DE into source ports `21/20` (masking D to seven bits), loads BC into count ports `27/26`, starts DMA control `30=60`, and waits for completion. | With source DE=`9A20` and high byte `02`, the source is physical `021A20`. This agrees with the MMU mapping of CPU `9A20`. |
| `5CDA–5CEB` | Loads `8002` into port `25`, `8001` into `24`, and `8000` into `23`. | An atomic destination-address loader for later transfer sections. Later sections must be traced with this destination change in mind. |

The pointer progression is stronger evidence than the earlier comparison of saved bytes with RAM defaults. It establishes the source and destination of this first transfer under the selected load branch.

## Tempo byte calculation

If the staged block at `9A00` is native file offset zero, the 32-byte copy makes the next DMA source file offset `20`.

```text
candidate file byte                    0036
first DMA file byte                    0020
offset within the first DMA transfer   0016
first DMA physical destination       0234BA
tempo byte destination               0234D0
```

The normal MMU view maps CPU `B4D0` to physical `0234D0`. Thus the first transfer places candidate file byte `0036` at the known tempo location. The inspected header's first-section length is long enough to include that byte.

Two other ROM paths independently identify RAM `B4D0` as tempo state. The UI at `4191–41BD` bounds its code to `00..69`, selects a timer reload at `43B6 + 2*code`, and writes ports `0E/0F`. The arithmetic at `7690` computes `40 + 2*code`. The observed candidate code `27` therefore gives 118 BPM, conditional on the load mapping above.

## Remaining evidence gates

1. Trace `6658` and the directory/FDC read chain to establish that the first buffer at `9A00` begins at native file offset zero, and that the selected file types reach the branch above.
2. Export reset vectors `0014/0018`, normal-bank restore code, and the load-completion route `5CB0–5CD7`. The latter conditionally sends six bytes beginning at `8016` when its first byte is `88`, then calls `0014`. Determine whether completion resets, transforms, or reapplies tempo.
3. Confirm the effective DMA mode and physical address interpretation against the hardware documentation and normal-bank transfer routines.
4. Run `D20TraceTempoLoad.java` and review the resulting disassembly and raw `D0 B4` operand hits. Raw hits may include data and must be checked as instructions.
5. When hardware is available, compare otherwise identical native saves at two tempos. Confirm the candidate code change and the resulting MIDI tempo before making extraction automatic.

The existing exporter continues to take the audition tempo explicitly. This checkpoint does not change the decoder's behavior.

## Reproduce the bounded trace

Prepare the research copy as described in the [firmware reverse-mapping guide](firmware-reverse-mapping.md). From the repository root, run the following command using the existing prepared project.

```sh
"$GHIDRA_HOME/support/analyzeHeadless" "$PROJECT_DIR" D20Research \
  -process D20-C-1.11-banked-analysis -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceTempoLoad.java /tmp/d20-tempo-load-evidence.txt
```

The script verifies the C ROM hash and exports the initial header transfer, DMA setup, class selection, completion branch, vectors, MMU helpers, and normal tempo code. Compilation and execution of this newly prepared script remain pending.
