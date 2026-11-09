#!/usr/bin/env python3
"""Read-only audit of note-shaped records in paired D-20 A/B PROM dumps.

Usage: python3 probe_ab_rom_patterns.py A.BIN B.BIN [--rhythm RHYTHM.444]
The byte-lane order B[i], A[i] is verified against the optional saved setup.
An embedded ROM record is identified by bytes; its assigned preset number
and the playback routine using it have not been established.
"""

import argparse
import csv
import hashlib
import sys
from pathlib import Path


HASH_A = "e33738439c4da248db1b34939fca6917fcf7eb89d0c670ca4fd5798bebc103be"
HASH_B = "abbfdf7919f067d682fa36e600f425e9e518ea2472fe363bc189b85c50a5109d"
OLD_HASH_A = "058837a2c85aea67ba26d1f29ccb474565bcb60b018cc96b78612582b1405c9d"
OLD_HASH_B = "28b19b6c36adec3b81c5748c1f3429c498f2c107dbc2c62b7b21074e1a01a2d1"
FACTORY_RECORD = 0x1BC9


def probe(a_path: Path, b_path: Path, rhythm_path: Path | None, csv_output: bool,
          older_a: Path | None, older_b: Path | None) -> None:
    a, b = a_path.read_bytes(), b_path.read_bytes()
    if len(a) != 32768 or len(b) != 32768:
        raise ValueError("expected two 32 KiB A/B PROM images")
    for label, data, expected in (("A", a, HASH_A), ("B", b, HASH_B)):
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError(f"{label} PROM SHA256 differs: {digest}")
    rom = bytes(value for index in range(len(a)) for value in (b[index], a[index]))
    empty_templates = [
        rom[0x1B99 + index * 6 : 0x1B99 + (index + 1) * 6]
        for index in range(8)
    ]
    if any(chunk != bytes((index, 0, 0, 255, 128, 0)) for index, chunk in enumerate(empty_templates)):
        raise ValueError("ROM empty pattern templates no longer match")
    duration_ticks = list(rom[0x1B91:0x1B99])
    if duration_ticks != [24 * (index + 1) for index in range(8)]:
        raise ValueError("ROM 24-step duration table no longer matches")
    header = rom[FACTORY_RECORD : FACTORY_RECORD + 3]
    if header != b"\x03\x0d\x00":
        raise ValueError("ROM note-record header no longer matches")
    count = header[1]
    events = [
        tuple(rom[FACTORY_RECORD + 3 + 3 * i : FACTORY_RECORD + 6 + 3 * i])
        for i in range(count)
    ]
    trailer = rom[FACTORY_RECORD + 3 + 3 * count : FACTORY_RECORD + 6 + 3 * count]
    if trailer != b"\xff\x80\x00" or not all(
        time < 24 * (header[0] + 1) and 24 <= note <= 108 and 1 <= vel <= 127
        for time, note, vel in events
    ) or any(x[0] > y[0] for x, y in zip(events, events[1:])):
        raise ValueError("ROM note record fails the candidate triplet grammar")
    if rom[0x189E:0x18A4] != b"\xa1\xc9\x1b\x22\xb2\x23":
        raise ValueError("newer ROM record pointer-like word no longer matches")
    if rom[0x1237:0x123C] != b"\x06\xea\x45\x99\x1b":
        raise ValueError("newer ROM template pointer-like word no longer matches")
    if (older_a is None) != (older_b is None):
        raise ValueError("both older A and B PROM paths are required")
    if older_a is not None and older_b is not None:
        old_a, old_b = older_a.read_bytes(), older_b.read_bytes()
        if len(old_a) != 32768 or len(old_b) != 32768:
            raise ValueError("expected two 32 KiB older A/B PROM images")
        for label, data, expected in (("old A", old_a, OLD_HASH_A),
                                      ("old B", old_b, OLD_HASH_B)):
            digest = hashlib.sha256(data).hexdigest()
            if digest != expected:
                raise ValueError(f"{label} PROM SHA256 differs: {digest}")
        old_rom = bytes(value for index in range(len(old_a))
                        for value in (old_b[index], old_a[index]))
        if (old_rom[0x1BF3:0x1BF3+45] != rom[FACTORY_RECORD:FACTORY_RECORD+45]
                or old_rom[0x1BBB:0x1BC3] != bytes(duration_ticks)
                or old_rom[0x1BC3:0x1BF3] != rom[0x1B99:0x1BC9]
                or old_rom[0x18C8:0x18CE] != b"\xa1\xf3\x1b\x22\xb2\x23"
                or old_rom[0x1237:0x123C] != b"\x06\xea\x45\xc3\x1b"):
            raise ValueError("older ROM templates and embedded record do not agree")
        if not csv_output:
            print("Older 1.00 A/B PROMs contain the same 45-byte record at 0x1BF3",
                  file=sys.stderr)
            print("Pointer-like words track shifted record and template addresses",
                  file=sys.stderr)
    if rhythm_path is not None:
        saved = rhythm_path.read_bytes()
        if len(saved) != 12288 or saved[:3] != b"\x04\x00\x00":
            raise ValueError("expected native .444 Rhythm file")
        same = sum(left == right for left, right in zip(rom[:340], saved[0x2800:0x2954]))
        if same < 330:
            raise ValueError("A/B interleave does not reproduce the saved rhythm setup")
        if not csv_output:
            print(f"PROM setup matches {same}/340 saved Rhythm setup bytes", file=sys.stderr)
    if not csv_output:
        print("A/B byte lanes: B[0], A[0], B[1], A[1], ...", file=sys.stderr)
        print("ROM templates: 8 empty records, meters 1..8", file=sys.stderr)
        print(f"ROM raw-position duration table: {duration_ticks}", file=sys.stderr)
        print(f"Embedded pattern record at 0x{FACTORY_RECORD:04X}: {count} events", file=sys.stderr)
    writer = csv.writer(sys.stdout)
    writer.writerow(("event", "rom_offset", "position", "note", "velocity"))
    for i, (time, note, velocity) in enumerate(events):
        writer.writerow((i + 1, f"0x{FACTORY_RECORD + 3 + 3*i:04X}", time, note, velocity))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--rhythm", type=Path)
    parser.add_argument("--older-a", type=Path)
    parser.add_argument("--older-b", type=Path)
    parser.add_argument("--csv", action="store_true", help="suppress audit summary on stderr")
    args = parser.parse_args()
    probe(args.a, args.b, args.rhythm, args.csv, args.older_a, args.older_b)
