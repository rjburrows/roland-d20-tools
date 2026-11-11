"""ROM-traced saved sound settings; no invented program or CC initialization."""

import os
from pathlib import Path
import tempfile
import unittest

import mido

from roland_d20_tools import inspect, song
from roland_d20_tools.core import D20Error
from test_song_beta import fixture


def with_setup(kind, values=(0, 7, 7, 99)):
    raw = bytearray(fixture(kind))
    mode, time, level, rhythm = values
    raw[0x16:0x1C] = bytes((0x88, mode, time, 0x89, level, rhythm))
    return bytes(raw)


def musical_events(midi):
    result = []
    for index, track in enumerate(midi.tracks):
        tick = 0
        for message in track:
            tick += message.time
            if not message.is_meta:
                result.append((index, tick, message.bytes()))
    return result


class SavedSetupTests(unittest.TestCase):
    def test_both_container_types_and_seven_bit_boundaries(self):
        for kind in ("SONG", "ALL"):
            for values in ((0, 7, 7, 99), (0, 0, 0, 0), (127, 127, 127, 127)):
                with self.subTest(kind=kind, values=values):
                    self.assertEqual(song.saved_setup(with_setup(kind, values)), song.SavedSetup(*values))
            self.assertIsNone(song.saved_setup(fixture(kind)))
            for index in (0x16, 0x19):
                raw = bytearray(with_setup(kind))
                raw[index] = 0
                self.assertIsNone(song.saved_setup(raw))
        with self.assertRaises(D20Error):
            song.saved_setup(b"short")

    def test_non_seven_bit_data_rejected_before_any_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "song.222", Path(directory) / "song.mid"
            for index in (0x17, 0x18, 0x1A, 0x1B):
                for value in (128, 255):
                    raw = bytearray(with_setup("SONG"))
                    raw[index] = value
                    source.write_bytes(raw)
                    with self.assertRaisesRegex(D20Error, "Invalid saved setup"):
                        song.convert(source, target, force=False)
                    self.assertFalse(target.exists())
                    self.assertEqual(source.read_bytes(), raw)
                    detail = dict(inspect._song_metadata(source, ("SONG", "test")))["Saved sound setup"]
                    self.assertIn("Unavailable (Invalid saved setup", detail)

    def test_export_preserves_values_as_text_without_changing_music(self):
        with tempfile.TemporaryDirectory() as directory:
            for kind, suffix in (("SONG", ".222"), ("ALL", ".111")):
                source = Path(directory) / (kind + suffix)
                plain, enriched = Path(directory) / (kind + "-plain.mid"), Path(directory) / (kind + "-setup.mid")
                source.write_bytes(fixture(kind))
                song.convert(source, plain, force=False)
                missing = dict(inspect._song_metadata(source, (kind, "test")))["Saved sound setup"]
                self.assertIn("no validated 88/89", missing)
                raw = with_setup(kind)
                source.write_bytes(raw)
                song.convert(source, enriched, force=False, expected_kind=kind)
                midi = mido.MidiFile(enriched)
                expected = song.SavedSetup(0, 7, 7, 99).description
                self.assertIn(expected, [m.text for m in midi.tracks[0] if m.type == "text"])
                self.assertTrue(all(m.time == 0 for m in midi.tracks[0] if m.type == "text"))
                self.assertEqual(musical_events(midi), musical_events(mido.MidiFile(plain)))
                self.assertFalse(any(m.type in ("control_change", "program_change") for t in midi.tracks for m in t))
                self.assertEqual(dict(inspect._song_metadata(source, (kind, "test")))["Saved sound setup"], expected)
                self.assertEqual(source.read_bytes(), raw)

    @unittest.skipUnless(os.getenv("D20_TESTSONG_222") and os.getenv("D20_TESTALL_111"),
                         "Set native SONG/ALL paths for private saved-setup regression.")
    def test_optional_private_pair(self):
        for name in ("D20_TESTSONG_222", "D20_TESTALL_111"):
            self.assertEqual(song.saved_setup(Path(os.environ[name]).read_bytes()), song.SavedSetup(0, 7, 7, 99))


if __name__ == "__main__":
    unittest.main()
