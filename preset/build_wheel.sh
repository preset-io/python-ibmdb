#!/bin/bash
# Build the Preset ibm_db wheel: the published ibm_db 3.2.3 cp311
# manylinux2014 wheel with only ibm_db.cpython-311-x86_64-linux-gnu.so rebuilt
# from this branch's ibm_db.c and ibm_db_dbi.py replaced. The bundled
# clidriver (11.5.9.0) and every other file are the published bytes.
#
# Run inside quay.io/pypa/manylinux2014_x86_64 from the repository root:
#   PRESET_VERSION=3.2.3+preset.1 preset/build_wheel.sh
set -euo pipefail

PRESET_VERSION="${PRESET_VERSION:?e.g. 3.2.3+preset.1}"
BASE_WHEEL=ibm_db-3.2.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
BASE_URL=https://files.pythonhosted.org/packages/8c/a1/1efbb1136b9090aa05531a886d43edc1447f051f9e082b309ccc899c5424/$BASE_WHEEL
BASE_SHA256=c5a8ab31130beea18dcd3dd447d6e35ec840ccaed1d3add8ed04ac5c4f44f94c
PY=/opt/python/cp311-cp311/bin/python
OUT="${OUT:-dist}"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fsSL -o "$work/$BASE_WHEEL" "$BASE_URL"
echo "$BASE_SHA256  $work/$BASE_WHEEL" | sha256sum -c -
"$PY" -m pip install -q 'wheel==0.45.1'
"$PY" -m wheel unpack -d "$work/unpacked" "$work/$BASE_WHEEL"
root="$work/unpacked/ibm_db-3.2.3"

# Rebuild the extension against the bundled clidriver headers and library,
# with the same run path as the published module.
include=$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["include"])')
gcc -pthread -fPIC -shared -O2 -g0 -fno-strict-aliasing -Wno-deprecated-declarations \
    -I"$root/clidriver/include" -I"$include" ibm_db.c \
    -L"$root/clidriver/lib" -ldb2 \
    -Wl,-rpath,'$ORIGIN/clidriver/lib:$ORIGIN/ibm_db.libs' \
    -o "$root/ibm_db.cpython-311-x86_64-linux-gnu.so"
cp ibm_db_dbi.py "$root/ibm_db_dbi.py"

# Rename to the Preset version; wheel pack rewrites RECORD.
mv "$root/ibm_db-3.2.3.dist-info" "$root/ibm_db-${PRESET_VERSION}.dist-info"
sed -i "s/^Version: 3\.2\.3$/Version: ${PRESET_VERSION}/" \
    "$root/ibm_db-${PRESET_VERSION}.dist-info/METADATA"
grep -qx "Version: ${PRESET_VERSION}" "$root/ibm_db-${PRESET_VERSION}.dist-info/METADATA"
mkdir -p "$OUT"
"$PY" -m wheel pack -d "$OUT" "$root"
ls -l "$OUT"
