"""Remote Desktop logins also own legacy Bot Chats stored with the TUI source label."""
import pytest

from gateway.session_identity import authenticated_subject
from hermes_state_local_migration import login_owned_by, validate_legacy_row
from tests.gateway import test_legacy_stamped_bot_chat as legacy_chat


_LOGIN = authenticated_subject({'provider': 'basic', 'user_id': 'alice'})


@pytest.mark.asyncio
@pytest.mark.parametrize('source', ['desktop', 'tui'])
async def test_login_opens_its_legacy_bot_chat(tmp_path, monkeypatch, source):
    monkeypatch.setattr(legacy_chat, '_OWN', _LOGIN)
    replies = await legacy_chat._bot_chat_lookup(tmp_path, monkeypatch, source, 'basic:alice')
    for profile, reply in replies.items():
        assert 'error' not in reply, (profile, reply)
        assert [session.get('id') or session.get('session_id')
                for session in reply['result']['sessions']] == [profile + '-bot-chat']


@pytest.mark.parametrize('source', ['desktop', 'tui'])
@pytest.mark.parametrize('identity', [
    {'provider': 'basic', 'user_id': 'bob'},
    {'provider': 'oidc', 'user_id': 'alice'},
    {'provider': 'basic', 'issuer': 'other', 'user_id': 'alice'},
])
def test_other_login_does_not_own_stamped_history(source, identity):
    row = {'source': source, 'user_id': 'basic:alice'}
    assert not login_owned_by(row, authenticated_subject(identity))


@pytest.mark.parametrize('subject', [None, 'uid:1000', 'basic:alice'])
def test_native_or_unverified_label_cannot_claim_tui_login(subject):
    assert not login_owned_by({'source': 'tui', 'user_id': 'basic:alice'}, subject)


@pytest.mark.parametrize('source', ['cli', 'api_server', 'telegram', 'tool'])
def test_login_stamp_exception_stays_on_desktop_surfaces(source):
    assert not login_owned_by({'source': source, 'user_id': 'basic:alice'}, _LOGIN)


def test_matching_login_validates_unrouted_tui_history(tmp_path):
    from hermes_state import SessionDB
    db = SessionDB(db_path=tmp_path / 'state.db')
    try:
        db.create_session('legacy-tui', source='tui', user_id='basic:alice')
        validate_legacy_row(db, db.get_session('legacy-tui'), subject=_LOGIN)
    finally:
        db.close()
