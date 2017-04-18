#!/bin/sh
rm .coverage -f
tox -c tox-coverage.ini
echo "\nWaiting for coverage to create files...\n" ; sleep 5
coverage combine ; coverage report -m
