"""Public and optional local regression tests for Roland D-20 Tools."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mido

from roland_d20_tools import cli, inspect, rhythm, sound
from roland_d20_tools.core import MemoryImage, make_messages, scan_messages


def complete_image(size: int) -> MemoryImage:
    image = MemoryImage.create(size)
    image.write(0, bytes(size), "test data")
    return image


def midi_from_messages(messages: list[mido.Message]) -> mido.MidiFile:
    midi = mido.MidiFile(type=0)
    track = mido.MidiTrack()
    track.extend(messages)
    midi.tracks.append(track)
    return midi


class PublicConverterTests(unittest.TestCase):
    def test_sound_round_trip_and_syx_inspection(self) -> None:
        tones = complete_image(sound.TONE_COUNT * sound.TONE_SYSEX_SIZE)
        timbres = complete_image(sound.TIMBRE_COUNT * sound.TIMBRE_SIZE)
        patches = complete_image(sound.PATCH_COUNT * sound.PATCH_SIZE)
        messages = [*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10)]
        raw = sound.encode("PUBLICTEST", scan_messages(messages))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.333"
            midi = root / "sound.mid"
            syx = root / "sound.syx"
            rebuilt = root / "rebuilt.333"
            source.write_bytes(raw)
            self.assertEqual(cli.main(["sound", str(source), str(midi)]), 0)
            self.assertEqual(cli.main(["sound", str(source), str(syx)]), 0)
            self.assertIn("Tone: 64 message(s)", inspect.report(syx))
            self.assertEqual(cli.main(["sound", str(midi), str(rebuilt), "--name", "PUBLICTEST"]), 0)
            self.assertEqual(rebuilt.read_bytes(), raw)

    def test_rhythm_round_trip(self) -> None:
        setup = complete_image(rhythm.SETUP_SIZE)
        pattern = complete_image(rhythm.PATTERN_SIZE)
        track = complete_image(rhythm.TRACK_SIZE)
        sequencer = complete_image(rhythm.SEQUENCER_SIZE)
        messages = [
            *make_messages(0x09, setup, 0x10),
            *make_messages(0x0A, pattern, 0x10),
            *make_messages(0x0B, track, 0x10),
            *make_messages(0x0C, sequencer, 0x10),
        ]
        raw = rhythm.encode("RHYTEST", scan_messages(messages))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.444"
            midi = root / "rhythm.mid"
            rebuilt = root / "rebuilt.444"
            source.write_bytes(raw)
            self.assertEqual(cli.main(["rhythm", str(source), str(midi)]), 0)
            self.assertEqual(cli.main(["rhythm", str(midi), str(rebuilt), "--name", "RHYTEST"]), 0)
            self.assertEqual(rebuilt.read_bytes(), raw)

    def test_invalid_and_wip_commands_fail_safely(self) -> None:
        self.assertEqual(cli.main(["song"]), 2)
        self.assertEqual(cli.main(["all"]), 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-a-midi.mid"
            path.write_bytes(b"not MIDI")
            self.assertEqual(cli.main(["inspect", str(path)]), 2)


class LocalRegressionTests(unittest.TestCase):
    """Run only when private local fixtures are explicitly supplied."""

    @property
    def awkward(self) -> Path:
        return Path(os.environ.get("D20_AWKWARD_MID", ""))

    @property
    def testsnd(self) -> Path:
        return Path(os.environ.get("D20_TESTSND_333", ""))

    @unittest.skipUnless(os.environ.get("D20_AWKWARD_MID"), "Set D20_AWKWARD_MID to run this private regression test.")
    def test_awkward_midi_inspection_and_native_conversions(self) -> None:
        self.assertTrue(self.awkward.is_file(), self.awkward)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sound_file, rhythm_file = root / "awkward.333", root / "awkward.444"
            sound_midi, rhythm_midi = root / "awkward-sound.mid", root / "awkward-rhythm.mid"
            self.assertIn("System: 1 message(s)", inspect.report(self.awkward))
            self.assertEqual(cli.main(["sound", str(self.awkward), str(sound_file), "--name", "AWKWARD"]), 0)
            self.assertEqual(cli.main(["sound", str(sound_file), str(sound_midi)]), 0)
            self.assertEqual(cli.main(["rhythm", str(self.awkward), str(rhythm_file), "--name", "AWKWARD"]), 0)
            self.assertEqual(cli.main(["rhythm", str(rhythm_file), str(rhythm_midi)]), 0)
            self.assertIn("Tone: 64 message(s)", inspect.report(sound_midi))
            self.assertIn("Rhythm Pattern: 64 message(s)", inspect.report(rhythm_midi))

    @unittest.skipUnless(os.environ.get("D20_TESTSND_333"), "Set D20_TESTSND_333 to run this private regression test.")
    def test_testsnd_333_round_trip_is_byte_identical(self) -> None:
        self.assertTrue(self.testsnd.is_file(), self.testsnd)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            midi, rebuilt = root / "testsnd.mid", root / "testsnd.333"
            self.assertEqual(cli.main(["sound", str(self.testsnd), str(midi)]), 0)
            self.assertEqual(cli.main(["sound", str(midi), str(rebuilt), "--name", "TESTSND"]), 0)
            self.assertEqual(rebuilt.read_bytes(), self.testsnd.read_bytes())


if __name__ == "__main__":
    unittest.main()

