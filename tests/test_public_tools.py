"""Public and optional local regression tests for Roland D-20 Tools."""

from __future__ import annotations

import os
import io
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mido

from roland_d20_tools import cli, inspect, reports, rhythm, sound
from roland_d20_tools.core import D20Error, MemoryImage, make_messages, roland_checksum, scan_messages


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
    def test_nested_report_commands_validate_and_decode_complete_records(self) -> None:
        system = complete_image(50)
        patches = complete_image(128 * 38)
        timbres = complete_image(128 * 8)
        tones = complete_image(64 * 256)
        rhythm_setup = complete_image(85 * 4)
        messages = [
            *make_messages(0x10, system, 0x10), *make_messages(0x07, patches, 0x10),
            *make_messages(0x05, timbres, 0x10), *make_messages(0x08, tones, 0x10),
            *make_messages(0x09, rhythm_setup, 0x10),
        ]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reports.mid"
            midi_from_messages(messages).save(source)
            cases = (
                (["report", "system", str(source)], "Global System"),
                (["report", "patch", str(source), "--patch", "1"], "Patch 1:"),
                (["report", "timbre", str(source), "--slot", "I-11"], "Timbre slot I-11"),
                (["report", "tone", str(source), "--tone", "1"], "Tone 1:"),
                (["report", "rhythm", str(source)], "Rhythm Setup"),
            )
            for command, expected in cases:
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(cli.main(command), 0)
                self.assertIn(expected, output.getvalue())
            self.assertEqual(cli.main(["report", "patch", str(source), "--patch", "129"]), 2)

    def test_selected_report_refuses_an_incomplete_record(self) -> None:
        address, payload = (0x07, 0x00, 0x00), (0x00,)
        message = mido.Message("sysex", data=(0x41, 0x10, 0x16, 0x12, *address, *payload, roland_checksum((*address, *payload))))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "partial.mid"
            midi_from_messages([message]).save(source)
            with self.assertRaisesRegex(D20Error, "incomplete"):
                reports.patch(source, 1)

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
    def demo_dump(self) -> Path:
        return Path(os.environ.get("D20_DEMO_DUMP_MID", ""))

    @property
    def testsnd(self) -> Path:
        return Path(os.environ.get("D20_TESTSND_333", ""))

    @unittest.skipUnless(os.environ.get("D20_DEMO_DUMP_MID"), "Set D20_DEMO_DUMP_MID to run this private regression test.")
    def test_demo_dump_midi_inspection_and_native_conversions(self) -> None:
        self.assertTrue(self.demo_dump.is_file(), self.demo_dump)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sound_file, rhythm_file = root / "demodump.333", root / "demodump.444"
            sound_midi, rhythm_midi = root / "demodump-sound.mid", root / "demodump-rhythm.mid"
            self.assertIn("System: 1 message(s)", inspect.report(self.demo_dump))
            self.assertEqual(cli.main(["sound", str(self.demo_dump), str(sound_file), "--name", "DEMODUMP"]), 0)
            self.assertEqual(cli.main(["sound", str(sound_file), str(sound_midi)]), 0)
            self.assertEqual(cli.main(["rhythm", str(self.demo_dump), str(rhythm_file), "--name", "DEMODUMP"]), 0)
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
