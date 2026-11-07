"""Public and optional local regression tests for Roland D-20 Tools."""

from __future__ import annotations

import os
import io
import json
from importlib.metadata import version
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mido

from roland_d20_tools import __version__, cli, d110, finder, inspect, reports, rhythm, sound
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
    def test_experimental_d110_converter_writes_common_blocks_and_report(self) -> None:
        tones = complete_image(64 * 256)
        timbres = complete_image(128 * 8)
        rhythm_setup = complete_image(85 * 4)
        tones.data[:10] = b"KICK TONE "
        timbres.data[:8] = bytes((2, 0, 24, 50, 2, 0, 1, 0))
        rhythm_setup.data[:8] = bytes((0, 92, 5, 1, 127, 0, 7, 0))
        messages = [
            *make_messages(0x08, tones, 0x10),
            *make_messages(0x05, timbres, 0x10),
            *make_messages(0x09, rhythm_setup, 0x10),
        ]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "complete.mid"
            destination = Path(directory) / "d110.syx"
            markdown = Path(directory) / "d110.md"
            midi_from_messages(messages).save(source)
            output = d110.convert(source, destination, device_id=0x10, force=False, report_path=markdown)
            raw = destination.read_bytes()
            report = markdown.read_text()
            json_report = d110.report(source, output_name=destination.name, output_messages=70, format="json")
            csv_report = d110.report(source, output_name=destination.name, output_messages=70, format="csv")
            html_report = d110.report(source, output_name=destination.name, output_messages=70, format="html")
        self.assertIn("Created experimental D-110 SysEx", output)
        self.assertNotIn("Rhythm-key comparison", output)
        self.assertIn("D-20 reverb omitted", report)
        self.assertIn("KICK TONE", report)
        self.assertIn("03 01 10", report)
        self.assertIn("## Transferred Tones", report)
        self.assertIn("## Transferred Timbres", report)
        self.assertIn("| A-11 | i01 | KICK TONE", report)
        self.assertIn("OFF → MIX", report)
        self.assertIn("### Tones i01 to i32", report)
        self.assertIn("### Tones i33 to i64", report)
        self.assertIn("| i01 | KICK TONE |", report)
        self.assertIn("| Tone | Tone name |", report)
        self.assertNotIn("Shared name", report)
        self.assertNotIn("reserved tail", report)
        self.assertNotIn("D-20 tone | D-110 tone", report)
        self.assertIn('"experimental": true', json_report)
        self.assertIn('"tones": [', json_report)
        self.assertIn('"timbres": [', json_report)
        self.assertTrue(csv_report.startswith("section,target,note,tone,tone_name"))
        self.assertIn("timbre,A-11,,i01,KICK TONE", csv_report)
        self.assertTrue(html_report.startswith("<!doctype html>"))
        self.assertIn("<table>", html_report)
        self.assertIn('class="timbres"', html_report)
        self.assertIn('class="tones"', html_report)
        self.assertIn("Tones i01 to i32", html_report)
        self.assertIn("Tones i33 to i64", html_report)
        self.assertIn("Timbres A (A-11 to A-88)", html_report)
        self.assertIn("Timbres B (B-11 to B-88)", html_report)
        self.assertIn("D-20 reverb omitted", html_report)
        self.assertIn("KICK TONE", html_report)
        frames = [frame for frame in raw.split(b"\xf0") if frame]
        self.assertEqual(len(frames), 70)  # 64 Tone + 4 Timbre + 2 Rhythm messages.
        rhythm_frames = [frame for frame in frames if frame[4:7] in (bytes((3, 1, 16)), bytes((3, 3, 16)))]
        self.assertEqual(len(rhythm_frames), 2)
        self.assertEqual(rhythm_frames[0][7:11], bytes((0, 92, 5, 0)))

    def test_experimental_d110_cli_keeps_report_table_out_of_console_when_saved(self) -> None:
        tones = complete_image(64 * 256)
        timbres = complete_image(128 * 8)
        rhythm_setup = complete_image(85 * 4)
        messages = [*make_messages(0x08, tones, 0x10), *make_messages(0x05, timbres, 0x10), *make_messages(0x09, rhythm_setup, 0x10)]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "complete.mid"
            destination = Path(directory) / "d110.syx"
            report = Path(directory) / "d110.html"
            midi_from_messages(messages).save(source)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(["d110", str(source), str(destination), "--report", str(report), "--report-format", "html"]), 0)
        self.assertIn("Created experimental D-110 SysEx", output.getvalue())
        self.assertIn("Validation report:", output.getvalue())
        self.assertNotIn("Rhythm-key comparison", output.getvalue())

    def test_experimental_d110_converter_requires_complete_common_data(self) -> None:
        tones = complete_image(64 * 256)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "partial.mid"
            destination = Path(directory) / "d110.syx"
            midi_from_messages(make_messages(0x08, tones, 0x10)).save(source)
            with self.assertRaisesRegex(D20Error, "Timbre memory is incomplete"):
                d110.convert(source, destination, device_id=0x10, force=False)

    def test_experimental_d110_validator_rejects_bad_memory_map_and_values(self) -> None:
        tones = complete_image(64 * 256)
        timbres = complete_image(128 * 8)
        rhythm_setup = complete_image(85 * 4)
        messages = [
            *make_messages(0x08, tones, 0x10),
            *make_messages(0x05, timbres, 0x10),
        ]
        # Use the documented D-110 Rhythm Setup base address, not D-20 area 09.
        import mido

        payload = rhythm_setup.data
        data = [0x41, 0x10, 0x16, 0x12, 0x03, 0x01, 0x10, *payload[:256]]
        messages.append(mido.Message("sysex", data=[*data, roland_checksum(data[4:])]))
        data = [0x41, 0x10, 0x16, 0x12, 0x03, 0x03, 0x10, *payload[256:]]
        messages.append(mido.Message("sysex", data=[*data, roland_checksum(data[4:])]))
        d110.validate_messages(messages)
        bad_map = list(messages)
        bad_map[-1] = mido.Message("sysex", data=[0x41, 0x10, 0x16, 0x12, 0x03, 0x03, 0x11, *payload[256:], roland_checksum((0x03, 0x03, 0x11, *payload[256:]))])
        with self.assertRaisesRegex(D20Error, "address map"):
            d110.validate_messages(bad_map)
        bad_rhythm = bytearray(payload)
        bad_rhythm[1] = 101
        data = [0x41, 0x10, 0x16, 0x12, 0x03, 0x01, 0x10, *bad_rhythm[:256]]
        bad_values = [*messages[:-2], mido.Message("sysex", data=[*data, roland_checksum(data[4:])]), messages[-1]]
        with self.assertRaisesRegex(D20Error, "output level"):
            d110.validate_messages(bad_values)
    def test_nested_report_commands_validate_and_decode_complete_records(self) -> None:
        system = complete_image(50)
        patches = complete_image(128 * 38)
        timbres = complete_image(128 * 8)
        tones = complete_image(64 * 256)
        rhythm_setup = complete_image(85 * 4)
        rhythm_pattern = complete_image(16_384)
        rhythm_track = complete_image(2_432)
        sequencer_header = complete_image(502)
        messages = [
            *make_messages(0x10, system, 0x10), *make_messages(0x07, patches, 0x10),
            *make_messages(0x05, timbres, 0x10), *make_messages(0x08, tones, 0x10),
            *make_messages(0x09, rhythm_setup, 0x10), *make_messages(0x0A, rhythm_pattern, 0x10),
            *make_messages(0x0B, rhythm_track, 0x10), *make_messages(0x0C, sequencer_header, 0x10),
        ]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reports.mid"
            midi_from_messages(messages).save(source)
            cases = (
                (["report", "system", str(source)], "Global System"),
                (["report", "patch", str(source), "--patch", "1"], "Patch 1:"),
                (["report", "timbre", str(source), "--timbre", "A-11"], "Timbre A-11"),
                (["report", "tone", str(source), "--tone", "i01"], "Internal/user Tone i01:"),
                (["report", "rhythm", str(source)], "Rhythm Setup"),
            )
            for command, expected in cases:
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(cli.main(command), 0)
                self.assertTrue(output.getvalue().startswith("\n"))
                self.assertTrue(output.getvalue().endswith("\n\n"))
                self.assertIn(expected, output.getvalue())
            inspection = io.StringIO()
            with redirect_stdout(inspection):
                self.assertEqual(cli.main(["inspect", str(source)]), 0)
            self.assertTrue(inspection.getvalue().endswith("\n\n"))
            self.assertIn("This is an ALL (MIDI DUMP) file.", inspection.getvalue())
            rhythm_output = reports.rhythm(source)
            self.assertIn("i01 User Tone", rhythm_output)
            self.assertNotIn("i01 (User Tone)", rhythm_output)
            errors = io.StringIO()
            with redirect_stderr(errors):
                self.assertEqual(cli.main(["report", "patch", str(source), "--patch", "129"]), 2)
            self.assertTrue(errors.getvalue().startswith("\n"))
            self.assertTrue(errors.getvalue().endswith("\n\n"))

    def test_internal_tone_identifier_requires_i_prefix_and_two_digits(self) -> None:
        self.assertEqual(cli.parse_internal_tone("i01"), 1)
        self.assertEqual(cli.parse_internal_tone("I64"), 64)
        for invalid in ("1", "i1", "i00", "i65", "a01"):
            with self.assertRaises(Exception):
                cli.parse_internal_tone(invalid)

    def test_tone_name_list_uses_internal_identifiers(self) -> None:
        tones = complete_image(64 * 256)
        tones.data[:10] = b"FIRST TONE"
        tones.data[256:266] = b"SECOND TNE"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "tones.mid"
            midi_from_messages(make_messages(0x08, tones, 0x10)).save(source)
            output = reports.tone(source)
        self.assertIn("i01  FIRST TONE", output)
        self.assertIn("i02  SECOND TNE", output)
        self.assertNotIn("1    FIRST TONE", output)

    def test_find_recursively_matches_tone_timbre_and_patch_names(self) -> None:
        tones = complete_image(64 * 256)
        timbres = complete_image(128 * 8)
        patches = complete_image(128 * 38)
        tones.data[16 * 256 : 16 * 256 + 10] = b"StarSynth "
        timbres.data[:8] = bytes((2, 16, 24, 50, 2, 0, 1, 0))
        patches.data[2:6] = bytes((2, 16, 2, 16))
        patches.data[21:37] = b"Night Pad       "
        messages = [
            *make_messages(0x05, timbres, 0x10),
            *make_messages(0x07, patches, 0x10),
            *make_messages(0x08, tones, 0x10),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "nested" / "library.mid"
            native_source = root / "native.333"
            source.parent.mkdir()
            midi_from_messages(messages).save(source)
            native_source.write_bytes(sound.encode("NATIVE", scan_messages(messages)))
            output = finder.search(root, "starsynth", match_type="all", exact=False)
            exact = finder.search(root, "StarSynth", match_type="tone", exact=True)
            no_match = finder.search(root, "star", match_type="tone", exact=True)
            json_output = finder.search(root, "StarSynth", match_type="tone", exact=True, output_format="json")
            csv_output = finder.search(root, "StarSynth", match_type="tone", exact=True, output_format="csv")
        self.assertIn(str(source.resolve()), output)
        self.assertIn(str(native_source.resolve()), output)
        self.assertIn("Tone i17: StarSynth", output)
        self.assertIn("Timbre A-11: i17 StarSynth", output)
        self.assertIn("Patch 1: Night Pad — i17 StarSynth / i17 StarSynth", output)
        self.assertIn("found 6 match(es) in 2 file(s)", output)
        self.assertIn("Tone i17: StarSynth", exact)
        self.assertIn("found 0 match(es) in 0 file(s)", no_match)
        structured = json.loads(json_output)
        self.assertEqual(structured["files_scanned"], 2)
        self.assertEqual(structured["files_with_matches"], 2)
        self.assertEqual(structured["matches"][0]["identifier"], "i17")
        self.assertTrue(csv_output.startswith("file,kind,identifier,detail\r\n"))
        self.assertEqual(len(csv_output.splitlines()), 3)

    def test_pcm_wave_names_use_one_based_reference_numbers(self) -> None:
        partial = bytearray(58)
        partial[4], partial[5] = 0, 24  # Stored 0-based index 24 is manual Bank 1, Wave 25.
        self.assertIn("Tambourine (PCM Bank 1, Wave 25)", reports._partial(bytes(partial), 0, "P")[1])
        partial[4], partial[5] = 0, 61
        self.assertIn("Acoustic Bass (PCM Bank 1, Wave 62)", reports._partial(bytes(partial), 0, "P")[1])
        partial[4], partial[5] = 1, 64
        self.assertIn("Loop-35 (PCM Bank 2, Wave 65)", reports._partial(bytes(partial), 0, "P")[1])
        partial[4], partial[5] = 2, 64  # Another selector value used by the factory dump.
        self.assertIn("Loop-35 (PCM Bank 2, Wave 65)", reports._partial(bytes(partial), 0, "P")[1])
        partial[4], partial[5] = 3, 126  # Factory dump: any non-zero selector maps to manual Bank 2.
        self.assertIn("Jam-33 (Loop) (PCM Bank 2, Wave 127)", reports._partial(bytes(partial), 0, "P")[1])

    def test_tone_and_timbre_manual_value_offsets(self) -> None:
        self.assertEqual(reports._bias_point(0), "<A1")
        self.assertEqual(reports._bias_point(63), "<C7")
        self.assertEqual(reports._bias_point(64), ">A1")
        self.assertEqual(reports._bias_point(127), ">C7")

        partial = bytearray(58)
        partial[0], partial[1], partial[6], partial[7] = 96, 100, 100, 14
        partial[8], partial[9], partial[20], partial[21], partial[22] = 10, 3, 100, 100, 100
        partial[23], partial[24], partial[26], partial[27] = 100, 30, 127, 14
        partial[15:20] = bytes((0, 25, 50, 75, 100))
        partial[28:41] = bytes((100, 100, 4, 4, 0, 25, 50, 75, 100, 0, 25, 50, 100))
        partial[41], partial[42], partial[43], partial[44], partial[45], partial[46] = 100, 0, 64, 12, 63, 0
        partial[47:58] = bytes((4, 4, 0, 25, 50, 75, 100, 0, 25, 50, 100))
        output = "\n".join(reports._partial(bytes(partial), 0, "S"))
        self.assertIn("pitch C9, fine +50", output)
        self.assertIn("pulse width 100; pulse-width velocity +7", output)
        self.assertIn("LFO: rate 100, depth 100, modulation 100", output)
        self.assertIn("Pitch envelope: depth 10, velocity 3", output)
        self.assertIn("levels L0/L1/L2/Sustain/End: [-50, -25, +0, +25, +50]", output)
        self.assertIn("TVF: cutoff 100, resonance 30", output)
        self.assertIn("TVF envelope: depth 100, velocity 100, depth key follow 4, time key follow 4", output)
        self.assertIn("levels L1/L2/L3/Sustain: [-50, -25, +0, +50]", output)
        self.assertIn("bias >C7 / +7", output)
        self.assertIn("bias 1 >A1 / -12; bias 2 <C7 / +0", output)
        self.assertIn("TVA envelope: time-1 velocity follow 4, time key follow 4", output)
        self.assertIn("levels L1/L2/L3/Sustain: [0, 25, 50, 100]", output)

        self.assertEqual(reports._signed(0, 24, 0, 48), "-24")
        self.assertEqual(reports._signed(48, 24, 0, 48), "+24")
        self.assertEqual(reports._signed(0, 50, 0, 100), "-50")
        self.assertEqual(reports._signed(100, 50, 0, 100), "+50")
        self.assertEqual(reports._negative(0, 12), "+0")
        self.assertEqual(reports._negative(12, 12), "-12")
        self.assertEqual(reports._one_based(0, 3), "1")
        self.assertEqual(reports._one_based(3, 3), "4")

        timbres = complete_image(128 * 8)
        timbres.data[:8] = bytes((2, 0, 0, 100, 24, 3, 1, 0))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "timbre-ranges.mid"
            midi_from_messages(make_messages(0x05, timbres, 0x10)).save(source)
            output = reports.timbre(source, "A-11")
            bank_b_output = reports.timbre(source, "B-11")
            with self.assertRaisesRegex(D20Error, "A-11 through A-88 or B-11 through B-88"):
                reports.timbre(source, "I-11")
        self.assertIn("Timbre A-11", output)
        self.assertIn("Tone: i01 User Tone", output)
        self.assertNotIn("Tone: i01 (User Tone)", output)
        self.assertIn("Key shift: -24; fine tune: +50", output)
        self.assertIn("Bender range: 24; assign mode: 4; reverb: ON", output)
        self.assertIn("Timbre B-11", bank_b_output)

    def test_patch_and_timbre_show_assigned_user_tones(self) -> None:
        timbres = complete_image(128 * 8)
        patches = complete_image(128 * 38)
        tones = complete_image(64 * 256)
        timbres.data[:8] = bytes((2, 0, 24, 50, 2, 0, 1, 0))
        patches.data[2:6] = bytes((2, 0, 2, 1))
        tones.data[:10] = b"TONE ONE  "
        tones.data[256:266] = b"TONE TWO  "
        messages = [*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10)]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "showtones.mid"
            midi_from_messages(messages).save(source)
            timbre_output = reports.timbre(source, "A-11", showtones=True)
            patch_output = reports.patch(source, 1, showtones=True)
            command_output = io.StringIO()
            with redirect_stdout(command_output):
                self.assertEqual(cli.main(["report", "patch", str(source), "--patch", "1", "--showtones"]), 0)
            with self.assertRaisesRegex(D20Error, "requires --timbre"):
                reports.timbre(source, showtones=True)
            with self.assertRaisesRegex(D20Error, "requires --patch"):
                reports.patch(source, showtones=True)
        self.assertIn("Underlying Tone configuration", timbre_output)
        self.assertIn("Internal/user Tone i01: TONE ONE", timbre_output)
        self.assertIn("Lower Tone: i01 TONE ONE", patch_output)
        self.assertIn("Upper Tone: i02 TONE TWO", patch_output)
        self.assertIn("Internal/user Tone i02: TONE TWO", patch_output)
        self.assertIn("Underlying Tone configuration", command_output.getvalue())

    def test_showtones_explains_fixed_and_missing_tone_data(self) -> None:
        timbres = complete_image(128 * 8)
        timbres.data[:2] = bytes((0, 0))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixed-tone.mid"
            midi_from_messages(make_messages(0x05, timbres, 0x10)).save(source)
            fixed_output = reports.timbre(source, "A-11", showtones=True)
            timbres.data[:2] = bytes((2, 0))
            source = Path(directory) / "missing-tone.mid"
            midi_from_messages(make_messages(0x05, timbres, 0x10)).save(source)
            missing_output = reports.timbre(source, "A-11", showtones=True)
        self.assertIn("fixed Preset A ROM Tone", fixed_output)
        self.assertIn("Tone configuration unavailable: No Tone data", missing_output)

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
        tones.data[:10] = b"NATIVE TNE"
        timbres.data[:2] = bytes((2, 0))
        messages = [*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10)]
        raw = sound.encode("PUBLICTEST", scan_messages(messages))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.333"
            midi = root / "sound.mid"
            syx = root / "sound.syx"
            rebuilt = root / "publictest.333"
            source.write_bytes(raw)
            self.assertIn("Tone: 64 message(s)", inspect.report(source))
            self.assertTrue(inspect.report(source).endswith("This is a SOUND file."))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["report", "tone", str(source), "--tone", "i01"]), 0)
                self.assertEqual(cli.main(["report", "timbre", str(source), "--timbre", "A-11"]), 0)
                self.assertEqual(cli.main(["report", "timbre", str(source), "--timbre", "A-11", "--showtones"]), 0)
            self.assertEqual(cli.main(["sound", str(source), str(midi)]), 0)
            self.assertEqual(cli.main(["sound", str(source), str(syx)]), 0)
            self.assertIn("Tone: 64 message(s)", inspect.report(syx))
            self.assertEqual(cli.main(["sound", str(midi), str(rebuilt)]), 0)
            self.assertEqual(sound.decode(rebuilt)[0], "PUBLICTEST")
            self.assertEqual(rebuilt.read_bytes(), raw)

    def test_inspect_identifies_native_song_and_all_from_contents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            song = bytearray(inspect.SONG_FILE_SIZE)
            song[2] = 0x03
            song[6:16] = b"UNIT SONG "
            song[inspect.SONG_EMBEDDED_RHYTHM_OFFSET : inspect.SONG_EMBEDDED_RHYTHM_OFFSET + 3] = b"\x03\x11\x00"
            song_path = root / "not-a-song.bin"
            song_path.write_bytes(song)
            self.assertEqual(inspect.native_type(song_path), ("SONG", "UNIT SONG"))
            song_output = inspect.report(song_path)
            self.assertIn("Valid messages: 78", song_output)
            self.assertIn("0AH  Rhythm Pattern: 64 message(s)", song_output)
            self.assertIn("Song event stream: 14,848 bytes", song_output)
            self.assertIn("saved tempo not decoded", song_output)
            self.assertTrue(song_output.endswith("This is a SONG file."))
            song_report = root / "song-report.html"
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(["inspect", str(song_path), "--report", str(song_report), "--report-format", "html"]), 0)
            rendered_song = song_report.read_text()
            self.assertIn("Native Song data", rendered_song)
            self.assertIn("Tempo / track count", rendered_song)
            self.assertIn("Rhythm Setup", rendered_song)
            self.assertIn("Undecoded data", rendered_song)
            self.assertIn("Inspection report:", output.getvalue())
            json_report, csv_report = root / "song-report.json", root / "song-report.csv"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["inspect", str(song_path), "--report", str(json_report), "--report-format", "json"]), 0)
                self.assertEqual(cli.main(["inspect", str(song_path), "--report", str(csv_report), "--report-format", "csv"]), 0)
            self.assertEqual(json.loads(json_report.read_text())["inspection_type"], "SONG")
            self.assertTrue(csv_report.read_text().startswith("section,area,meaning"))

            all_file = bytearray(inspect.ALL_FILE_SIZE)
            all_file[2], all_file[0x10] = 0x03, 0x01
            all_file[6:16] = b"UNIT ALL  "
            all_file[inspect.ALL_SOUND_OFFSET : inspect.ALL_SOUND_OFFSET + 10] = b"ALL FINDER"
            all_path = root / "not-an-all.111"
            all_path.write_bytes(all_file)
            self.assertEqual(inspect.native_type(all_path), ("ALL", "UNIT ALL"))
            all_output = inspect.report(all_path)
            self.assertIn("Valid messages: 165", all_output)
            self.assertIn("08H  Tone: 64 message(s)", all_output)
            self.assertIn("Song event stream: 14,848 bytes", all_output)
            self.assertNotIn("10H  System", all_output)
            self.assertTrue(all_output.endswith("This is an ALL (DISK) file."))
            all_report = inspect.detailed_report(all_path)
            self.assertIn("## Native Song data", all_report)
            self.assertIn("embedded Song region", all_report)
            finder_output = finder.search(root, "all finder", match_type="tone", exact=True)
            self.assertIn(str(all_path.resolve()), finder_output)
            self.assertIn("Tone i01: ALL FINDER", finder_output)

    def test_structured_inspect_report_identifies_combined_sound_and_rhythm_dump(self) -> None:
        tones = complete_image(64 * 256)
        timbres = complete_image(128 * 8)
        patches = complete_image(128 * 38)
        setup = complete_image(85 * 4)
        pattern = complete_image(16_384)
        track = complete_image(2_432)
        sequencer = complete_image(502)
        tones.data[:10] = b"MIXED TONE"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "mixed.mid"
            midi_from_messages([*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10), *make_messages(0x09, setup, 0x10), *make_messages(0x0A, pattern, 0x10), *make_messages(0x0B, track, 0x10), *make_messages(0x0C, sequencer, 0x10)]).save(source)
            markdown = inspect.detailed_report(source)
            html_report = inspect.detailed_report(source, format="html")
        self.assertIn("Inspection type: **MIXED**", markdown)
        self.assertIn("Both Sound and Rhythm memory areas are present.", markdown)
        self.assertIn("## Internal/user Tones (08H): i01 to i32", markdown)
        self.assertIn("## Timbres A (A-11 to A-88)", markdown)
        self.assertIn("## Patches 65 to 128", markdown)
        self.assertIn("| Note | Tone | Tone name | Level | Pan | Reverb |", markdown)
        self.assertNotIn("Shared name", markdown)
        self.assertIn('class="paired"', html_report)
        self.assertIn("MIXED", html_report)

    def test_native_validation_and_safe_conversion_failures(self) -> None:
        tones = complete_image(sound.TONE_COUNT * sound.TONE_SYSEX_SIZE)
        timbres = complete_image(sound.TIMBRE_COUNT * sound.TIMBRE_SIZE)
        patches = complete_image(sound.PATCH_COUNT * sound.PATCH_SIZE)
        sound_raw = sound.encode("SAFE", scan_messages([*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10)]))
        setup = complete_image(rhythm.SETUP_SIZE)
        pattern = complete_image(rhythm.PATTERN_SIZE)
        track = complete_image(rhythm.TRACK_SIZE)
        sequencer = complete_image(rhythm.SEQUENCER_SIZE)
        rhythm_raw = rhythm.encode("SAFE", scan_messages([*make_messages(0x09, setup, 0x10), *make_messages(0x0A, pattern, 0x10), *make_messages(0x0B, track, 0x10), *make_messages(0x0C, sequencer, 0x10)]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.333"
            source.write_bytes(sound_raw)
            bad_header = root / "bad-header.333"
            bad_header.write_bytes(b"\x00" + sound_raw[1:])
            bad_mirror = bytearray(sound_raw)
            bad_mirror[sound.PATCH_MIRROR_OFFSET] ^= 1
            bad_mirror_path = root / "bad-mirror.333"
            bad_mirror_path.write_bytes(bad_mirror)
            self.assertRaises(D20Error, sound.decode, bad_header)
            self.assertRaises(D20Error, sound.decode, bad_mirror_path)
            destination = root / "existing.mid"
            destination.write_bytes(b"existing")
            with self.assertRaisesRegex(D20Error, "already exists"):
                sound.convert(source, destination, device_id=0x10, force=False)
            self.assertIn("Converted", sound.convert(source, destination, device_id=0x10, force=True))
            with self.assertRaisesRegex(D20Error, "extensions"):
                sound.convert(source, root / "wrong.txt", device_id=0x10, force=False)

            bad_rhythm_mirror = bytearray(rhythm_raw)
            bad_rhythm_mirror[rhythm.MIRROR_OFFSET] ^= 1
            bad_rhythm_path = root / "bad-mirror.444"
            bad_rhythm_path.write_bytes(bad_rhythm_mirror)
            with self.assertRaisesRegex(D20Error, "mirror"):
                rhythm.decode(bad_rhythm_path)

        tones.data[246] = 1
        lossy_messages = scan_messages([*make_messages(0x05, timbres, 0x10), *make_messages(0x07, patches, 0x10), *make_messages(0x08, tones, 0x10)])
        with self.assertRaisesRegex(D20Error, "cannot represent"):
            sound.encode("LOSSY", lossy_messages)

    def test_malformed_dt1_is_rejected(self) -> None:
        address, payload = (0x08, 0x00, 0x00), (0x01,)
        bad_checksum = (roland_checksum((*address, *payload)) + 1) & 0x7F
        message = mido.Message("sysex", data=(0x41, 0x10, 0x16, 0x12, *address, *payload, bad_checksum))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.mid"
            midi_from_messages([message]).save(source)
            with self.assertRaisesRegex(D20Error, "malformed"):
                inspect.report(source)
            truncated = Path(directory) / "truncated.syx"
            truncated.write_bytes(b"\xF0\x41\x10\x16\x12")
            with self.assertRaisesRegex(D20Error, "Unterminated"):
                inspect.report(truncated)
            finder_output = finder.search(Path(directory), "anything", match_type="all", exact=False)
        self.assertIn("Skipped 2 unsupported or incomplete D-20 file(s).", finder_output)
        with self.assertRaisesRegex(D20Error, "Search directory does not exist"):
            finder.search(Path("/path/that/does/not/exist"), "anything", match_type="all", exact=False)

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
            rebuilt = root / "rhytest.444"
            source.write_bytes(raw)
            self.assertIn("Rhythm Pattern: 64 message(s)", inspect.report(source))
            self.assertTrue(inspect.report(source).endswith("This is a RHYTHM file."))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["report", "rhythm", str(source)]), 0)
            self.assertEqual(cli.main(["rhythm", str(source), str(midi)]), 0)
            self.assertEqual(cli.main(["rhythm", str(midi), str(rebuilt)]), 0)
            self.assertEqual(rhythm.decode(rebuilt)[0], "RHYTEST")
            self.assertEqual(rebuilt.read_bytes(), raw)

    def test_invalid_and_incomplete_beta_commands_fail_safely(self) -> None:
        errors = io.StringIO()
        with redirect_stderr(errors):
            for command in ("song", "all"):
                with self.assertRaises(SystemExit) as exited:
                    cli.main([command])
                self.assertEqual(exited.exception.code, 2)
        self.assertTrue(errors.getvalue().startswith("\n"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-a-midi.mid"
            path.write_bytes(b"not MIDI")
            errors = io.StringIO()
            with redirect_stderr(errors):
                self.assertEqual(cli.main(["inspect", str(path)]), 2)
            self.assertTrue(errors.getvalue().startswith("\n"))

    def test_help_output_starts_with_a_blank_line(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as exited:
            cli.main(["--help"])
        self.assertEqual(exited.exception.code, 0)
        self.assertTrue(output.getvalue().startswith("\n"))
        self.assertTrue(output.getvalue().endswith("\n\n"))

    def test_version_and_doctor_are_available_for_support(self) -> None:
        version = io.StringIO()
        with redirect_stdout(version), self.assertRaises(SystemExit) as exited:
            cli.main(["--version"])
        self.assertEqual(exited.exception.code, 0)
        self.assertIn("d20-tools 0.2.0", version.getvalue())
        doctor_output = io.StringIO()
        with redirect_stdout(doctor_output):
            self.assertEqual(cli.main(["doctor"]), 0)
        self.assertIn("D-20 Tools doctor", doctor_output.getvalue())
        self.assertIn("Version: 0.2.0", doctor_output.getvalue())
        self.assertIn("experimental: d110", doctor_output.getvalue())
        self.assertIn("BETA note export: song, all", doctor_output.getvalue())
        self.assertIn("Live MIDI input/output: not included", doctor_output.getvalue())

    def test_version_is_sourced_from_package_metadata(self) -> None:
        self.assertEqual(__version__, version("roland-d20-tools"))

    def test_converter_help_has_no_filename_override(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as exited:
            cli.main(["sound", "--help"])
        self.assertEqual(exited.exception.code, 0)
        self.assertNotIn("--name", output.getvalue())

    def test_every_command_help_includes_an_example(self) -> None:
        commands = (
            (),
            ("sound",),
            ("rhythm",),
            ("inspect",),
            ("find",),
            ("doctor",),
            ("report",),
            ("report", "system"),
            ("report", "patch"),
            ("report", "timbre"),
            ("report", "tone"),
            ("report", "rhythm"),
            ("song",),
            ("all",),
        )
        for command in commands:
            with self.subTest(command=command):
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as exited:
                    cli.main([*command, "--help"])
                self.assertEqual(exited.exception.code, 0)
                self.assertIn("Examples:", output.getvalue())
                self.assertIn("d20-tools", output.getvalue())
                self.assertTrue(output.getvalue().endswith("\n\n"))


class LocalRegressionTests(unittest.TestCase):
    """Run only when private local fixtures are explicitly supplied."""

    @property
    def demo_dump(self) -> Path:
        return Path(os.environ.get("D20_DEMO_DUMP_MID", ""))

    @property
    def testsnd(self) -> Path:
        return Path(os.environ.get("D20_TESTSND_333", ""))

    @property
    def testrhy(self) -> Path:
        return Path(os.environ.get("D20_TESTRHY_444", ""))

    @property
    def factory_dump(self) -> Path:
        return Path(os.environ.get("D20_FACTORY_MID", ""))

    @unittest.skipUnless(os.environ.get("D20_DEMO_DUMP_MID"), "Set D20_DEMO_DUMP_MID to run this private regression test.")
    def test_demo_dump_midi_inspection_and_native_conversions(self) -> None:
        self.assertTrue(self.demo_dump.is_file(), self.demo_dump)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sound_file, rhythm_file = root / "demodump.333", root / "demodump.444"
            sound_midi, rhythm_midi = root / "demodump-sound.mid", root / "demodump-rhythm.mid"
            self.assertIn("System: 1 message(s)", inspect.report(self.demo_dump))
            self.assertEqual(cli.main(["sound", str(self.demo_dump), str(sound_file)]), 0)
            self.assertEqual(cli.main(["sound", str(sound_file), str(sound_midi)]), 0)
            self.assertEqual(cli.main(["rhythm", str(self.demo_dump), str(rhythm_file)]), 0)
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
            self.assertEqual(cli.main(["sound", str(midi), str(rebuilt)]), 0)
            self.assertEqual(rebuilt.read_bytes(), self.testsnd.read_bytes())

    @unittest.skipUnless(os.environ.get("D20_TESTRHY_444"), "Set D20_TESTRHY_444 to run this private regression test.")
    def test_testrhy_444_round_trip_is_byte_identical(self) -> None:
        self.assertTrue(self.testrhy.is_file(), self.testrhy)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            midi, rebuilt = root / "testrhy.mid", root / "testrhy.444"
            self.assertIn("Rhythm Pattern: 64 message(s)", inspect.report(self.testrhy))
            self.assertIn("D-20 Rhythm Setup", reports.rhythm(self.testrhy))
            self.assertEqual(cli.main(["rhythm", str(self.testrhy), str(midi)]), 0)
            self.assertEqual(cli.main(["rhythm", str(midi), str(rebuilt)]), 0)
            self.assertEqual(rebuilt.read_bytes(), self.testrhy.read_bytes())

    @unittest.skipUnless(os.environ.get("D20_FACTORY_MID"), "Set D20_FACTORY_MID to validate the private factory dump.")
    def test_factory_dump_decodes_known_tone_values(self) -> None:
        self.assertTrue(self.factory_dump.is_file(), self.factory_dump)
        tone_output = reports.tone(self.factory_dump, 1)
        self.assertIn("Internal/user Tone i01: TouchPiano", tone_output)
        self.assertIn("Acoustic Piano High (PCM Bank 1, Wave 33)", tone_output)
        self.assertIn("Acoustic Piano Low (PCM Bank 1, Wave 34)", tone_output)
        self.assertIn("bias 1 >C4 / -12; bias 2 <G4 / -4", tone_output)
        self.assertIn("TVF envelope:", tone_output)
        self.assertIn("TVA envelope:", tone_output)


if __name__ == "__main__":
    unittest.main()
