#!/bin/bash
set -e
pip install --no-cache-dir --index-url https://test.pypi.org/simple/ --extra-index-url=https://pypi.org/simple/ -r requirements.txt
pip list --outdated
pylint *.py
docker build --tag zonnetijden .
