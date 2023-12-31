#!/bin/bash
set -e
pylint *.py
docker build --tag zonnetijden .
