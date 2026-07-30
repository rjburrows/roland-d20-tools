# D-20 memory-address reference

This is the address map implemented by the converters and diagnostic reports.
It is a source-derived engineering reference, not a replacement for Roland's
manual. A SysEx DT1 address has three 7-bit bytes: `MSB MID LSB`. Within an
area, the byte offset is `MID × 128 + LSB`; all ranges below are inclusive.

## SysEx areas

| Address area | Bytes | Used by | Meaning |
| --- | ---: | --- | --- |
| `04H 00 00–7F 7F` | 16,384 | Tone report | Temporary Tone memory (used only when no permanent Tone data is present). |
| `05H 00 00–07 7F` | 1,024 | Sound converter; Timbre report | 128 Timbre records × 8 bytes. |
| `07H 00 00–25 7F` | 4,864 | Sound converter; Patch report | 128 Patch records × 38 bytes. |
| `08H 00 00–7F 7F` | 16,384 | Sound converter; Tone report | 64 permanent Tone records × 256 bytes. |
| `09H 00 00–02 53` | 340 | Rhythm converter; Rhythm report | Rhythm Setup: 85 notes × 4 bytes. |
| `0AH 00 00–7F 7F` | 16,384 | Rhythm converter; compact inspection | Rhythm Patterns. |
| `0BH 00 00–12 7F` | 2,432 | Rhythm converter; compact inspection | Rhythm Track. |
| `0CH 00 00–03 75` | 502 | Rhythm converter; compact inspection | Sequencer Header. |
| `10H 00 00–00 31` | 50 | System report; compact inspection | Global System settings. |

`inspect` recognises each row but only prints message counts. The five `report`
decoders read `04H/05H/07H/08H/09H/10H`; `0AH/0BH/0CH` are preserved by the
Rhythm converter but are not yet interpreted as musical events.

## Detailed report records

| Module/report | Record and base address | Byte offsets interpreted |
| --- | --- | --- |
| System | One 50-byte record at `10H 00 00` | `0` master tune; `1–3` reverb mode/time/level; `4–11` part reserve; `12` rhythm reserve; `13` rhythm stored channel; `20–27` part stored channels; `33–40` part levels; `41` rhythm level; `42–49` part pans. |
| Patch | 128 × 38, record *n* begins at `07H`, offset `38n` | `0` key mode; `1` split; `2–5` lower/upper tone group + number; `6–15` lower/upper shift, fine tune, bender, assign and reverb switch; `16–20` reverb/balance/level; `21–36` name. Byte `37` is not decoded. |
| Timbre | 128 × 8, record *n* begins at `05H`, offset `8n` | `0–1` tone group + number; `2` key shift; `3` fine tune; `4` bender; `5` assign; `6` reverb switch. Byte `7` is not decoded. |
| Tone | 64 × 256, record *n* begins at `08H` (or `04H`), offset `256n` | `0–9` name; `10–11` structures; `12` partial mask; `13` envelope mode; four 58-byte partials at `14`, `72`, `130`, `188`. Bytes `246–255` are not interpreted. |
| Rhythm Setup | 85 × 4, record *n* begins at `09H`, offset `4n` | One record for MIDI note `24+n` (C1 through C8): `0` tone (`0–63` user, `64–127` rhythm/off); `1` level; `2` pan; `3` reverb switch. |

Each 58-byte Tone partial has this implemented layout: `0–7` wave generator
(pitch, fine tune, key follow, bender, wave/PCM selection and pulse-width
values); `8–19` pitch envelope; `20–22` LFO; `23–40` TVF and its envelope; and
`41–57` TVA and its envelope. The detailed Tone report displays the safe,
meaningful fields within those groups.

## Native Sound file (`.333`) layout

All file offsets are zero-based and use an exclusive end address.

| File offset | Size | SysEx relation | Notes |
| --- | ---: | --- | --- |
| `0000–00FF` | 256 | None | Header; type marker `03 00 00`, disk name at `0006–000F`. |
| `0100–3E7F` | 15,744 | `08H` Tone | 64 × 246 native bytes. The final ten bytes of each 256-byte SysEx Tone record cannot be represented. |
| `3F00–42FF` | 1,024 | `05H` Timbre | Direct copy. |
| `4300–55FF` | 4,864 | `07H` Patch | Direct copy. |
| `5600–5FFF` | 2,560 | Patch mirror | Must match `07H` offsets `0700–10FF` (the corresponding native bytes `4A00–54FF`). |

## Native Rhythm file (`.444`) layout

| File offset | Size | SysEx relation | Notes |
| --- | ---: | --- | --- |
| `0000–00FF` | 256 | None | Header; type marker `04 00 00`, disk name at `0006–000F`. |
| `0100–20FF` | 8,192 | `0AH` Pattern | Nibble-packed, low nibble first. |
| `2100–25BF` | 1,216 | `0BH` Rhythm Track | Nibble-packed, low nibble first. |
| `2600–27F5` | 502 | `0CH` Sequencer Header | Direct copy. |
| `2800–2953` | 340 | `09H` Rhythm Setup | Direct copy. |
| `2A00–2FFF` | 1,536 | Native mirror | Must match native bytes `1E00–23FF` exactly. |

The intervening unused/reserved bytes are retained as part of the file but are
not independently decoded. The Rhythm converter validates the mandatory
mirror before writing a native file.
