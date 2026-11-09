"""BETA single-pattern MIDI extraction from native D-20 Rhythm/Song/All files.

The A/B 1.12 MCS-96 editor at 1A6D and 1910 confirms the 294-byte record:
meter-minus-one, event count, reserved zero, then [position, note, velocity].
The record has no stored gate. Exported note-offs use an explicit audition gate.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import io
from pathlib import Path

import mido

from .core import D20Error, atomic_write, read_file, require_new_output

PATTERN_SIZE = 294
PATTERN_COUNT = 32
TICKS_PER_QUARTER = 96
RAW_POSITIONS_PER_QUARTER = 24
SETUP_SIZE = 340
CONTAINERS = {
    12_288: ("RHYTHM", 0x0100),
    27_648: ("SONG", 0x3B00),
    49_152: ("ALL", 0x9000),
}


@dataclass(frozen=True, slots=True)
class Hit:
    position: int  # stored units, 24 per quarter note
    note: int
    velocity: int
    file_offset: int


@dataclass(frozen=True, slots=True)
class Pattern:
    kind: str
    pattern_id: int
    beats: int
    hits: tuple[Hit, ...]
    setup: tuple[tuple[int, bytes], ...]  # observed notes and their raw 09H records


def valid_header(meter: int, count: int, reserved: int) -> bool:
    """Check the three bytes at the start of a stored pattern record."""
    return meter <= 7 and count <= 96 and reserved == 0


def decode(raw: bytes, pattern_id: int) -> Pattern:
    """Read one writable pattern ID 20..3F, without assuming a chain or gate."""
    if not 0x20 <= pattern_id <= 0x3F:
        raise D20Error("BETA pattern export supports stored IDs 0x20..0x3F (P-51..P-88).")
    container = CONTAINERS.get(len(raw))
    if container is None:
        raise D20Error("Expected a native .444 Rhythm, .222 Song, or .111 All file.")
    kind, base = container
    if kind == "RHYTHM":
        if raw[:3] != b"\x04\x00\x00":
            raise D20Error("Invalid native Rhythm header.")
    elif raw[2] != 3 or (kind == "ALL" and raw[0x10] != 1):
        raise D20Error(f"Invalid native {kind} header.")
    if raw[base + 0x2900:base + 0x2F00] != raw[base + 0x1D00:base + 0x2300]:
        raise D20Error("Rhythm mirror does not match the source pattern data.")

    start = base + (pattern_id - 0x20) * PATTERN_SIZE
    record = raw[start:start + PATTERN_SIZE]
    meter, count, reserved = record[:3]
    if not valid_header(meter, count, reserved):
        raise D20Error(f"Invalid pattern header at byte 0x{start:X}.")
    beats = meter + 1
    hits: list[Hit] = []
    previous = -1
    for i in range(count):
        position, note, velocity = record[3 + i * 3:6 + i * 3]
        if not previous <= position < beats * RAW_POSITIONS_PER_QUARTER or note >= 128 or not 1 <= velocity < 128:
            raise D20Error(f"Invalid pattern hit at byte 0x{start + 3 + i * 3:X}.")
        hits.append(Hit(position, note, velocity, start + 3 + i * 3))
        previous = position
    pad = record[3 + count * 3:]
    # The fixed 294-byte record and count limit leave at least one complete triple.
    if any(pad[i:i + 3] not in (b"\xff\x80\x00", b"\xff\x00\x00") for i in range(0, len(pad), 3)):
        raise D20Error(f"Invalid pattern terminator/padding at byte 0x{start + 3 + count * 3:X}.")

    setup_start = base + 0x2700
    setup = raw[setup_start:setup_start + SETUP_SIZE]
    used = tuple((note, setup[(note - 24) * 4:(note - 23) * 4]) for note in sorted({hit.note for hit in hits}) if 24 <= note <= 108)
    return Pattern(kind, pattern_id, beats, tuple(hits), used)


def rhythm_chain(raw: bytes) -> tuple[int, ...]:
    """Read a native pattern-number list; reject preset IDs not yet decoded."""
    kind = CONTAINERS.get(len(raw))
    if kind is None:
        raise D20Error("A rhythm track requires a native .444, .222, or .111 file.")
    if kind[0] == "RHYTHM":
        count = int.from_bytes(raw[0x2600:0x2602], "little")
        if not 1 <= count <= 500:
            raise D20Error("Invalid native Rhythm track selection count.")
        ids = tuple(raw[0x2602:0x2602 + count])
    else:
        chain = raw[0x44:0x23B]
        end = chain.find(b"\xff")
        if end <= 0:
            raise D20Error("Song rhythm track has no validated FF terminator.")
        ids = tuple(chain[:end])
    for index, pattern_id in enumerate(ids):
        if not 0x20 <= pattern_id <= 0x3F:
            raise D20Error(f"Rhythm selection {index + 1} uses pattern ID 0x{pattern_id:02X}; "
                           "ROM preset patterns are not decoded. Use --no-rhythm-track for Song notes only.")
    return ids


def append_hits(track: mido.MidiTrack, selections: tuple[tuple[int, Pattern], ...], *,
                gate_ticks: int, channel: int, markers: bool = False) -> int:
    """Append time-ordered hits, note-offs and raw setup metadata to a track."""
    events = []
    used: dict[int, bytes] = {}
    hit_count = 0
    for selection, (start, parsed) in enumerate(selections):
        if markers:
            events.append((start, -1, selection, mido.MetaMessage(
                "marker", text=f"P-{(parsed.pattern_id >> 3 & 7) + 1}{(parsed.pattern_id & 7) + 1} "
                f"(ID 0x{parsed.pattern_id:02X}, {parsed.beats} beats)", time=0)))
        used.update(parsed.setup)
        for order, hit in enumerate(parsed.hits):
            tick = start + hit.position * (TICKS_PER_QUARTER // RAW_POSITIONS_PER_QUARTER)
            events.append((tick, 1, hit_count + order, mido.Message(
                "note_on", channel=channel, note=hit.note, velocity=hit.velocity)))
            events.append((tick + gate_ticks, 0, hit_count + order, mido.Message(
                "note_off", channel=channel, note=hit.note, velocity=0)))
        hit_count += len(parsed.hits)
    for note, settings in sorted(used.items()):
        track.append(mido.MetaMessage("text", text=f"D-20 rhythm setup note {note}: raw 09H "
                                      f"{settings.hex().upper()} (device settings, unmapped)", time=0))
    previous = 0
    for tick, _, _, message in sorted(events):
        track.append(message.copy(time=tick - previous))
        previous = tick
    return hit_count


def expanded_rhythm_track(raw: bytes, *, gate_ticks: int, channel: int = 9) -> tuple[mido.MidiTrack, int, int]:
    """Assemble the saved selection list, preserving rests from empty patterns."""
    ids = rhythm_chain(raw)
    cache = {number: decode(raw, number) for number in set(ids)}
    if len(raw) != 12_288:
        lengths = raw[0x23B:0x27B]
        for number, parsed in cache.items():
            if lengths[number] != parsed.beats:
                raise D20Error(f"Song rhythm duration for ID 0x{number:02X} disagrees with its saved pattern.")
    start = 0
    selections = []
    for number in ids:
        parsed = cache[number]
        selections.append((start, parsed))
        start += parsed.beats * TICKS_PER_QUARTER
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name="Rhythm track (BETA stored patterns)", time=0))
    track.append(mido.MetaMessage("text", text="BETA: note-off gate and position scale provisional; tempo supplied for audition", time=0))
    hits = append_hits(track, tuple(selections), gate_ticks=gate_ticks, channel=channel, markers=True)
    return track, len(ids), hits


def convert_rhythm(source: Path, destination: Path, *, mode: str, pattern_id: int | None,
                   tempo_bpm: int, gate_ticks: int = 1, channel: int = 9, force: bool = False) -> str:
    """Export one, all, or the arranged stored patterns from a .444 file."""
    source, destination = source.expanduser(), destination.expanduser()
    if source.suffix.lower() != ".444" or destination.suffix.lower() not in {".mid", ".midi"}:
        raise D20Error("Rhythm note export requires a native .444 input and .mid/.midi output.")
    if not 4 <= tempo_bpm <= 300:
        raise D20Error("--tempo-bpm must be between 4 and 300.")
    if not 1 <= gate_ticks <= 96 or not 0 <= channel <= 15:
        raise D20Error("--gate-ticks must be 1..96 and MIDI channel must be 1..16.")
    if (mode == "pattern" and pattern_id is None) or (mode != "pattern" and pattern_id is not None):
        raise D20Error("--pattern-id is required only with --notes pattern.")
    if mode not in {"pattern", "all", "track"}:
        raise D20Error("--notes must be pattern, all, or track.")
    require_new_output(source, destination, force)
    raw = read_file(source)
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_QUARTER)
    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage("track_name", name="D-20 Rhythm BETA", time=0))
    conductor.append(mido.MetaMessage("text", text="BETA: user tempo; provisional note gate and timing scale", time=0))
    conductor.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))
    midi.tracks.append(conductor)
    if mode == "track":
        track, selections, hits = expanded_rhythm_track(raw, gate_ticks=gate_ticks, channel=channel)
        position, previous, numerator = 0, 0, None
        for number in rhythm_chain(raw):
            beats = decode(raw, number).beats
            if beats != numerator:
                conductor.append(mido.MetaMessage("time_signature", numerator=beats, denominator=4,
                                                   time=position - previous))
                previous, numerator = position, beats
            position += beats * TICKS_PER_QUARTER
        midi.tracks.append(track)
        description = f"{selections} saved selections, {hits} hits"
    else:
        ids = range(0x20, 0x40) if mode == "all" else (pattern_id,)
        patterns = [decode(raw, number) for number in ids]
        if mode == "pattern":
            conductor.append(mido.MetaMessage("time_signature", numerator=patterns[0].beats, denominator=4, time=0))
        hits = 0
        for parsed in patterns:
            track = mido.MidiTrack()
            track.append(mido.MetaMessage("track_name", name=f"P-{(parsed.pattern_id >> 3 & 7) + 1}"
                         f"{(parsed.pattern_id & 7) + 1} (0x{parsed.pattern_id:02X}, "
                         f"{parsed.beats} beats, BETA)", time=0))
            hits += append_hits(track, ((0, parsed),), gate_ticks=gate_ticks, channel=channel)
            midi.tracks.append(track)
        description = f"{len(patterns)} stored patterns, {hits} hits"
    buffer = io.BytesIO()
    midi.save(file=buffer)
    atomic_write(destination, buffer.getvalue())
    return f"BETA: exported Rhythm {mode}: {description} to {destination.name} at audition {tempo_bpm} BPM."


def convert(source: Path, destination: Path, *, pattern_id: int, tempo_bpm: int,
            gate_ticks: int = 1, channel: int = 9, force: bool = False) -> str:
    """Export a Type-1 MIDI with a single selected drum pattern, preserving input."""
    source, destination = source.expanduser(), destination.expanduser()
    if destination.suffix.lower() not in {".mid", ".midi"}:
        raise D20Error("BETA pattern export writes a Standard MIDI .mid/.midi file.")
    if not 4 <= tempo_bpm <= 300:
        raise D20Error("--tempo-bpm must be between 4 and 300.")
    if not 1 <= gate_ticks <= TICKS_PER_QUARTER:
        raise D20Error("--gate-ticks must be between 1 and 96 (provisional note length).")
    if not 0 <= channel <= 15:
        raise D20Error("--channel must be 0..15 (zero-based MIDI channel).")
    require_new_output(source, destination, force)
    parsed = decode(read_file(source), pattern_id)
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_QUARTER)
    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage("track_name", name=f"D-20 P-{(pattern_id >> 3 & 7) + 1}{(pattern_id & 7) + 1} BETA", time=0))
    conductor.append(mido.MetaMessage("text", text="BETA pattern: 24 stored positions/beat; note-off gate and tempo supplied for audition", time=0))
    conductor.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))
    conductor.append(mido.MetaMessage("time_signature", numerator=parsed.beats, denominator=4, time=0))
    midi.tracks.append(conductor)
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name=f"Rhythm pattern 0x{pattern_id:02X} (BETA)", time=0))
    for note, settings in parsed.setup:
        track.append(mido.MetaMessage("text", text=f"D-20 rhythm setup note {note}: raw 09H {settings.hex().upper()} (device settings, unmapped)", time=0))
    events = []
    for order, hit in enumerate(parsed.hits):
        tick = hit.position * (TICKS_PER_QUARTER // RAW_POSITIONS_PER_QUARTER)
        events.append((tick, 1, order, mido.Message("note_on", channel=channel, note=hit.note, velocity=hit.velocity)))
        events.append((tick + gate_ticks, 0, order, mido.Message("note_off", channel=channel, note=hit.note, velocity=0)))
    previous = 0
    for tick, _, _, message in sorted(events):
        track.append(message.copy(time=tick - previous))
        previous = tick
    midi.tracks.append(track)
    buffer = io.BytesIO()
    midi.save(file=buffer)
    atomic_write(destination, buffer.getvalue())
    concurrency = max(Counter(hit.position for hit in parsed.hits).values(), default=0)
    return (f"BETA: exported {len(parsed.hits)} pattern hits from {parsed.kind} ID 0x{pattern_id:02X} "
            f"({parsed.beats}/4, up to {concurrency} simultaneous, {TICKS_PER_QUARTER} PPQ) to {destination.name}. "
            f"Tempo {tempo_bpm} BPM, gate {gate_ticks} ticks, MIDI channel {channel + 1} are audition settings.")
