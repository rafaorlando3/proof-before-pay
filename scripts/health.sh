#!/bin/sh
# Bind readiness to this container boot, so a restart cannot reuse an old marker.
set -eu
test -r /tmp/pbp-ready
test "$(cat /tmp/pbp-ready)" = "$(awk '{print $22}' /proc/1/stat)"
sh "$(dirname "$0")/check_cgroup_oom.sh"
exec /irisHealth.sh
