"""Read-only inspection of Roland D-20 SysEx dumps and native containers."""

from __future__ import annotations

from collections import Counter
import csv
import html
import io
import json
from pathlib import Path

from .core import D20Error, MemoryImage, assemble_partial, atomic_write, make_messages, note_name, printable_text, read_file, require_new_output, scan_messages, scan_midi, scan_syx, user_tone_names
from . import pattern, reports


SOUND_FILE_SIZE = 24_576
RHYTHM_FILE_SIZE = 12_288
SONG_FILE_SIZE = 27_648
ALL_FILE_SIZE = 49_152
SONG_EMBEDDED_RHYTHM_OFFSET = 0x3B00
ALL_SOUND_OFFSET = 0x3B00
ALL_RHYTHM_OFFSET = 0x9000


LABELS = {
    0x04: "Temporary Tone",
    0x05: "Timbre",
    0x07: "Patch",
    0x08: "Tone",
    0x09: "Rhythm Setup",
    0x0A: "Rhythm Pattern",
    0x0B: "Rhythm Track",
    0x0C: "Sequencer Header",
    0x10: "System",
}
COMPLETE_ALL_AREAS = frozenset((0x05, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x10))
AREA_SIZES = {0x04: 16_384, 0x05: 1_024, 0x07: 4_864, 0x08: 16_384, 0x09: 340, 0x0A: 16_384, 0x0B: 2_432, 0x0C: 502, 0x10: 50}


def _disk_name(raw: bytes, source: Path) -> str:
    name = raw[6:16]
    if any(byte and not 32 <= byte <= 126 for byte in name):
        raise D20Error("The native D-20 filename field contains invalid bytes.")
    return name.decode("ascii", "replace").strip() or source.stem.upper()[:10]


def native_type(path: Path) -> tuple[str, str] | None:
    """Identify a native container by its validated contents, never its suffix."""
    source = path.expanduser()
    raw = read_file(source)
    if len(raw) == SOUND_FILE_SIZE and raw[:3] == b"\x03\x00\x00":
        from . import sound

        name, _, _, _ = sound.decode(source)
        return "SOUND", name
    if len(raw) == RHYTHM_FILE_SIZE and raw[:3] == b"\x04\x00\x00":
        from . import rhythm

        name, _, _, _, _ = rhythm.decode(source)
        return "RHYTHM", name
    if (
        len(raw) == SONG_FILE_SIZE
        and raw[2] == 0x03
        and pattern.valid_header(*raw[SONG_EMBEDDED_RHYTHM_OFFSET : SONG_EMBEDDED_RHYTHM_OFFSET + 3])
    ):
        return "SONG", _disk_name(raw, source)
    if len(raw) == ALL_FILE_SIZE and raw[2] == 0x03 and raw[0x10] == 0x01:
        return "ALL", _disk_name(raw, source)
    return None


def _sound_messages(raw: bytes, offset: int) -> list:
    """Expand a Sound data region stored without its disk header/mirror."""
    from . import sound

    tones = MemoryImage.create(sound.TONE_COUNT * sound.TONE_SYSEX_SIZE)
    for index in range(sound.TONE_COUNT):
        start = offset + index * sound.TONE_DISK_SIZE
        tones.write(index * sound.TONE_SYSEX_SIZE, raw[start : start + sound.TONE_DISK_SIZE] + b"\x00" * 10, "embedded Sound Tone memory")
    timbres = MemoryImage.create(sound.TIMBRE_COUNT * sound.TIMBRE_SIZE)
    timbres.write(0, raw[offset + sound.TIMBRE_OFFSET - sound.HEADER_SIZE : offset + sound.PATCH_OFFSET - sound.HEADER_SIZE], "embedded Sound Timbre memory")
    patches = MemoryImage.create(sound.PATCH_COUNT * sound.PATCH_SIZE)
    patches.write(0, raw[offset + sound.PATCH_OFFSET - sound.HEADER_SIZE : offset + sound.PATCH_MIRROR_OFFSET - sound.HEADER_SIZE], "embedded Sound Patch memory")
    return scan_messages([*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10)])


def _rhythm_messages(raw: bytes, offset: int) -> list:
    """Expand a Rhythm data region stored without its disk header."""
    from . import rhythm

    def relative(native_offset: int) -> int:
        return offset + native_offset - rhythm.HEADER_SIZE
    mirror = raw[relative(rhythm.MIRROR_OFFSET) : relative(rhythm.MIRROR_OFFSET) + rhythm.MIRROR_SIZE]
    expected = raw[relative(rhythm.MIRROR_SOURCE) : relative(rhythm.MIRROR_SOURCE) + rhythm.MIRROR_SIZE]
    if mirror != expected:
        raise D20Error("The embedded Rhythm mirror region does not match its source data.")
    pattern = MemoryImage.create(rhythm.PATTERN_SIZE)
    pattern.write(0, rhythm.unpack_nibbles(raw[relative(rhythm.PATTERN_OFFSET) : relative(rhythm.PATTERN_OFFSET) + rhythm.PATTERN_SIZE // 2]), "embedded Rhythm Pattern memory")
    track = MemoryImage.create(rhythm.TRACK_SIZE)
    track.write(0, rhythm.unpack_nibbles(raw[relative(rhythm.TRACK_OFFSET) : relative(rhythm.TRACK_OFFSET) + rhythm.TRACK_SIZE // 2]), "embedded Rhythm Track")
    sequencer = MemoryImage.create(rhythm.SEQUENCER_SIZE)
    sequencer.write(0, raw[relative(rhythm.SEQUENCER_OFFSET) : relative(rhythm.SEQUENCER_OFFSET) + rhythm.SEQUENCER_SIZE], "embedded Rhythm Sequencer Header")
    setup = MemoryImage.create(rhythm.SETUP_SIZE)
    setup.write(0, raw[relative(rhythm.SETUP_OFFSET) : relative(rhythm.SETUP_OFFSET) + rhythm.SETUP_SIZE], "embedded Rhythm Setup")
    return scan_messages([*make_messages(0x09, setup, 0x10), *make_messages(0x0A, pattern, 0x10), *make_messages(0x0B, track, 0x10), *make_messages(0x0C, sequencer, 0x10)])


def _native_messages(kind: str, path: Path) -> list:
    """Expand native container data into validated DT1-equivalent messages."""
    source = path.expanduser()
    raw = read_file(source)
    if kind == "SOUND":
        return _sound_messages(raw, 0x100)
    if kind == "RHYTHM":
        return _rhythm_messages(raw, 0x100)
    if kind == "SONG":
        return _rhythm_messages(raw, SONG_EMBEDDED_RHYTHM_OFFSET)
    if kind == "ALL":
        return [*_sound_messages(raw, ALL_SOUND_OFFSET), *_rhythm_messages(raw, ALL_RHYTHM_OFFSET)]
    raise ValueError(f"Unsupported native type: {kind}")


def _native_detail(kind: str) -> str:
    if kind == "SONG":
        return "Embedded Rhythm data was expanded; real-time Song events have no DT1-memory equivalent."
    if kind == "ALL":
        return "Embedded Sound and Rhythm data were expanded; System settings are not stored as a DT1 area in this disk container."
    return f"Native {kind.title()} data was expanded to DT1-equivalent messages."


def _classify_blocks(blocks: Counter[int], messages=None) -> tuple[str, str]:
    if COMPLETE_ALL_AREAS <= blocks.keys() and messages is not None and all(
        assemble_partial(messages, area, AREA_SIZES[area], LABELS[area]).complete()
        for area in COMPLETE_ALL_AREAS
    ):
        return "ALL_DUMP", "Every complete-backup memory area, including System, is present."
    if 0x10 in blocks:
        return "SYSTEM_DUMP", "The System area is present, but this is not a complete All MIDI/SysEx dump."
    sound = any(area in blocks for area in (0x04, 0x05, 0x07, 0x08))
    rhythm = any(area in blocks for area in (0x09, 0x0A, 0x0B, 0x0C))
    if sound and rhythm:
        return "MIXED", "Both Sound and Rhythm memory areas are present."
    if sound:
        return "SOUND", "Sound memory areas are present."
    if rhythm:
        return "RHYTHM", "Rhythm memory areas are present."
    return "UNKNOWN", "No recognised D-20 memory area is present."


def _declaration(kind: str) -> str:
    if kind == "ALL_DISK":
        return "This is an ALL (DISK) file."
    if kind == "ALL_DUMP":
        return "This is an ALL (MIDI DUMP) file."
    if kind == "SYSTEM_DUMP":
        return "This is a System-inclusive MIDI/SysEx dump."
    return f"This is {'an' if kind == 'ALL' else 'a'} {kind} file."


def report(path: Path) -> str:
    source = path.expanduser()
    native = native_type(source)
    if native:
        kind, _ = native
        messages = _native_messages(kind, source)
    elif source.suffix.lower() == ".syx":
        messages = scan_syx(source)
    elif source.suffix.lower() in {".mid", ".midi"}:
        messages = scan_midi(source)
    else:
        raise D20Error("Inspection accepts MIDI (.mid/.midi), raw SysEx (.syx), or recognised native D-20 files.")
    if not messages:
        raise D20Error("No valid Roland D-20 DT1 messages were found.")
    blocks = Counter(message.address[0] for message in messages)
    lines = [f"D-20 DT1 inspection: {source.name}", f"Valid messages: {len(messages)}"]
    for area, count in sorted(blocks.items()):
        lines.append(f"  {area:02X}H  {LABELS.get(area, 'Unknown')}: {count} message(s)")
    if native:
        kind, _ = native
        if kind in {"SONG", "ALL"}:
            raw = read_file(source)
            event_data = raw[0x100:SONG_EMBEDDED_RHYTHM_OFFSET]
            from . import song
            try:
                notes = song.decode(raw)
                detail = f"BETA {len(notes.events)} note events, stored lanes {notes.lanes}"
            except D20Error:
                detail = "BETA note decode unavailable"
            try:
                detail += f"; saved tempo {song.saved_tempo(raw)} BPM"
            except D20Error as exc:
                detail += f"; saved tempo unavailable ({exc})"
            lines.append(f"  Song event stream: {len(event_data):,} bytes; {sum(bool(value) for value in event_data):,} non-zero bytes ({detail})")
        if kind == "ALL":
            kind, detail = "ALL_DISK", _native_detail("ALL")
        else:
            detail = _native_detail(kind)
    else:
        kind, detail = _classify_blocks(blocks, messages)
    lines.extend(("", detail, _declaration(kind)))
    return "\n".join(lines)


def _inspection_data(path: Path):
    """Load one supported input once for concise and structured inspection."""
    source = path.expanduser()
    native = native_type(source)
    if native:
        kind, _ = native
        messages = _native_messages(kind, source)
    elif source.suffix.lower() == ".syx":
        messages = scan_syx(source)
    elif source.suffix.lower() in {".mid", ".midi"}:
        messages = scan_midi(source)
    else:
        raise D20Error("Inspection accepts MIDI (.mid/.midi), raw SysEx (.syx), or recognised native D-20 files.")
    if not messages:
        raise D20Error("No valid Roland D-20 DT1 messages were found.")
    return source, native, messages


def _complete_records(messages, area: int, record_size: int, count: int, label: str):
    image = assemble_partial(messages, area, record_size * count, label)
    return image, [index for index in range(count) if image.complete(index * record_size, record_size)]


def _tone_rows(messages):
    names = user_tone_names(messages)
    area = 0x08 if any(message.address[0] == 0x08 for message in messages) else 0x04
    image, complete = _complete_records(messages, area, 256, 64, "Tone data")
    return area, [(f"i{index + 1:02d}", names.get(index, printable_text(image.data[index * 256 : index * 256 + 10]) or "(unnamed)")) for index in complete]


def _timbre_rows(messages, names):
    image, complete = _complete_records(messages, 0x05, 8, 128, "Timbre data")
    rows = []
    for index in complete:
        data = image.data[index * 8 : index * 8 + 8]
        group, number = data[:2]
        source = ("Preset A", "Preset B", "User", "Rhythm")[group] if group < 4 else "Unknown"
        identifier = ("a", "b", "i", "r")[group] + f"{number + 1:02d}" if group < 4 else f"Invalid({group}:{number + 1})"
        resolved = reports._tone_label(group, number, names, parenthesize_name=False)
        tone_name = resolved[len(identifier) + 1 :] if resolved.startswith(identifier + " ") else resolved
        rows.append((reports._timbre_id(index), source, identifier, tone_name, f"{data[2] - 24:+d}", f"{data[3] - 50:+d}", str(data[4]), str(data[5] + 1), "ON" if data[6] else "OFF"))
    return rows


def _patch_rows(messages, names):
    image, complete = _complete_records(messages, 0x07, 38, 128, "Patch data")
    rows = []
    layouts = ("Whole", "Dual", "Split")
    for index in complete:
        data = image.data[index * 38 : index * 38 + 38]
        lower_id = ("a", "b", "i", "r")[data[2]] + f"{data[3] + 1:02d}" if data[2] < 4 else f"Invalid({data[2]}:{data[3] + 1})"
        upper_id = ("a", "b", "i", "r")[data[4]] + f"{data[5] + 1:02d}" if data[4] < 4 else f"Invalid({data[4]}:{data[5] + 1})"
        lower = reports._tone_label(data[2], data[3], names, parenthesize_name=False)
        upper = reports._tone_label(data[4], data[5], names, parenthesize_name=False)
        lower_name = lower[len(lower_id) + 1 :] if lower.startswith(lower_id + " ") else lower
        upper_name = upper[len(upper_id) + 1 :] if upper.startswith(upper_id + " ") else upper
        rows.append((str(index + 1), printable_text(data[21:37]) or "(unnamed)", layouts[data[0]] if data[0] < len(layouts) else f"Unknown({data[0]})", note_name(data[1]), lower_id, lower_name, upper_id, upper_name, str(data[20])))
    return rows


def _rhythm_rows(messages, names):
    image, complete = _complete_records(messages, 0x09, 4, 85, "Rhythm Setup data")
    rows = []
    for index in complete:
        tone, level, pan, reverb = image.data[index * 4 : index * 4 + 4]
        group, number = (2, tone) if tone < 64 else (3, tone - 64)
        identifier = ("a", "b", "i", "r")[group] + f"{number + 1:02d}"
        resolved = reports._tone_label(group, number, names, parenthesize_name=False)
        tone_name = resolved[len(identifier) + 1 :] if resolved.startswith(identifier + " ") else resolved
        pan_text = "Center" if pan == 7 else f"L{7 - pan}" if pan < 7 else f"R{pan - 7}"
        rows.append((note_name(index + 24), identifier, tone_name, str(level), pan_text, "ON" if reverb else "OFF"))
    return rows


def _system_rows(messages):
    image = assemble_partial(messages, 0x10, 50, "System data")
    if not image.complete(0, 50):
        return []
    data = image.data
    rows = [("Part " + str(index + 1), str(data[4 + index]), str(data[33 + index]), "Center" if data[42 + index] == 7 else f"L{7 - data[42 + index]}" if data[42 + index] < 7 else f"R{data[42 + index] - 7}", str(data[20 + index] + 1)) for index in range(8)]
    rows.append(("Rhythm", str(data[12]), str(data[41]), "Per-key", str(data[13] + 1)))
    return rows


def _song_metadata(source: Path, native) -> list[tuple[str, str]]:
    if not native or native[0] not in {"SONG", "ALL"}:
        return []
    raw = read_file(source)
    event_data = raw[0x100:SONG_EMBEDDED_RHYTHM_OFFSET]
    from . import song
    try:
        notes = song.decode(raw)
        note_details = f"BETA: {len(notes.events)} note events on stored lanes {notes.lanes}; 96 positions per quarter"
        meter_details = f"{notes.pattern_count} pattern selections; changes {notes.meter_changes}" if notes.pattern_count else "Pattern meter unverified"
    except D20Error:
        note_details = "BETA note decode unavailable for this container"
        meter_details = "Pattern meter unverified"
    try:
        tempo_details = f"Saved tempo {song.saved_tempo(raw)} BPM; original track routing remains undecoded."
    except D20Error as exc:
        tempo_details = f"Saved tempo unavailable ({exc}); original track routing remains undecoded."
    rhythm_description = (
        f"{len(raw) - SONG_EMBEDDED_RHYTHM_OFFSET:,} bytes including the 256-byte Rhythm header; expanded to areas 09H, 0AH, 0BH, and 0CH"
        if native[0] == "SONG"
        else "Native All container retains a Song event-stream region; its Rhythm data is listed separately in the recognised memory areas."
    )
    return [
        ("Container name", native[1] + (" (embedded Song region)" if native[0] == "ALL" else "")),
        ("Native event-stream region", f"{len(event_data):,} bytes; {sum(bool(value) for value in event_data):,} non-zero bytes"),
        ("Rhythm data", rhythm_description),
        ("BETA note events", note_details),
        ("BETA rhythm-chain meter", meter_details),
        ("Tempo / track count", tempo_details),
    ]


def _markdown_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    def clean(value: str) -> str:
        return value.replace("|", "\\|")
    return ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|", *("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)]


def _partial_area_rows(messages, blocks) -> list[tuple[str, str, str]]:
    rows = []
    for area in sorted(blocks):
        size = AREA_SIZES.get(area)
        if size is None:
            continue
        image = assemble_partial(messages, area, size, LABELS.get(area, "data"))
        if not image.complete():
            rows.append((f"{area:02X}H {LABELS.get(area, 'Unknown')}", f"{image.coverage():,} / {size:,} bytes", "Incomplete: records are omitted from detailed tables until all bytes are present."))
    return rows


def _machine_sections(sections):
    return [
        {"section": title, "columns": list(headers), "rows": [dict(zip(headers, row, strict=True)) for row in rows]}
        for title, headers, rows in sections
    ]


def detailed_report(path: Path, *, format: str = "markdown") -> str:
    """Render a comprehensive, read-only inventory of recognised D-20 data."""
    source, native, messages = _inspection_data(path)
    names = user_tone_names(messages)
    blocks = Counter(message.address[0] for message in messages)
    inspection_kind, inspection_detail = (native[0], _native_detail(native[0])) if native else _classify_blocks(blocks, messages)
    partial_rows = _partial_area_rows(messages, blocks)
    area_rows = [(f"{area:02X}H", LABELS.get(area, "Unknown"), str(count), f"{len({message.offset + index for message in messages if message.address[0] == area for index in range(len(message.payload))}):,}", f"{AREA_SIZES[area]:,}" if area in AREA_SIZES else "Unknown", "Unknown" if area not in AREA_SIZES else "PARTIAL" if any(row[0].startswith(f"{area:02X}H ") for row in partial_rows) else "Complete") for area, count in sorted(blocks.items())]
    tone_area, tones = _tone_rows(messages) if any(area in blocks for area in (0x04, 0x08)) else (None, [])
    timbres = _timbre_rows(messages, names) if 0x05 in blocks else []
    patches = _patch_rows(messages, names) if 0x07 in blocks else []
    rhythm = _rhythm_rows(messages, names) if 0x09 in blocks else []
    system = _system_rows(messages) if 0x10 in blocks else []
    song = _song_metadata(source, native)
    sections = [("Recognised memory areas", ("Area", "Meaning", "Messages", "Bytes present", "Expected bytes", "Status"), area_rows)]
    if partial_rows:
        sections.append(("Incomplete / partial data", ("Area", "Coverage", "Handling"), partial_rows))
    if song:
        sections.append(("Native Song data", ("Item", "Value"), song))
    if system:
        sections.append(("System settings", ("Part", "Reserve", "Level", "Pan", "Stored MIDI channel"), system))
    if tones:
        sections.extend(((f"Internal/user Tones ({tone_area:02X}H): i01 to i32", ("Tone", "Tone name"), tones[:32]), (f"Internal/user Tones ({tone_area:02X}H): i33 to i64", ("Tone", "Tone name"), tones[32:])))
    if timbres:
        sections.extend((("Timbres A (A-11 to A-88)", ("Timbre", "Source", "Tone", "Tone name", "Shift", "Fine", "Bend", "Assign", "Reverb"), timbres[:64]), ("Timbres B (B-11 to B-88)", ("Timbre", "Source", "Tone", "Tone name", "Shift", "Fine", "Bend", "Assign", "Reverb"), timbres[64:])))
    if patches:
        sections.extend((("Patches 1 to 64", ("Patch", "Name", "Layout", "Split", "Lower Tone", "Lower Tone name", "Upper Tone", "Upper Tone name", "Level"), patches[:64]), ("Patches 65 to 128", ("Patch", "Name", "Layout", "Split", "Lower Tone", "Lower Tone name", "Upper Tone", "Upper Tone name", "Level"), patches[64:])))
    if rhythm:
        sections.append(("Rhythm Setup", ("Note", "Tone", "Tone name", "Level", "Pan", "Reverb"), rhythm))
    opaque = [(f"{area:02X}H {LABELS[area]}", "Present and preserved; musical events are not decoded.") for area in (0x0A, 0x0B, 0x0C) if area in blocks]
    if opaque:
        sections.append(("Undecoded data", ("Area", "Handling"), opaque))
    machine = _machine_sections(sections)
    if format == "json":
        return json.dumps({"source": source.name, "inspection_type": inspection_kind, "detail": inspection_detail, "valid_messages": len(messages), "sections": machine}, indent=2) + "\n"
    if format == "csv":
        fields = ("section", "area", "meaning", "messages", "bytes_present", "expected_bytes", "status", "coverage", "handling", "item", "value", "part", "reserve", "level", "pan", "stored_midi_channel", "tone", "tone_name", "target", "source", "shift", "fine", "bend", "assign", "reverb", "patch", "name", "layout", "split", "lower_tone", "lower_tone_name", "upper_tone", "upper_tone_name", "note")
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for section in machine:
            for row in section["rows"]:
                normalized = {key.lower().replace(" ", "_").replace("/", "_"): value for key, value in row.items()}
                writer.writerow({"section": section["section"], **normalized})
        return stream.getvalue()
    if format == "html":
        def table(title, headers, rows):
            table_class = " tone-table" if headers == ("Tone", "Tone name") else " rhythm-table" if headers[:3] == ("Note", "Tone", "Tone name") else ""
            return f"<section><h3>{html.escape(title)}</h3><table class=\"{table_class.strip()}\"><thead><tr>{''.join(f'<th>{html.escape(head)}</th>' for head in headers)}</tr></thead><tbody>{''.join('<tr>' + ''.join(f'<td>{html.escape(value)}</td>' for value in row) + '</tr>' for row in rows)}</tbody></table></section>"
        body_parts, paired = [], []
        for title, headers, rows in sections:
            if title.startswith(("Internal/user Tones", "Timbres ", "Patches ")):
                paired.append(table(title, headers, rows))
                if len(paired) == 2:
                    body_parts.append('<div class="paired">' + ''.join(paired) + "</div>")
                    paired = []
            else:
                table_class = "rhythm-table" if headers[:3] == ("Note", "Tone", "Tone name") else ""
                body_parts.append(f"<section><h2>{html.escape(title)}</h2><table class=\"{table_class}\"><thead><tr>{''.join(f'<th>{html.escape(head)}</th>' for head in headers)}</tr></thead><tbody>{''.join('<tr>' + ''.join(f'<td>{html.escape(value)}</td>' for value in row) + '</tr>' for row in rows)}</tbody></table></section>")
        body = ''.join(body_parts + paired)
        native_label = f" ({native[0]})" if native else ""
        return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>D-20 inspection report</title><style>body{{font:15px/1.45 system-ui,sans-serif;margin:2rem;color:#17202a}}main{{max-width:1500px;margin:auto}}table{{border-collapse:collapse;width:100%;margin:1rem 0 2rem;font-size:.9rem}}th,td{{border:1px solid #ccd3d9;padding:.4rem;text-align:left;vertical-align:top}}th{{background:#eef3f7;position:sticky;top:0}}tr:nth-child(even){{background:#f8fafb}}.note{{background:#eef6ff;border-left:5px solid #4385c5;padding:1rem}}.paired{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.5rem}}.paired table{{font-size:.8rem}}.tone-table th:first-child,.tone-table td:first-child,.rhythm-table th:nth-child(2),.rhythm-table td:nth-child(2){{width:4.5rem;white-space:nowrap}}.rhythm-table th:first-child,.rhythm-table td:first-child{{width:5.5rem;white-space:nowrap}}.tone-table th:nth-child(2),.tone-table td:nth-child(2),.rhythm-table th:nth-child(3),.rhythm-table td:nth-child(3){{width:13rem;max-width:13rem;overflow-wrap:anywhere}}@media(max-width:1000px){{.paired{{display:block}}}}</style></head><body><main><h1>D-20 inspection report</h1><p class="note"><strong>{html.escape(inspection_kind)}:</strong> {html.escape(inspection_detail)}<br>Pattern, Rhythm Track, Sequencer Header, and native Song event data are not musically decoded.</p><p><strong>Source:</strong> <code>{html.escape(source.name)}</code>{native_label}<br><strong>Valid DT1-equivalent messages:</strong> {len(messages)}</p>{body}</main></body></html>\n'
    lines = ["# D-20 inspection report", "", f"Source: `{source.name}`" + (f" ({native[0]})" if native else ""), f"Inspection type: **{inspection_kind}** — {inspection_detail}", f"Valid DT1-equivalent messages: {len(messages)}", "", "Read-only inventory: Pattern, Rhythm Track, Sequencer Header, and native Song event data are not musically decoded."]
    for title, headers, rows in sections:
        lines.extend(("", f"## {title}", "", *_markdown_table(headers, rows)))
    return "\n".join(lines) + "\n"


def write_detailed_report(path: Path, destination: Path, *, format: str, force: bool) -> None:
    destination = destination.expanduser()
    require_new_output(path.expanduser(), destination, force)
    atomic_write(destination, detailed_report(path, format=format).encode("utf-8"))
