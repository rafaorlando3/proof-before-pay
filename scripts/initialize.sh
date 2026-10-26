#!/bin/sh
set -eu
output=$(iris session IRIS -U USER < /opt/pbp/scripts/initialize.script)
printf '%s\n' "$output"
case "$output" in
  *'PBP_INIT=1 ERRORS=0'*) ;;
  *) exit 1 ;;
esac
