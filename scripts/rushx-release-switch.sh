#!/usr/bin/python3
"""Restricted RushX release promotion/switch helper. Install root:root mode 0755."""
import fcntl
import os
import pathlib
import re
import shutil
import stat
import sys
import tempfile

ROOT = pathlib.Path("/var/www/rushx")
STAGING = ROOT / "staging"
RELEASES = ROOT / "releases"
LIVE = ROOT / "frontend"
LOCK = "/run/lock/rushx-release-switch.lock"
MAX_TOTAL = 500 * 1024 * 1024
MAX_FILES = 10000


def fail(message):
    raise SystemExit("rushx-release-switch: " + message)


def copy_snapshot(srcfd, dest, counters):
    for name in os.listdir(srcfd):
        if name in (".", "..") or "/" in name:
            fail("invalid filename")
        info = os.stat(name, dir_fd=srcfd, follow_symlinks=False)
        destination = dest / name
        if stat.S_ISDIR(info.st_mode):
            destination.mkdir(mode=0o755)
            destination.chmod(0o755)
            childfd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=srcfd)
            try:
                copy_snapshot(childfd, destination, counters)
            finally:
                os.close(childfd)
        elif stat.S_ISREG(info.st_mode):
            counters[0] += 1
            if counters[0] > MAX_FILES:
                fail("too many files")
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=srcfd)
            try:
                actual = os.fstat(fd)
                if not stat.S_ISREG(actual.st_mode):
                    fail("non-regular file")
                counters[1] += actual.st_size
                if counters[1] > MAX_TOTAL:
                    fail("release too large")
                with os.fdopen(fd, "rb", closefd=False) as source, open(destination, "xb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                destination.chmod(0o644)
            finally:
                os.close(fd)
        else:
            fail("links and special files forbidden")


def validate(directory):
    if not (directory / "index.html").is_file() or (directory / "index.html").stat().st_size == 0:
        fail("index.html missing")
    for folder, suffix in (("js", ".js"), ("css", ".css")):
        assets = directory / "static" / folder
        if not assets.is_dir() or not any(p.is_file() and p.stat().st_size for p in assets.glob("*" + suffix)):
            fail("missing " + suffix + " asset")


def main():
    if os.geteuid() != 0 or len(sys.argv) != 3:
        fail("usage: rushx-release-switch promote|switch|discard SHA")
    action, release_id = sys.argv[1:]
    if action not in ("promote", "switch", "discard"):
        fail("invalid action")
    if not (re.fullmatch("[0-9a-f]{40}", release_id) or (action == "switch" and release_id == "initial-stable")):
        fail("invalid release ID")
    with open(LOCK, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if ROOT.is_symlink() or RELEASES.is_symlink() or STAGING.is_symlink():
            fail("unsafe parent")
        if not ROOT.is_dir() or not RELEASES.is_dir() or not STAGING.is_dir():
            fail("missing directories")
        if RELEASES.stat().st_uid != 0 or RELEASES.stat().st_mode & 0o022:
            fail("releases must be root-owned and not group/other writable")
        if not LIVE.is_symlink():
            fail("frontend is not a symlink; migration not completed")
        current = LIVE.resolve(strict=True)
        if current.parent != RELEASES or not current.is_dir():
            fail("unsafe current target")
        target = RELEASES / release_id
        if action == "promote":
            if target.exists() or target.is_symlink():
                fail("release already exists")
            source = STAGING / release_id
            fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            temp = pathlib.Path(tempfile.mkdtemp(prefix=".promote-", dir=RELEASES))
            temp.chmod(0o755)
            try:
                copy_snapshot(fd, temp, [0, 0])
                validate(temp)
                os.rename(temp, target)
            finally:
                os.close(fd)
                if temp.exists():
                    shutil.rmtree(temp)
            print("Promoted", release_id)
        elif action == "discard":
            if target == current or release_id == "initial-stable":
                fail("cannot discard active or stable release")
            if target.is_symlink():
                fail("symlink release forbidden")
            if target.exists():
                shutil.rmtree(target)
        else:
            if target.is_symlink() or not target.is_dir():
                fail("missing or unsafe target")
            validate(target)
            if target == current:
                return
            temporary = ROOT / (".frontend-switch-" + str(os.getpid()))
            if temporary.exists() or temporary.is_symlink():
                fail("temporary path exists")
            try:
                os.symlink(str(target), temporary)
                os.replace(temporary, LIVE)
            finally:
                if temporary.is_symlink():
                    temporary.unlink()
            print("Switched", current, "->", target)


if __name__ == "__main__":
    main()
