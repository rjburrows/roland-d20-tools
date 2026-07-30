# D-20 memory-address reference

This is the address map implemented by the converters and diagnostic reports.
It is a source-derived engineering reference, not a replacement for Roland's
manual. A SysEx DT1 address has three 7-bit bytes: `MSB MID LSB`. Within an
area, the byte offset is `MID × 128 + LSB`; all ranges below are inclusive.

## SysEx areas

| Address area | Bytes | Used by | Meaning |
| --- | ---: | --- | --- |
| `04H 00 00–7F 7F` | 16,384 | Tone report | Temporary editable Tone memory (used only when no permanent Tone data is present). |
| `05H 00 00–07 7F` | 1,024 | Sound converter; Timbre report | 128 Timbre records × 8 bytes. |
| `07H 00 00–25 7F` | 4,864 | Sound converter; Patch report | 128 Patch records × 38 bytes. |
| `08H 00 00–7F 7F` | 16,384 | Sound converter; Tone report | 64 permanent internal/user Tone records × 256 bytes. |
| `09H 00 00–02 53` | 340 | Rhythm converter; Rhythm report | Rhythm Setup: 85 notes × 4 bytes. |
| `0AH 00 00–7F 7F` | 16,384 | Rhythm converter; compact inspection | Rhythm Patterns. |
| `0BH 00 00–12 7F` | 2,432 | Rhythm converter; compact inspection | Rhythm Track. |
| `0CH 00 00–03 75` | 502 | Rhythm converter; compact inspection | Sequencer Header. |
| `10H 00 00–00 31` | 50 | System report; compact inspection | Global System settings. |

`inspect` recognises each row but only prints message counts. The five `report`
decoders read `04H/05H/07H/08H/09H/10H`; `0AH/0BH/0CH` are preserved by the
Rhythm converter but are not yet interpreted as musical events.

Preset A and Preset B Tone definitions are fixed ROM content, not editable
DT1 Tone-memory records. The Tone report therefore exposes only internal/user
Tones (`i01–i64`); the other reports show preset names only when referenced.

## Detailed report records

| Module/report | Record and base address | Byte offsets interpreted |
| --- | --- | --- |
| System | One 50-byte record at `10H 00 00` | `0` master tune; `1–3` reverb mode/time/level; `4–11` part reserve; `12` rhythm reserve; `13` rhythm stored channel; `20–27` part stored channels; `33–40` part levels; `41` rhythm level; `42–49` part pans. |
| Patch | 128 × 38, record *n* begins at `07H`, offset `38n` | `0` key mode; `1` split; `2–5` lower/upper tone group + number; `6–15` lower/upper shift, fine tune, bender, assign and reverb switch; `16–20` reverb/balance/level; `21–36` name. Byte `37` is not decoded. |
| Timbre | 128 × 8, record *n* begins at `05H`, offset `8n` | Two 64-record panel banks: `A-11…A-88` then `B-11…B-88`. Bytes `0–1` tone group + number; `2` key shift; `3` fine tune; `4` bender; `5` assign; `6` reverb switch. Byte `7` is not decoded. |
| Tone | 64 × 256, record *n* begins at `08H` (or `04H`), offset `256n` | `0–9` name; `10–11` structures; `12` partial mask; `13` envelope mode; four 58-byte partials at `14`, `72`, `130`, `188`. Bytes `246–255` are not interpreted. |
| Rhythm Setup | 85 × 4, record *n* begins at `09H`, offset `4n` | One record for MIDI note `24+n` (C1 through C8): `0` tone (`0–63` user, `64–127` rhythm/off); `1` level; `2` pan; `3` reverb switch. |

Each 58-byte Tone partial has this implemented layout: `0–7` wave generator
(pitch, fine tune, key follow, bender, wave/PCM selection and pulse-width
values); `8–19` pitch envelope; `20–22` LFO; `23–40` TVF and its envelope; and
`41–57` TVA and its envelope. The detailed Tone report displays the safe,
meaningful fields within those groups.

For a PCM (`P`) partial, wave-generator byte `4` is a bank selector and byte
`5` is a zero-based waveform index (`0–127`). The supplied D-20 PCM reference
labels the same data as **Bank 1** or **Bank 2**, and **No. 1–128**. Factory
Tone data uses selectors `0`, `2`, and `3`: `0` selects PCM bank `0`
(reference Bank 1), while any non-zero selector selects PCM bank `1`
(reference Bank 2). The report preserves an unusual raw selector in its
output. For example, stored selector `0`, index `61` is shown as `PCM bank 0,
wave 62 (Acoustic Bass; stored index 61, reference Bank 1)`.

## Manual-checked ranges and offsets

The following report conversions were checked against the supplied D-20 Patch
Setup and Tone Parameters manuals, including their stated minimum and maximum
values, and exercised against the factory `D1020ORIG.MID` dump.

| Report field | Stored bytes | Stored range → displayed range |
| --- | --- | --- |
| Timbre key shift | record `2` | `0–48` → `−24…+24` |
| Timbre fine tune | record `3` | `0–100` → `−50…+50` |
| Timbre bender / assign / reverb | record `4` / `5` / `6` | `0–24` / `0–3` → modes `1–4` / `0–1` |
| Tone WG coarse / fine | partial `0` / `1` | `0–96` → `C1…C9` / `0–100` → `−50…+50` |
| Tone pulse-width / velocity | partial `6` / `7` | `0–100` / `0–14` → `0…100` / `−7…+7` |
| Tone pitch envelope depth / velocity | partial `8` / `9` | `0–10` / `0–3` |
| Tone LFO and cutoff | partial `20–23` | each `0–100` |
| Tone resonance | partial `24` | `0–30` |
| Tone TVF Bias Level | partial `27` | `0–14` → `−7…+7` |
| Tone TVF / TVA Bias Point | partial `26` / `43,45` | `0–63` = `<A1…<C7`; `64–127` = `>A1…>C7` |
| Tone TVA Bias Level | partial `44,46` | `0–12` → `0…−12` |
| Tone TVA level / velocity | partial `41` / `42` | `0–100` / `0–100` → `−50…+50` |

When a displayed bounded field contains an out-of-range stored value, the
report says `Invalid(...; expected ...)` instead of silently converting it.

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
