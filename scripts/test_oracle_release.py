import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import oracle_release as release


class OracleReleaseTest(unittest.TestCase):
    sha = "a" * 40
    files = {
        "release-sha.txt": (sha + "\n").encode(),
        "frontend/rushx-release.txt": (sha + "\n").encode(),
        "frontend/index.html": b"<html>candidate</html>",
        "frontend/static/js/main.test.js": b"console.log(1)",
        "frontend/static/css/main.test.css": b"body{}",
        "backend/requirements.txt": b"",
        "backend/server.py": b"candidate",
        "wheels/fixture.whl": b"unused",
    }

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.previous = self.root / "releases" / "initial-stable"
        self.previous.mkdir(parents=True)
        self.active = self.root / "current"
        self.active.symlink_to(self.previous)
        self.state = self.root / "deployed.json"
        self.state.write_text('{"sha":"initial-stable","sequence":10}')
        self.cfg = dict(root=str(self.root), environment="staging", service="test.service",
                        preflight_service="test-check.service", python="/usr/bin/python3",
                        loopback="http://127.0.0.1:8000")
        self.commands = self.enterContext(patch.object(release, "command"))
        self.verify = self.enterContext(patch.object(release, "verify_live"))

    def bundle(self, files):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            for path, content in files.items():
                entry = tarfile.TarInfo(path)
                entry.size = len(content)
                archive.addfile(entry, io.BytesIO(content))
        return stream, hashlib.sha256(stream.getvalue()).hexdigest()

    def deploy(self, environment="staging", sequence="11", files=None, digest=None):
        stream, real_digest = self.bundle(files if files is not None else self.files)
        stream.seek(0)
        release.deploy(self.cfg, environment, self.sha, sequence, digest or real_digest, stream)

    def test_switches_both_components_and_records_release(self):
        self.deploy()
        self.assertEqual(self.active.resolve().name, self.sha)
        self.assertEqual((self.active / "backend/server.py").read_bytes(), b"candidate")
        self.assertEqual((self.active / "frontend/index.html").read_bytes(), b"<html>candidate</html>")
        self.assertEqual(json.loads(self.state.read_text()), {"sha": self.sha, "sequence": 11})
        self.assertFalse((self.root / "pending.json").exists())

    def test_rollback_after_frontend_or_backend_failure(self):
        for check in ("frontend", "backend"):
            with self.subTest(check=check):
                def verify(cfg, active):
                    self.assertEqual(self.active.resolve(), active)
                    if active.name == self.sha:
                        raise RuntimeError(check)
                self.verify.side_effect = verify
                with self.assertRaisesRegex(RuntimeError, check):
                    self.deploy()
                self.assertEqual(self.active.resolve(), self.previous)
                self.assertEqual(json.loads(self.state.read_text())["sequence"], 10)
                self.assertFalse((self.root / "releases" / self.sha).exists())
                self.assertFalse((self.root / "pending.json").exists())

    def test_rejects_stale_wrong_target_bad_digest_and_unsafe_archive(self):
        for options in ({"sequence": "10"}, {"environment": "production"}, {"digest": "b" * 64},
                        {"files": {**self.files, "../unexpected": b"bad"}},
                        {"files": {**self.files, "release-sha.txt": b"wrong"}},
                        {"files": {**self.files, "backend/.env": b"unexpected"}}):
            with self.subTest(options=options), self.assertRaises(RuntimeError):
                self.deploy(**options)
        self.assertEqual(self.active.resolve(), self.previous)

    def test_host_lock_rejects_concurrent_release(self):
        with release.locked(self.root), self.assertRaises(BlockingIOError):
            self.deploy()

    def test_interruption_after_state_write_restores_previous_record(self):
        write = release.write_json

        def interrupt_after_candidate_write(path, value):
            write(path, value)
            if path == self.state and value["sha"] == self.sha:
                raise RuntimeError("Interrupted after writing candidate state")

        with patch.object(release, "write_json", side_effect=interrupt_after_candidate_write):
            with self.assertRaisesRegex(RuntimeError, "Interrupted"):
                self.deploy()

        self.assertEqual(self.active.resolve(), self.previous)
        self.assertEqual(json.loads(self.state.read_text()), {"sha": "initial-stable", "sequence": 10})
        self.assertFalse((self.root / "pending.json").exists())

    def test_failed_rollback_preserves_recovery_journal(self):
        self.verify.side_effect = RuntimeError("check failed")
        with self.assertRaisesRegex(RuntimeError, "CRITICAL"):
            self.deploy()
        self.assertTrue((self.root / "pending.json").exists())
        with self.assertRaisesRegex(RuntimeError, "operator recovery"):
            self.deploy()
