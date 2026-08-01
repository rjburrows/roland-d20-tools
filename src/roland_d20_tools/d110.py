"""Experimental, one-way D-20 to D-110 SysEx conversion.

This module intentionally supports only the common LA-synthesis data needed
for a D-110 Rhythm Setup: user Tones, Timbres, and the 85 Rhythm keys.
"""

from __future__ import annotations

import csv
import html
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .core import D20Error, assemble, load_dt1, make_messages, printable_text, require_new_output, roland_checksum, write_syx
from .reports import PRESET_A, PRESET_B, RHYTHM_TONES


TONE_SIZE = 64 * 256
TIMBRE_SIZE = 128 * 8
RHYTHM_SIZE = 85 * 4


@dataclass(frozen=True, slots=True)
class RhythmRow:
    midi_note: int
    tone: str
    tone_name: str
    level: int
    pan: int
    output: str
    status: str


@dataclass(frozen=True, slots=True)
class ToneRow:
    tone: str
    tone_name: str


@dataclass(frozen=True, slots=True)
class TimbreRow:
    target: str
    tone: str
    tone_name: str
    key_shift: int
    fine_tune: int
    bender_range: int
    assign_mode: int
    d20_reverb: str
    d110_output: str
    status: str


def _note_name(note: int) -> str:
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return f"{names[note % 12]}{note // 12 - 1} ({note})"


def _tone_label(value: int) -> str:
    if value < 64:
        return f"i{value + 1:02d}"
    if value < 127:
        return f"r{value - 63:02d}"
    return "OFF (r64)"


def _tone_name(identifier: str, user_names: dict[int, str]) -> str:
    """Return the D-110/D-20 Tone name represented by a group identifier."""
    if identifier.startswith("OFF"):
        return "OFF"
    group, number = identifier[0], int(identifier[1:3]) - 1
    if group == "i":
        return user_names.get(number, "User Tone")
    if group == "r":
        return RHYTHM_TONES[number] if 0 <= number < len(RHYTHM_TONES) else "Unknown Rhythm Tone"
    if group == "a":
        return PRESET_A[number] if 0 <= number < len(PRESET_A) else "Unknown Preset A Tone"
    if group == "b":
        return PRESET_B[number] if 0 <= number < len(PRESET_B) else "Unknown Preset B Tone"
    return "OFF"


def _timbre_tone_label(group: int, number: int) -> str:
    """Return the common D-20/D-110 Tone identifier stored by a Timbre."""
    prefixes = ("a", "b", "i", "r")
    return f"{prefixes[group]}{number + 1:02d}" if 0 <= group < len(prefixes) else f"Invalid({group}:{number + 1})"


def _timbre_id(index: int) -> str:
    """Return the common D-20/D-110 panel-bank identifier for a Timbre."""
    bank = "A" if index < 64 else "B"
    item = index if index < 64 else index - 64
    return f"{bank}-{item // 8 + 1}{item % 8 + 1}"


def _converted_tones(user_names: dict[int, str]) -> list[ToneRow]:
    return [ToneRow(f"i{index + 1:02d}", user_names[index]) for index in range(64)]


def _converted_timbre_rows(source, user_names: dict[int, str]) -> list[TimbreRow]:
    rows: list[TimbreRow] = []
    for index in range(128):
        group, number, key_shift, fine_tune, bender_range, assign_mode, reverb, _ = source.data[index * 8 : index * 8 + 8]
        tone = _timbre_tone_label(group, number)
        rows.append(TimbreRow(
            _timbre_id(index), tone, _tone_name(tone, user_names), key_shift - 24,
            fine_tune - 50, bender_range, assign_mode + 1,
            "ON" if reverb else "OFF", "MIX",
            "D-20 reverb replaced" if reverb else "Direct fields copied",
        ))
    return rows


def _images(source: Path):
    messages = load_dt1(source)
    if not messages:
        raise D20Error("No valid Roland D-20 DT1 messages were found.")
    return (
        assemble(messages, 0x08, TONE_SIZE, "D-20 permanent Tone memory"),
        assemble(messages, 0x05, TIMBRE_SIZE, "D-20 Timbre memory"),
        assemble(messages, 0x09, RHYTHM_SIZE, "D-20 Rhythm Setup"),
    )


def _converted_timbres(source) -> tuple[bytearray, int]:
    result = bytearray(source.data)
    replaced = 0
    for offset in range(0, len(result), 8):
        if result[offset + 6]:
            replaced += 1
        # D-20: reverb switch. D-110: output assignment. 0 is MIX.
        result[offset + 6] = 0
    return result, replaced


def _check_range(label: str, value: int, minimum: int, maximum: int) -> None:
    if not minimum <= value <= maximum:
        raise D20Error(f"D-110 {label} has invalid value {value}; expected {minimum}..{maximum}.")


def _validate_timbres(data: bytes) -> None:
    for index in range(128):
        offset = index * 8
        group, number, shift, fine, bender, assign, output = data[offset : offset + 7]
        _check_range(f"Timbre {index + 1} tone group", group, 0, 3)
        _check_range(f"Timbre {index + 1} tone number", number, 0, 63)
        _check_range(f"Timbre {index + 1} key shift", shift, 0, 48)
        _check_range(f"Timbre {index + 1} fine tune", fine, 0, 100)
        _check_range(f"Timbre {index + 1} bender range", bender, 0, 24)
        _check_range(f"Timbre {index + 1} assign mode", assign, 0, 3)
        _check_range(f"Timbre {index + 1} output assignment", output, 0, 7)


def _validate_rhythm(data: bytes) -> None:
    for index in range(85):
        offset = index * 4
        tone, level, pan, output = data[offset : offset + 4]
        _check_range(f"Rhythm key {index + 24} tone", tone, 0, 127)
        _check_range(f"Rhythm key {index + 24} output level", level, 0, 100)
        _check_range(f"Rhythm key {index + 24} pan", pan, 0, 14)
        _check_range(f"Rhythm key {index + 24} output assignment", output, 0, 7)


def validate_messages(messages) -> None:
    """Validate the exact D-110 DT1 map emitted by this experimental tool."""
    expected = [(0x08, offset // 128, offset % 128, 256) for offset in range(0, TONE_SIZE, 256)]
    expected += [(0x05, offset // 128, offset % 128, 256) for offset in range(0, TIMBRE_SIZE, 256)]
    expected += [(0x03, 1, 16, 256), (0x03, 3, 16, 84)]
    actual = []
    tone_data = bytearray()
    timbre_data = bytearray()
    rhythm_data = bytearray()
    for message in messages:
        data = tuple(message.data)
        if len(data) < 9 or data[0] != 0x41 or data[2:4] != (0x16, 0x12):
            raise D20Error("Generated output contains an invalid D-110 Roland DT1 header.")
        address, payload, checksum = data[4:7], data[7:-1], data[-1]
        if checksum != roland_checksum((*address, *payload)):
            raise D20Error("Generated output contains an invalid D-110 DT1 checksum.")
        actual.append((*address, len(payload)))
        if address[0] == 0x08:
            tone_data.extend(payload)
        elif address[0] == 0x05:
            timbre_data.extend(payload)
        elif address[0] == 0x03:
            rhythm_data.extend(payload)
    if actual != expected:
        raise D20Error("Generated output does not match the supported D-110 Tone, Timbre, and Rhythm Setup address map.")
    if len(tone_data) != TONE_SIZE or any(any(tone_data[index + 246 : index + 256]) for index in range(0, TONE_SIZE, 256)):
        raise D20Error("Generated D-110 Tone memory has invalid reserved bytes or size.")
    _validate_timbres(timbre_data)
    _validate_rhythm(rhythm_data)


def _converted_rhythm(source, user_names: dict[int, str]) -> tuple[bytearray, list[RhythmRow], int]:
    result = bytearray(source.data)
    rows: list[RhythmRow] = []
    reverb_enabled = 0
    for index in range(85):
        offset, note = index * 4, index + 24
        tone, level, pan, reverb = source.data[offset : offset + 4]
        if reverb:
            reverb_enabled += 1
        # D-20: reverb switch. D-110: output assignment. 0 is MIX.
        result[offset + 3] = 0
        identifier = _tone_label(tone)
        rows.append(RhythmRow(note, identifier, _tone_name(identifier, user_names), level, pan, "MIX", "D-20 reverb omitted" if reverb else "Direct"))
    return result, rows, reverb_enabled


def report(source: Path, *, output_name: str, output_messages: int, format: str = "markdown") -> str:
    tones, timbres, rhythm = _images(source)
    user_names = {index: printable_text(tones.data[index * 256 : index * 256 + 10]) or "User Tone" for index in range(64)}
    _, timbre_replaced = _converted_timbres(timbres)
    tone_rows = _converted_tones(user_names)
    timbre_rows = _converted_timbre_rows(timbres, user_names)
    _, rhythm_rows, rhythm_replaced = _converted_rhythm(rhythm, user_names)
    payload = {
        "experimental": True,
        "source": source.name,
        "destination": output_name,
        "d110_messages": output_messages,
        "writes": [
            {"d20_area": "08", "d110_address": "08 00 00", "item": "64 permanent user Tones", "records": 64},
            {"d20_area": "05", "d110_address": "05 00 00", "item": "128 Timbres", "records": 128},
            {"d20_area": "09", "d110_address": "03 01 10", "item": "Rhythm Setup (keys 24-108)", "records": 85},
        ],
        "non_direct": [
            f"{timbre_replaced} D-20 Timbre reverb-switch values replaced with D-110 MIX output assignment.",
            f"{rhythm_replaced} D-20 Rhythm reverb-switch values omitted; D-110 uses per-key output assignment (MIX).",
            "D-20 Patch memory (07), Rhythm patterns (0A), Rhythm track (0B), and sequencer header (0C) are not converted.",
        ],
        "tones": [asdict(row) for row in tone_rows],
        "timbres": [asdict(row) for row in timbre_rows],
        "rhythm": [asdict(row) for row in rhythm_rows],
    }
    if format == "json":
        return json.dumps(payload, indent=2) + "\n"
    if format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=("section", "target", "note", "tone", "tone_name", "key_shift", "fine_tune", "bender_range", "assign_mode", "d20_reverb", "d110_output", "level", "pan", "status"))
        writer.writeheader()
        for row in tone_rows:
            writer.writerow({"section": "tone", "target": row.tone, "tone": row.tone, "tone_name": row.tone_name})
        for row in timbre_rows:
            writer.writerow({"section": "timbre", "target": row.target, "tone": row.tone, "tone_name": row.tone_name, "key_shift": row.key_shift, "fine_tune": row.fine_tune, "bender_range": row.bender_range, "assign_mode": row.assign_mode, "d20_reverb": row.d20_reverb, "d110_output": row.d110_output, "status": row.status})
        for row in rhythm_rows:
            writer.writerow({"section": "rhythm", "target": row.midi_note, "note": _note_name(row.midi_note), "tone": row.tone, "tone_name": row.tone_name, "level": row.level, "pan": row.pan, "d110_output": row.output, "status": row.status})
        return stream.getvalue()
    if format == "html":
        def tone_table(rows: list[ToneRow], title: str) -> str:
            body = "\n".join(
                f"<tr><td>{html.escape(row.tone)}</td><td>{html.escape(row.tone_name)}</td></tr>"
                for row in rows
            )
            return f"<section><h3>{title}</h3><table class=\"tone-table\"><thead><tr><th>Tone</th><th>Tone name</th></tr></thead><tbody>{body}</tbody></table></section>"
        tones_html = tone_table(tone_rows[:32], "Tones i01 to i32") + tone_table(tone_rows[32:], "Tones i33 to i64")
        def timbre_table(rows: list[TimbreRow], title: str) -> str:
            body = "\n".join(
                "<tr>"
                f"<td>{html.escape(row.target)}</td><td>{html.escape(row.tone)}</td><td>{html.escape(row.tone_name)}</td>"
                f"<td>{row.key_shift:+d}</td><td>{row.fine_tune:+d}</td><td>{row.bender_range}</td><td>{row.assign_mode}</td>"
                f"<td>{row.d20_reverb} &rarr; {row.d110_output}</td><td>{html.escape(row.status)}</td></tr>"
                for row in rows
            )
            return f"<section><h3>{title}</h3><table><thead><tr><th>Timbre</th><th>Tone</th><th>Tone name</th><th>Shift</th><th>Fine</th><th>Bend</th><th>Assign</th><th>Reverb &rarr; output</th><th>Status</th></tr></thead><tbody>{body}</tbody></table></section>"
        timbres_html = timbre_table(timbre_rows[:64], "Timbres A (A-11 to A-88)") + timbre_table(timbre_rows[64:], "Timbres B (B-11 to B-88)")
        rhythm_rows_html = "\n".join(
            "<tr>"
            f"<td>{html.escape(_note_name(row.midi_note))}</td>"
            f"<td>{html.escape(row.tone)}</td><td>{html.escape(row.tone_name)}</td>"
            f"<td>{row.level}</td><td>{row.pan}</td><td>{html.escape(row.output)}</td><td>{html.escape(row.status)}</td></tr>"
            for row in rhythm_rows
        )
        notices = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["non_direct"])
        source_name, destination_name = html.escape(source.name), html.escape(output_name)
        return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Experimental D-20 to D-110 conversion validation</title>
<style>body{{font:15px/1.45 system-ui,sans-serif;margin:2rem;color:#17202a}}main{{max-width:1500px;margin:auto}}.warning{{background:#fff4ce;border-left:5px solid #c79500;padding:1rem}}table{{border-collapse:collapse;width:100%;margin:1rem 0 2rem;font-size:.9rem}}th,td{{border:1px solid #ccd3d9;padding:.4rem;text-align:left;vertical-align:top}}th{{background:#eef3f7;position:sticky;top:0}}tr:nth-child(even){{background:#f8fafb}}code{{background:#f1f3f5;padding:.1rem .25rem}}.tones,.timbres{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.5rem}}.timbres table{{font-size:.78rem}}.tone-table th:first-child,.tone-table td:first-child,.rhythm-table th:nth-child(2),.rhythm-table td:nth-child(2){{width:4.5rem;white-space:nowrap}}.rhythm-table th:first-child,.rhythm-table td:first-child{{width:5.5rem;white-space:nowrap}}.tone-table th:nth-child(2),.tone-table td:nth-child(2),.rhythm-table th:nth-child(3),.rhythm-table td:nth-child(3){{width:13rem;max-width:13rem;overflow-wrap:anywhere}}@media(max-width:1000px){{.tones,.timbres{{display:block}}}}</style>
</head><body><main><h1>Experimental D-20 to D-110 conversion validation</h1><p class=\"warning\"><strong>Experimental:</strong> review this report before sending the SysEx to hardware.</p>
<p><strong>Source:</strong> <code>{source_name}</code><br><strong>D-110 output:</strong> <code>{destination_name}</code> ({output_messages} DT1 messages)</p>
<h2>D-110 destination blocks</h2><table><thead><tr><th>D-20 area</th><th>D-110 address</th><th>Data sent</th><th>Records</th></tr></thead><tbody><tr><td>08</td><td>08 00 00</td><td>Permanent internal user Tones</td><td>64</td></tr><tr><td>05</td><td>05 00 00</td><td>Internal Timbres</td><td>128</td></tr><tr><td>09</td><td>03 01 10</td><td>Internal Rhythm Setup, notes 24-108</td><td>85</td></tr></tbody></table>
<h2>Transferred Tones</h2><p>Each shared D-20/D-110 user Tone name is sent to the matching internal slot.</p><div class="tones">{tones_html}</div>
<h2>Transferred Timbres</h2><p>All fields are copied directly except the D-20 reverb switch, which becomes the D-110 output assignment <code>MIX</code>.</p><div class=\"timbres\">{timbres_html}</div>
<h2>Rhythm-key comparison</h2><table class="rhythm-table"><thead><tr><th>Key</th><th>Tone</th><th>Tone name</th><th>Level</th><th>Pan</th><th>Output</th><th>Status</th></tr></thead><tbody>{rhythm_rows_html}</tbody></table><h2>Non-direct translations</h2><ul>{notices}</ul></main></body></html>\n"""
    lines = [
        "# EXPERIMENTAL: D-20 to D-110 conversion validation",
        "",
        f"Source: `{source.name}`  ",
        f"D-110 output: `{output_name}` ({output_messages} DT1 messages)",
        "",
        "## D-110 destination blocks",
        "",
        "| D-20 area | D-110 address | Data sent | Records |",
        "|---|---|---|---:|",
        "| `08` | `08 00 00` | Permanent internal user Tones | 64 |",
        "| `05` | `05 00 00` | Internal Timbres | 128 |",
        "| `09` | `03 01 10` | Internal Rhythm Setup, notes 24-108 | 85 |",
        "",
        "## Transferred Tones",
        "",
        "Each shared D-20/D-110 user Tone name is sent to the matching internal slot.",
        "",
    ]
    for title, group in (("Tones i01 to i32", tone_rows[:32]), ("Tones i33 to i64", tone_rows[32:])):
        lines.extend((f"### {title}", "", "| Tone | Tone name |", "|---|---|"))
        lines.extend(f"| {row.tone} | {row.tone_name} |" for row in group)
        lines.append("")
    lines.extend(("", "## Transferred Timbres", "", "All fields are copied directly except the D-20 reverb switch, which becomes the D-110 output assignment `MIX`.", ""))
    for title, group in (("Timbres A (A-11 to A-88)", timbre_rows[:64]), ("Timbres B (B-11 to B-88)", timbre_rows[64:])):
        lines.extend((f"### {title}", "", "| Timbre | Tone | Tone name | Shift | Fine | Bend | Assign | Reverb → output | Status |", "|---|---|---|---:|---:|---:|---:|---|---|"))
        lines.extend(f"| {row.target} | {row.tone} | {row.tone_name} | {row.key_shift:+d} | {row.fine_tune:+d} | {row.bender_range} | {row.assign_mode} | {row.d20_reverb} → {row.d110_output} | {row.status} |" for row in group)
        lines.append("")
    lines.extend((
        "## Rhythm-key comparison",
        "",
        "| Key | Tone | Tone name | Level | Pan | Output | Status |",
        "|---|---|---|---:|---:|---|---|",
    ))
    lines.extend(f"| {_note_name(row.midi_note)} | {row.tone} | {row.tone_name} | {row.level} | {row.pan} | {row.output} | {row.status} |" for row in rhythm_rows)
    lines.extend(("", "## Non-direct translations", "", *(f"- {item}" for item in payload["non_direct"])))
    return "\n".join(lines) + "\n"


def convert(source: Path, destination: Path, *, device_id: int, force: bool, report_path: Path | None = None, report_format: str = "markdown") -> str:
    """Convert a complete D-20 dump into experimental D-110 DT1 SysEx."""
    source, destination = source.expanduser(), destination.expanduser()
    if source.suffix.lower() not in {".mid", ".midi", ".syx"}:
        raise D20Error("Experimental D-110 conversion accepts a complete D-20 .mid/.midi or .syx dump.")
    if destination.suffix.lower() != ".syx":
        raise D20Error("Experimental D-110 conversion writes raw SysEx; the destination must end in .syx.")
    require_new_output(source, destination, force)
    tones, timbres, rhythm = _images(source)
    d110_tones = bytearray(tones.data)
    for offset in range(0, TONE_SIZE, 256):
        # D-110 documents 246 active Tone bytes; do not send D-20's reserved tail.
        d110_tones[offset + 246 : offset + 256] = b"\x00" * 10
    d110_timbres, _ = _converted_timbres(timbres)
    user_names = {index: printable_text(tones.data[index * 256 : index * 256 + 10]) or "User Tone" for index in range(64)}
    d110_rhythm, _, _ = _converted_rhythm(rhythm, user_names)
    # Tone and Timbre memory are the D-110's persistent internal-memory blocks.
    # Rhythm Setup is its documented MIDI bulk-transfer block.
    from .core import MemoryImage

    timbre_image = MemoryImage.create(TIMBRE_SIZE)
    timbre_image.write(0, d110_timbres, "D-110 Timbre memory")
    rhythm_image = MemoryImage.create(RHYTHM_SIZE)
    rhythm_image.write(0, d110_rhythm, "D-110 Rhythm Setup")
    tone_image = MemoryImage.create(TONE_SIZE)
    tone_image.write(0, d110_tones, "D-110 Tone memory")
    messages = [*make_messages(0x08, tone_image, device_id), *make_messages(0x05, timbre_image, device_id)]
    # D-110 Rhythm Setup temporary/bulk-transfer base: 03 01 10, not a D-20 area.
    import mido
    from .core import roland_checksum

    for offset in range(0, RHYTHM_SIZE, 256):
        payload = rhythm_image.data[offset : offset + 256]
        d110_offset = 0x90 + offset  # 03 01 10 is offset 144 in its address area.
        address = (0x03, d110_offset // 128, d110_offset % 128)
        data = [0x41, device_id, 0x16, 0x12, *address, *payload]
        messages.append(mido.Message("sysex", data=[*data, roland_checksum(data[4:])]))
    validate_messages(messages)
    write_syx(destination, messages)
    rendered = report(source, output_name=destination.name, output_messages=len(messages), format=report_format)
    if report_path is not None:
        report_path = report_path.expanduser()
        if report_path.exists() and not force:
            raise D20Error(f"Report already exists: {report_path}. Use --force to replace it.")
        from .core import atomic_write

        atomic_write(report_path, rendered.encode("utf-8"))
        return f"Created experimental D-110 SysEx: {destination.name} ({len(messages)} DT1 messages).\nValidation report: {report_path}"
    return rendered
