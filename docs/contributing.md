# Contributing and releasing

Create a virtual environment, install the project in editable mode, and run
the tests before opening a pull request:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
make check
```

After activating the virtual environment, use `make lint`, `make test`,
`make coverage`, `make check`, and `make package` as needed. Branch-aware
coverage has a 90% repository-wide floor. The Song and rhythm pattern
decoders require 100% statement and branch coverage. Their synthetic fixtures
exercise valid exports, malformed containers, timing and CLI error paths.
Do not add private disk images
or copyrighted factory content as fixtures. Use the optional local regression
tests for that material instead.

For a release, update `src/roland_d20_tools/__init__.py` and `CHANGELOG.md`,
pass local checks and CI, tag the commit, and create a GitHub Release from that
tag. Before publishing, install the wheel into a fresh virtual environment and
confirm `d20-tools --help`.

GitHub Actions runs linting and the public suite on Python 3.10–3.13 for Linux
and Python 3.12 on macOS. It then builds and smoke-installs the wheel, and
installs and runs the whole generated-fixture suite from the source archive in
a fresh environment. Run the optional private fixture checks locally before a
release when you have the original files available.

For firmware work, document the ROM version, bank, address, evidence and
confidence level in the [firmware reverse-mapping guide](firmware-reverse-mapping.md).
Add reusable probes under `research/ghidra/`. Keep generated disassembly and
event ledgers with your local research materials.
