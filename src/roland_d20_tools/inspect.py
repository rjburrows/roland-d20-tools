"""Read-only inspection of standard Roland D-20 DT1 SysEx dumps."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .core import D20Error, scan_midi, scan_syx


LABELS = {
    0x04: "Temporary Tone",
    0x05: "Timbre",
    0x07: "Patch",
    0x08: "Tone",
    0x09: "Rhythm Setup",
    0x0A: "Rhythm Pattern",
    0x0B: "Rhythm Track",
    0x0C: "Sequencer Header",
    0x10: "System",
}


def report(path: Path) -> str:
    source = path.expanduser()
    if source.suffix.lower() == ".syx":
        messages = scan_syx(source)
    elif source.suffix.lower() in {".mid", ".midi"}:
        messages = scan_midi(source)
    else:
        raise D20Error("Inspection accepts Standard MIDI (.mid/.midi) or raw SysEx (.syx) files.")
    if not messages:
        raise D20Error("No valid Roland D-20 DT1 messages were found.")
    blocks = Counter(message.address[0] for message in messages)
    lines = [f"D-20 DT1 inspection: {source.name}", f"Valid messages: {len(messages)}"]
    for area, count in sorted(blocks.items()):
        lines.append(f"  {area:02X}H  {LABELS.get(area, 'Unknown')}: {count} message(s)")
    return "\n".join(lines)

