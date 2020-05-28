from __future__ import annotations

import json
import logging
import random
import string

import bottle

from swa.spotifyoauthredis import access_token
from swa.utils import redis_client, redis_session_data_key

cookie_secret = 'TODO'


class SessionData:
    """Immutable class to store user data"""

    def __init__(self, data=None):
        if data is None:
            data = {}
        self._data = data

    def __getattr__(self, key):
        if key in self._data:
            return self._data[key]

        return None

    def add(self, key: str, value):
        _d = self._data
        _d[key] = value
        return self.__class__(data=_d)

    def all(self) -> dict:
        return self._data

    @classmethod
    def from_json(cls, json_str: str) -> SessionData:
        data = json.loads(json_str)
        return cls(data=data)

    def to_json(self) -> str:
        return json.dumps(self._data)


def session_start() -> str:
    """
    Starts a session, setting the data in Redis
    """
    session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    bottle.response.set_cookie('SID', session_id, secret=cookie_secret, path='/', httponly=True)
    redis_key = redis_session_data_key(session_id)
    redis_data = SessionData({'id': session_id}).to_json()
    redis_client().set(name=redis_key, value=redis_data)

    return session_id


def session_get_id(auto_start: bool = True) -> str or None:
    """Will return a session identifier, auto-starting a session when required."""
    session_id = bottle.request.get_cookie('SID')
    if session_id is None:
        return session_start() if auto_start else None

    return str(session_id)


def session_get_data(session_id=None) -> SessionData:
    if not session_id:
        session_id = session_get_id(auto_start=False)

    if not session_id:
        raise RuntimeError('No valid session and no session_id provided!')

    redis_data = redis_client().get(redis_session_data_key(session_id))
    logging.debug("Session data: ", end=" ")
    logging.debug({session_id: redis_data})
    if redis_data:
        return SessionData.from_json(redis_data)

    return SessionData()


def session_set_data(data: SessionData, session_id: str = None) -> bool:
    if not session_id:
        session_id = session_get_id(False)

    if not session_id:
        raise RuntimeError('No valid session and no session_id provided!')

    redis_key = redis_session_data_key(session_id)
    redis_data = data.to_json()
    logging.debug("Set session data: ", end=" ")
    logging.debug({session_id: redis_data})
    if not redis_client().set(name=redis_key, value=redis_data):
        return False

    return True


def session_get_oauth_token() -> (SessionData, str):
    try:
        session_data = session_get_data()
        # Try to get the token from cache.
        token = access_token(email=session_data.email)
        if not token:
            bottle.redirect('/login?message=no-auth')

        return session_data, token
    except RuntimeError:
        return bottle.redirect('/login?message=no-session')
