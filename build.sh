#!/bin/bash
set -e
export PYTHONPATH=.
pip install --no-cache-dir -r requirements.txt
pip list --outdated
pylint *.py
pytest tests
docker build --tag zonnetijden .
