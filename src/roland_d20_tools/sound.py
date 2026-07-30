"""Conversion for native Roland D-20 Sound (.333) files."""

from __future__ import annotations

from pathlib import Path

from .core import D20Error, D20Message, MemoryImage, assemble, atomic_write, make_messages, read_file, require_new_output, scan_midi, scan_syx, write_midi, write_syx


FILE_SIZE, HEADER_SIZE = 24_576, 0x100
TONE_COUNT, TONE_DISK_SIZE, TONE_SYSEX_SIZE = 64, 246, 256
TIMBRE_COUNT, TIMBRE_SIZE = 128, 8
PATCH_COUNT, PATCH_SIZE = 128, 38
TONE_OFFSET, TIMBRE_OFFSET, PATCH_OFFSET = 0x0100, 0x3F00, 0x4300
PATCH_MIRROR_OFFSET, PATCH_MIRROR_SOURCE = 0x5600, 0x0700


def header(name: str) -> bytes:
    try:
        encoded = name.upper().encode("ascii", "strict")
    except UnicodeEncodeError as exc:
        raise D20Error("--name must use printable ASCII characters.") from exc
    if not 1 <= len(encoded) <= 10 or any(byte < 32 or byte > 126 for byte in encoded):
        raise D20Error("--name must contain 1 to 10 printable ASCII characters.")
    result = bytearray(HEADER_SIZE)
    result[:3] = b"\x03\x00\x00"
    result[6:16] = encoded.ljust(10, b" ")
    return bytes(result)


def decode(path: Path) -> tuple[str, MemoryImage, MemoryImage, MemoryImage]:
    raw = read_file(path)
    if len(raw) != FILE_SIZE:
        raise D20Error(f"A D-20 .333 Sound file must be {FILE_SIZE} bytes; this file is {len(raw)} bytes.")
    if raw[:3] != b"\x03\x00\x00":
        raise D20Error("This is not the expected D-20 Sound-file header (03 00 00).")
    name_bytes = raw[6:16]
    if any(byte and not 32 <= byte <= 126 for byte in name_bytes):
        raise D20Error("The Sound filename field contains invalid bytes.")
    name = name_bytes.decode("ascii", "replace").strip() or path.stem.upper()[:10]
    tones = MemoryImage.create(TONE_COUNT * TONE_SYSEX_SIZE)
    for index in range(TONE_COUNT):
        source = TONE_OFFSET + index * TONE_DISK_SIZE
        tones.write(index * TONE_SYSEX_SIZE, raw[source : source + TONE_DISK_SIZE] + b"\x00" * 10, "Sound tone memory")
    timbres = MemoryImage.create(TIMBRE_COUNT * TIMBRE_SIZE)
    timbres.write(0, raw[TIMBRE_OFFSET : TIMBRE_OFFSET + len(timbres.data)], "Sound timbre memory")
    patches = MemoryImage.create(PATCH_COUNT * PATCH_SIZE)
    patches.write(0, raw[PATCH_OFFSET : PATCH_OFFSET + len(patches.data)], "Sound patch memory")
    mirror = raw[PATCH_MIRROR_OFFSET:]
    expected = patches.data[PATCH_MIRROR_SOURCE : PATCH_MIRROR_SOURCE + len(mirror)]
    if mirror != expected:
        raise D20Error("The .333 duplicate patch region does not match primary patch data.")
    return name, tones, timbres, patches


def encode(name: str, messages: list[D20Message]) -> bytes:
    tones = assemble(messages, 0x08, TONE_COUNT * TONE_SYSEX_SIZE, "Tone Memory")
    timbres = assemble(messages, 0x05, TIMBRE_COUNT * TIMBRE_SIZE, "Timbre Memory")
    patches = assemble(messages, 0x07, PATCH_COUNT * PATCH_SIZE, "Patch Memory")
    for index in range(TONE_COUNT):
        end = (index + 1) * TONE_SYSEX_SIZE
        if any(tones.data[end - 10 : end]):
            raise D20Error(f"Tone {index + 1} has non-zero bytes 247-256, which .333 cannot represent.")
    raw = bytearray(FILE_SIZE)
    raw[:HEADER_SIZE] = header(name)
    for index in range(TONE_COUNT):
        target = TONE_OFFSET + index * TONE_DISK_SIZE
        raw[target : target + TONE_DISK_SIZE] = tones.data[index * TONE_SYSEX_SIZE : index * TONE_SYSEX_SIZE + TONE_DISK_SIZE]
    raw[TIMBRE_OFFSET : TIMBRE_OFFSET + len(timbres.data)] = timbres.data
    raw[PATCH_OFFSET : PATCH_OFFSET + len(patches.data)] = patches.data
    raw[PATCH_MIRROR_OFFSET:] = patches.data[PATCH_MIRROR_SOURCE : PATCH_MIRROR_SOURCE + FILE_SIZE - PATCH_MIRROR_OFFSET]
    return bytes(raw)


def convert(source: Path, destination: Path, *, name: str | None, device_id: int, force: bool) -> str:
    source, destination = source.expanduser(), destination.expanduser()
    input_type, output_type = source.suffix.lower(), destination.suffix.lower()
    valid = {".333", ".mid", ".midi", ".syx"}
    if input_type not in valid or output_type not in valid:
        raise D20Error("Sound conversion uses .333, .mid/.midi, or .syx extensions.")
    require_new_output(source, destination, force)
    if input_type == ".333":
        if output_type == ".333":
            raise D20Error("A .333 input must produce .mid, .midi, or .syx.")
        disk_name, tones, timbres, patches = decode(source)
        messages = [*make_messages(0x05, timbres, device_id), *make_messages(0x07, patches, device_id), *make_messages(0x08, tones, device_id)]
        if output_type in {".mid", ".midi"}:
            write_midi(destination, "Roland D-20 Sound conversion", messages)
        else:
            write_syx(destination, messages)
        return f"Converted {source.name} ({disk_name}) to {destination.name}: {len(messages)} DT1 messages."
    if output_type != ".333":
        raise D20Error("MIDI/SysEx Sound input can only produce a .333 file.")
    messages = scan_syx(source) if input_type == ".syx" else scan_midi(source)
    disk_name = name or destination.stem.upper()[:10]
    atomic_write(destination, encode(disk_name, messages))
    return f"Converted {source.name} to {destination.name} ({disk_name.upper()}), {FILE_SIZE} bytes."

