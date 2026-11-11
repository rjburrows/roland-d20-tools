"""Synthetic factory pointer records and native arrangement integration."""

from contextlib import redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import mido

from roland_d20_tools import cli, pattern, song
from roland_d20_tools.core import D20Error
from test_pattern_beta import rhythm_with_chain
from test_song_beta import fixture as song_fixture


def factory_fixture() -> bytes:
    """Generate small original records in the documented banked table layout."""
    rom = bytearray(pattern.FACTORY_ROM_SIZE)
    for number in range(32):
        start = 0x3100 + 32 * number
        rom[0x3000 + 2 * number:0x3002 + 2 * number] = start.to_bytes(2, "little")
        beats = 3 if number == 0x17 else 8 if number in (0x1B, 0x1C) else 4
        rom[start:start + 9] = bytes((beats - 1, 1, 0, 0, 36 + number, 100, 255, 128, 0))
    return bytes(rom)


def note_times(track):
    tick, events = 0, []
    for message in track:
        tick += message.time
        if message.type == "note_on" and message.velocity:
            events.append((tick, message.channel, message.note, message.velocity))
    return events


class FactoryPatternTests(unittest.TestCase):
    def test_all_factory_ids_and_mixed_song_arrangements(self):
        rom = factory_fixture()
        for number in range(32):
            parsed = pattern.decode(rhythm_with_chain(), number, factory_rom=rom)
            self.assertEqual([(h.position, h.note, h.velocity) for h in parsed.hits], [(0, 36 + number, 100)])
            self.assertEqual(parsed.hits[0].file_offset, 0x3100 + 32 * number + 3)
        with tempfile.TemporaryDirectory() as directory:
            factory_path = Path(directory) / "owned.bin"
            factory_path.write_bytes(rom)
            with patch.object(pattern, "FACTORY_ROM_SHA256", hashlib.sha256(rom).hexdigest()):
                for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                    source, target = Path(directory) / (kind + suffix), Path(directory) / (kind + ".mid")
                    raw = bytearray(song_fixture(kind))
                    raw[0x44:0x48] = bytes((0x17, 0x3E, 0x3F, 255))
                    raw[0x23B + 0x17] = 3
                    source.write_bytes(raw)
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(cli.main([kind.lower(), str(source), str(target),
                                                   "--factory-rom", str(factory_path), "--gate-ticks", "12"]), 0)
                    midi = mido.MidiFile(target)
                    self.assertEqual(len(midi.tracks), 4)
                    self.assertEqual(note_times(midi.tracks[-1]), [(0, 9, 59, 100), (1104, 9, 38, 100)])
                    meters, tick = [], 0
                    for message in midi.tracks[0]:
                        tick += message.time
                        if message.type == "time_signature":
                            meters.append((tick, message.numerator))
                    self.assertEqual(meters, [(0, 3), (288, 8)])
                    self.assertEqual(source.read_bytes(), raw)
                self.assertEqual(factory_path.read_bytes(), rom)

    def test_rhythm_cli_factory_single_all_and_chain(self):
        rom = factory_fixture()
        with tempfile.TemporaryDirectory() as directory:
            source, factory_path = Path(directory) / "rhythm.444", Path(directory) / "owned.bin"
            raw = bytearray(rhythm_with_chain())
            raw[0x2602:0x2605] = bytes((0x17, 0x3E, 0))
            source.write_bytes(raw)
            factory_path.write_bytes(rom)
            with patch.object(pattern, "FACTORY_ROM_SHA256", hashlib.sha256(rom).hexdigest()):
                for command, mode, tracks, hits in (("pattern", None, 2, 1),
                                                    ("rhythm", "pattern", 2, 1),
                                                    ("rhythm", "all", 65, 35),
                                                    ("rhythm", "track", 2, 2)):
                    target = Path(directory) / f"{command}-{mode}.mid"
                    args = [command, str(source), str(target), "--factory-rom", str(factory_path), "--tempo-bpm", "120"]
                    if mode is not None:
                        args += ["--notes", mode]
                    if mode == "pattern" or command == "pattern":
                        args += ["--pattern-id", "0x17"]
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(cli.main(args), 0)
                    midi = mido.MidiFile(target)
                    self.assertEqual(len(midi.tracks), tracks)
                    self.assertEqual(sum(len(note_times(t)) for t in midi.tracks), hits)
                    if mode == "track":
                        self.assertEqual(note_times(midi.tracks[-1]), [(0, 9, 59, 100), (672, 9, 36, 100)])
                        self.assertEqual(sum(m.time for m in midi.tracks[-1]), 1056)
                    if mode == "all":
                        self.assertEqual(sum(m.time for m in midi.tracks[1 + 0x17]), 288)
                        self.assertEqual(sum(m.time for m in midi.tracks[1 + 0x3E]), 384)
                    if mode == "pattern" or command == "pattern":
                        self.assertEqual(sum(m.time for m in midi.tracks[-1]), 288)

    def test_factory_integrity_pointers_and_record_bounds(self):
        raw = rhythm_with_chain()
        rom = factory_fixture()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "owned.bin"
            for bad in (b"short", bytes(pattern.FACTORY_ROM_SIZE)):
                source.write_bytes(bad)
                with self.assertRaisesRegex(D20Error, "size or SHA256"):
                    pattern.read_factory_rom(source)
        for offset, value, message in ((0x3000, b"\0\0", "pointer"),
                                        (0x3101, b"\x61", "record bounds"),
                                        (0x3108, b"\x01", "terminator")):
            corrupt = bytearray(rom)
            corrupt[offset:offset + len(value)] = value
            with self.subTest(offset=offset), self.assertRaisesRegex(D20Error, message):
                pattern.decode(raw, 0, factory_rom=corrupt)
        truncated = rom[:0x3108]
        with self.assertRaisesRegex(D20Error, "record bounds"):
            pattern.decode(raw, 0, factory_rom=truncated)
        raw = bytearray(raw)
        raw[0x2602] = 0x40
        with self.assertRaisesRegex(D20Error, "Invalid rhythm selection"):
            pattern.rhythm_chain(raw, factory_rom=rom)

    def test_factory_rom_cannot_be_overwritten_by_any_export(self):
        with tempfile.TemporaryDirectory() as directory:
            rhythm_path, song_path = Path(directory) / "rhythm.444", Path(directory) / "song.222"
            factory_path = Path(directory) / "factory.mid"
            rhythm_path.write_bytes(rhythm_with_chain())
            song_path.write_bytes(song_fixture("SONG"))
            factory_path.write_bytes(factory_fixture())
            with self.assertRaisesRegex(D20Error, "different files"):
                pattern.convert(rhythm_path, factory_path, factory_rom=factory_path,
                                pattern_id=0, tempo_bpm=120, force=True)
            with self.assertRaisesRegex(D20Error, "different files"):
                pattern.convert_rhythm(rhythm_path, factory_path, factory_rom=factory_path,
                                       mode="all", pattern_id=None, tempo_bpm=120, force=True)
            with self.assertRaisesRegex(D20Error, "different files"):
                song.convert(song_path, factory_path, factory_rom=factory_path, force=True)
            self.assertEqual(factory_path.read_bytes(), factory_fixture())

    @unittest.skipUnless(os.getenv("D20_FACTORY_ROM") and os.getenv("D20_TESTRHY_444"),
                         "Set D20_FACTORY_ROM and D20_TESTRHY_444 for owned-ROM regression.")
    def test_optional_real_factory_table_and_meter_defaults(self):
        rom = pattern.read_factory_rom(Path(os.environ["D20_FACTORY_ROM"]))
        raw = Path(os.environ["D20_TESTRHY_444"]).read_bytes()
        decoded = [pattern.decode(raw, number, factory_rom=rom) for number in range(32)]
        self.assertEqual(len(decoded[0].hits), 13)
        self.assertEqual([p.beats for p in decoded], [3 if n == 0x17 else 8 if n in (0x1B, 0x1C) else 4 for n in range(32)])
        self.assertEqual([(h.position, h.note, h.velocity) for h in decoded[0].hits[:2]], [(0, 35, 125), (0, 42, 109)])


if __name__ == "__main__":
    unittest.main()
