#!/bin/bash
set -e
export PYTHONPATH=.
pip install --no-cache-dir --index-url https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple/ -r requirements.txt
pip list --outdated
pylint *.py
pytest tests
docker build --tag zonnetijden .
