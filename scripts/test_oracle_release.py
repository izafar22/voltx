import hashlib
import io
import json
from pathlib import Path
import os
import subprocess
import tarfile
import tempfile
import unittest
from urllib.error import HTTPError
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
        self.verify_live = release.verify_live
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

    def test_startup_failure_restarts_previous_release(self):
        restarted = []

        def command(args):
            if args[:4] == ["sudo", "-n", "/usr/bin/systemctl", "restart"]:
                active = self.active.resolve()
                restarted.append(active.name)
                if active.name == self.sha:
                    raise subprocess.CalledProcessError(1, args)

        self.commands.side_effect = command
        with self.assertRaises(subprocess.CalledProcessError):
            self.deploy()
        self.assertEqual(restarted, [self.sha, self.previous.name])
        self.verify.assert_called_once_with(self.cfg, self.previous)
        self.assertEqual(json.loads(self.state.read_text())["sha"], self.previous.name)

    def test_readiness_failure_rolls_back_both_components(self):
        # Use the actual probe orchestration. Only network and waiting are simulated.
        self.verify.side_effect = self.verify_live
        for relative, content in self.files.items():
            if relative.startswith("frontend/") and relative != "frontend/rushx-release.txt":
                path = self.previous / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)

        def probe(url, expected):
            if url.endswith("/api/health/ready"):
                raise HTTPError(url, 503, "database unavailable", {}, None)

        with patch.object(release, "probe", side_effect=probe) as checks, patch.object(release.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "verification failed"):
                self.deploy()
        self.assertEqual(self.active.resolve(), self.previous)
        self.assertEqual(json.loads(self.state.read_text())["sha"], self.previous.name)
        self.assertTrue(any(call.args[0].endswith("/api/health/ready") for call in checks.call_args_list))
        self.assertTrue(any(call.args[0].endswith("/api/") for call in checks.call_args_list))

    def test_repeated_commit_cannot_replace_release_even_with_later_sequence(self):
        self.deploy()
        for sequence, message in [("11", "Stale"), ("12", "already exists")]:
            with self.subTest(sequence=sequence), self.assertRaisesRegex(RuntimeError, message):
                self.deploy(sequence=sequence)
        self.assertEqual(self.active.resolve().name, self.sha)
        self.assertEqual(json.loads(self.state.read_text())["sequence"], 11)
        self.verify.assert_called_once()

    def test_operator_recovery_from_incomplete_activation(self):
        self.verify.side_effect = RuntimeError("unavailable")
        with self.assertRaisesRegex(RuntimeError, "CRITICAL"):
            self.deploy()
        pending = self.root / "pending.json"
        journal = json.loads(pending.read_text())
        with self.assertRaisesRegex(RuntimeError, "operator recovery"):
            self.deploy()
        self.verify.side_effect = None
        with release.locked(self.root):
            restored = self.root / "releases" / journal["previous"]["sha"]
            release.activate(self.cfg, self.root, restored)
            release.write_json(self.state, journal["previous"])
            pending.unlink()
            (self.root / "releases" / journal["candidate"]).rename(self.root / "quarantined")
        self.assertEqual(self.active.resolve(), self.previous)
        self.deploy()
        self.assertEqual(self.active.resolve().name, self.sha)


class StagingTransferTest(unittest.TestCase):
    def test_invalid_host_or_missing_artifact_never_opens_ssh(self):
        sender = Path(__file__).with_name("send-oracle-release.sh").resolve()
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            binary = work / "bin"
            binary.mkdir()
            for name in ("ssh", "gh"):
                executable = binary / name
                executable.write_text("#!/bin/sh\ntouch unexpected-network-call\nexit 42\n")
                executable.chmod(0o755)
            env = {
                "PATH": f"{binary}:{os.environ['PATH']}",
                "GITHUB_REPOSITORY": "izafar22/voltx",
                "GITHUB_SHA": sha,
                "RELEASE_SHA": sha,
                "RELEASE_SEQUENCE": "11",
                "GITHUB_REF": "refs/heads/repair-mvp",
                "GITHUB_EVENT_NAME": "push",
                "ORACLE_USER": "deploy",
            }
            for host, diagnostic in (("-oProxyCommand=unexpected", b"Invalid SSH destination"),
                                     ("staging.example.test", b"Missing release artifact")):
                with self.subTest(host=host):
                    result = subprocess.run(
                        ["bash", str(sender), "staging"], cwd=work, capture_output=True,
                        env={**env, "ORACLE_HOST": host}, timeout=5,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(diagnostic, result.stderr)
                    self.assertFalse((work / "unexpected-network-call").exists())
