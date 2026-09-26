# Preset build of ibm_db 3.2.3

This branch is ibm_db 3.2.3 with two fixes:

- `ibm_db.c`: DECFLOAT columns were bound with a buffer of precision + 3
  characters, so valid values whose character form is longer (for example
  `0.00520257200000000` in DECFLOAT(16), or `1E+6144` in DECFLOAT(34)) failed
  to fetch with `CLI0111E Numeric value out of range`
  (ibmdb/python-ibmdb#1075). The buffer now holds the longest DECFLOAT
  character form (42 characters).
- `ibm_db_dbi.py`: `fetchall`/`fetchmany` returned the rows read so far when a
  later fetch failed (for example when the connection was lost mid-result),
  silently truncating the result. They now raise.

`preset/build_wheel.sh` takes the published ibm_db 3.2.3 cp311 manylinux2014
wheel (verified by SHA256), rebuilds only the extension module from this
branch's `ibm_db.c` against the clidriver bundled in that wheel, replaces
`ibm_db_dbi.py`, and repackages it as `ibm_db` `3.2.3+preset.<n>`. Every other
file, including the clidriver, is the published bytes.
