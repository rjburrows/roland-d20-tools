"""Boundary, parser, and file-safety coverage for shared D-20 helpers."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mido

from test_support import complete_image
from roland_d20_tools import rhythm, sound
from roland_d20_tools.core import (
    D20Error,
    D20Message,
    MemoryImage,
    assemble,
    assemble_partial,
    atomic_write,
    load_dt1,
    make_messages,
    parse_device_id,
    require_new_output,
    scan_midi,
    scan_syx,
)


class CoreTests(unittest.TestCase):
    def test_memory_image_boundaries_and_partial_assembly(self) -> None:
        image = MemoryImage.create(4, fill=9)
        image.write(1, (4, 5), "test")
        self.assertEqual(bytes(image.data), b"\x09\x04\x05\x09")
        self.assertFalse(image.complete())
        self.assertTrue(image.complete(1, 2))
        with self.assertRaisesRegex(D20Error, "exceeds"):
            image.write(3, (1, 2), "test")
        messages = (
            D20Message(0x10, (0x08, 0, 0), (1, 2)),
            D20Message(0x10, (0x08, 0, 2), (3, 4)),
            D20Message(0x10, (0x07, 0, 0), (9,)),
        )
        partial = assemble_partial(messages, 0x08, 4, "Tone data")
        self.assertTrue(partial.complete())
        self.assertEqual(bytes(partial.data), b"\x01\x02\x03\x04")
        self.assertEqual(bytes(assemble(messages, 0x08, 4, "Tone data").data), b"\x01\x02\x03\x04")
        with self.assertRaisesRegex(D20Error, "incomplete"):
            assemble(messages, 0x08, 5, "Tone data")

    def test_midi_and_syx_parsers_handle_multiple_valid_frames(self) -> None:
        image = complete_image(1)
        first, second = make_messages(0x08, image, 0x10)[0], make_messages(0x07, image, 0x10)[0]
        raw = b"\x00\n" + bytes((0xF0, *first.data, 0xF7)) + b" \t" + bytes((0xF0, 0x7D, 1, 2, 0xF7)) + bytes((0xF0, *second.data, 0xF7))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            syx = root / "mixed.syx"
            syx.write_bytes(raw)
            self.assertEqual([(item.device_id, item.address[0]) for item in scan_syx(syx)], [(0x10, 0x08), (0x10, 0x07)])
            midi = mido.MidiFile(type=1)
            midi.tracks.append(mido.MidiTrack([first]))
            midi.tracks.append(mido.MidiTrack([second]))
            midi_path = root / "TRACKS.MID"
            midi.save(midi_path)
            self.assertEqual(len(scan_midi(midi_path)), 2)
            self.assertEqual(len(load_dt1(midi_path)), 2)

    def test_malformed_syx_is_rejected_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = {
                "empty.syx": b"",
                "junk.syx": b"before\xF0\x7D\xF7",
                "unfinished.syx": b"\xF0\x41\x10\x16\x12",
                "non7bit.syx": b"\xF0\x41\x10\x16\x12\x08\x00\x00\x80\xF7",
            }
            for name, contents in cases.items():
                with self.subTest(name=name):
                    source = root / name
                    source.write_bytes(contents)
                    with self.assertRaises(D20Error):
                        scan_syx(source)

    def test_device_ids_headers_and_output_safety(self) -> None:
        self.assertEqual(parse_device_id("0"), 0)
        self.assertEqual(parse_device_id("0x7f"), 127)
        for value in ("-1", "128", "not-a-number"):
            with self.subTest(value=value), self.assertRaises(D20Error):
                parse_device_id(value)
        for module in (sound, rhythm):
            self.assertEqual(module.header("abcdefghij")[6:16], b"ABCDEFGHIJ")
            for name in ("", "elevenchars", "cafe\N{LATIN SMALL LETTER E WITH ACUTE}"):
                with self.subTest(module=module.__name__, name=name), self.assertRaises(D20Error):
                    module.header(name)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "source.mid", root / "destination.mid"
            source.write_bytes(b"source")
            destination.write_bytes(b"existing")
            with self.assertRaisesRegex(D20Error, "already exists"):
                require_new_output(source, destination, False)
            with self.assertRaisesRegex(D20Error, "must be different"):
                require_new_output(source, source, True)
            nested = root / "new" / "output.syx"
            atomic_write(nested, b"new contents")
            self.assertEqual(nested.read_bytes(), b"new contents")

    def test_atomic_write_cleans_up_after_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "output.syx"
            with patch("roland_d20_tools.core.os.replace", side_effect=OSError("blocked")):
                with self.assertRaises(OSError):
                    atomic_write(destination, b"data")
            self.assertFalse(destination.exists())
            self.assertEqual(list(destination.parent.iterdir()), [])
