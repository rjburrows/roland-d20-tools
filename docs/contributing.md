# Contributing and releasing

Create a virtual environment, install the project in editable mode, and run
the tests before opening a pull request:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Use `make test` and `make package` as shortcuts after activating the virtual
environment. Do not add private disk images or copyrighted factory content as
fixtures. The optional local regression tests are designed for that purpose.

For a release, update the version in `pyproject.toml`, pass CI, tag the commit,
and create a GitHub Release from that tag.

