"""Program reference preservation, running status and same-tick event order."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

import mido

from roland_d20_tools import cli, inspect, song
from roland_d20_tools.core import D20Error
from test_song_beta import fixture


def with_intervals(kind, intervals):
    raw = bytearray(fixture(kind))
    raw[song.INDEX_START:song.INDEX_END] = b"\xff" * (song.INDEX_END - song.INDEX_START)
    raw[song.EVENT_START:song.EVENT_END] = b"\xff" * (song.EVENT_END - song.EVENT_START)
    base = int.from_bytes(raw[0x41:0x44], "little")
    offset = song.EVENT_START
    for index, data in enumerate(intervals):
        assert data[-1] == 255
        raw[offset:offset + len(data)] = data
        end = base + offset + len(data) - 1 - song.EVENT_START
        slot = song.INDEX_START + index * 3
        raw[slot:slot + 3] = end.to_bytes(3, "little")
        offset += len(data)
    return bytes(raw)


def events(track):
    tick, result = 0, []
    for msg in track:
        tick += msg.time
        if not msg.is_meta:
            result.append((tick, tuple(msg.bytes())))
    return result


class SongProgramTests(unittest.TestCase):
    def test_mixed_stream_preserves_order_repeats_numbers_and_offsets(self):
        intervals = [bytes.fromhex("00 C0 00 00 90 3C 64 10 C0 3F 10 40 10 40 "
                                   "10 90 3E 50 20 80 3C 21 3E 22 C1 7F FF"),
                     bytes.fromhex("00 C0 01 00 90 40 64 20 80 40 FF")]
        expected = [(0, (0xC0, 0)), (0, (0x90, 60, 100)),
                    (16, (0xC0, 63)), (16, (0xC0, 64)), (16, (0xC0, 64)),
                    (16, (0x90, 62, 80)), (32, (0x90, 60, 0)), (33, (0x90, 62, 0)),
                    (192, (0xC0, 1)), (192, (0x90, 64, 100)), (224, (0x90, 64, 0))]
        with tempfile.TemporaryDirectory() as directory:
            for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                raw = bytearray(with_intervals(kind, intervals))
                if kind == "ALL":
                    # Original synthetic user Tone/Timbre content must not trigger
                    # a GM remapping or alter the original program reference 64.
                    raw[0x7900 + 64 * 8:0x7902 + 64 * 8] = bytes((2, 31))
                    raw[0x3B00 + 31 * 246:0x3B0A + 31 * 246] = b"USER TONE "
                parsed = song.decode(raw)
                self.assertEqual((parsed.note_count, parsed.program_count, parsed.lanes), (6, 6, (0, 1)))
                changes = [e for e in parsed.events if isinstance(e, song.ProgramEvent)]
                self.assertEqual([(e.position, e.status, e.program) for e in changes],
                                 [(0, 0xC0, 0), (16, 0xC0, 63), (16, 0xC0, 64),
                                  (16, 0xC0, 64), (34, 0xC1, 127), (192, 0xC0, 1)])
                self.assertEqual([e.file_offset for e in changes[:4]], [0x1A00, 0x1A07, 0x1A0A, 0x1A0C])
                source, target = Path(directory) / (kind + suffix), Path(directory) / (kind + ".mid")
                source.write_bytes(raw)
                with redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(cli.main([kind.lower(), str(source), str(target)]), 0)
                self.assertIn("6 note events and 6 program changes", stdout.getvalue())
                midi = mido.MidiFile(target)
                self.assertEqual(len(midi.tracks), 4)
                self.assertEqual(events(midi.tracks[1]), expected)
                self.assertEqual(events(midi.tracks[2]), [(34, (0xC1, 127))])
                self.assertEqual(len(events(midi.tracks[3])), 2)  # independent rhythm on/off
                self.assertTrue(any(m.type == "text" and "no General MIDI translation" in m.text
                                    for m in midi.tracks[1]))
                self.assertIn("6 program changes", dict(inspect._song_metadata(source, (kind, "test")))["BETA note events"])
                self.assertEqual(source.read_bytes(), raw)

    def test_all_program_numbers_on_all_stored_lanes_without_notes(self):
        intervals = [bytes((0, 0xC0 | lane, 0)) + b"".join(bytes((p, p)) for p in range(1, 128)) + b"\xff"
                     for lane in range(16)]
        with tempfile.TemporaryDirectory() as directory:
            for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                raw = with_intervals(kind, intervals)
                parsed = song.decode(raw)
                self.assertEqual((parsed.note_count, parsed.program_count), (0, 2048))
                self.assertEqual(parsed.lanes, tuple(range(16)))
                source, target = Path(directory) / (kind + suffix), Path(directory) / (kind + ".mid")
                source.write_bytes(raw)
                song.convert(source, target, force=False, rhythm_track=False)
                midi = mido.MidiFile(target)
                self.assertEqual(len(midi.tracks), 17)
                for lane in range(16):
                    self.assertEqual(events(midi.tracks[lane + 1]),
                                     [(lane * 192 + p, (0xC0 | lane, p)) for p in range(128)])
                self.assertEqual(source.read_bytes(), raw)

    def test_bad_program_payload_and_status_reset_stop_before_output(self):
        cases = [([bytes.fromhex("00 C0 FF")], "Invalid Song event data"),
                 ([bytes.fromhex("00 C0 80 FF")], "Invalid Song event data"),
                 ([bytes.fromhex("00 C0 7F FF"), bytes.fromhex("00 04 FF")], "Unsupported BETA"),
                 ([bytes.fromhex("00 D0 01 FF")], "Unsupported BETA"),
                 ([bytes.fromhex("00 B0 07 FF")], "Invalid Song event data"),
                 ([bytes.fromhex("00 E0 00 FF")], "Invalid Song event data")]
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "song.222", Path(directory) / "song.mid"
            for intervals, message in cases:
                source.write_bytes(with_intervals("SONG", intervals))
                with self.subTest(intervals=intervals), self.assertRaisesRegex(D20Error, message):
                    song.convert(source, target, force=False)
                self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
