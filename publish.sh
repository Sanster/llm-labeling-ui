#!/usr/bin/env bash
set -e

pushd ./web
npm run export
popd

python3 setup.py sdist bdist_wheel
twine upload dist/*
