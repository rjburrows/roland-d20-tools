"""Read-only inspection of Roland D-20 SysEx dumps and native containers."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .core import D20Error, MemoryImage, make_messages, read_file, scan_messages, scan_midi, scan_syx


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


def _classify_blocks(blocks: Counter[int]) -> tuple[str, str]:
    if COMPLETE_ALL_AREAS <= blocks.keys():
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
        if kind == "ALL":
            kind, detail = "ALL_DISK", _native_detail("ALL")
        else:
            detail = _native_detail(kind)
    else:
        kind, detail = _classify_blocks(blocks)
    lines.extend(("", detail, _declaration(kind)))
    return "\n".join(lines)
