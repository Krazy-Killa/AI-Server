"""Local command-line management for dashboard accounts and Proxmox roles."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from auth import AuthStore, ROLES
from config import settings


def _confirmed_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match.")
    return password


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="Create a local dashboard account.")
    create.add_argument("--username", required=True)
    create.add_argument("--role", required=True, choices=ROLES)

    reset = commands.add_parser("reset-password", help="Reset a local account password.")
    reset.add_argument("--username", required=True)

    set_role = commands.add_parser("set-role", help="Change a local account role.")
    set_role.add_argument("--username", required=True)
    set_role.add_argument("--role", required=True, choices=ROLES)

    for command, help_text in (
        ("disable-user", "Disable a local account and revoke its sessions."),
        ("enable-user", "Enable a previously disabled local account."),
    ):
        account = commands.add_parser(command, help=help_text)
        account.add_argument("--username", required=True)

    commands.add_parser("list-users", help="List local accounts and roles.")

    map_user = commands.add_parser(
        "map-proxmox", help="Explicitly map a Proxmox identity to a dashboard role."
    )
    map_user.add_argument("--username", required=True)
    map_user.add_argument("--role", required=True, choices=ROLES)

    unmap_user = commands.add_parser(
        "unmap-proxmox", help="Remove a Proxmox mapping and revoke its sessions."
    )
    unmap_user.add_argument("--username", required=True)
    commands.add_parser("list-proxmox", help="List explicit Proxmox role mappings.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = AuthStore(settings.auth_database_path)
    try:
        if args.command == "create-user":
            store.create_local_user(args.username, _confirmed_password(), args.role)
            print(f"Created local {args.role} account {args.username.strip()}.")
        elif args.command == "reset-password":
            store.set_local_password(args.username, _confirmed_password())
            print(f"Password reset for {args.username.strip()}; existing sessions revoked.")
        elif args.command == "set-role":
            store.set_local_role(args.username, args.role)
            print(f"Updated role for {args.username.strip()}; existing sessions revoked.")
        elif args.command == "disable-user":
            store.set_local_disabled(args.username, True)
            print(f"Disabled {args.username.strip()} and revoked its sessions.")
        elif args.command == "enable-user":
            store.set_local_disabled(args.username, False)
            print(f"Enabled {args.username.strip()}.")
        elif args.command == "list-users":
            print(json.dumps(store.list_local_users(), indent=2))
        elif args.command == "map-proxmox":
            store.map_proxmox_user(args.username, args.role)
            print(f"Mapped {args.username.strip()} to {args.role}.")
        elif args.command == "unmap-proxmox":
            store.unmap_proxmox_user(args.username)
            print(f"Removed mapping for {args.username.strip()}; sessions revoked.")
        elif args.command == "list-proxmox":
            print(json.dumps(store.list_proxmox_mappings(), indent=2))
    except (ValueError, RuntimeError) as error:
        print(f"Authentication administration failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
