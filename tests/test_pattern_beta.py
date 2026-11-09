"""ROM-supported D-20 pattern note MIDI, native-container and safety checks."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import mido

from roland_d20_tools import cli, pattern
from roland_d20_tools.core import D20Error


def fixture(kind: str) -> bytes:
    size, base = {"RHYTHM": (12_288, 0x100), "SONG": (27_648, 0x3B00), "ALL": (49_152, 0x9000)}[kind]
    data = bytearray(size)
    data[:3] = b"\x04\x00\x00" if kind == "RHYTHM" else b"\x00\x00\x03"
    if kind == "ALL":
        data[0x10] = 1
    offset = base + 31 * pattern.PATTERN_SIZE
    data[offset:offset + 3] = bytes((3, 3, 0))
    data[offset + 3:offset + 12] = bytes((0, 36, 90, 0, 38, 75, 24, 42, 100))
    data[offset + 12:offset + pattern.PATTERN_SIZE] = b"\xff\x80\x00" * 93 + b"\xff\x00\x00"
    setup = base + 0x2700
    data[setup + (36 - 24) * 4:setup + (36 - 23) * 4] = b"\x4e\x64\x07\x00"
    return bytes(data)


def rhythm_with_chain() -> bytes:
    raw = bytearray(fixture("RHYTHM"))
    for index in range(31):
        offset = 0x100 + index * pattern.PATTERN_SIZE
        raw[offset:offset + pattern.PATTERN_SIZE] = b"\x03\x00\x00" + b"\xff\x80\x00" * 97
    raw[0x2600:0x2605] = b"\x03\x00\x3e\x3f\x3f"
    empty = 0x100 + 30 * pattern.PATTERN_SIZE
    raw[empty:empty + pattern.PATTERN_SIZE] = b"\x03\x00\x00" + b"\xff\x80\x00" * 97
    raw[0x2A00:0x3000] = raw[0x1E00:0x2400]
    return bytes(raw)


def notes_from(path: Path) -> tuple[list[tuple[int, str, int, int, int]], list[mido.MetaMessage]]:
    midi = mido.MidiFile(path)
    assert midi.type == 1 and midi.ticks_per_beat == 96
    track = midi.tracks[1]
    tick = 0
    notes = []
    for message in track:
        tick += message.time
        if message.type in ("note_on", "note_off"):
            notes.append((tick, message.type, message.channel, message.note, message.velocity))
    return notes, [m for m in track if m.is_meta]


class PatternBetaTests(unittest.TestCase):
    def test_rhythm_cli_pattern_all_and_saved_track_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rhythm.444"
            source.write_bytes(rhythm_with_chain())
            for mode, expected_tracks, expected_hits in (("pattern", 2, 3),
                                                          ("all", 33, 3),
                                                          ("track", 2, 6)):
                output = Path(directory) / f"{mode}.mid"
                args = ["rhythm", str(source), str(output), "--notes", mode,
                        "--tempo-bpm", "120", "--gate-ticks", "2"]
                if mode == "pattern":
                    args += ["--pattern-id", "0x3f"]
                with redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(cli.main(args), 0)
                self.assertIn("BETA: exported Rhythm", stdout.getvalue())
                midi = mido.MidiFile(output)
                self.assertEqual(len(midi.tracks), expected_tracks)
                hits = sum(m.type == "note_on" and m.velocity > 0 for t in midi.tracks for m in t)
                self.assertEqual(hits, expected_hits)
                if mode == "track":
                    self.assertEqual([(m.numerator, m.denominator) for m in midi.tracks[0]
                                      if m.type == "time_signature"], [(4, 4)])
                    tick, times = 0, []
                    for message in midi.tracks[1]:
                        tick += message.time
                        if message.type == "note_on" and message.velocity:
                            times.append(tick)
                    self.assertEqual(times, [384, 384, 480, 768, 768, 864])
                    self.assertEqual(len([m for m in midi.tracks[1] if m.type == "marker"]), 3)
                if mode == "all":
                    self.assertIn("P-88", midi.tracks[-1][0].name)

    def test_rhythm_selection_count_and_preset_are_not_silent(self) -> None:
        raw = bytearray(rhythm_with_chain())
        raw[0x2600:0x2602] = b"\x00\x00"
        with self.assertRaisesRegex(D20Error, "selection count"):
            pattern.rhythm_chain(raw)
        raw[0x2600:0x2603] = b"\x01\x00\x1f"
        with self.assertRaisesRegex(D20Error, "ROM preset"):
            pattern.expanded_rhythm_track(raw, gate_ticks=1)

    def test_three_containers_produce_identical_note_tracks_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for kind, suffix in (("RHYTHM", ".444"), ("SONG", ".222"), ("ALL", ".111")):
                source = Path(directory) / (kind + suffix)
                target = Path(directory) / (kind + ".mid")
                source.write_bytes(fixture(kind))
                with redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(cli.main(["pattern", str(source), str(target), "--pattern-id", "0x3f",
                                               "--tempo-bpm", "120", "--gate-ticks", "2"]), 0)
                self.assertIn("BETA: exported 3 pattern hits", stdout.getvalue())
                midi = mido.MidiFile(target)
                self.assertEqual([(m.numerator, m.denominator) for m in midi.tracks[0] if m.type == "time_signature"], [(4, 4)])
                self.assertEqual([m.tempo for m in midi.tracks[0] if m.type == "set_tempo"], [500_000])
                notes, metadata = notes_from(target)
                self.assertIn("09H 4E640700", " ".join(m.text for m in metadata if m.type == "text"))
                self.assertEqual(notes, [(0, "note_on", 9, 36, 90), (0, "note_on", 9, 38, 75),
                                         (2, "note_off", 9, 36, 0), (2, "note_off", 9, 38, 0),
                                         (96, "note_on", 9, 42, 100), (98, "note_off", 9, 42, 0)])
                outputs.append(notes)
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[1], outputs[2])

    def test_reject_corrupt_hits_terminator_and_mirror_without_output(self) -> None:
        raw = fixture("RHYTHM")
        start = 0x100 + 31 * pattern.PATTERN_SIZE
        for offset, replacement, reason in ((start + 3, 96, "Invalid pattern hit"),
                                            (start + 5, 0, "Invalid pattern hit"),
                                            (start + 12, 0, "terminator"),
                                            (0x2A00, 1, "mirror")):
            damaged = bytearray(raw)
            damaged[offset] = replacement
            with self.subTest(offset=offset), self.assertRaisesRegex(D20Error, reason):
                pattern.decode(damaged, 0x3F)
        with self.assertRaisesRegex(D20Error, "0x20..0x3F"):
            pattern.decode(raw, 0x1F)

    def test_output_safety_and_audition_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "pattern.444"
            target = Path(directory) / "pattern.mid"
            source.write_bytes(fixture("RHYTHM"))
            with self.assertRaisesRegex(D20Error, "gate-ticks"):
                pattern.convert(source, target, pattern_id=0x3F, tempo_bpm=120, gate_ticks=0)
            self.assertFalse(target.exists())
            with self.assertRaisesRegex(D20Error, "tempo-bpm"):
                pattern.convert(source, target, pattern_id=0x3F, tempo_bpm=0)
            pattern.convert(source, target, pattern_id=0x3F, tempo_bpm=120)
            first = target.read_bytes()
            with self.assertRaisesRegex(D20Error, "Output already exists"):
                pattern.convert(source, target, pattern_id=0x3F, tempo_bpm=120)
            self.assertEqual(target.read_bytes(), first)
            pattern.convert(source, target, pattern_id=0x3F, tempo_bpm=120, channel=0, force=True)
            self.assertEqual(notes_from(target)[0][0][2], 0)

    @unittest.skipUnless(all(os.getenv(name) for name in ("D20_TESTRHY_444", "D20_TESTSONG_222", "D20_TESTALL_111")),
                         "Set D20_TESTRHY_444, D20_TESTSONG_222, and D20_TESTALL_111 for local regression.")
    def test_optional_saved_p88_matches_all_three_containers(self) -> None:
        paths = (os.environ["D20_TESTRHY_444"], os.environ["D20_TESTSONG_222"], os.environ["D20_TESTALL_111"])
        decoded = [pattern.decode(Path(filename).read_bytes(), 0x3F) for filename in paths]
        self.assertEqual([len(item.hits) for item in decoded], [77] * 3)
        self.assertEqual([item.beats for item in decoded], [8] * 3)
        self.assertEqual([(hit.position, hit.note, hit.velocity) for hit in decoded[0].hits],
                         [(hit.position, hit.note, hit.velocity) for hit in decoded[1].hits])
        self.assertEqual([(hit.position, hit.note, hit.velocity) for hit in decoded[1].hits],
                         [(hit.position, hit.note, hit.velocity) for hit in decoded[2].hits])
        chains = [pattern.rhythm_chain(Path(filename).read_bytes()) for filename in paths]
        self.assertEqual([len(chain) for chain in chains], [49, 51, 51])
        self.assertEqual(chains[1], chains[2])
        expanded = [pattern.expanded_rhythm_track(Path(filename).read_bytes(), gate_ticks=12)
                    for filename in paths]
        self.assertEqual([result[2] for result in expanded], [3157] * 3)


if __name__ == "__main__":
    unittest.main()
