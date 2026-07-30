"""Read-only inspection of Roland D-20 SysEx dumps and native containers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .core import D20Error, make_messages, read_file, scan_messages, scan_midi, scan_syx


SOUND_FILE_SIZE = 24_576
RHYTHM_FILE_SIZE = 12_288
SONG_FILE_SIZE = 27_648
ALL_FILE_SIZE = 49_152
SONG_EMBEDDED_RHYTHM_OFFSET = 0x3B00


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
        and raw[SONG_EMBEDDED_RHYTHM_OFFSET : SONG_EMBEDDED_RHYTHM_OFFSET + 3] == b"\x03\x11\x00"
    ):
        return "SONG", _disk_name(raw, source)
    if len(raw) == ALL_FILE_SIZE and raw[2] == 0x03 and raw[0x10] == 0x01:
        return "ALL", _disk_name(raw, source)
    return None


def _native_messages(kind: str, path: Path):
    """Expand validated Sound/Rhythm containers to their DT1-equivalent data."""
    if kind == "SOUND":
        from . import sound

        _, tones, timbres, patches = sound.decode(path)
        return scan_messages([*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10)])
    if kind == "RHYTHM":
        from . import rhythm

        _, setup, pattern, track, sequencer = rhythm.decode(path)
        return scan_messages([*make_messages(0x09, setup, 0x10), *make_messages(0x0A, pattern, 0x10), *make_messages(0x0B, track, 0x10), *make_messages(0x0C, sequencer, 0x10)])
    return []


def _classify_blocks(blocks: Counter[int]) -> tuple[str, str]:
    if 0x10 in blocks:
        return "ALL", "The System area is present."
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
    return f"This is {'an' if kind == 'ALL' else 'a'} {kind} file."


def report(path: Path) -> str:
    source = path.expanduser()
    native = native_type(source)
    if native and native[0] in {"SONG", "ALL"}:
        kind, name = native
        return "\n".join(
            (
                f"D-20 native inspection: {source.name}",
                f"Stored D-20 name: {name}",
                "Native file structure validated from its contents.",
                "",
                _declaration(kind),
            )
        )
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
    kind, detail = _classify_blocks(blocks)
    lines.extend(("", detail, _declaration(kind)))
    return "\n".join(lines)
