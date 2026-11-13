#!/usr/bin/python3
"""Install as rushx-oracle-release. Runs unprivileged with an operator-owned host config."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

CONFIG = Path("/etc/rushx/oracle-release.json")
ORIGINS = {
    "staging": "https://staging.evchargerrepair.in",
    "production": "https://evchargerrepair.in",
}
SHA = re.compile(r"[a-f0-9]{40}")
MAX_ARCHIVE = 1024**3
MAX_EXPANDED = 2 * MAX_ARCHIVE


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def config():
    require(not CONFIG.is_symlink(), "Unsafe host configuration")
    metadata = CONFIG.stat()
    require(metadata.st_uid == 0 and not metadata.st_mode & 0o022, "Unsafe host configuration")
    return json.loads(CONFIG.read_text())


def command(args):
    subprocess.run(args, check=True, timeout=600, stdin=subprocess.DEVNULL)


def write_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp:
        json.dump(value, temp)
        temp.flush()
        os.fsync(temp.fileno())
    os.replace(temp.name, path)


def receive(stream, archive, digest):
    checksum = hashlib.sha256()
    with archive.open("xb") as output:
        while chunk := stream.read(1024 * 1024):
            require(output.tell() + len(chunk) <= MAX_ARCHIVE, "Archive too large")
            checksum.update(chunk)
            output.write(chunk)
    require(checksum.hexdigest() == digest, "Archive checksum mismatch")


def unpack(archive, destination):
    # Only normal files and directories from the declared release layout.
    total = 0
    seen = set()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and ".." not in path.parts and path.parts and
                    path.parts[0] in ("frontend", "backend", "wheels", "release-sha.txt") and
                    not any(part.startswith(".") for part in path.parts) and
                    (member.isfile() or member.isdir()) and path not in seen,
                    "Unsafe archive member")
            seen.add(path)
            total += member.size
            require(total <= MAX_EXPANDED and len(seen) <= 30000, "Expanded archive exceeds limits")
            target = destination.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)


def frontend_assets(frontend):
    for folder, suffix in (("js", ".js"), ("css", ".css")):
        path = next((p for p in sorted((frontend / "static" / folder).glob("main.*" + suffix))
                     if p.is_file() and p.stat().st_size), None)
        require(path is not None, "Missing compiled frontend asset")
        yield path


def probe(url, expected=None):
    with urllib.request.build_opener(NoRedirect()).open(url, timeout=8) as response:
        require(response.status == 200, "Health check did not return 200")
        if expected is not None:
            require(response.read(len(expected) + 1) == expected, "Unexpected deployed response")


def verify_live(cfg, release):
    frontend = release / "frontend"
    origin = ORIGINS[cfg["environment"]]
    legacy = release.name == "initial-stable" and not (release / "release-sha.txt").exists()
    for _ in range(8):
        try:
            probe(origin + "/", (frontend / "index.html").read_bytes())
            for path in frontend_assets(frontend):
                probe(origin + "/" + path.relative_to(frontend).as_posix(), path.read_bytes())
            if legacy:
                for base in (cfg["loopback"], origin):
                    probe(base + "/api/", b'{"message":"EV Charging Network API"}')
            else:
                probe(origin + "/rushx-release.txt", (release / "release-sha.txt").read_bytes())
                expected = json.dumps({"status": "ready", "sha": release.name}, separators=(",", ":")).encode()
                for base in (cfg["loopback"], origin):
                    probe(base + "/api/health/ready", expected)
            return
        except (OSError, RuntimeError):
            time.sleep(3)
    raise RuntimeError("Frontend or backend verification failed")


def switch(root, release):
    with tempfile.TemporaryDirectory(prefix=".switch-", dir=root) as work:
        link = Path(work) / "current"
        link.symlink_to(release)
        os.replace(link, root / "current")


def activate(cfg, root, release):
    switch(root, release)
    command(["sudo", "-n", "/usr/bin/systemctl", "restart", cfg["service"]])
    verify_live(cfg, release)


def prepare(cfg, root, sha, digest, stream):
    releases = root / "releases"
    target = releases / sha
    require(not target.exists() and not target.is_symlink(), "Release already exists")
    with tempfile.TemporaryDirectory(prefix=".incoming-", dir=root) as work:
        archive, snapshot = Path(work) / "bundle.tar.gz", Path(work) / "release"
        receive(stream, archive, digest)
        snapshot.mkdir()
        unpack(archive, snapshot)
        marker = sha + "\n"
        require((snapshot / "release-sha.txt").read_text() == marker and
                (snapshot / "frontend/rushx-release.txt").read_text() == marker and
                (snapshot / "frontend/index.html").stat().st_size > 0, "Incomplete or wrong release")
        list(frontend_assets(snapshot / "frontend"))
        snapshot.rename(target)
    try:
        # Build at the final location, since virtual environments use absolute paths.
        venv = target / "venv"
        command([cfg["python"], "-m", "venv", str(venv)])
        command([str(venv / "bin/python"), "-m", "pip", "--isolated", "install",
                 "--no-index", "--only-binary=:all:", "--find-links", str(target / "wheels"),
                 "-r", str(target / "backend/requirements.txt")])
        command([str(venv / "bin/python"), "-m", "pip", "check"])
        shutil.rmtree(target / "wheels")
    except BaseException:
        shutil.rmtree(target)
        raise
    return target


@contextlib.contextmanager
def locked(root):
    with (root / "deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def deploy(cfg, environment, sha, sequence, digest, stream):
    require(environment in ORIGINS and cfg["environment"] == environment, "Host environment mismatch")
    require(SHA.fullmatch(sha) and sequence.isdecimal() and len(sequence) <= 12 and
            0 < int(sequence) and re.fullmatch(r"[a-f0-9]{64}", digest), "Invalid release metadata")
    require(re.fullmatch(r"[a-zA-Z0-9_.@-]+\.service", cfg["service"]) and
            re.fullmatch(r"[a-zA-Z0-9_.@-]+\.service", cfg["preflight_service"]) and
            re.fullmatch(r"http://127\.0\.0\.1:[1-9][0-9]{0,4}", cfg["loopback"]), "Invalid host service settings")
    root = Path(cfg["root"]).resolve(strict=True)
    releases, live = root / "releases", root / "current"
    state_file, pending = root / "deployed.json", root / "pending.json"
    os.umask(0o022)
    with locked(root):
        require(not pending.exists(), "Interrupted deployment requires operator recovery")
        require(live.is_symlink() and not releases.is_symlink(), "Release layout requires provisioning")
        previous = live.resolve(strict=True)
        state = json.loads(state_file.read_text())
        require(previous.parent == releases and previous.name == state["sha"] and previous.is_dir(),
                "Active release and deployed state disagree")
        require(int(sequence) > state["sequence"], "Stale or already deployed release")
        # This oneshot runs with the service's environment, before accepting any new release.
        command(["sudo", "-n", "/usr/bin/systemctl", "start", cfg["preflight_service"]])
        target = prepare(cfg, root, sha, digest, stream)
        write_json(pending, {"previous": state, "candidate": sha, "sequence": int(sequence)})
        try:
            activate(cfg, root, target)
            write_json(state_file, {"sha": sha, "sequence": int(sequence)})
        except BaseException:
            print("Activation failed. Restoring previous frontend and backend.", file=sys.stderr)
            try:
                activate(cfg, root, previous)
                write_json(state_file, state)
            except BaseException:
                raise RuntimeError("CRITICAL: rollback failed. Recover using pending.json.") from None
            pending.unlink()
            shutil.rmtree(target)
            raise
        pending.unlink()
        print(f"Deployed {sha} (CI run {sequence}); previous release {previous.name}")


def interrupt(signum, frame):
    # Allow a catchable disconnect to finish recovery without a second signal interrupting it.
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, signal.SIG_IGN)
    raise RuntimeError("Deployment interrupted")


def main():
    # For an authorized_keys forced command, only accept this exact wire format.
    original = os.environ.get("SSH_ORIGINAL_COMMAND")
    if original is not None:
        args = original.split()
        require(len(args) == 6 and args[0] == "/usr/local/bin/rushx-oracle-release",
                "Unsupported SSH command")
        args = args[1:]
    else:
        args = sys.argv[1:]
    require(len(args) == 5 and args[0] == "deploy", "Expected deploy environment SHA sequence digest")
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupt)
    deploy(config(), *args[1:], sys.stdin.buffer)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, tarfile.TarError, subprocess.SubprocessError) as error:
        sys.exit(f"Oracle release failed ({error})")
