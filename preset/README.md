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

## Publishing

Like PyHive's `master` publisher, the Jenkins multibranch build of the merged
release branch publishes the stable version: merging into `preset/base-v3.2.3`
triggers a branch build that publishes `preset/VERSION` (`3.2.3+preset.1`).
No tag is required; tag builds and other non-PR branches are rejected. PR builds
continue to publish `<version>.pr.<PR number>.<first 12 commit SHA characters>`.
The build and bundled driver are unchanged.

Both paths smoke-test the installed wheel's version, check the archive's
METADATA before upload, and use `preset/publish_wheel.py` with an atomic S3
`If-None-Match: *` write to `preset-pypi/ibm-db/<wheel filename>`. An existing
stable artifact always fails, even if identical; bump `preset/VERSION` for a
subsequent release. Only PR retries may accept identical archive contents
(ignoring ZIP timestamps), without overwriting. Storage/authentication errors
fail closed. After reading back and verifying the stored wheel, the publisher
writes its actual SHA256 to `published.sha256`; Jenkins archives both files.

The index serves S3 object keys directly (there is no `/simple/ibm-db/` index).
The stable artifact URL is:

```
https://pypi.devops.preset.zone/ibm-db/ibm_db-3.2.3+preset.1-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
```

Offline publisher checks (requires boto3):
`python -m unittest discover -s preset -p 'test_*.py'`.
