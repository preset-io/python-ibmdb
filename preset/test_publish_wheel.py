"""Offline regressions for immutable release and retry behavior."""
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

from botocore.exceptions import ClientError

import publish_wheel as publisher


def wheel(version='3.2.3+preset.1', year=2026):
    output = io.BytesIO()
    with ZipFile(output, 'w') as archive:
        archive.writestr(
            ZipInfo('ibm_db-{}.dist-info/METADATA'.format(version),
                    (year, 1, 1, 0, 0, 0)),
            'Name: ibm_db\nVersion: {}\n'.format(version),
        )
    return output.getvalue()


class FakeS3:
    def __init__(self, stored=None, error=None):
        self.stored = stored
        self.error = error
        self.writes = 0

    def put_object(self, *, Bucket, Key, Body, IfNoneMatch):
        assert IfNoneMatch == '*'
        code = self.error or ('PreconditionFailed' if self.stored is not None else None)
        if code:
            raise ClientError({'Error': {'Code': code}}, 'PutObject')
        self.stored = Body
        self.writes += 1

    def get_object(self, **kwargs):
        return {'Body': io.BytesIO(self.stored)}


class PublisherTests(unittest.TestCase):
    def test_new_stable_is_written_and_verified(self):
        body = wheel()
        s3 = FakeS3()
        self.assertEqual(publisher.publish_wheel(s3, 'bucket', 'key', body),
                         hashlib.sha256(body).hexdigest())
        self.assertEqual(s3.writes, 1)

    def test_existing_stable_is_rejected_even_when_identical(self):
        body = wheel()
        s3 = FakeS3(body)
        with self.assertRaisesRegex(RuntimeError, 'Stable version already exists'):
            publisher.publish_wheel(s3, 'bucket', 'key', body)
        self.assertEqual(s3.writes, 0)
        self.assertEqual(s3.stored, body)

    def test_pr_retry_uses_stored_digest_despite_zip_timestamps(self):
        stored, fresh = wheel(year=2025), wheel()
        self.assertNotEqual(stored, fresh)
        s3 = FakeS3(stored)
        self.assertEqual(publisher.publish_wheel(s3, 'bucket', 'key', fresh, is_pr=True),
                         hashlib.sha256(stored).hexdigest())
        self.assertEqual(s3.writes, 0)

    def test_changed_pr_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Stored wheel differs'):
            publisher.publish_wheel(FakeS3(wheel()), 'bucket', 'key',
                                    wheel('3.2.3+preset.2'), is_pr=True)

    def test_unexpected_s3_errors_fail_closed(self):
        for code in ('AccessDenied', 'ConditionalRequestConflict'):
            with self.subTest(code=code), self.assertRaises(ClientError):
                publisher.publish_wheel(FakeS3(error=code), 'bucket', 'key', wheel())

    def test_version_metadata(self):
        publisher.verify_wheel_version(wheel(), '3.2.3+preset.1')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            publisher.verify_wheel_version(wheel(), '3.2.3+preset.2')
        output = io.BytesIO()
        with ZipFile(output, 'w'):
            pass
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            publisher.verify_wheel_version(output.getvalue(), '3.2.3+preset.1')

    def test_receipt_only_after_success_and_version_checked_before_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist').mkdir()
            (root / 'dist' / 'test.whl').write_bytes(wheel())
            old_cwd = os.getcwd()
            os.chdir(root)
            try:
                s3 = FakeS3()
                with patch.dict(os.environ, WHEEL='test.whl', KEY='ibm-db/test.whl',
                                PRESET_VERSION='3.2.3+preset.1',
                                ALLOW_IDENTICAL_PR_ARTIFACT='false'), \
                        patch.object(publisher.boto3, 'client', return_value=s3):
                    publisher.main()
                    receipt = Path('published.sha256')
                    self.assertEqual(receipt.read_text(),
                                     hashlib.sha256(s3.stored).hexdigest() + '  test.whl\n')
                    with self.assertRaises(RuntimeError):
                        publisher.main()
                    self.assertFalse(receipt.exists())
                    with patch.dict(os.environ, PRESET_VERSION='wrong'):
                        with self.assertRaises(ValueError):
                            publisher.main()
                    self.assertEqual(s3.writes, 1)
            finally:
                os.chdir(old_cwd)


if __name__ == '__main__':
    unittest.main()
