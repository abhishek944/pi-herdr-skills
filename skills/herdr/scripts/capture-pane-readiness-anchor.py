#!/usr/bin/env python3
"""Atomically capture the clock anchor for one future Herdr pane creation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

READINESS_TIMEOUT = timedelta(seconds=300)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def publish_once(path: Path, payload: dict[str, Any]) -> None:
    parent = path.parent
    if not parent.is_dir():
        raise ValueError(f"output parent does not exist: {parent}")
    encoded = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = handle.name
            os.chmod(temporary, 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ValueError(f"readiness anchor already exists and cannot be reset: {path}") from error
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture one portable RFC 3339 readiness anchor immediately before creating a Herdr pane.",
    )
    parser.add_argument("--output", required=True, help="New JSON artifact path; existing files are never overwritten")
    args = parser.parse_args()
    try:
        created_at = datetime.now(timezone.utc)
        payload = {
            "createdAt": format_time(created_at),
            "deadlineAt": format_time(created_at + READINESS_TIMEOUT),
            "timeoutSeconds": int(READINESS_TIMEOUT.total_seconds()),
            "version": 1,
        }
        publish_once(Path(args.output), payload)
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error), "output": args.output}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
