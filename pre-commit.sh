#!/bin/sh

python -m unittest discover || exit 1
flake8 --max-line-length=100 --ignore E221,E127,E241 || exit 1
