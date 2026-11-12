"""Recorded controls and pitch bend: exact bytes, timing and safety."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest

import mido

from roland_d20_tools import cli, inspect, song
from roland_d20_tools.core import D20Error
from test_song_programs import events, with_intervals


class SongControllerTests(unittest.TestCase):
    def test_mixed_events_and_sustain_order_for_both_containers(self):
        intervals = [bytes.fromhex(
            "00 C0 00 00 B0 07 64 00 0A 40 00 01 00 00 E0 00 40 "
            "00 90 3C 64 08 B0 01 7F 10 40 7F 10 40 7F 10 80 3C "
            "18 B0 40 40 19 40 3F 1A 40 00 20 E0 00 00 30 7F 7F 40 00 40 FF"),
            bytes.fromhex("00 B1 0A 00 00 E1 7F 3F 01 00 40 FF")]
        expected = [(0, (0xC0, 0)), (0, (0xB0, 7, 100)), (0, (0xB0, 10, 64)),
                    (0, (0xB0, 1, 0)), (0, (0xE0, 0, 64)), (0, (0x90, 60, 100)),
                    (8, (0xB0, 1, 127)), (16, (0xB0, 64, 127)), (16, (0xB0, 64, 127)),
                    (16, (0x90, 60, 0)), (24, (0xB0, 64, 64)), (25, (0xB0, 64, 63)),
                    (26, (0xB0, 64, 0)), (32, (0xE0, 0, 0)), (48, (0xE0, 127, 127)),
                    (64, (0xE0, 0, 64))]
        with tempfile.TemporaryDirectory() as directory:
            for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                raw = with_intervals(kind, intervals)
                parsed = song.decode(raw)
                self.assertEqual((parsed.note_count, parsed.program_count, parsed.controller_count,
                                  parsed.pitch_bend_count, parsed.lanes), (2, 1, 10, 6, (0, 1)))
                controls = [e for e in parsed.events if isinstance(e, song.ControllerEvent)]
                bends = [e for e in parsed.events if isinstance(e, song.PitchBendEvent)]
                self.assertEqual((controls[0].file_offset, controls[0].control, controls[0].value), (0x1A03, 7, 100))
                self.assertEqual(bends[0].file_offset, 0x1A0D)
                self.assertEqual([e.pitch for e in bends], [0, -8192, 8191, 0, -1, 0])
                source, target = Path(directory) / (kind + suffix), Path(directory) / (kind + ".mid")
                source.write_bytes(raw)
                with redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(cli.main([kind.lower(), str(source), str(target)]), 0)
                self.assertIn("10 controller events and 6 pitch bends", stdout.getvalue())
                midi = mido.MidiFile(target)
                self.assertEqual((midi.type, midi.ticks_per_beat, len(midi.tracks)), (1, 96, 4))
                self.assertEqual(events(midi.tracks[1]), expected)
                self.assertEqual(events(midi.tracks[2]), [(192, (0xB1, 10, 0)),
                                                         (192, (0xE1, 127, 63)), (193, (0xE1, 0, 64))])
                self.assertEqual(len(events(midi.tracks[-1])), 2)  # separate rhythm on/off
                details = dict(inspect._song_metadata(source, (kind, "test")))["BETA note events"]
                self.assertIn("10 controller events and 6 pitch bends", details)
                self.assertEqual(source.read_bytes(), raw)

    def test_controller_only_all_numbers_and_lanes(self):
        values = (0, 1, 63, 64, 127)
        intervals = [bytes((0, 0xB0 | lane, 0, values[lane % 5]))
                     + b"".join(bytes((cc, cc, values[(cc + lane) % 5])) for cc in range(1, 128))
                     + b"\xff" for lane in range(16)]
        with tempfile.TemporaryDirectory() as directory:
            for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                raw = with_intervals(kind, intervals)
                parsed = song.decode(raw)
                self.assertEqual((parsed.note_count, parsed.program_count, parsed.controller_count,
                                  parsed.pitch_bend_count), (0, 0, 2048, 0))
                source, target = Path(directory) / (kind + suffix), Path(directory) / (kind + ".mid")
                source.write_bytes(raw)
                song.convert(source, target, force=False, rhythm_track=False)
                midi = mido.MidiFile(target)
                self.assertEqual(len(midi.tracks), 17)
                for lane in range(16):
                    self.assertEqual(events(midi.tracks[lane + 1]),
                                     [(lane * 192 + cc, (0xB0 | lane, cc, values[(cc + lane) % 5]))
                                      for cc in range(128)])
                self.assertEqual(source.read_bytes(), raw)

    def test_full_fourteen_bit_pitch_range_round_trips_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                for group in range(16):
                    # Eight intervals fit safely within the native event region.
                    upper = range(group * 8, group * 8 + 8)
                    intervals = [bytes((0, 0xE0 | (msb % 16), 0, msb))
                                 + b"".join(bytes((lsb, lsb, msb)) for lsb in range(1, 128))
                                 + b"\xff" for msb in upper]
                    raw = with_intervals(kind, intervals)
                    parsed = song.decode(raw)
                    self.assertEqual((parsed.note_count, parsed.program_count, parsed.controller_count,
                                      parsed.pitch_bend_count), (0, 0, 0, 1024))
                    self.assertEqual([e.pitch for e in parsed.events],
                                     [msb * 128 + lsb - 8192 for msb in upper for lsb in range(128)])
                    source = Path(directory) / (kind + suffix)
                    target = Path(directory) / f"{kind}-{group}.mid"
                    source.write_bytes(raw)
                    song.convert(source, target, force=False, rhythm_track=False)
                    midi = mido.MidiFile(target)
                    self.assertEqual(len(midi.tracks), 9)
                    for track, msb in zip(midi.tracks[1:], upper):
                        self.assertEqual(events(track),
                                         [((msb % 8) * 192 + lsb, (0xE0 | (msb % 16), lsb, msb))
                                          for lsb in range(128)])
                    self.assertEqual(source.read_bytes(), raw)

    def test_truncated_data_reset_and_unsupported_families_preserve_output(self):
        invalid_data = ("00 B0 07 FF", "00 B0 80 40 FF", "00 B0 07 80 FF",
                        "00 B0 07 64 01 0A FF", "00 E0 FF", "00 E0 00 FF",
                        "00 E0 80 40 FF", "00 E0 00 80 FF", "00 E0 00 40 01 00 FF")
        cases = [([bytes.fromhex(data)], "Invalid Song event data") for data in invalid_data]
        cases += [([bytes.fromhex("00 B0 07 64 FF"), bytes.fromhex("00 0A 40 FF")], "Unsupported BETA"),
                  ([bytes.fromhex("00 E0 00 40 FF"), bytes.fromhex("00 00 40 FF")], "Unsupported BETA")]
        cases += [([bytes((0, status, 1, 2, 255))], "Unsupported BETA") for status in (0xA0, 0xD0, 0xF0)]
        with tempfile.TemporaryDirectory() as directory:
            for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                source, target = Path(directory) / (kind + suffix), Path(directory) / (kind + ".mid")
                target.write_bytes(b"existing output")
                for intervals, error in cases:
                    raw = with_intervals(kind, intervals)
                    source.write_bytes(raw)
                    with self.subTest(kind=kind, intervals=intervals), self.assertRaisesRegex(D20Error, error):
                        song.convert(source, target, force=True)
                    self.assertEqual(target.read_bytes(), b"existing output")
                    self.assertEqual(source.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
