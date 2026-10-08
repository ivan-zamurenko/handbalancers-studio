"""Call before opening integration-test connections, including direct pytest runs."""

import os

from tools import local_stack


def require_test_database() -> None:
    local_stack.verify_test_target(
        app_env=os.environ.get("APP_ENV", ""),
        database_url=os.environ.get("DATABASE_URL", ""),
        supabase_url=os.environ.get("SUPABASE_URL", ""),
        project_id=os.environ.get("SUPABASE_PROJECT_ID", ""),
    )
