"""Command line interface for Roland D-20 Tools."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import inspect, reports, rhythm, sound
from .core import D20Error, parse_device_id


def add_converter_arguments(parser: argparse.ArgumentParser, label: str) -> None:
    parser.add_argument("input", type=Path, help=f"source {label} file")
    parser.add_argument("output", type=Path, help=f"destination {label} file")
    parser.add_argument("--name", help="1-10 character D-20 disk name for native output")
    parser.add_argument("--device-id", default="0x10", help="Roland device ID for MIDI/SysEx output (default: 0x10)")
    parser.add_argument("--force", action="store_true", help="replace an existing output")


def parse_internal_tone(value: str) -> int:
    """Parse an internal/user Tone identifier such as ``i01``."""
    normalized = value.strip().lower()
    if len(normalized) != 3 or normalized[0] != "i" or not normalized[1:].isdigit():
        raise argparse.ArgumentTypeError("--tone must be an internal Tone identifier from i01 through i64.")
    number = int(normalized[1:])
    if not 1 <= number <= 64:
        raise argparse.ArgumentTypeError("--tone must be an internal Tone identifier from i01 through i64.")
    return number


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="d20-tools", description="Safe local SysEx inspection and file conversion for Roland D-20 data.")
    commands = result.add_subparsers(dest="command", required=True, title="commands")
    sound_parser = commands.add_parser("sound", help="convert Sound .333 files")
    add_converter_arguments(sound_parser, "Sound (.333), MIDI, or SysEx")
    rhythm_parser = commands.add_parser("rhythm", help="convert Rhythm .444 files")
    add_converter_arguments(rhythm_parser, "Rhythm (.444), MIDI, or SysEx")
    inspect_parser = commands.add_parser("inspect", help="summarize D-20 DT1 SysEx in a MIDI or SysEx file")
    inspect_parser.add_argument("input", type=Path, help="source .mid/.midi or raw .syx D-20 dump")
    report_parser = commands.add_parser("report", help="decode System, Patch, Timbre, Tone, or Rhythm parameters")
    report_commands = report_parser.add_subparsers(dest="report", required=True, title="reports")
    for name, help_text in (
        ("system", "decode 10H global System settings"),
        ("patch", "decode 07H Patch records"),
        ("timbre", "decode 05H Timbre records"),
        ("tone", "decode 08H permanent or 04H temporary Tone records"),
        ("rhythm", "decode 09H Rhythm Setup assignments"),
    ):
        report = report_commands.add_parser(name, help=help_text)
        report.add_argument("input", type=Path, help="source .mid/.midi or raw .syx D-20 dump")
        if name == "patch":
            report.add_argument("--patch", type=int, metavar="1..128", help="show one complete Patch record")
        elif name == "timbre":
            report.add_argument("--timbre", metavar="A-11..A-88 | B-11..B-88", help="show one complete Timbre")
        elif name == "tone":
            report.add_argument("--tone", type=parse_internal_tone, metavar="i01..i64", help="show one complete internal/user Tone record")
    commands.add_parser("song", help="Song .222 conversion (work in progress)")
    commands.add_parser("all", help="All .111 conversion (work in progress)")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"song", "all"}:
            print(f"The D-20 {args.command.title()} converter is a work in progress and is not available in v0.1.", file=sys.stderr)
            return 2
        if args.command == "inspect":
            print(inspect.report(args.input))
            return 0
        if args.command == "report":
            runner = getattr(reports, args.report)
            option = {"patch": "patch", "timbre": "timbre", "tone": "tone"}.get(args.report)
            print(runner(args.input, getattr(args, option)) if option else runner(args.input))
            return 0
        device_id = parse_device_id(args.device_id)
        converter = sound.convert if args.command == "sound" else rhythm.convert
        print(converter(args.input, args.output, name=args.name, device_id=device_id, force=args.force))
        return 0
    except D20Error as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
