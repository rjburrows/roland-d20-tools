.PHONY: install test package clean

install:
	python3 -m pip install --upgrade pip
	python3 -m pip install -e .

test:
	python3 -m unittest discover -s tests -v

package:
	python3 -m pip install --upgrade build
	python3 -m build

clean:
	rm -rf build dist *.egg-info src/*.egg-info

