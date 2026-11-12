"""BETA Song/All note export, including byte-level timing and safety boundaries."""

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

from roland_d20_tools import cli, inspect, pattern, song
from roland_d20_tools.core import D20Error


def fixture(kind: str) -> bytes:
    raw = bytearray(song.SONG_SIZE)
    raw[2] = 3
    raw[6:16] = b"TEST SONG "
    base = 0x024E95
    raw[0x41:0x44] = base.to_bytes(3, "little")
    raw[0x44:0x47] = bytes((0x3E, 0x3F, 0xFF))
    raw[0x23B + 0x3E] = 8
    raw[0x23B + 0x3F] = 8
    interval0 = bytes.fromhex("00 90 3c 64 10 3e 50 30 80 3c 31 3e ff")
    interval1 = bytes.fromhex("00 91 40 50 40 81 40 ff")
    raw[0x1A00:0x1A00 + len(interval0 + interval1)] = interval0 + interval1
    raw[0x283:0x286] = (base + len(interval0) - 1).to_bytes(3, "little")
    raw[0x286:0x289] = (base + len(interval0 + interval1) - 1).to_bytes(3, "little")
    raw[0x289:0x28C] = b"\xff" * 3
    base_pattern = 0x3B00
    raw[base_pattern:base_pattern + 294] = b"\x02\x00\x00" + b"\xff\x80\x00" * 97
    empty = base_pattern + 30 * 294
    active = base_pattern + 31 * 294
    raw[empty:empty + 294] = b"\x07\x00\x00" + b"\xff\x80\x00" * 97
    raw[active:active + 294] = b"\x07\x01\x00\x0c\x26\x64" + b"\xff\x80\x00" * 96
    raw[base_pattern + 0x2900:base_pattern + 0x2F00] = raw[base_pattern + 0x1D00:base_pattern + 0x2300]
    if kind == "SONG":
        return bytes(raw)
    all_data = bytearray(song.ALL_SIZE)
    all_data[:0x3B00] = raw[:0x3B00]
    all_data[0x10] = 1
    all_data[0x9000:0xC000] = raw[0x3B00:0x6B00]
    return bytes(all_data)


class SongBetaTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("D20_TESTSONG_222") and os.environ.get("D20_TESTALL_111"),
                         "Set D20_TESTSONG_222 and D20_TESTALL_111 for local disk-image regression.")
    def test_optional_real_song_and_all_match_known_note_fixture(self) -> None:
        native_song = Path(os.environ["D20_TESTSONG_222"]).read_bytes()
        native_all = Path(os.environ["D20_TESTALL_111"]).read_bytes()
        song_notes, all_notes = song.decode(native_song), song.decode(native_all)
        self.assertEqual(song_notes.events, all_notes.events)
        self.assertEqual(song_notes.meter_changes, all_notes.meter_changes)
        self.assertEqual((len(song_notes.events), song_notes.lanes, song_notes.pattern_count),
                         (2044, (0, 1, 7), 51))
        self.assertEqual((song.saved_tempo(native_song), song.saved_tempo(native_all)), (118, 118))

    def test_saved_tempo_defaults_and_explicit_override_for_both_containers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for kind, extension in (("SONG", ".222"), ("ALL", ".111")):
                source = Path(directory) / (kind + extension)
                output = Path(directory) / (kind + ".mid")
                for code, bpm in ((0, 40), (0x27, 118), (0x28, 120), (0x69, 250)):
                    raw = bytearray(fixture(kind))
                    raw[0x36] = code
                    source.write_bytes(raw)
                    self.assertEqual(song.saved_tempo(raw), bpm)
                    with redirect_stdout(io.StringIO()) as stdout:
                        self.assertEqual(cli.main([kind.lower(), str(source), str(output), "--force"]), 0)
                    self.assertIn(f"saved tempo {bpm} BPM", stdout.getvalue())
                    midi = mido.MidiFile(output)
                    self.assertEqual([m.tempo for m in midi.tracks[0] if m.type == "set_tempo"],
                                     [mido.bpm2tempo(bpm)])
                    self.assertIn(f"Saved tempo {bpm} BPM", inspect._song_metadata(source, (kind, "TEST"))[-1][1])
                    self.assertEqual(source.read_bytes(), raw)
                song.convert(source, output, tempo_bpm=119, force=True)
                midi = mido.MidiFile(output)
                self.assertEqual([m.tempo for m in midi.tracks[0] if m.type == "set_tempo"], [mido.bpm2tempo(119)])
                self.assertTrue(any(m.type == "text" and "override tempo 119 BPM" in m.text for m in midi.tracks[0]))

    def test_invalid_saved_tempo_requires_override_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "song.222", Path(directory) / "song.mid"
            raw = bytearray(fixture("SONG"))
            raw[0x36] = 0x6A
            source.write_bytes(raw)
            with self.assertRaisesRegex(D20Error, "Invalid saved tempo code.*--tempo-bpm"):
                song.convert(source, output, force=False)
            self.assertFalse(output.exists())
            self.assertIn("saved tempo unavailable", inspect.report(source))
            self.assertIn("Saved tempo unavailable", inspect._song_metadata(source, ("SONG", "TEST"))[-1][1])
            song.convert(source, output, tempo_bpm=120, force=False)
            self.assertEqual([m.tempo for m in mido.MidiFile(output).tracks[0] if m.type == "set_tempo"], [500000])

    def test_synthetic_running_status_absolute_time_and_midi_for_both_containers(self) -> None:
        expected = [(0, 0, 60, 100), (16, 0, 62, 80), (48, 0, 60, 0),
                    (49, 0, 62, 0), (192, 1, 64, 80), (256, 1, 64, 0)]
        results = []
        with tempfile.TemporaryDirectory() as directory:
            for kind, extension in (("SONG", ".222"), ("ALL", ".111")):
                source = Path(directory) / (kind + extension)
                dest = Path(directory) / (kind + ".mid")
                source.write_bytes(fixture(kind))
                self.assertEqual(inspect.native_type(source)[0], kind)
                parsed = song.decode(source.read_bytes())
                self.assertEqual(parsed.kind, kind)
                self.assertEqual(parsed.lanes, (0, 1))
                self.assertEqual(parsed.meter_changes, ((0, 8),))
                self.assertEqual(parsed.pattern_count, 2)
                self.assertEqual([(e.position, e.status, e.note, e.velocity) for e in parsed.events],
                                 [(0, 0x90, 60, 100), (16, 0x90, 62, 80), (48, 0x80, 60, 0),
                                  (49, 0x80, 62, 0), (192, 0x91, 64, 80), (256, 0x81, 64, 0)])
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(cli.main([kind.lower(), str(source), str(dest), "--tempo-bpm", "120"]), 0)
                self.assertIn("BETA: exported 6 note events", stdout.getvalue())
                midi = mido.MidiFile(dest)
                self.assertEqual((midi.type, midi.ticks_per_beat, len(midi.tracks)), (1, 96, 4))
                self.assertEqual([(m.numerator, m.denominator) for m in midi.tracks[0]
                                  if m.type == "time_signature"], [(8, 4)])
                self.assertEqual([m.tempo for m in midi.tracks[0] if m.type == "set_tempo"], [500_000])
                notes = []
                for track in midi.tracks[1:-1]:
                    tick = 0
                    for message in track:
                        tick += message.time
                        if message.type == "note_on":
                            notes.append((tick, message.channel, message.note, message.velocity))
                self.assertEqual(sorted(notes), sorted(expected))
                rhythm = midi.tracks[-1]
                drum_time = 0
                drum_events = []
                for message in rhythm:
                    drum_time += message.time
                    if message.type in ("note_on", "note_off"):
                        drum_events.append((drum_time, message.type, message.channel, message.note, message.velocity))
                self.assertEqual(drum_events, [(816, "note_on", 9, 38, 100),
                                               (817, "note_off", 9, 38, 0)])
                results.append(sorted(notes))
            self.assertEqual(results[0], results[1])

    def test_bad_index_unsupported_status_and_cross_interval_running_status(self) -> None:
        raw = bytearray(fixture("SONG"))
        raw[0x283:0x286] = (0x024E96).to_bytes(3, "little")
        with self.assertRaisesRegex(D20Error, "index"):
            song.decode(raw)
        raw = bytearray(fixture("SONG"))
        raw[0x1A01] = 0xA0
        with self.assertRaisesRegex(D20Error, "Unsupported BETA"):
            song.decode(raw)
        raw = bytearray(fixture("SONG"))
        raw[0x1A0E] = 0x40  # first record after FF has no status to reuse
        with self.assertRaisesRegex(D20Error, "Unsupported BETA"):
            song.decode(raw)

    def test_wrong_command_tempo_and_output_safety(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "song.222"
            output = Path(directory) / "notes.mid"
            source.write_bytes(fixture("SONG"))
            with self.assertRaisesRegex(D20Error, "Standard MIDI"):
                song.convert(source, output.with_suffix(".syx"), tempo_bpm=120, force=False)
            with self.assertRaisesRegex(D20Error, "use the 'song' command"):
                song.convert(source, output, tempo_bpm=120, force=False, expected_kind="ALL")
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(D20Error, "tempo-bpm"):
                song.convert(source, output, tempo_bpm=0, force=False)
            with self.assertRaisesRegex(D20Error, "tempo-bpm"):
                song.convert(source, output, tempo_bpm=3, force=False)
            alias = Path(directory) / "native-by-content.mid"
            alias.write_bytes(source.read_bytes())
            with self.assertRaisesRegex(D20Error, "different files"):
                song.convert(alias, alias, tempo_bpm=120, force=True)
            song.convert(source, output, tempo_bpm=120, force=False)
            original = output.read_bytes()
            with self.assertRaisesRegex(D20Error, "Output already exists"):
                song.convert(source, output, tempo_bpm=120, force=False)
            self.assertEqual(output.read_bytes(), original)
            song.convert(source, output, tempo_bpm=100, force=True)
            self.assertNotEqual(output.read_bytes(), original)

    def test_malformed_song_rejected_at_each_decode_stage(self) -> None:
        for offset, value, message in (
            (2, b"\x00", "recognised native"),
            (0x3B00, b"\x08", "recognised native"),
            (0x6400, b"\x01", "Rhythm mirror"),
            (0x41, b"\0" * 3, "physical base pointer"),
            (0x283, b"\xff" * 3, "missing its FF boundaries"),
            (0x1A00, b"\xc0", "Invalid Song position"),
            (0x1A03, b"\x80", "Invalid Song event data"),
        ):
            raw = bytearray(fixture("SONG"))
            raw[offset:offset + len(value)] = value
            with self.subTest(offset=offset), self.assertRaisesRegex(D20Error, message):
                song.decode(raw)
        raw = bytearray(fixture("SONG"))
        raw[0x283:0x289] = raw[0x41:0x44] + b"\xff" * 3
        raw[0x1A00] = 0xFF
        with self.assertRaisesRegex(D20Error, "No supported Song events"):
            song.decode(raw)

    def test_cli_note_only_export_can_omit_unvalidated_meter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "song.222"
            output = Path(directory) / "song.mid"
            raw = bytearray(fixture("SONG"))
            raw[0x23B + 0x3E] = 0
            source.write_bytes(raw)
            with redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(cli.main(["song", str(source), str(output), "--tempo-bpm", "120", "--no-rhythm-track"]), 0)
            self.assertIn("meter unavailable", stdout.getvalue())
            self.assertEqual(len(mido.MidiFile(output).tracks), 3)
            self.assertFalse(any(msg.type == "time_signature" for msg in mido.MidiFile(output).tracks[0]))

    def test_full_index_can_end_at_the_region_limit(self) -> None:
        raw = bytearray(fixture("SONG"))
        expected = song.decode(raw).events
        pointer = int.from_bytes(raw[0x286:0x289], "little")
        base = int.from_bytes(raw[0x41:0x44], "little")
        # A full table can address successive empty intervals after the music.
        for offset in range(0x289, song.INDEX_END - 2, 3):
            pointer += 1
            raw[offset:offset + 3] = pointer.to_bytes(3, "little")
            raw[song.EVENT_START + pointer - base] = 0xFF
        self.assertEqual(song.decode(raw).events, expected)

    def test_meter_changes_are_placed_at_pattern_boundaries(self) -> None:
        raw = bytearray(fixture("SONG"))
        raw[0x23B + 0x3F] = 3
        parsed = song.decode(raw)
        self.assertEqual(parsed.meter_changes, ((0, 8), (768, 3)))

    def test_unsupported_preset_rejects_rhythm_without_losing_song_only_option(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = bytearray(fixture("SONG"))
            raw[0x44] = 0x01
            raw[0x23B + 0x01] = 4
            source, output = Path(directory) / "song.222", Path(directory) / "song.mid"
            source.write_bytes(raw)
            with self.assertRaisesRegex(D20Error, "ROM preset"):
                song.convert(source, output, tempo_bpm=120, force=False)
            self.assertFalse(output.exists())
            song.convert(source, output, tempo_bpm=120, force=False, rhythm_track=False)
            self.assertEqual(len(mido.MidiFile(output).tracks), 3)
            with self.assertRaisesRegex(D20Error, "gate-ticks"):
                song.convert(source, output, tempo_bpm=120, force=True, gate_ticks=0)

    def test_song_duration_conflict_rejects_rhythm_expansion(self) -> None:
        raw = bytearray(fixture("SONG"))
        raw[0x23B + 0x3F] = 4
        with self.assertRaisesRegex(D20Error, "disagrees"):
            pattern.expanded_rhythm_track(raw, gate_ticks=1)


if __name__ == "__main__":
    unittest.main()
