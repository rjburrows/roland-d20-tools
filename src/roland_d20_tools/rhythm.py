"""Conversion for native Roland D-20 Rhythm (.444) files."""

from __future__ import annotations

from pathlib import Path

from . import preservation

from .core import D20Error, D20Message, MemoryImage, assemble, atomic_write, make_messages, read_file, require_new_output, require_outputs, scan_midi, scan_syx, write_midi, write_syx


FILE_SIZE, HEADER_SIZE = 12_288, 0x100
PATTERN_OFFSET, PATTERN_SIZE = 0x0100, 16_384
TRACK_OFFSET, TRACK_SIZE = 0x2100, 2_432
SEQUENCER_OFFSET, SEQUENCER_SIZE = 0x2600, 502
SETUP_OFFSET, SETUP_SIZE = 0x2800, 340
MIRROR_OFFSET, MIRROR_SOURCE, MIRROR_SIZE = 0x2A00, 0x1E00, 0x600


def header(name: str) -> bytes:
    try:
        encoded = name.upper().encode("ascii", "strict")
    except UnicodeEncodeError as exc:
        raise D20Error("The destination filename must use printable ASCII characters.") from exc
    if not 1 <= len(encoded) <= 10 or any(byte < 32 or byte > 126 for byte in encoded):
        raise D20Error("The destination filename stem must contain 1 to 10 printable ASCII characters.")
    result = bytearray(HEADER_SIZE)
    result[:3] = b"\x04\x00\x00"
    result[6:16] = encoded.ljust(10, b" ")
    return bytes(result)


def unpack_nibbles(data: bytes) -> bytes:
    return bytes(value for byte in data for value in (byte & 0x0F, byte >> 4))


def pack_nibbles(data: bytes, label: str) -> bytes:
    if len(data) % 2 or any(byte > 0x0F for byte in data):
        raise D20Error(f"{label} cannot be represented by the native .444 nibble encoding.")
    return bytes(data[index] | (data[index + 1] << 4) for index in range(0, len(data), 2))


def decode(path: Path) -> tuple[str, MemoryImage, MemoryImage, MemoryImage, MemoryImage]:
    raw = read_file(path)
    if len(raw) != FILE_SIZE:
        raise D20Error(f"A D-20 .444 Rhythm file must be {FILE_SIZE} bytes; this file is {len(raw)} bytes.")
    if raw[:3] != b"\x04\x00\x00":
        raise D20Error("This is not the expected D-20 Rhythm-file header (04 00 00).")
    name_bytes = raw[6:16]
    if any(byte and not 32 <= byte <= 126 for byte in name_bytes):
        raise D20Error("The Rhythm filename field contains invalid bytes.")
    if raw[MIRROR_OFFSET:] != raw[MIRROR_SOURCE : MIRROR_SOURCE + MIRROR_SIZE]:
        raise D20Error("The .444 mirror region does not match its source data.")
    name = name_bytes.decode("ascii", "replace").strip() or path.stem.upper()[:10]
    pattern = MemoryImage.create(PATTERN_SIZE)
    pattern.write(0, unpack_nibbles(raw[PATTERN_OFFSET : PATTERN_OFFSET + PATTERN_SIZE // 2]), "Rhythm pattern memory")
    track = MemoryImage.create(TRACK_SIZE)
    track.write(0, unpack_nibbles(raw[TRACK_OFFSET : TRACK_OFFSET + TRACK_SIZE // 2]), "Rhythm track")
    sequencer = MemoryImage.create(SEQUENCER_SIZE)
    sequencer.write(0, raw[SEQUENCER_OFFSET : SEQUENCER_OFFSET + SEQUENCER_SIZE], "Rhythm sequencer header")
    setup = MemoryImage.create(SETUP_SIZE)
    setup.write(0, raw[SETUP_OFFSET : SETUP_OFFSET + SETUP_SIZE], "Rhythm setup")
    return name, setup, pattern, track, sequencer


def encode(name: str, messages: list[D20Message]) -> bytes:
    setup = assemble(messages, 0x09, SETUP_SIZE, "Rhythm Setup")
    pattern = assemble(messages, 0x0A, PATTERN_SIZE, "Pattern Memory")
    track = assemble(messages, 0x0B, TRACK_SIZE, "Rhythm Track")
    sequencer = assemble(messages, 0x0C, SEQUENCER_SIZE, "Sequencer Header")
    raw = bytearray(FILE_SIZE)
    raw[:HEADER_SIZE] = header(name)
    raw[PATTERN_OFFSET : PATTERN_OFFSET + PATTERN_SIZE // 2] = pack_nibbles(bytes(pattern.data), "Pattern Memory")
    raw[TRACK_OFFSET : TRACK_OFFSET + TRACK_SIZE // 2] = pack_nibbles(bytes(track.data), "Rhythm Track")
    raw[SEQUENCER_OFFSET : SEQUENCER_OFFSET + SEQUENCER_SIZE] = sequencer.data
    raw[SETUP_OFFSET : SETUP_OFFSET + SETUP_SIZE] = setup.data
    raw[MIRROR_OFFSET:] = raw[MIRROR_SOURCE : MIRROR_SOURCE + MIRROR_SIZE]
    return bytes(raw)


def convert(source: Path, destination: Path, *, device_id: int, force: bool) -> str:
    source, destination = source.expanduser(), destination.expanduser()
    input_type, output_type = source.suffix.lower(), destination.suffix.lower()
    valid = {".444", ".mid", ".midi", ".syx"}
    if input_type not in valid or output_type not in valid:
        raise D20Error("Rhythm conversion uses .444, .mid/.midi, or .syx extensions.")
    require_new_output(source, destination, force)
    if input_type == ".444":
        if output_type == ".444":
            raise D20Error("A .444 input must produce .mid, .midi, or .syx.")
        require_outputs(source, [destination, preservation.sidecar(destination)], force)
        disk_name, setup, pattern, track, sequencer = decode(source)
        messages = [*make_messages(0x09, setup, device_id), *make_messages(0x0A, pattern, device_id), *make_messages(0x0B, track, device_id), *make_messages(0x0C, sequencer, device_id)]
        if output_type in {".mid", ".midi"}:
            write_midi(destination, "Roland D-20 Rhythm conversion", messages)
        else:
            write_syx(destination, messages)
        preservation.save(source, destination)
        return f"Preserved original native bytes in {preservation.sidecar(destination).name}. Converted {source.name} ({disk_name}) to {destination.name}: {len(messages)} DT1 messages."
    if output_type != ".444":
        raise D20Error("MIDI/SysEx Rhythm input can only produce a .444 file.")
    messages = scan_syx(source) if input_type == ".syx" else scan_midi(source)
    disk_name = destination.stem.upper()[:10]
    normalized = encode(disk_name, messages)
    preserved = preservation.restore(source, ".444")
    atomic_write(destination, preserved if preserved is not None else normalized)
    detail = "Original native bytes and stored name restored." if preserved is not None else "Normalized container: header/reserved bytes regenerated; unrelated SysEx areas are omitted."
    return detail + " " + f"Converted {source.name} to {destination.name} ({disk_name.upper()}), {FILE_SIZE} bytes."
