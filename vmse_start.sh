#!/bin/sh


script_dir="$(dirname $(readlink -e "$0"))"
cd "$script_dir"

tmux     new-session -d -s VMSE 'hostname; exec /bin/bash'

tmux new-window -t VMSE:1 -n VMSE_firmware
tmux new-window -t VMSE:2 -n VMSE_detector

echo Launching firmware
tmux send-keys -t VMSE:VMSE_firmware "cd code/vmse2000 && poetry run python vmse2000.py"

echo Launching detector
tmux send-keys -t VMSE:VMSE_detector "cd code/v3 && ./start.sh 1"
