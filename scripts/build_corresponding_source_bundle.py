#!/usr/bin/env python3
"""
build_corresponding_source_bundle.py — AGPL-3.0 §13 source archive builder.

Builds a reproducible gzip-compressed tar archive of this overlay's
corresponding source, suitable for serving at:
  /_brand/postiz-complete-corresponding-source.tar.gz

Usage:
    python3 scripts/build_corresponding_source_bundle.py \\
        --postiz-digest sha256:875e61ac5d0ac43c3dec78a78a7032dfb03d9a8c6d4936ebb18adb606cc207c5 \\
        --postiz-version 2.26.0 \\
        --overlay-revision cd6ff8160db91ad64ed43f0b8b3c09a0401c2ee8 \\
        --upstream-revision c92d58be17da1a9bfd8de02bb703c783bf4e5d1b \\
        --out-dir /tmp/brand-bundles

Invariants:
    - Zero vault/secret files in the archive (rejected by path pattern)
    - Sorted, deterministic file order
    - Reproducible gzip metadata (mtime=0, OS=255)
    - SHA-256 digest written to <name>.sha256
    - AGPL-3.0 LICENSE must be present in repo root
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_PATTERNS = [
    re.compile(r'(^|/)\.env(\.|$)', re.IGNORECASE),
    re.compile(r'(^|/)secrets?/', re.IGNORECASE),
    re.compile(r'(^|/)vault/', re.IGNORECASE),
    re.compile(r'(^|/)\.aws/', re.IGNORECASE),
    re.compile(r'(^|/)\.ssh/', re.IGNORECASE),
    re.compile(r'\.pem$', re.IGNORECASE),
    re.compile(r'\.key$', re.IGNORECASE),
    re.compile(r'_secret', re.IGNORECASE),
    re.compile(r'credentials', re.IGNORECASE),
    re.compile(r'(^|/)node_modules/'),
    re.compile(r'(^|/)__pycache__/'),
    re.compile(r'(^|/)\.git/'),
]

ALLOWED_EXTENSIONS = {
    '.ts', '.js', '.json', '.md', '.txt', '.html', '.css', '.sh',
    '.py', '.diff', '.patch', '.yml', '.yaml', '.Caddyfile', '',
}


def _is_secret_path(rel_path: str) -> bool:
    for pat in SECRET_PATTERNS:
        if pat.search(rel_path):
            return True
    return False


def _collect_files(repo_root: str) -> list:
    result = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.git'))
        for fname in sorted(filenames):
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, repo_root)
            if _is_secret_path(rel):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            result.append((rel, full))
    return sorted(result)


def _verify_license(repo_root: str) -> None:
    license_path = os.path.join(repo_root, 'LICENSE')
    if not os.path.isfile(license_path):
        raise FileNotFoundError("LICENSE file not found in repo root — AGPL-3.0 required")
    with open(license_path) as fh:
        content = fh.read()
    if 'GNU AFFERO GENERAL PUBLIC LICENSE' not in content.upper():
        raise ValueError("LICENSE does not appear to be AGPL — verify before bundling")


def build_bundle(
    postiz_digest: str,
    postiz_version: str,
    overlay_revision: str,
    upstream_revision: str,
    out_dir: str,
) -> str:
    if not re.match(r'^sha256:[0-9a-f]{64}$', postiz_digest):
        raise ValueError(f"Invalid digest format: {postiz_digest!r}  (expected sha256:<64 hex chars>)")

    _verify_license(REPO_ROOT)

    digest_short = postiz_digest[7:15]
    for name, revision in (("overlay", overlay_revision), ("upstream", upstream_revision)):
        if not re.match(r"^[0-9a-f]{40}$", revision):
            raise ValueError(f"Invalid {name} source revision: {revision!r}")

    archive_name = "postiz-complete-corresponding-source.tar.gz"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, archive_name)

    files = _collect_files(REPO_ROOT)
    if not files:
        raise RuntimeError("No files collected — check repo root path")

    manifest = {
        "postiz_image_digest": postiz_digest,
        "postiz_version": postiz_version,
        "overlay_repo": "https://github.com/FogArmy-LLC/postiz-fas-overlay",
        "overlay_source_revision": overlay_revision,
        "upstream_repo": "https://github.com/gitroomhq/postiz-app",
        "upstream_source_revision": upstream_revision,
        "built_at_utc": "REPRODUCIBLE",
        "files": [rel for rel, _ in files],
    }

    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w|") as tf:
            def _add(name: str, data: bytes) -> None:
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                info.mtime = 0
                info.mode = 0o644
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                tf.addfile(info, io.BytesIO(data))

            prefix = "postiz-complete-corresponding-source"
            _add(f"{prefix}/MANIFEST.json", json.dumps(manifest, indent=2).encode())
            for rel, full in files:
                with open(full, "rb") as fh:
                    _add(f"{prefix}/{rel}", fh.read())

    archive_bytes = buf.getvalue()
    with open(out_path, "wb") as fh:
        fh.write(archive_bytes)

    digest_hex = hashlib.sha256(archive_bytes).hexdigest()
    sha_path = out_path + ".sha256"
    with open(sha_path, "w") as fh:
        fh.write(f"{digest_hex}  {archive_name}\n")

    print(f"Archive: {out_path}")
    print(f"SHA-256: {digest_hex}")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postiz-digest", required=True,
                        help="Exact sha256 digest of the running Postiz image, e.g. sha256:875e61ac...")
    parser.add_argument("--postiz-version", required=True,
                        help="Postiz version string, e.g. 2.26.0")
    parser.add_argument("--overlay-revision", required=True,
                        help="Exact 40-hex revision of FogArmy's overlay source")
    parser.add_argument("--upstream-revision", required=True,
                        help="Exact 40-hex revision of the Postiz upstream source")
    parser.add_argument("--out-dir", default="/tmp/brand-bundles",
                        help="Output directory (default: /tmp/brand-bundles)")
    parser.add_argument("--verify-reproducible", action="store_true",
                        help="Build twice and assert byte-identical output")
    args = parser.parse_args()

    try:
        p1 = build_bundle(
            args.postiz_digest,
            args.postiz_version,
            args.overlay_revision,
            args.upstream_revision,
            args.out_dir,
        )
        if args.verify_reproducible:
            import tempfile, filecmp
            tmp = tempfile.mkdtemp()
            p2 = build_bundle(
                args.postiz_digest,
                args.postiz_version,
                args.overlay_revision,
                args.upstream_revision,
                tmp,
            )
            if not filecmp.cmp(p1, p2, shallow=False):
                print("ERROR: builds are NOT byte-identical", file=sys.stderr)
                return 1
            print("Reproducibility check: PASSED (byte-identical)")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
