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
    """
    Immutable class to store user data.

    :param data: The session data as a dictionary. If not provided, an empty dictionary is used.
    """

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
        """
        Returns all the session data as a dictionary.
        """
        return self._data

    @classmethod
    def from_json(cls, json_str: str) -> SessionData:
        """
        Returns a new `SessionData` instance from the given JSON string.

        :param json_str: The JSON string to convert to `SessionData`.
        :return: The new `SessionData` instance.
        """
        data = json.loads(json_str)
        return cls(data=data)

    def to_json(self) -> str:
        """
        Converts the `SessionData` instance to a JSON string.
        """
        return json.dumps(self._data)


def session_start() -> str:
    """
    Starts a session, setting the data in Redis.

    :return: The session ID for the new session.
    """
    session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    bottle.response.set_cookie('SID', session_id, secret=cookie_secret, path='/', httponly=True)
    redis_key = redis_session_data_key(session_id)
    redis_data = SessionData({'id': session_id}).to_json()
    redis_client().set(name=redis_key, value=redis_data)

    return session_id


def session_get_id(auto_start: bool = True) -> Union[str, None]:
    """
    Returns the session ID for the current session.

    :param auto_start: If True (the default), a new session will be started if no session is currently active.
    :return: The session ID for the current session, or None if no session is active and `auto_start` is False.
    """
    session_id = bottle.request.get_cookie('SID')
    if session_id is None:
        return session_start() if auto_start else None

    return str(session_id)


def session_get_data(session_id=None) -> SessionData:
    """
    Returns the SessionData instance for the current session or the given session ID.

    :param session_id: The session ID to get the data for. If not provided, the current session ID will be used.
    :return: The `SessionData` instance for the current or given session.
    :raises RuntimeError: If no session is active and no `session_id` is provided.
    """
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
    """
    Sets the session data for the current or given session.

    :param data: The `SessionData` instance to set for the session.
    :param session_id: The session ID to set the data for. If not provided, the current session ID will be used.
    :return: True if the data was successfully set, or False otherwise.
    :raises RuntimeError: If no session is active and no `session_id` is provided.
    """
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

def session_get_oauth_token() -> Tuple[SessionData, str]:
    """
    Returns the SessionData instance and OAuth token for the current session.

    :return: A tuple containing the `SessionData` instance and OAuth token for the current session.
    :raises HTTPError: If no session is active or no OAuth token is available for the current session.
    """
    try:
        session_data = session_get_data()
        # Try to get the token from cache.
        token = access_token(email=session_data.email)
        if not token:
            bottle.redirect('/login?message=no-auth')

        return session_data, token
    except RuntimeError:
        return bottle.redirect('/login?message=no-session')
