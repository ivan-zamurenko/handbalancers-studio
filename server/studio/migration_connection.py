def migration_owner_username_matches(username: str | None, project_ref: str | None) -> bool:
    return username == "migration_owner" or (
        bool(project_ref) and username == f"migration_owner.{project_ref}"
    )
