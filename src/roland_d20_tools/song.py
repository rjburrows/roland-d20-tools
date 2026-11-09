"""BETA, one-way note-event export from native D-20 Song and All files.

The event grammar follows C 1.11 ROM 6F6A-6FDB and 6FDC-70B0. The 192-position
storage interval follows 6ED1; 5E06/5EAA support 96 positions per quarter.
Stored rhythm-pattern hits can be expanded along the selection list. Saved
tempo, ROM preset pattern notes, note-off policy, and routing remain unresolved.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path

import mido

from . import pattern
from .core import D20Error, atomic_write, read_file, require_new_output

SONG_SIZE = 27_648
ALL_SIZE = 49_152
EVENT_START = 0x1A00
EVENT_END = 0x3A02  # last observed indexed FF may be at 0x3A01
INDEX_START = 0x283
INDEX_END = 0x1A00
INTERVAL_POSITIONS = 192
POSITIONS_PER_QUARTER = 96


@dataclass(frozen=True, slots=True)
class NoteEvent:
    position: int
    status: int
    note: int
    velocity: int
    file_offset: int


@dataclass(frozen=True, slots=True)
class SongNotes:
    kind: str
    events: tuple[NoteEvent, ...]
    meter_changes: tuple[tuple[int, int], ...]  # absolute position, numerator / 4
    pattern_count: int

    @property
    def lanes(self) -> tuple[int, ...]:
        return tuple(sorted({event.status & 0x0F for event in self.events}))


def _kind(raw: bytes) -> str:
    if len(raw) == SONG_SIZE and raw[2] == 3 and raw[0x3B00:0x3B03] == b"\x03\x11\x00":
        kind, rhythm_start = "SONG", 0x3B00
    elif len(raw) == ALL_SIZE and raw[2] == 3 and raw[0x10] == 1:
        kind, rhythm_start = "ALL", 0x9000
    else:
        raise D20Error("BETA note export requires a recognised native .222 Song or .111 All file.")
    if raw[rhythm_start + 0x2900:rhythm_start + 0x2F00] != raw[rhythm_start + 0x1D00:rhythm_start + 0x2300]:
        raise D20Error("Embedded Rhythm mirror does not match its source data.")
    return kind


def _meter(raw: bytes) -> tuple[tuple[tuple[int, int], ...], int]:
    """Pattern IDs/lengths aligned with RAM B4DE/B6D5; omit if not credible."""
    chain = raw[0x44:0x23B]
    end = chain.find(b"\xff")
    lengths = raw[0x23B:0x27B]
    if end < 0 or not end or any(value >= 64 or not 1 <= lengths[value] <= 8 for value in chain[:end]):
        return (), 0
    position = 0
    changes = []
    for pattern_id in chain[:end]:
        numerator = lengths[pattern_id]
        if not changes or changes[-1][1] != numerator:
            changes.append((position, numerator))
        position += numerator * POSITIONS_PER_QUARTER
    return tuple(changes), end


def decode(raw: bytes) -> SongNotes:
    """Validate indexed FF boundaries and read only the ROM-confirmed 8x/9x records."""
    kind = _kind(raw)
    base = int.from_bytes(raw[0x41:0x44], "little")
    if not base:
        raise D20Error("Song event stream has no validated physical base pointer.")
    boundaries = []
    previous = base - 1
    for offset in range(INDEX_START, INDEX_END - 2, 3):
        pointer = int.from_bytes(raw[offset:offset + 3], "little")
        if pointer == 0xFFFFFF:
            break
        boundary = EVENT_START + pointer - base
        if pointer <= previous or not EVENT_START <= boundary < EVENT_END or raw[boundary] != 0xFF:
            raise D20Error(f"Invalid Song event index at file byte 0x{offset:04X}.")
        boundaries.append(boundary)
        previous = pointer
    if not boundaries:
        raise D20Error("Song event index is missing its FF boundaries.")

    events = []
    start = EVENT_START
    for interval, boundary in enumerate(boundaries):
        offset = start
        status = None  # ROM resets running status at every FF marker.
        last_position = -1
        while offset < boundary:
            at = offset
            position = raw[offset]
            offset += 1
            if not last_position <= position < INTERVAL_POSITIONS or offset >= boundary:
                raise D20Error(f"Invalid Song position or truncated record at file byte 0x{at:04X}.")
            last_position = position
            if raw[offset] & 0x80:
                status = raw[offset]
                offset += 1
            if status is None or status & 0xF0 not in (0x80, 0x90):
                raise D20Error(f"Unsupported BETA Song status at file byte 0x{at:04X}.")
            size = 2 if status & 0xF0 == 0x90 else 1
            if offset + size > boundary or any(value > 0x7F for value in raw[offset:offset + size]):
                raise D20Error(f"Invalid Song note data at file byte 0x{at:04X}.")
            note = raw[offset]
            velocity = raw[offset + 1] if size == 2 else 0
            events.append(NoteEvent(interval * INTERVAL_POSITIONS + position, status, note, velocity, at))
            offset += size
        start = boundary + 1
    if not events:
        raise D20Error("No supported Song note events were found.")
    meter_changes, pattern_count = _meter(raw)
    return SongNotes(kind, tuple(events), meter_changes, pattern_count)


def convert(source: Path, destination: Path, *, tempo_bpm: int, force: bool,
            expected_kind: str | None = None, rhythm_track: bool = True,
            gate_ticks: int = 1) -> str:
    """Write a Type-1 MIDI with one track per stored status lane, never modifying input."""
    source, destination = source.expanduser(), destination.expanduser()
    if destination.suffix.lower() not in {".mid", ".midi"}:
        raise D20Error("BETA Song/All note export writes Standard MIDI .mid/.midi only.")
    if not 4 <= tempo_bpm <= 300:
        raise D20Error("--tempo-bpm must be between 4 and 300; the saved tempo is not decoded yet.")
    if not 1 <= gate_ticks <= 96:
        raise D20Error("--gate-ticks must be 1..96 (provisional rhythm note-off length).")
    require_new_output(source, destination, force)
    raw = read_file(source)
    parsed = decode(raw)
    if expected_kind and parsed.kind != expected_kind:
        raise D20Error(f"This is a native {parsed.kind} file; use the '{parsed.kind.lower()}' command.")
    midi = mido.MidiFile(type=1, ticks_per_beat=POSITIONS_PER_QUARTER)
    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage("track_name", name="D-20 Song notes BETA", time=0))
    conductor.append(mido.MetaMessage("text", text="BETA: audition tempo supplied by user; rhythm gate and channel routing unresolved", time=0))
    conductor.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))
    previous = 0
    for position, numerator in parsed.meter_changes:
        conductor.append(mido.MetaMessage("time_signature", numerator=numerator, denominator=4, time=position - previous))
        previous = position
    midi.tracks.append(conductor)
    lanes: dict[int, list[NoteEvent]] = {}
    for event in parsed.events:
        lanes.setdefault(event.status & 0x0F, []).append(event)
    for lane, events in sorted(lanes.items()):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name=f"Stored status lane {lane} (BETA provisional channel)", time=0))
        previous = 0
        for event in events:
            # ROM 6FCF converts the stored one-data-byte 8x off to 9x velocity zero.
            track.append(mido.Message("note_on", channel=lane, note=event.note,
                                      velocity=event.velocity, time=event.position - previous))
            previous = event.position
        midi.tracks.append(track)
    rhythm_detail = "rhythm omitted by request"
    if rhythm_track:
        drum_track, selections, hits = pattern.expanded_rhythm_track(raw, gate_ticks=gate_ticks)
        midi.tracks.append(drum_track)
        rhythm_detail = f"rhythm {selections} selections, {hits} hits"
    buffer = io.BytesIO()
    midi.save(file=buffer)
    atomic_write(destination, buffer.getvalue())
    meters = f"{parsed.pattern_count} pattern selections" if parsed.pattern_count else "meter unavailable"
    return (f"BETA: exported {len(parsed.events)} note events from {parsed.kind} to {destination.name} "
            f"({len(lanes)} provisional lanes; 96 PPQ; {meters}; {rhythm_detail}; "
            f"audition tempo {tempo_bpm} BPM). Saved tempo, ROM preset notes, "
            "rhythm gate, and track routing remain undecoded.")
