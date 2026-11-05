#!/usr/bin/env python3
"""Create, sign and verify AI Server release bundles (maintainer workstation tool).

  keygen  Create an Ed25519 signing key. The private key is encrypted with a
          passphrase typed at the prompt; it is never written in clear text and
          must be stored outside this repository. Prints the public key to put
          in AI_SERVER_UPDATE_PUBLIC_KEYS on the server.
  build   Wrap a payload made by scripts/proxmox/build-lab-bundle.py into a
          signed .aibundle (manifest.json + manifest.sig + payload.tar.gz).
  verify  Check a .aibundle against a public key, using the server's verifier.

The passphrase is read with getpass and is never accepted as an argument.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import io
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-backend"))

import release_bundle  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)


def _passphrase(confirm: bool) -> bytes:
    first = getpass.getpass("Signing key passphrase: ")
    if not first:
        raise SystemExit("A passphrase is required.")
    if confirm and getpass.getpass("Repeat passphrase: ") != first:
        raise SystemExit("Passphrases did not match.")
    return first.encode("utf-8")


def _public_raw(key: Ed25519PrivateKey) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


def keygen(args: argparse.Namespace) -> int:
    if args.private_key.exists():
        raise SystemExit(f"{args.private_key} already exists; refusing to overwrite.")
    if ROOT in args.private_key.resolve().parents:
        raise SystemExit("Store the signing key outside the repository.")
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(_passphrase(confirm=True)),
    )
    args.private_key.write_bytes(pem)
    print(f"Private key written to {args.private_key} (encrypted).")
    print("Add this to the server .env:")
    print(f"AI_SERVER_UPDATE_PUBLIC_KEYS={base64.b64encode(_public_raw(key)).decode('ascii')}")
    return 0


def build(args: argparse.Namespace) -> int:
    payload = args.payload.read_bytes()
    manifest = {
        "format_version": release_bundle.FORMAT_VERSION,
        "release_id": args.release_id,
        "version": args.version,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requires_data_migration": False,
        "payload": {
            "type": release_bundle.PAYLOAD_TYPE,
            "filename": release_bundle.PAYLOAD_NAME,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        },
    }
    try:
        release_bundle._validate_manifest(manifest)
    except release_bundle.BundleError as error:
        raise SystemExit(f"Invalid release metadata: {error}")
    manifest_bytes = release_bundle.canonical_json(manifest)
    key = serialization.load_pem_private_key(
        args.private_key.read_bytes(), password=_passphrase(confirm=False)
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("The signing key must be an Ed25519 key.")
    signature = base64.b64encode(key.sign(manifest_bytes))
    with tarfile.open(args.output, "w:") as outer:
        for name, data in (
            (release_bundle.MANIFEST_NAME, manifest_bytes),
            (release_bundle.SIGNATURE_NAME, signature),
            (release_bundle.PAYLOAD_NAME, payload),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o600
            outer.addfile(info, io.BytesIO(data))
    print(f"Wrote {args.output} ({args.output.stat().st_size} bytes), signer "
          f"{release_bundle.key_fingerprint(_public_raw(key))}.")
    return 0


def verify(args: argparse.Namespace) -> int:
    trusted = (release_bundle.decode_public_key(args.public_key),)
    with tempfile.TemporaryDirectory(prefix="ai-server-verify-") as staging:
        try:
            record = release_bundle.verify_and_stage(
                args.bundle,
                staging_dir=Path(staging) / "staging",
                trusted_keys=trusted,
                expiry_seconds=60,
            )
        except release_bundle.BundleError as error:
            print(f"REJECTED: {error}")
            return 1
    print(f"OK: {record['release_id']} v{record['version']} signer {record['signer']} "
          f"sha256 {record['payload_sha256']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("keygen")
    gen.add_argument("private_key", type=Path)
    gen.set_defaults(handler=keygen)
    make = commands.add_parser("build")
    make.add_argument("--payload", type=Path, required=True)
    make.add_argument("--release-id", required=True)
    make.add_argument("--version", required=True)
    make.add_argument("--private-key", type=Path, required=True)
    make.add_argument("--output", type=Path, required=True)
    make.set_defaults(handler=build)
    check = commands.add_parser("verify")
    check.add_argument("bundle", type=Path)
    check.add_argument("--public-key", required=True)
    check.set_defaults(handler=verify)
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
