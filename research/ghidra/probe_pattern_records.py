#!/usr/bin/env python3
"""Read-only structural probe of candidate D-20 rhythm event blocks.

Usage: python3 probe_pattern_records.py PATH.111|PATH.222|PATH.444
The three container offsets are sample-verified, not proven firmware mappings.
For .111/.222 it also compares the 32 proposed IDs 20..3F to the saved
64-entry duration table. The MCS-96 editor confirms record addressing and
the position/note/velocity order; real-time playback gate is still open.
"""

import argparse
import csv
import sys
from pathlib import Path


OFFSETS = {".111": 0x9000, ".222": 0x3B00, ".444": 0x100}
BLOCK_SIZE = 294
BLOCK_COUNT = 32


def probe(path: Path, events_id: int | None = None) -> None:
    suffix = path.suffix.lower()
    if suffix not in OFFSETS:
        raise ValueError(f"expected one of {', '.join(OFFSETS)}")
    data = path.read_bytes()
    base = OFFSETS[suffix]
    if len(data) < base + BLOCK_COUNT * BLOCK_SIZE:
        raise ValueError("file is shorter than the candidate rhythm block region")
    if events_id is not None and not 0x20 <= events_id < 0x40:
        raise ValueError("candidate stored pattern ID must be 0x20..0x3F")
    summary = sys.stderr if events_id is not None else sys.stdout
    print("slot  offset  header  events  max_time  notes      velocities  padding", file=summary)
    for index in range(BLOCK_COUNT):
        offset = base + index * BLOCK_SIZE
        block = data[offset : offset + BLOCK_SIZE]
        count = block[1]
        if count > 96:
            raise ValueError(f"invalid event count in block {index}: {count}")
        events = [tuple(block[pos : pos + 3]) for pos in range(3, 3 + 3 * count, 3)]
        times = [event[0] for event in events]
        notes = [event[1] for event in events]
        velocities = [event[2] for event in events]
        padding = block[3 + 3 * count :]
        valid = (
            block[0] <= 7
            and block[2] == 0
            and times == sorted(times)
            and all(time < (block[0] + 1) * 24 for time in times)
            and all(0 <= note <= 127 for note in notes)
            and all(1 <= velocity <= 127 for velocity in velocities)
            and all(padding[i:i + 3] in (b"\xff\x80\x00", b"\xff\x00\x00")
                    for i in range(0, len(padding), 3))
        )
        note_range = f"{min(notes):3}..{max(notes):3}" if notes else "    empty"
        velocity_range = f"{min(velocities):3}..{max(velocities):3}" if velocities else "    empty"
        print(
            f"{index:4}  {offset:06x}  {block[:3].hex()}  {count:6}  "
            f"{max(times, default=-1):8}  {note_range}  {velocity_range}  "
            f"{padding[:3].hex() if padding else '(none)'}", file=summary
        )
        if not valid:
            raise ValueError(f"candidate grammar fails at block {index}")
    print("All 32 candidate event blocks passed structural checks.", file=summary)
    if suffix in (".111", ".222"):
        table = data[0x23B:0x27B]
        if len(table) != 64:
            raise ValueError("missing proposed 64-byte pattern-duration table")
        matches = sum(
            table[0x20 + i] == data[base + BLOCK_SIZE * i] + 1
            for i in range(BLOCK_COUNT)
        )
        print(f"IDs 20..3F: header + 1 agrees with duration table for {matches}/32 blocks.", file=summary)
        if matches != BLOCK_COUNT:
            raise ValueError("candidate ID-to-block mapping conflicts with saved duration table")
        for selected in (0x3E, 0x3F):
            index = selected - 0x20
            count = data[base + BLOCK_SIZE * index + 1]
            print(f"ID {selected:02X} -> candidate block {index}: {count} events", file=summary)
    if events_id is not None:
        index = events_id - 0x20
        offset = base + index * BLOCK_SIZE
        count = data[offset + 1]
        writer = csv.writer(sys.stdout)
        writer.writerow(("pattern_id", "event", "file_offset", "position", "note", "velocity"))
        for i in range(count):
            pos = offset + 3 + 3 * i
            writer.writerow((f"0x{events_id:02X}", i + 1, f"0x{pos:04X}", *data[pos:pos+3]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--events-id", type=lambda value: int(value, 0),
                        help="print candidate event CSV for saved pattern ID 0x20..0x3F")
    args = parser.parse_args()
    probe(args.path, args.events_id)
