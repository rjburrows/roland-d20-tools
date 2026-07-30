"""Deterministic malformed-input corpus: parsers must fail safely."""

from __future__ import annotations

from pathlib import Path
import random
import tempfile
import unittest

from roland_d20_tools import finder, inspect, rhythm, sound
from roland_d20_tools.core import D20Error


class RobustnessTests(unittest.TestCase):
    def test_deterministic_random_corpus_never_raises_unexpected_errors(self) -> None:
        generator = random.Random(20_260_730)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, suffix in enumerate((".mid", ".syx", ".333", ".444") * 8):
                source = root / f"corrupt-{index:02d}{suffix}"
                source.write_bytes(generator.randbytes(generator.randrange(0, 300)))
                with self.subTest(source=source.name):
                    try:
                        inspect.report(source)
                    except D20Error:
                        pass
                    if suffix == ".333":
                        try:
                            sound.decode(source)
                        except D20Error:
                            pass
                    if suffix == ".444":
                        try:
                            rhythm.decode(source)
                        except D20Error:
                            pass
            result = finder.search(root, "anything", match_type="all", exact=False)
        self.assertIn("Searched 24 supported file(s)", result)
