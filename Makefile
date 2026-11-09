.PHONY: install lint test coverage check package clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m unittest discover -s tests -v

coverage:
	$(PYTHON) -m coverage run -m unittest discover -s tests -v
	$(PYTHON) -m coverage report
	$(PYTHON) -m coverage report --include '*/song.py,*/pattern.py' --fail-under=100

check: lint coverage

package:
	$(PYTHON) -m build

clean:
	rm -rf build dist *.egg-info src/*.egg-info
