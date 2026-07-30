"""Recursive search for named D-20 Patches, Timbres, and Tones."""

from __future__ import annotations

from dataclasses import dataclass
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


def search(directory: Path, query: str, *, match_type: str, exact: bool) -> str:
    """Search supported D-20 files below ``directory`` for a literal name."""
    root = directory.expanduser()
    if not root.is_dir():
        raise D20Error(f"Search directory does not exist: {root}")
    normalized_query = query.strip().casefold()
    if not normalized_query:
        raise D20Error("Search text must not be empty.")

    candidates = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)
    files_with_matches = match_count = skipped = 0
    sections: list[str] = []
    for path in candidates:
        try:
            matches = _search_file(path, normalized_query, match_type, exact)
        except D20Error:
            skipped += 1
            continue
        if not matches:
            continue
        files_with_matches += 1
        match_count += len(matches)
        sections.append("\n".join((str(path.resolve()), *(match.format() for match in matches))))

    mode = "exact" if exact else "case-insensitive substring"
    summary = f"Searched {len(candidates)} supported file(s) for {query!r} ({mode}); found {match_count} match(es) in {files_with_matches} file(s)."
    if skipped:
        summary += f" Skipped {skipped} unsupported or incomplete D-20 file(s)."
    return "\n\n".join((*sections, summary)) if sections else summary
