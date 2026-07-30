"""Shared validation and file-handling helpers for D-20 disk converters."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Iterable, Sequence

import mido


class D20Error(RuntimeError):
    """A concise error caused by malformed or unsupported user input."""


@dataclass(frozen=True, slots=True)
class D20Message:
    device_id: int
    address: tuple[int, int, int]
    payload: tuple[int, ...]

    @property
    def offset(self) -> int:
        return self.address[1] * 128 + self.address[2]


@dataclass(slots=True)
class MemoryImage:
    data: bytearray
    present: bytearray

    @classmethod
    def create(cls, size: int, fill: int = 0) -> "MemoryImage":
        if size <= 0:
            raise ValueError("memory size must be positive")
        return cls(bytearray([fill]) * size, bytearray(size))

    def write(self, offset: int, payload: Sequence[int], label: str) -> None:
        end = offset + len(payload)
        if offset < 0 or end > len(self.data):
            raise D20Error(f"{label} exceeds its {len(self.data)}-byte D-20 memory area.")
        self.data[offset:end] = bytes(payload)
        self.present[offset:end] = b"\x01" * len(payload)

    def complete(self, offset: int = 0, length: int | None = None) -> bool:
        length = len(self.data) - offset if length is None else length
        return 0 <= offset <= len(self.data) and 0 <= length <= len(self.data) - offset and all(self.present[offset : offset + length])

    def coverage(self) -> int:
        return sum(self.present)


def roland_checksum(values: Iterable[int]) -> int:
    return (-sum(values)) & 0x7F


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(data)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def require_new_output(source: Path, destination: Path, force: bool) -> None:
    if source.resolve() == destination.resolve():
        raise D20Error("Input and output must be different files.")
    if destination.exists() and not force:
        raise D20Error(f"Output already exists: {destination}. Use --force to replace it.")


def read_file(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise D20Error(f"Cannot read '{path}': {exc}") from exc


def scan_midi(path: Path) -> list[D20Message]:
    try:
        midi = mido.MidiFile(path)
    except (OSError, ValueError, EOFError) as exc:
        raise D20Error(f"Cannot read MIDI file '{path}': {exc}") from exc
    return scan_messages(message for track in midi.tracks for message in track)


def scan_messages(messages: Iterable[mido.Message]) -> list[D20Message]:
    result: list[D20Message] = []
    invalid = 0
    for message in messages:
        if message.type != "sysex":
            continue
        raw = tuple(message.data)
        if not raw or raw[0] != 0x41:
            continue
        if len(raw) < 8 or raw[2:4] != (0x16, 0x12):
            continue
        if any(value > 0x7F for value in raw):
            invalid += 1
            continue
        address, payload, checksum = raw[4:7], raw[7:-1], raw[-1]
        if not payload or checksum != roland_checksum((*address, *payload)):
            invalid += 1
            continue
        result.append(D20Message(raw[1], address, payload))
    if invalid:
        raise D20Error(f"Input contains {invalid} malformed D-20 DT1 message(s).")
    return result


def scan_syx(path: Path) -> list[D20Message]:
    raw = read_file(path)
    midi_messages: list[mido.Message] = []
    position = frame_count = 0
    whitespace = b"\x00\x09\x0A\x0D\x20"
    while position < len(raw):
        start = raw.find(b"\xF0", position)
        if start < 0:
            if raw[position:].strip(whitespace):
                raise D20Error(f"Unexpected non-SysEx data at byte {position}.")
            break
        if raw[position:start].strip(whitespace):
            raise D20Error(f"Unexpected data before SysEx frame at byte {start}.")
        end = raw.find(b"\xF7", start + 1)
        if end < 0:
            raise D20Error(f"Unterminated SysEx frame at byte {start}.")
        body = raw[start + 1 : end]
        if len(body) >= 4 and body[0] == 0x41 and body[2:4] == b"\x16\x12":
            if any(value > 0x7F for value in body):
                raise D20Error(f"D-20 SysEx frame at byte {start} contains non-7-bit data.")
            midi_messages.append(mido.Message("sysex", data=tuple(body)))
        frame_count += 1
        position = end + 1
    if not frame_count:
        raise D20Error("No F0...F7 SysEx frames found.")
    return scan_messages(midi_messages)


def assemble(messages: Iterable[D20Message], area: int, size: int, label: str) -> MemoryImage:
    image = MemoryImage.create(size)
    for message in messages:
        if message.address[0] == area:
            image.write(message.offset, message.payload, label)
    if not image.complete():
        raise D20Error(f"{label} is incomplete ({image.coverage()}/{size} bytes).")
    return image


def make_messages(area: int, image: MemoryImage, device_id: int) -> list[mido.Message]:
    result: list[mido.Message] = []
    for offset in range(0, len(image.data), 256):
        payload = bytes(image.data[offset : offset + 256])
        address = (area, offset // 128, offset % 128)
        data = [0x41, device_id, 0x16, 0x12, *address, *payload]
        result.append(mido.Message("sysex", data=[*data, roland_checksum(data[4:])]))
    return result


def write_midi(path: Path, title: str, messages: Iterable[mido.Message]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".mid", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        midi = mido.MidiFile(type=0)
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=title, time=0))
        track.extend(messages)
        midi.tracks.append(track)
        midi.save(temporary_path)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_syx(path: Path, messages: Iterable[mido.Message]) -> None:
    atomic_write(path, b"".join(bytes([0xF0, *message.data, 0xF7]) for message in messages))


def parse_device_id(value: str) -> int:
    try:
        device_id = int(value, 0)
    except ValueError as exc:
        raise D20Error("--device-id must be an integer in 0..127.") from exc
    if not 0 <= device_id <= 0x7F:
        raise D20Error("--device-id must be in 0..127.")
    return device_id

