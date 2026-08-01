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
coverage has a 90% floor; use its missing-line report to improve meaningful
coverage rather than adding superficial tests. Do not add private disk images
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
