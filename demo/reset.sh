#!/bin/sh
# put the bug back so the demo can be run (and recorded) again
cp "$(dirname "$0")/.login.broken.py" "$(dirname "$0")/login.py" && echo "login.py reset to the broken version"
