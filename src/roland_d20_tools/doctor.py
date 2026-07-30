"""Read-only environment summary for support and troubleshooting."""

from __future__ import annotations

import platform

from importlib.metadata import version

from . import __version__


def report() -> str:
    """Return a concise summary of the installed command-line environment."""
    return "\n".join((
        "D-20 Tools doctor",
        f"Version: {__version__}",
        f"Python: {platform.python_version()} ({platform.system()} {platform.release()})",
        f"Mido: {version('mido')}",
        "Supported input: .mid, .midi, .syx, .333, .444, .111, .222",
        "Ready commands: inspect, find, report, sound, rhythm",
        "Song and All conversion: work in progress",
        "Live MIDI input/output: not included",
    ))
