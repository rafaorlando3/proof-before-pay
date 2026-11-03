#!/bin/sh
# Detect kernel OOM kills only when the visible counter belongs to this process's
# cgroup. Missing telemetry is not proof that workers survived.
set -eu
scope=${1:-/sys/fs/cgroup}
self_cgroup=${2:-/proc/self/cgroup}
unavailable() {
    echo "PBP_HEALTH=oom_telemetry_unavailable reason=$1" >&2
    exit 0
}
[ -r "$self_cgroup" ] || unavailable cgroup_identity_missing
events=
if [ -r "$scope/memory.events" ]; then
    # A non-root v2 path means this mount may expose the host hierarchy. Never
    # attribute a host/root OOM kill to this container.
    grep -qx '0::/' "$self_cgroup" || unavailable cgroup_namespace_not_private
    events=$scope/memory.events
else
    # v1: resolve the memory controller's exact self path when the mount exposes
    # a hierarchy; do not fall back to a host/root counter for a non-root path.
    group=$(awk -F: '("," $2 ",") ~ /,memory,/ { sub(/^[^:]*:[^:]*:/, ""); print }' "$self_cgroup")
    case "$group" in
        /) relative= ;;
        /*) relative=$group ;;
        *) unavailable memory_controller_identity_missing ;;
    esac
    for candidate in "$scope/memory$relative/memory.oom_control" "$scope$relative/memory.oom_control"; do
        if [ -r "$candidate" ]; then events=$candidate; break; fi
    done
fi
[ -n "$events" ] || unavailable counter_file_missing
# Older v1 kernels expose memory.oom_control without an oom_kill counter.
# An absent field is unavailable; an exposed malformed value fails closed.
if ! awk '$1 == "oom_kill" { found=1 } END { exit !found }' "$events"; then unavailable counter_field_missing; fi
count=$(awk '$1 == "oom_kill" { print $2 }' "$events")
case "$count" in
    ''|*[!0-9]*)
        echo 'PBP_HEALTH=oom_telemetry_invalid' >&2
        exit 1
        ;;
    *[1-9]*)
        echo "PBP_HEALTH=oom_kill_detected count=$count" >&2
        exit 1
        ;;
esac
exit 0
