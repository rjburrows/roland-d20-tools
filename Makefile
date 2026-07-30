.PHONY: install lint test check package clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m unittest discover -s tests -v

check: lint test

package:
	$(PYTHON) -m build

clean:
	rm -rf build dist *.egg-info src/*.egg-info
