#!/bin/bash
set -e
pip install -r requirements.txt
pip install setuptools pip --upgrade
pip list --outdated
pylint *.py
docker build --tag zonnetijden .
