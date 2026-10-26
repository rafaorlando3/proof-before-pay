#!/bin/sh
# Bind readiness to this container boot, so a restart cannot reuse an old marker.
set -eu
test -r /tmp/pbp-ready
test "$(cat /tmp/pbp-ready)" = "$(awk '{print $22}' /proc/1/stat)"
exec /irisHealth.sh
