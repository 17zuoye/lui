#!/usr/bin/env bash

python lui.py test_lui.json

test -e Foobar1
test -e Foobar2
rm -f Foobar*
