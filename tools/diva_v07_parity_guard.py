#!/usr/bin/env python3
"""DIVA v0.7 golden/provenance guard.

Phase-0 rule: this tool verifies the immutable hardware-verified v0.3 binary.
It deliberately does not claim source-level parity yet; that gate remains closed
until the exact v0.3 source transformation is reconstructed.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

GOLDEN_NAME = "cve-2026-43499-app.FULL-DIVA-v0.3-HARDWARE-VERIFIED-BASE.so"
GOLDEN_SIZE = 116_108
GOLDEN_SHA256 = "fe00f7d4680752ccdbd3470f2808630a7f3f0306f490d11f5e81f5c2c92a0e86"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the immutable hardware-verified DIVA v0.3 reference"
    )
    parser.add_argument("golden", type=Path, help=f"path to {GOLDEN_NAME}")
    parser.add_argument(
        "--allow-different-name",
        action="store_true",
        help="verify bytes even if the basename differs",
    )
    args = parser.parse_args()

    path = args.golden
    if not path.is_file():
        print(f"FAIL golden_missing path={path}", file=sys.stderr)
        return 2

    if not args.allow_different_name and path.name != GOLDEN_NAME:
        print(
            f"FAIL golden_name expected={GOLDEN_NAME} actual={path.name}",
            file=sys.stderr,
        )
        return 3

    size = path.stat().st_size
    digest = sha256_file(path)

    print("DIVA_V07_PARITY_GUARD")
    print("phase=golden-binary-provenance")
    print(f"path={path}")
    print(f"size={size}")
    print(f"sha256={digest}")

    ok = True
    if size != GOLDEN_SIZE:
        print(f"FAIL size expected={GOLDEN_SIZE} actual={size}", file=sys.stderr)
        ok = False
    if digest != GOLDEN_SHA256:
        print(f"FAIL sha256 expected={GOLDEN_SHA256} actual={digest}", file=sys.stderr)
        ok = False

    if not ok:
        print("parity=REJECTED", file=sys.stderr)
        return 1

    print("golden_binary=EXACT")
    print("source_parity=NOT_YET_PROVEN")
    print("parity=GOLDEN_VERIFIED_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
