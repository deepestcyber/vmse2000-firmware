#!/bin/sh
tmux \
    new-session  'cd code/vmse2000 && poetry run python vmse2000.py' \; \
    split-window 'cd code/v3 && ./start.sh' \;
