"""Regression checks for extraction, stale candidates and paired rollback."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("deploy", Path(__file__).with_name("deploy-staging.py"))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class StagingDeployTests(unittest.TestCase):
    def test_archive_rejects_traversal_and_links(self):
        for name, kind in (("../outside", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                archive = io.BytesIO()
                with tarfile.open(fileobj=archive, mode="w:gz") as bundle:
                    entry = tarfile.TarInfo(name)
                    entry.type = kind
                    bundle.addfile(entry)
                archive.seek(0)
                with self.assertRaises(ValueError):
                    deploy.unpack(archive, directory)

    def test_failed_candidate_restores_both_components(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "live"
            stable = root / "stable"
            stable.mkdir()
            live.symlink_to(stable)
            dropin = root / "service/override.conf"
            dropin.parent.mkdir()
            dropin.write_text("previous backend configuration")
            sha = "a" * 40
            def fake_unpack(archive, release):
                for name in ("backend/server.py", "backend/staging_safety.py",
                             "requirements.lock", "frontend/index.html"):
                    target = release / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("test")
                (release / "frontend/asset-manifest.json").write_text('{"entrypoints":[]}')
                (release / "release.json").write_text(json.dumps(dict(sha=sha, run_number=2, branch="repair-mvp")))
            def fake_run(*args):
                if "--property=User" in args:
                    return "ubuntu"
                if "--property=WorkingDirectory" in args:
                    return str(root / "releases" / f"{sha}-2" / "backend")
                return ""
            with patch.multiple(deploy, ROOT=root, LIVE=live, DROPIN=dropin), \
                    patch.object(deploy, "unpack", side_effect=fake_unpack), \
                    patch.object(deploy, "run", side_effect=fake_run), \
                    patch.object(deploy.subprocess, "run"), \
                    patch.object(deploy, "healthy", side_effect=[None, RuntimeError("smoke failed"), None]) as health:
                with self.assertRaisesRegex(RuntimeError, "smoke failed"):
                    deploy.deploy(None, sha, 2)
                self.assertEqual(live.resolve(), stable.resolve())
                self.assertEqual(dropin.read_text(), "previous backend configuration")
                self.assertFalse((root / "active.json").exists())
                self.assertEqual(health.call_count, 3)

    def test_stale_candidate_never_switches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "live"
            live.symlink_to(root)
            (root / "active.json").write_text('{"run_number":10}')
            with patch.multiple(deploy, ROOT=root, LIVE=live), \
                    patch.object(deploy, "run", return_value="ubuntu"), \
                    patch.object(deploy, "healthy"), patch.object(deploy, "unpack") as unpack:
                deploy.deploy(None, "a" * 40, 9)
                unpack.assert_not_called()


if __name__ == "__main__":
    unittest.main()
