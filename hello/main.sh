#!/bin/bash
cd `dirname $0`
export PYTHONPATH="$PYTHONPATH:`pwd`"
python hello/cmd/api.py --config-file=etc/hello/hello.conf --config-dir="`pwd`/etc"
