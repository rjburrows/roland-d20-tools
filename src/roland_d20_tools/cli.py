"""Command line interface for Roland D-20 Tools."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import inspect, rhythm, sound
from .core import D20Error, parse_device_id


def add_converter_arguments(parser: argparse.ArgumentParser, label: str) -> None:
    parser.add_argument("input", type=Path, help=f"source {label} file")
    parser.add_argument("output", type=Path, help=f"destination {label} file")
    parser.add_argument("--name", help="1-10 character D-20 disk name for native output")
    parser.add_argument("--device-id", default="0x10", help="Roland device ID for MIDI/SysEx output (default: 0x10)")
    parser.add_argument("--force", action="store_true", help="replace an existing output")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="d20-tools", description="Safe local SysEx inspection and file conversion for Roland D-20 data.")
    commands = result.add_subparsers(dest="command", required=True, title="commands")
    sound_parser = commands.add_parser("sound", help="convert Sound .333 files")
    add_converter_arguments(sound_parser, "Sound (.333), MIDI, or SysEx")
    rhythm_parser = commands.add_parser("rhythm", help="convert Rhythm .444 files")
    add_converter_arguments(rhythm_parser, "Rhythm (.444), MIDI, or SysEx")
    inspect_parser = commands.add_parser("inspect", help="summarize D-20 DT1 SysEx in a MIDI or SysEx file")
    inspect_parser.add_argument("input", type=Path, help="source .mid/.midi or raw .syx D-20 dump")
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
        device_id = parse_device_id(args.device_id)
        converter = sound.convert if args.command == "sound" else rhythm.convert
        print(converter(args.input, args.output, name=args.name, device_id=device_id, force=args.force))
        return 0
    except D20Error as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
