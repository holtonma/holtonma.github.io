"""Local record of which Hugo post became which Substack draft.

Keyed by (publication URL, Hugo permalink). States:
  creating  written *before* the create request is sent
  created   the request succeeded; draft_id and url are known
  pending   the request's outcome is unknown (timeout, error, crash mid-request)

`creating` found at startup means an earlier run died mid-request, so it is
treated exactly like `pending`.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("SUBSTACK_CROSSPOST_HOME", Path.home() / ".config" / "substack-crosspost"))

CREATING = "creating"
CREATED = "created"
PENDING = "pending"


class Locked(Exception):
    pass


def key(publication: str, permalink: str) -> str:
    return f"{publication.rstrip('/')}|{permalink}"


class Ledger:
    def __init__(self, home: Path | None = None):
        self.home = Path(home or CONFIG_DIR)
        self.path = self.home / "ledger.json"
        self.locks = self.home / "locks"

    # -------------------------------------------------------------- locking

    @contextmanager
    def post_lock(self, k: str):
        """Exclusive, non-blocking lock for one (publication, permalink)."""
        self.locks.mkdir(parents=True, exist_ok=True)
        path = self.locks / (hashlib.sha1(k.encode()).hexdigest() + ".lock")
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Locked(f"another run is already working on {k.split('|', 1)[1]}") from None
            yield
        finally:
            os.close(fd)  # closing releases the flock

    @contextmanager
    def _file_lock(self):
        """Serialize read-modify-write of ledger.json across all posts."""
        self.home.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.home / "ledger.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    # -------------------------------------------------------------- storage

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _write_atomic(self, data: dict) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.home, prefix=".ledger-", suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
            dfd = os.open(self.home, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def get(self, k: str) -> dict | None:
        with self._file_lock():
            return self._read().get(k)

    def set(self, k: str, state: str, **fields) -> dict:
        entry = {"state": state, "updated": datetime.now(timezone.utc).isoformat(), **fields}
        with self._file_lock():
            data = self._read()
            data[k] = entry
            self._write_atomic(data)
        return entry

    def clear(self, k: str) -> None:
        with self._file_lock():
            data = self._read()
            data.pop(k, None)
            self._write_atomic(data)
