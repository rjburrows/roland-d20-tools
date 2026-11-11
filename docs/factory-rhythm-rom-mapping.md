# Factory rhythm preset mapping

The 32 D-20 factory rhythm presets can be extracted from the 128 KiB tone
ROM. Their IDs are `00..1F` (P-11–P-48). The A/B program selects them through
a banked pointer table and imports them through the same editor reader used
for writable patterns. The supported data image has SHA-256
`ae4aa5a80b5e5aba9584db6906707ea9d74fb04936a917e6e62585a4529782a1`.
The interleaved A/B 1.12 program image has SHA-256
`283cda5527d3b21cc39093cdcb0f982f0399466585b871b9fa77ac3ae855f2ca`.

## How the record source was identified

The Service Notes mainboard schematic (printed p.19) identifies the tone mask
ROM at IC12, separate from program PROMs IC14/IC13 and the PCM waveform ROMs.
The A/B selector writes `28` to external bank register `0100`, then reads a
word at CPU `B000 + 2*id`. Flat A/B program file offset `B000` contains display
text. The selected bank therefore has to be considered when interpreting the
CPU address.

The tone ROM has an aligned 32-word table at file offset `3000`. Its words
point to compact pattern records at `3100..39A0`. All 32 records have valid
headers, ordered hit positions, notes and velocities, and `FF 80 00`
terminators. The stored pointer word W produces this bank/address pair in the
program.

| Value | Instruction-derived expression |
| --- | --- |
| Bank register | `28 + (W >> 14)` |
| CPU record address | `8000 + (W & 3FFF)` |
| Tone ROM offset represented by W | `(bank - 28)*4000 + (CPU address - 8000)` |

Every pointer in the supported factory table is below `4000`, so these records
use bank `28`. For example, ID `00` has word `3100`, which becomes CPU `B100`.
The record at tone ROM `3100` has a four-beat header and 13 hits. This mapping
is corroborated across all 32 records, by the shared editor reader, and by the
C ROM duration defaults. The gate-array internals have not been independently
simulated.

## Executed Ghidra trace and function map

`D20TraceABFactoryPatterns.java` verifies the A/B image hash and exports the
selector, editor import, external bank writer, and display-label code. It was
compiled and run in Ghidra 12.2 with the research program opened read-only.
It makes two localized analysis repairs after verifying the ROM hash. At
`11FE`, bytes `B0 ED F5` form one `LDB` instruction, consuming byte `1200`.
At `1A1F`, bytes `26 F7` form one `SJMP`. Earlier stale boundaries displayed
`POPA` at `1200` and `TRAP` at `1A20`. Raw ROM bytes remain unchanged.

| Function / span | Confirmed instructions and dependencies | Remaining interpretation |
| --- | --- | --- |
| `16ED–1716` | Tests ID bit 6 and bit 5. IDs below `20` select bank `28`, double the ID, load a word from `B000`, split the bank bits from its high byte, and read the selected header. | Header selector, with separate writable and empty-template branches. It does not establish timed MIDI output. |
| `11EA–122F` | Another selection/reporting path chooses the same factory pointer table, sets the bank/address pair, and conditionally queues `F3`, pattern index and header through `1CB4`. | Caller-mode flags remain partly unresolved. |
| `1A21–1A6C` | Clears editor grid `E000–EBFF` to `80 00`. For a factory ID, selects bank `28`, reads `B000 + 2*id`, sets the resulting source bank, and jumps from `1A69` to `1A7C`. | Confirms that factory and writable records share the editor importer. Input flags at bit 7 select another source branch. |
| `1A7C–1AE0` | Loads header and hit count, advances by three bytes, uses the raw-duration table, and imports `[position,note,velocity]` triples into eight slots per grid position. | Device playback scheduling and note-off gate remain open. |
| `1CEB–1CF3` | Copies requested bank RF5 to shadow R69 and writes byte R69 to external address `0100`. | Atomic bank-register writer. |
| `1CF4–1CFC`, `1CFD–1D05` | Writes constant bank values `21` and `03` respectively to the same register. | Atomic constant-bank helpers. The use of bank `03` requires caller-specific tracing. |
| `5E7A–5EA3` | Clamps a display index to 32, multiplies by 11, adds program address `AF1A` and copies the label. Index 32 selects `UserPattern`. | Establishes the 11-byte factory label table. |
| `42D4–4319` | Selects a bank, saves a byte, writes and checks a test value and its complement, restores the original byte, then returns carry/status. Error path also restores the original byte. | Atomic memory-test helper discovered during the `B000` reference search. Its `B000 + address` read is a test-value source and is separate from the factory pointer lookup. |

The C 1.11 initializer at `077B–0793` independently sets most factory lengths
to four beats and overrides IDs `17`, `1B`, and `1C` to three, eight, and eight
beats. These are exactly the special lengths in the decoded tone-ROM records.

## Factory table inventory

Offsets are tone-ROM file offsets. Labels come from the A/B program's
11-byte table at `AF1A`. Hit records total 630 across the 32 presets.

| ID | Panel number | Display label | Record offset | Beats | Hits |
| --- | --- | --- | --- | ---: | ---: |
| `00` | P-11 | 8Beat 1 | `3100` | 4 | 13 |
| `01` | P-12 | 8Beat 2 | `3130` | 4 | 14 |
| `02` | P-13 | 8Beat 3 | `3160` | 4 | 14 |
| `03` | P-14 | 8Beat 4 | `3190` | 4 | 16 |
| `04` | P-15 | 8Beat 5 | `31D0` | 4 | 14 |
| `05` | P-16 | 8Beat 6 | `3200` | 4 | 13 |
| `06` | P-17 | Ballad | `3230` | 4 | 17 |
| `07` | P-18 | Reggae | `3270` | 4 | 8 |
| `08` | P-21 | 16Beat 1 | `3290` | 4 | 22 |
| `09` | P-22 | 16Beat 2 | `32E0` | 4 | 22 |
| `0A` | P-23 | 16Beat 3 | `3330` | 4 | 25 |
| `0B` | P-24 | 16Beat 4 | `3390` | 4 | 23 |
| `0C` | P-25 | 16Beat 5 | `33E0` | 4 | 22 |
| `0D` | P-26 | 16Beat 6 | `3430` | 4 | 28 |
| `0E` | P-27 | Shuffle 1 | `3490` | 4 | 14 |
| `0F` | P-28 | Shuffle 2 | `34C0` | 4 | 12 |
| `10` | P-31 | Disco 1 | `34F0` | 4 | 14 |
| `11` | P-32 | Disco 2 | `3520` | 4 | 14 |
| `12` | P-33 | Elec Pop 1 | `3550` | 4 | 26 |
| `13` | P-34 | Elec Pop 2 | `35B0` | 4 | 26 |
| `14` | P-35 | Jazz 1 | `3610` | 4 | 8 |
| `15` | P-36 | Jazz 2 | `3630` | 4 | 9 |
| `16` | P-37 | Jazz 3 | `3660` | 4 | 11 |
| `17` | P-38 | Jazz Waltz | `3690` | 3 | 6 |
| `18` | P-41 | Samba 1 | `36B0` | 4 | 39 |
| `19` | P-42 | Samba 2 | `3730` | 4 | 35 |
| `1A` | P-43 | Samba 3 | `37A0` | 4 | 43 |
| `1B` | P-44 | Bossanova 1 | `3830` | 8 | 21 |
| `1C` | P-45 | Bossanova 2 | `3880` | 8 | 29 |
| `1D` | P-46 | Mambo | `38E0` | 4 | 25 |
| `1E` | P-47 | Merengue | `3940` | 4 | 30 |
| `1F` | P-48 | Rhumba | `39A0` | 4 | 17 |

The three-beat ID `17` is P-38, Jazz Waltz. Its six hits provide a short
validation case with a meter different from the previously validated writable
patterns. The exported example uses 120 BPM, channel 10 and a provisional
12-tick note gate. These audition choices remain separate from the saved
position, pitch and velocity bytes.

## Reproduce and export

Prepare the interleaved A/B project following the
[firmware guide](firmware-reverse-mapping.md). Run this trace on that program.

```sh
"$GHIDRA_HOME/support/analyzeHeadless" "$PROJECT_DIR" ABResearch \
  -process AB-interleaved-1.12.bin -noanalysis -readOnly \
  -scriptPath research/ghidra \
  -postScript D20TraceABFactoryPatterns.java /tmp/d20-factory-pattern-evidence.txt

d20-tools pattern RHYTHM.444 jazz-waltz.mid --pattern-id 0x17 --factory-rom TONE_ROM.BIN --tempo-bpm 120 --gate-ticks 12
d20-tools rhythm RHYTHM.444 all-patterns.mid --notes all --factory-rom TONE_ROM.BIN --tempo-bpm 120
d20-tools song MYSONG.222 song.mid --factory-rom TONE_ROM.BIN
d20-tools all MYBACKUP.111 all.mid --factory-rom TONE_ROM.BIN
```

`--factory-rom` checks the ROM size and SHA-256 locally. Single-pattern and
standalone Rhythm exports require an audition tempo. Song and All use their
saved tempo unless overridden. Their chains may mix factory and writable
patterns. The saved duration table must agree with each selected record's
length. Raw `09H` setup metadata comes from the native container.

All-pattern mode writes 64 pattern tracks plus a conductor when the factory
ROM is supplied. The native-only mode writes 32 writable pattern tracks plus
a conductor. Pattern tracks start at zero and can be soloed separately.
End-of-track events preserve whole pattern lengths and trailing silent
selections. The extractor and generated synthetic tests are part of the
repository. Use the optional `D20_FACTORY_ROM` and `D20_TESTRHY_444` variables
for local regression against owned files.

## Remaining hardware checks

The editor instruction path confirms the shared record fields and the banked
selection mechanism. Runtime voice/MIDI triggering, note-off gates and exact
real-time scheduling still need their own traces. The bank-to-tone-file mapping
is supported by the record inventory and ROM duration/name cross-checks. A
factory preset playback comparison on the hardware will provide the next
independent validation.
