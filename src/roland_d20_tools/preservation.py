"""Keep native bytes outside hardware-bound MIDI/SysEx streams."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from .core import D20Error, atomic_write, read_file


def sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".native.json")


def save(source: Path, destination: Path) -> None:
    payload = {
        "version": 1,
        "native_type": source.suffix.lower(),
        "export_sha256": hashlib.sha256(read_file(destination)).hexdigest(),
        "native_base64": base64.b64encode(read_file(source)).decode("ascii"),
    }
    atomic_write(sidecar(destination), (json.dumps(payload, indent=2) + "\n").encode())


def restore(source: Path, native_type: str) -> bytes | None:
    path = sidecar(source)
    if not path.exists():
        return None
    try:
        payload = json.loads(read_file(path))
        if payload["version"] != 1 or payload["native_type"] != native_type:
            raise ValueError("wrong version or native type")
        if payload["export_sha256"] != hashlib.sha256(read_file(source)).hexdigest():
            raise ValueError("export has changed")
        raw = base64.b64decode(payload["native_base64"], validate=True)
        expected = {".333": (24576, 3), ".444": (12288, 4)}[native_type]
        if len(raw) != expected[0] or raw[:3] != bytes((expected[1], 0, 0)):
            raise ValueError("invalid native container")
        return raw
    except (ValueError, KeyError, TypeError) as exc:
        raise D20Error(f"Invalid preservation sidecar {path}: {exc}. Keep it with its original export; move it aside for a normalized conversion.") from exc
