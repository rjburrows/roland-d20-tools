"""Command line interface for Roland D-20 Tools."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__, d110, doctor, finder, inspect, reports, rhythm, sound
from .core import D20Error, parse_device_id


class OutputParser(argparse.ArgumentParser):
    """Keep command help and argument errors visually separate from the prompt."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
        super().__init__(*args, **kwargs)

    def _print_message(self, message: str | None, file=None) -> None:
        if message:
            super()._print_message(f"\n{message}\n", file)


def emit(message: str, *, file=None, padded: bool = True) -> None:
    """Print one command result, padding human-readable output."""
    if padded:
        print(file=file)
    print(message, file=file)
    if padded:
        print(file=file)


def add_converter_arguments(parser: argparse.ArgumentParser, label: str) -> None:
    parser.add_argument("input", type=Path, help=f"source {label} file")
    parser.add_argument("output", type=Path, help=f"destination {label} file")
    parser.add_argument("--device-id", default="0x10", help="Roland device ID for MIDI/SysEx output (default: 0x10)")
    parser.add_argument("--force", action="store_true", help="replace an existing output")


def examples(*commands: str) -> str:
    """Format one or more executable command-line examples for argparse help."""
    return "Examples:\n" + "\n".join(f"  {command}" for command in commands)


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
    result = OutputParser(
        prog="d20-tools",
        description="Safe local inspection, reporting, and file conversion for Roland D-20 MIDI, SysEx, and native data. Nothing is uploaded.",
        epilog=examples(
            "d20-tools inspect D20BACKUP.mid",
            "d20-tools report tone D20BACKUP.mid --tone i01",
            "d20-tools sound TESTSND.333 TESTSND.mid",
        ),
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}", help="show the installed version and exit")
    commands = result.add_subparsers(dest="command", required=True, title="commands")
    sound_parser = commands.add_parser(
        "sound",
        help="convert Sound .333 files",
        description="Convert a complete D-20 Sound file (.333) to MIDI or SysEx, or rebuild a .333 from a complete compatible dump.",
        epilog=examples("d20-tools sound TESTSND.333 TESTSND.mid"),
    )
    add_converter_arguments(sound_parser, "Sound (.333), MIDI, or SysEx")
    rhythm_parser = commands.add_parser(
        "rhythm",
        help="convert Rhythm .444 files",
        description="Convert a complete D-20 Rhythm file (.444) to MIDI or SysEx, or rebuild a .444 from a complete compatible dump.",
        epilog=examples("d20-tools rhythm TESTRHY.444 TESTRHY.syx"),
    )
    add_converter_arguments(rhythm_parser, "Rhythm (.444), MIDI, or SysEx")
    d110_parser = commands.add_parser(
        "d110",
        help="EXPERIMENTAL: convert a complete D-20 dump to D-110 SysEx",
        description="EXPERIMENTAL and opt-in: convert common D-20 user Tone, Timbre, and Rhythm Setup data to D-110 raw SysEx. Review the generated validation report before sending it to hardware.",
        epilog=examples("d20-tools d110 D20BACKUP.mid D110-SNDRHY.syx --report D110-SNDRHY.md"),
    )
    d110_parser.add_argument("input", type=Path, help="source complete D-20 MIDI or SysEx dump")
    d110_parser.add_argument("output", type=Path, help="destination D-110 raw SysEx (.syx) file")
    d110_parser.add_argument("--device-id", default="0x10", help="Roland D-110 device ID (default: 0x10)")
    d110_parser.add_argument("--force", action="store_true", help="replace an existing output or report")
    d110_parser.add_argument("--report", type=Path, help="write the full experimental validation report to this file")
    d110_parser.add_argument("--report-format", choices=("markdown", "html", "json", "csv"), default="markdown", help="validation report format (default: markdown)")
    inspect_parser = commands.add_parser(
        "inspect",
        help="identify native files or summarize D-20 SysEx data",
        description="Identify a native D-20 file or validate a D-20 MIDI/SysEx dump, then show complete DT1 messages in each recognised memory area. This command never changes files.",
        epilog=examples("d20-tools inspect D20BACKUP.mid", "d20-tools inspect TESTSONG.222"),
    )
    inspect_parser.add_argument("input", type=Path, help="source MIDI, SysEx, or native D-20 file")
    inspect_parser.add_argument("--report", type=Path, help="write a structured inspection report (Markdown by default)")
    inspect_parser.add_argument("--report-format", choices=("markdown", "html", "json", "csv"), default="markdown", help="structured report format (default: markdown)")
    inspect_parser.add_argument("--force", action="store_true", help="replace an existing inspection report")
    find_parser = commands.add_parser(
        "find",
        help="recursively find named Patches, Timbres, or Tones",
        description="Search supported D-20 MIDI, SysEx, Sound, and All files below a directory for named Patches, Timbres, and Tones. By default, matches are case-insensitive literal substrings.",
        epilog=examples("d20-tools find ~/D20-library \"Star Synth\"", "d20-tools find ~/D20-library StarSynth --type tone --format json"),
    )
    find_parser.add_argument("directory", type=Path, help="folder to search recursively")
    find_parser.add_argument("query", help="Patch, Timbre, or Tone name to find")
    find_parser.add_argument("--type", dest="match_type", choices=("all", "patch", "timbre", "tone"), default="all", help="limit matches to one kind (default: all)")
    find_parser.add_argument("--exact", action="store_true", help="require an exact case-insensitive name match")
    find_parser.add_argument("--format", dest="output_format", choices=("text", "json", "csv"), default="text", help="output format (default: text)")
    commands.add_parser(
        "doctor",
        help="show installed version and supported capabilities",
        description="Show a read-only support summary of the installed D-20 Tools command and its capabilities.",
        epilog=examples("d20-tools doctor"),
    )
    report_parser = commands.add_parser(
        "report",
        help="decode System, Patch, Timbre, Tone, or Rhythm parameters",
        description="Produce read-only, human-readable parameter reports from a D-20 dump or native Sound/Rhythm file.",
        epilog=examples("d20-tools report tone D20BACKUP.mid --tone i01"),
    )
    report_commands = report_parser.add_subparsers(dest="report", required=True, title="reports")
    for name, help_text, example in (
        ("system", "decode 10H global System settings", "d20-tools report system D20BACKUP.mid"),
        ("patch", "list or decode 07H Patch records", "d20-tools report patch TESTSND.333 --patch 1 --showtones"),
        ("timbre", "list or decode 05H Timbre records", "d20-tools report timbre TESTSND.333 --timbre A-11 --showtones"),
        ("tone", "list or decode 08H permanent or 04H temporary Tone records", "d20-tools report tone D20BACKUP.mid --tone i01"),
        ("rhythm", "decode 09H Rhythm Setup assignments", "d20-tools report rhythm TESTRHY.444"),
    ):
        report = report_commands.add_parser(
            name,
            help=help_text,
            description=f"Read-only report: {help_text}.",
            epilog=examples(example),
        )
        report.add_argument("input", type=Path, help="source .333/.444, .mid/.midi, or raw .syx D-20 data")
        if name == "patch":
            report.add_argument("--patch", type=int, metavar="1..128", help="show one complete Patch record (omit to list populated Patches)")
            report.add_argument("--showtones", action="store_true", help="append assigned editable Tone configuration (requires --patch)")
        elif name == "timbre":
            report.add_argument("--timbre", metavar="A-11..A-88 | B-11..B-88", help="show one complete Timbre (omit to list populated Timbres)")
            report.add_argument("--showtones", action="store_true", help="append assigned editable Tone configuration (requires --timbre)")
        elif name == "tone":
            report.add_argument("--tone", type=parse_internal_tone, metavar="i01..i64", help="show one complete internal/user Tone record (omit to list populated Tones)")
    commands.add_parser(
        "song",
        help="Song .222 conversion (work in progress)",
        description="Reserved for D-20 Song (.222) conversion. This command is not available in v0.1.",
        epilog=examples("d20-tools song"),
    )
    commands.add_parser(
        "all",
        help="All .111 conversion (work in progress)",
        description="Reserved for D-20 All (.111) conversion. This command is not available in v0.1.",
        epilog=examples("d20-tools all"),
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"song", "all"}:
            emit(f"The D-20 {args.command.title()} converter is a work in progress and is not available in v0.2.", file=sys.stderr)
            return 2
        if args.command == "inspect":
            if args.report:
                inspect.write_detailed_report(args.input, args.report, format=args.report_format, force=args.force)
                emit(f"Inspection report: {args.report}")
            else:
                emit(inspect.report(args.input))
            return 0
        if args.command == "find":
            emit(
                finder.search(args.directory, args.query, match_type=args.match_type, exact=args.exact, output_format=args.output_format),
                padded=args.output_format == "text",
            )
            return 0
        if args.command == "doctor":
            emit(doctor.report())
            return 0
        if args.command == "report":
            runner = getattr(reports, args.report)
            if args.report == "patch":
                result = runner(args.input, args.patch, showtones=args.showtones)
            elif args.report == "timbre":
                result = runner(args.input, args.timbre, showtones=args.showtones)
            elif args.report == "tone":
                result = runner(args.input, args.tone)
            else:
                result = runner(args.input)
            emit(result)
            return 0
        device_id = parse_device_id(args.device_id)
        if args.command == "d110":
            emit(d110.convert(args.input, args.output, device_id=device_id, force=args.force, report_path=args.report, report_format=args.report_format))
            return 0
        converter = sound.convert if args.command == "sound" else rhythm.convert
        emit(converter(args.input, args.output, device_id=device_id, force=args.force))
        return 0
    except D20Error as exc:
        emit(f"Error: {exc}", file=sys.stderr)
        return 2
