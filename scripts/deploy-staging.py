#!/usr/bin/env python3
"""Installed root-owned on the staging VM and called through restricted SSH."""
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request


ROOT = Path("/opt/rushx-staging/cd")
LIVE = Path("/var/www/rushx-staging/staging")
DROPIN = Path("/etc/systemd/system/rushx-staging.service.d/90-staging-cd.conf")
SERVICE = "rushx-staging.service"


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def replace_link(link, target):
    temporary = link.with_name(link.name + ".cd-next")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, link)


def unpack(archive, destination):
    with tarfile.open(fileobj=archive, mode="r:gz") as source:
        members = source.getmembers()
        total = sum(member.size for member in members)
        if total > 1024 * 1024 * 1024 or len(members) > 20000:
            raise ValueError("Release exceeds extraction limits")
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                raise ValueError("Unsafe release entry")
            if path.name == ".env" or ".git" in path.parts:
                raise ValueError("Environment and Git files are forbidden")
        # Only ordinary files/directories remain. Ignore archived owners and modes.
        for member in members:
            member.uid = member.gid = 0
            member.uname = member.gname = ""
            member.mode = 0o755 if member.isdir() else 0o644
        source.extractall(destination, members=members)


def check_http(url, expected=None):
    with urllib.request.urlopen(url, timeout=10) as response:
        body = response.read()
        if response.status != 200 or (expected is not None and body != expected):
            raise RuntimeError("Staging HTTP verification failed")
        return body


def healthy(metadata=None):
    for attempt in range(30):
        try:
            if run("systemctl", "is-active", SERVICE) != "active":
                raise RuntimeError("Backend is inactive")
            check_http("http://127.0.0.1:8000/api/")
            check_http("https://staging.evchargerrepair.in/api/")
            check_http("https://staging.evchargerrepair.in/")
            if metadata is not None:
                check_http("https://staging.evchargerrepair.in/release.json", metadata)
            return
        except (OSError, RuntimeError, subprocess.CalledProcessError):
            if attempt == 29:
                raise
            time.sleep(2)


def write_dropin(release):
    DROPIN.parent.mkdir(parents=True, exist_ok=True)
    DROPIN.write_text(
        "[Service]\n"
        f"WorkingDirectory={release}/backend\n"
        "ExecStart=\n"
        f"ExecStart={release}/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000\n"
        "EnvironmentFile=/etc/rushx/staging-cd.env\n"
    )


def prune_releases():
    """Retain recent attempts and both active and previous component releases."""
    try:
        protected = [LIVE.resolve(), Path(run("systemctl", "show", SERVICE, "--property=WorkingDirectory", "--value"))]
        marker = ROOT / "active.json"
        if marker.exists():
            metadata = json.loads(marker.read_text())
            for name in ("previous_frontend", "previous_backend_working_directory"):
                if metadata.get(name):
                    protected.append(Path(metadata[name]))
        releases = ROOT / "releases"
        candidates = sorted(
            (path for path in releases.glob("*") if not path.is_symlink() and path.is_dir()
             and re.fullmatch(r"[0-9a-f]{40}-[1-9][0-9]*", path.name)),
            key=lambda path: int(path.name.rsplit("-", 1)[1]), reverse=True,
        )
        for path in candidates[5:]:
            if not any(target.resolve().is_relative_to(path.resolve()) for target in protected):
                shutil.rmtree(path)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"WARNING: staging release cleanup failed: {error}", file=sys.stderr, flush=True)


def deploy(archive, sha, sequence):
    if not LIVE.is_symlink() or not LIVE.resolve().is_dir():
        raise RuntimeError("Staging frontend must already be a working symlink")
    user = run("systemctl", "show", SERVICE, "--property=User", "--value")
    if not user or user == "root":
        raise RuntimeError("Staging backend requires an explicit non-root service user")
    healthy()
    marker = ROOT / "active.json"
    previous = json.loads(marker.read_text()) if marker.exists() else {}
    if sequence <= previous.get("run_number", 0):
        print("Skipping candidate superseded by a deployed CI run")
        return
    prune_releases()
    release = ROOT / "releases" / f"{sha}-{sequence}"
    if release.exists():
        backend_directory = Path(run("systemctl", "show", SERVICE, "--property=WorkingDirectory", "--value"))
        if (LIVE.resolve().is_relative_to(release) or backend_directory.is_relative_to(release)
                or release.is_symlink()):
            raise RuntimeError("Existing candidate is active or unsafe")
        shutil.rmtree(release)
    release.mkdir(parents=True)
    unpack(archive, release)
    metadata = json.loads((release / "release.json").read_text())
    if (metadata.get("sha") != sha or metadata.get("run_number") != sequence
            or metadata.get("branch") != "repair-mvp"):
        raise RuntimeError("Artifact does not match the requested CI candidate")
    for required in ("backend/server.py", "backend/staging_safety.py",
                     "requirements.lock", "frontend/index.html", "frontend/asset-manifest.json"):
        if not (release / required).is_file():
            raise RuntimeError("Incomplete release")
    manifest = json.loads((release / "frontend/asset-manifest.json").read_text())
    for asset in manifest["entrypoints"]:
        path = PurePosixPath(asset)
        if path.is_absolute() or ".." in path.parts or not (release / "frontend" / asset).is_file():
            raise RuntimeError("Missing or unsafe frontend asset")
    venv = release / "venv"
    subprocess.run(["python3", "-m", "venv", str(venv)], check=True)
    subprocess.run(["chown", "-R", user, str(venv)], check=True)
    subprocess.run(["runuser", "-u", user, "--", str(venv / "bin/pip"),
                    "install", "--disable-pip-version-check", "-r", str(release / "requirements.lock")],
                   check=True)
    shutil.copyfile(release / "release.json", release / "frontend/release.json")
    previous_frontend = LIVE.resolve()
    previous_backend = run("systemctl", "show", SERVICE, "--property=WorkingDirectory", "--value")
    previous_dropin = DROPIN.read_bytes() if DROPIN.exists() else None
    try:
        write_dropin(release)
        run("systemctl", "daemon-reload")
        run("systemctl", "restart", SERVICE)
        if run("systemctl", "show", SERVICE, "--property=WorkingDirectory", "--value") != str(release / "backend"):
            raise RuntimeError("Backend working directory does not match the candidate")
        replace_link(LIVE, release / "frontend")
        healthy((release / "release.json").read_bytes())
        metadata["previous_frontend"] = str(previous_frontend)
        metadata["previous_backend_working_directory"] = previous_backend
        metadata["backend_working_directory"] = str(release / "backend")
        pending = ROOT / "active.next.json"
        pending.write_text(json.dumps(metadata) + "\n")
        os.replace(pending, marker)
    except BaseException:
        try:
            replace_link(LIVE, previous_frontend)
            if previous_dropin is None:
                DROPIN.unlink(missing_ok=True)
            else:
                DROPIN.write_bytes(previous_dropin)
            run("systemctl", "daemon-reload")
            run("systemctl", "restart", SERVICE)
            healthy()
            print("ROLLBACK VERIFIED: previous frontend and backend restored", flush=True)
        except BaseException:
            print("CRITICAL: staging rollback failed; operator action required", file=sys.stderr, flush=True)
        raise
    prune_releases()
    print(f"STAGING DEPLOYED: {sha} from CI run {sequence}", flush=True)


def main():
    os.umask(0o022)
    if os.geteuid() != 0 or socket.gethostname() != "rushx-staging-vnic":
        raise RuntimeError("Run the installed helper as root on the staging VM")
    if len(sys.argv) != 3 or not re.fullmatch(r"[0-9a-f]{40}", sys.argv[1]) or not re.fullmatch(r"[1-9][0-9]*", sys.argv[2]):
        raise ValueError("Expected commit SHA and CI run number")
    def interrupted(signum, frame):
        raise InterruptedError("Deployment interrupted")
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, interrupted)
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / "deploy.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with tempfile.TemporaryFile() as archive:
            size = 0
            while chunk := sys.stdin.buffer.read(1024 * 1024):
                size += len(chunk)
                if size > 300 * 1024 * 1024:
                    raise ValueError("Release upload exceeds limit")
                archive.write(chunk)
            archive.seek(0)
            deploy(archive, sys.argv[1], int(sys.argv[2]))


if __name__ == "__main__":
    main()
