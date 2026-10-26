#!/bin/sh
set -eu
rm -f /tmp/pbp-ready
output=$(iris session IRIS -U USER < /opt/pbp/scripts/initialize.script)
printf '%s\n' "$output"
case "$output" in
  *'PBP_INIT=1 ERRORS=0'*) ;;
  *) exit 1 ;;
esac
case "$output" in
  *'PBP_INSTALL=1'*) ;;
  *) exit 1 ;;
esac
awk '{print $22}' /proc/1/stat > /tmp/pbp-ready
