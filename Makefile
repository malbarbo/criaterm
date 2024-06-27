.PHONY: all check test

all: check test

check:
	mypy criaterm.py

test:
	python -B -mdoctest criaterm.py
