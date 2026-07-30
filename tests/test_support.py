"""Generated fixtures shared by the public test modules."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mido

from roland_d20_tools.core import MemoryImage


def complete_image(size: int) -> MemoryImage:
    image = MemoryImage.create(size)
    image.write(0, bytes(size), "generated test data")
    return image


def midi_from_messages(messages: list[mido.Message], *, file_type: int = 0) -> mido.MidiFile:
    midi = mido.MidiFile(type=file_type)
    track = mido.MidiTrack()
    track.extend(messages)
    midi.tracks.append(track)
    return midi
