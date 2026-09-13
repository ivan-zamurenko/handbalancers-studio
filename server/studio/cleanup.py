"""Remove expired transient data only: python -m studio.cleanup.

Schedule this daily in deployment. Profiles, users, memberships and payment records are retained.
"""

from sqlalchemy import delete

from studio.db import make_engine, make_session_factory
from studio.models import BrowserSession, OAuthAttempt, utcnow
from studio.settings import Settings


def cleanup_expired(db):
    now = utcnow()
    oauth = db.execute(delete(OAuthAttempt).where(OAuthAttempt.expires_at <= now)).rowcount
    sessions = db.execute(delete(BrowserSession).where(BrowserSession.expires_at <= now)).rowcount
    db.commit()
    return {"oauth_attempts_removed": oauth, "sessions_removed": sessions}


def main():
    engine = make_engine(Settings())
    try:
        with make_session_factory(engine)() as db:
            result = cleanup_expired(db)
            print(
                f"Removed expired sessions: {result['sessions_removed']}; OAuth attempts: {result['oauth_attempts_removed']}"
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
