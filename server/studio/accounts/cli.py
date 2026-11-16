"""Owner CLI: grant/revoke coach by verified auth UUID.

Authorization is possession of the operator database credential
(STUDIO_MIGRATION_DATABASE_URL), not knowledge of an email address.
Usage: python -m studio.accounts.cli grant-coach <auth_user_id> --actor <name>
"""

import argparse
import os
import sys
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from studio.accounts.roles import RoleChangeRejected, grant_coach, revoke_coach


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio.accounts.cli")
    parser.add_argument("command", choices=["grant-coach", "revoke-coach"])
    parser.add_argument("auth_user_id")
    parser.add_argument("--actor", required=True)
    args = parser.parse_args(argv)
    try:
        auth_user_id = UUID(args.auth_user_id)
    except ValueError:
        print("auth_user_id must be a Supabase auth UUID, not an email", file=sys.stderr)
        return 2
    url = os.environ.get("STUDIO_MIGRATION_DATABASE_URL")
    if not url:
        print("STUDIO_MIGRATION_DATABASE_URL is required", file=sys.stderr)
        return 2
    engine = create_engine(url, poolclass=NullPool, hide_parameters=True)
    action = grant_coach if args.command == "grant-coach" else revoke_coach
    try:
        with engine.begin() as conn:
            changed = action(conn, auth_user_id, actor=args.actor)
    except RoleChangeRejected as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print("changed" if changed else "unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
