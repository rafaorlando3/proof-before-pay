#!/bin/sh
# Run inside the dedicated, licensed IRIS test container. No dependency download.
set -eu
src=${1:?Usage: build.sh /path/to/pex /tmp/build-directory}
out=${2:?Usage: build.sh /path/to/pex /tmp/build-directory}
iris_dir=${IRISINSTALLDIR:-/usr/irissys}
mkdir -p "$out/classes"
javac --release 8 -cp "$iris_dir/dev/java/lib/1.8/*" -d "$out/classes" "$src"/java/pbp/pex/*.java
java -Xmx64m -cp "$out/classes" pbp.pex.ExportDigestTest
jar cf "$out/pbp-export-digest.jar" -C "$out/classes" pbp/pex/ExportDigest.class -C "$out/classes" 'pbp/pex/ExportDigest$Result.class' -C "$out/classes" pbp/pex/ExportDigestOperation.class
printf 'Built own-code JAR: %s/pbp-export-digest.jar\n' "$out"
