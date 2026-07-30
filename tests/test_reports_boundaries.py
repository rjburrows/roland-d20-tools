"""Known-value and boundary coverage for human-readable D-20 reports."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from test_support import complete_image, midi_from_messages
from roland_d20_tools import reports
from roland_d20_tools.core import make_messages


class ReportBoundaryTests(unittest.TestCase):
    def test_all_tone_groups_and_pcm_bank_edges_have_stable_labels(self) -> None:
        names = {0: "USER"}
        self.assertEqual(reports._tone_label(0, 0, names, parenthesize_name=False), "a01 AcouPiano 1")
        self.assertEqual(reports._tone_label(1, 63, names, parenthesize_name=False), "b64 Jungle Tune")
        self.assertEqual(reports._tone_label(2, 0, names, parenthesize_name=False), "i01 USER")
        self.assertEqual(reports._tone_label(3, 63, names, parenthesize_name=False), "r64 OFF")
        self.assertIn("unknown group 4", reports._tone_label(4, 0, names))
        self.assertIn("Bass Drum-1 (PCM Bank 1, Wave 1)", reports._pcm_wave_name(0, 0))
        self.assertIn("Shot-17 (PCM Bank 1, Wave 128)", reports._pcm_wave_name(0, 127))
        self.assertIn("Bass Drum-1 (PCM Bank 2, Wave 1)", reports._pcm_wave_name(1, 0))
        self.assertIn("Jam-34 (Loop) (PCM Bank 2, Wave 128)", reports._pcm_wave_name(3, 127))
        self.assertIn("Unknown waveform", reports._pcm_wave_name(0, 128))

    def test_report_invalid_ranges_remain_visible(self) -> None:
        self.assertIn("Invalid", reports._raw(101, 0, 100))
        self.assertIn("Invalid", reports._signed(101, 50, 0, 100))
        self.assertIn("Invalid", reports._negative(13, 12))
        self.assertIn("Invalid", reports._one_based(4, 3))
        self.assertEqual(reports._bias_point(0), "<A1")
        self.assertEqual(reports._bias_point(127), ">C7")

    def test_system_patch_and_rhythm_reports_decode_selected_boundary_values(self) -> None:
        system = complete_image(50)
        patches = complete_image(128 * 38)
        rhythm_setup = complete_image(85 * 4)
        system.data[0:4] = bytes((64, 8, 127, 0))
        system.data[4], system.data[20], system.data[33], system.data[42] = 32, 15, 100, 0
        patches.data[0:22] = bytes((2, 60, 0, 0, 1, 63, 0, 48, 0, 100, 24, 0, 3, 0, 1, 0, 8, 127, 0, 127, 100, 0))
        patches.data[21:37] = b"BOUNDARY PATCH  "
        rhythm_setup.data[0:4] = bytes((0, 127, 0, 1))
        rhythm_setup.data[4:8] = bytes((127, 0, 7, 0))
        messages = [
            *make_messages(0x10, system, 0x10),
            *make_messages(0x07, patches, 0x10),
            *make_messages(0x09, rhythm_setup, 0x10),
        ]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "boundaries.mid"
            midi_from_messages(messages).save(source)
            system_output, patch_output, rhythm_output = reports.system(source), reports.patch(source, 1), reports.rhythm(source)
        self.assertIn("Master tune: 64", system_output)
        self.assertIn("Global reverb: OFF (time 127, level 0)", system_output)
        self.assertIn("Layout: Split; split: C4", patch_output)
        self.assertIn("Patch 1: BOUNDARY PATCH", patch_output)
        self.assertIn("C1", rhythm_output)
        self.assertNotIn("C#1", rhythm_output)
