"""End-to-end CLI and machine-readable finder coverage."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import argparse
from contextlib import redirect_stderr, redirect_stdout

from test_support import complete_image, midi_from_messages
from roland_d20_tools import cli, finder
from roland_d20_tools.core import make_messages


class CliAndFinderTests(unittest.TestCase):
    def _library(self, root: Path) -> tuple[Path, Path]:
        tones = complete_image(64 * 256)
        timbres = complete_image(128 * 8)
        patches = complete_image(128 * 38)
        tones.data[:10] = b'PAD, "ONE"'
        timbres.data[:2] = bytes((2, 0))
        patches.data[2:6] = bytes((2, 0, 0, 0))
        patches.data[21:37] = b'PAD, "ONE"     '
        messages = [
            *make_messages(0x05, timbres, 0x10),
            *make_messages(0x07, patches, 0x10),
            *make_messages(0x08, tones, 0x10),
        ]
        first, second = root / "a-library.mid", root / "z-library.mid"
        midi_from_messages(messages).save(second)
        midi_from_messages(messages).save(first)
        return first, second

    def test_cli_json_and_csv_output_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = self._library(root)
            json_output = io.StringIO()
            with redirect_stdout(json_output):
                self.assertEqual(cli.main(["find", str(root), "PAD", "--type", "patch", "--format", "json"]), 0)
            csv_output = io.StringIO()
            with redirect_stdout(csv_output):
                self.assertEqual(cli.main(["find", str(root), "PAD", "--type", "timbre", "--format", "csv"]), 0)
        self.assertFalse(json_output.getvalue().startswith("\n"))
        self.assertFalse(csv_output.getvalue().startswith("\n"))
        payload = json.loads(json_output.getvalue())
        self.assertEqual(payload["files_with_matches"], 2)
        self.assertEqual([item["file"] for item in payload["matches"]], [str(first.resolve()), str(second.resolve())])
        rows = list(csv.DictReader(io.StringIO(csv_output.getvalue())))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["detail"], 'i01 PAD, "ONE"')

    def test_finder_filters_empty_results_and_excluded_file_types(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "song.222").write_bytes(b"not a song")
            (root / "rhythm.444").write_bytes(b"not a rhythm")
            result = finder.search_results(root, "missing", match_type="all", exact=False)
            no_matches = json.loads(finder.search(root, "missing", match_type="all", exact=False, output_format="json"))
        self.assertEqual(result.files_scanned, 0)
        self.assertEqual(result.files_with_matches, 0)
        self.assertEqual(no_matches["matches"], [])

    def test_cli_argument_errors_are_clean_and_tone_parser_is_specific(self) -> None:
        with self.assertRaisesRegex(argparse.ArgumentTypeError, "internal Tone identifier"):
            cli.parse_internal_tone("i1")
        errors = io.StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as exited:
            cli.main(["find", ".", "tone", "--format", "yaml"])
        self.assertEqual(exited.exception.code, 2)
        self.assertTrue(errors.getvalue().startswith("\n"))
        self.assertIn("invalid choice", errors.getvalue())
