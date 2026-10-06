#!/usr/bin/env python3
"""Read-only projection of the privately installed upstream review engine.

This is a display adapter, not an authenticated chat host or an approval API.
Upstream code must be installed separately under its private-use license.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True


def _deny_mutation(event: str, args: tuple) -> None:
    """Fail on accidental runtime writes; not an adversarial-code sandbox."""
    if event == "open":
        _path, mode, flags = args
        if (mode and any(c in mode for c in "wax+")) or (
            flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            raise PermissionError("review adapter is read-only")
    if event in {
        "os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.chown",
        "os.link", "os.symlink", "os.truncate", "os.utime", "subprocess.Popen",
        "os.system", "os.exec", "socket.__new__", "socket.connect",
    }:
        raise PermissionError("review adapter forbids writes, processes and network")


def read_review(engine_root: Path, instance_root: Path, operation: str,
                case_id: str | None = None) -> dict:
    """Load only upstream list_cases/case_detail; never synthesize approval."""
    engine_root = engine_root.resolve(strict=True)
    instance_root = instance_root.resolve(strict=True)
    if not (engine_root / "LICENSE").is_file():
        raise ValueError("private engine LICENSE is missing")
    if engine_root == instance_root:
        raise ValueError("engine and private instance must be separate")
    if operation not in {"list", "show", "packet"}:
        raise ValueError("only list, show and packet are supported")
    if operation != "list" and not re.fullmatch(r"case_[A-Za-z0-9_-]+", case_id or ""):
        raise ValueError("an exact engine case ID is required")
    sys.path.insert(0, str(engine_root / "scripts"))
    from librarian.review import list_cases
    from librarian.rail import case_detail
    if operation == "list":
        return {"operation": "list", "cases": list_cases(instance_root)}
    detail = case_detail(instance_root, case_id)
    if operation == "show":
        return {"operation": "show", "detail": detail}
    from librarian.paths import review_case_path
    from librarian.storage import read_json
    case = read_json(review_case_path(instance_root, case_id, "case.json"))
    revision = (case.get("proposal_revisions") or [None])[-1]
    proposal = (read_json(review_case_path(instance_root, case_id, "proposals",
                                          revision, "proposal.json"))
                if revision else None)
    packet = {"case": case, "proposal_envelope": proposal, "detail": detail}
    canonical = json.dumps(packet, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    return {
        "operation": "packet",
        "mode": "read_only_display",
        "approval_available": False,
        "authentication": "not_implemented",
        "display_sha256": hashlib.sha256(canonical).hexdigest(),
        "hash_scope": "display packet only; not an authenticated approval token",
        **packet,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", type=Path, required=True)
    parser.add_argument("--instance-root", type=Path, required=True)
    parser.add_argument("operation", choices=("list", "show", "packet"))
    parser.add_argument("case_id", nargs="?")
    args = parser.parse_args()
    sys.addaudithook(_deny_mutation)
    try:
        result = read_review(args.engine_root, args.instance_root,
                             args.operation, args.case_id)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
