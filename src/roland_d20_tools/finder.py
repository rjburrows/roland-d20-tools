"""Recursive search for named D-20 Patches, Timbres, and Tones."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import json
from pathlib import Path

from . import inspect, reports
from .core import D20Error, assemble_partial, load_dt1, printable_text, user_tone_names


SUPPORTED_SUFFIXES = frozenset((".111", ".333", ".mid", ".midi", ".syx"))


@dataclass(frozen=True, slots=True)
class Match:
    """One named D-20 object found in a file."""

    kind: str
    identifier: str
    detail: str

    def format(self) -> str:
        return f"  {self.kind} {self.identifier}: {self.detail}"


@dataclass(frozen=True, slots=True)
class SearchResults:
    """Structured matches and accounting for one recursive search."""

    query: str
    match_type: str
    exact: bool
    files_scanned: int
    files_skipped: int
    matches: tuple[tuple[Path, Match], ...]

    @property
    def files_with_matches(self) -> int:
        return len({path for path, _ in self.matches})

    def text(self) -> str:
        sections: list[str] = []
        for path in dict.fromkeys(path for path, _ in self.matches):
            lines = [str(path)]
            lines.extend(match.format() for match_path, match in self.matches if match_path == path)
            sections.append("\n".join(lines))
        mode = "exact" if self.exact else "case-insensitive substring"
        summary = (
            f"Searched {self.files_scanned} supported file(s) for {self.query!r} ({mode}); "
            f"found {len(self.matches)} match(es) in {self.files_with_matches} file(s)."
        )
        if self.files_skipped:
            summary += f" Skipped {self.files_skipped} unsupported or incomplete D-20 file(s)."
        return "\n\n".join((*sections, summary)) if sections else summary

    def json(self) -> str:
        """Return a stable, machine-readable record of this search."""
        return json.dumps(
            {
                "query": self.query,
                "match_type": self.match_type,
                "exact": self.exact,
                "files_scanned": self.files_scanned,
                "files_skipped": self.files_skipped,
                "files_with_matches": self.files_with_matches,
                "matches": [
                    {
                        "file": str(path),
                        "kind": match.kind,
                        "identifier": match.identifier,
                        "detail": match.detail,
                    }
                    for path, match in self.matches
                ],
            },
            indent=2,
        )

    def csv(self) -> str:
        """Return one CSV record for each named object match."""
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=("file", "kind", "identifier", "detail"))
        writer.writeheader()
        for path, match in self.matches:
            writer.writerow({"file": path, "kind": match.kind, "identifier": match.identifier, "detail": match.detail})
        return output.getvalue().rstrip("\r\n")


def _matches(value: str, query: str, exact: bool) -> bool:
    normalized = value.casefold()
    return normalized == query if exact else query in normalized


def _messages(path: Path):
    native = inspect.native_type(path)
    if native:
        kind, _ = native
        if kind in {"SOUND", "ALL"}:
            return inspect._native_messages(kind, path)
        return []
    return load_dt1(path)


def _tone_matches(messages, query: str, exact: bool) -> list[Match]:
    permanent = assemble_partial(messages, 0x08, 64 * 256, "Tone data")
    temporary = assemble_partial(messages, 0x04, 64 * 256, "Temporary Tone data")
    image = permanent if permanent.coverage() else temporary
    matches: list[Match] = []
    for index in range(64):
        start = index * 256
        if not image.complete(start, 10):
            continue
        name = printable_text(image.data[start : start + 10])
        if name and _matches(name, query, exact):
            matches.append(Match("Tone", f"i{index + 1:02d}", name))
    return matches


def _timbre_matches(messages, names: dict[int, str], query: str, exact: bool) -> list[Match]:
    image = assemble_partial(messages, 0x05, 128 * 8, "Timbre data")
    matches: list[Match] = []
    for index in range(128):
        start = index * 8
        if not image.complete(start, 8):
            continue
        data = image.data[start : start + 8]
        tone = reports._tone_label(data[0], data[1], names, parenthesize_name=False)
        if _matches(tone, query, exact):
            matches.append(Match("Timbre", reports._timbre_id(index), tone))
    return matches


def _patch_matches(messages, names: dict[int, str], query: str, exact: bool) -> list[Match]:
    image = assemble_partial(messages, 0x07, 128 * 38, "Patch data")
    matches: list[Match] = []
    for index in range(128):
        start = index * 38
        if not image.complete(start, 38):
            continue
        data = image.data[start : start + 38]
        if not any(data):
            continue
        name = printable_text(data[21:37]) or "Unnamed Patch"
        lower = reports._tone_label(data[2], data[3], names, parenthesize_name=False)
        upper = reports._tone_label(data[4], data[5], names, parenthesize_name=False)
        if any(_matches(value, query, exact) for value in (name, lower, upper)):
            matches.append(Match("Patch", str(index + 1), f"{name} — {lower} / {upper}"))
    return matches


def _search_file(path: Path, query: str, match_type: str, exact: bool) -> list[Match]:
    messages = _messages(path)
    if not messages:
        return []
    names = user_tone_names(messages)
    results: list[Match] = []
    if match_type in {"all", "tone"}:
        results.extend(_tone_matches(messages, query, exact))
    if match_type in {"all", "timbre"}:
        results.extend(_timbre_matches(messages, names, query, exact))
    if match_type in {"all", "patch"}:
        results.extend(_patch_matches(messages, names, query, exact))
    return results


def search_results(directory: Path, query: str, *, match_type: str, exact: bool) -> SearchResults:
    """Search supported D-20 files below ``directory`` for a literal name."""
    root = directory.expanduser()
    if not root.is_dir():
        raise D20Error(f"Search directory does not exist: {root}")
    normalized_query = query.strip().casefold()
    if not normalized_query:
        raise D20Error("Search text must not be empty.")

    candidates = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)
    skipped = 0
    found: list[tuple[Path, Match]] = []
    for path in candidates:
        try:
            matches = _search_file(path, normalized_query, match_type, exact)
        except D20Error:
            skipped += 1
            continue
        found.extend((path.resolve(), match) for match in matches)
    return SearchResults(query, match_type, exact, len(candidates), skipped, tuple(found))


def search(directory: Path, query: str, *, match_type: str, exact: bool, output_format: str = "text") -> str:
    """Search files and format results as text, JSON, or CSV."""
    results = search_results(directory, query, match_type=match_type, exact=exact)
    formatters = {"text": results.text, "json": results.json, "csv": results.csv}
    try:
        return formatters[output_format]()
    except KeyError as exc:
        raise D20Error("Search output format must be text, json, or csv.") from exc
