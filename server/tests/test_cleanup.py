import secrets
from datetime import timedelta

import pytest

from studio.cleanup import cleanup_expired
from studio.models import BrowserSession, OnboardingProfile, User, utcnow
from studio.security import token_hash


@pytest.mark.postgres
def test_cleanup_removes_expired_draft_without_deleting_profile(db_factory, answers):
    with db_factory() as db:
        user = User(name="Fixture", is_demo=True)
        db.add(user)
        db.flush()
        profile = OnboardingProfile(user_id=user.id, answers=answers)
        expired = BrowserSession(
            token_hash=token_hash(secrets.token_urlsafe(32)),
            draft=answers,
            expires_at=utcnow() - timedelta(seconds=1),
        )
        current = BrowserSession(
            token_hash=token_hash(secrets.token_urlsafe(32)),
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=1),
        )
        db.add_all([profile, expired, current])
        db.commit()
        result = cleanup_expired(db)
        assert result["sessions_removed"] == 1
        assert db.get(BrowserSession, expired.token_hash) is None
        assert db.get(BrowserSession, current.token_hash) is not None
        assert db.get(OnboardingProfile, user.id).answers == answers
