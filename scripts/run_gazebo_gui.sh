#!/bin/bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
root=$(cd "$(dirname "$0")/.." && pwd)
source "$root/install/setup.bash"
set -u
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA

gui_rate=${ARACHNE_GZ_GUI_HZ:-30}
gui_config="$root/install/arachne_hx6_simulation/share/arachne_hx6_simulation/config/flight_hex_lean.config"
server_pid=

cleanup() {
  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill -INT "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "$root"
ros2 launch arachne_hx6_simulation flight_hex.launch.py gz_args:="-s -r" "$@" &
server_pid=$!

# Keep the physics server independent from the GUI. Closing or replacing the
# WSLg window therefore cannot stop the simulation or ROS bridge unexpectedly.
gz sim -g -z "$gui_rate" --render-engine-gui ogre --gui-config "$gui_config"
