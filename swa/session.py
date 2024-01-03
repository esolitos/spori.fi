
"""
A module to manage user sessions.

This module provides classes and functions to manage user sessions. It now supports storing the data in Redis,
and falls back to file-based storage when REDIS_URL is not provided.
"""

from __future__ import annotations
import json
import logging
import random
import string
import os
from typing import Optional

import bottle
from swa.spotifyoauthredis import access_token
from swa.utils import redis_client, redis_session_data_key

COOKIE_SECRET = str(os.getenv("SPOTIPY_CLIENT_SECRET", "default"))

# File-based storage directory
FILE_STORAGE_PATH = './session_data'


def is_redis_enabled() -> bool:
    """
    Check if Redis is enabled by looking for REDIS_URL.
    Returns True if REDIS_URL is set, False otherwise.
    """
    return 'REDIS_URL' in os.environ


def get_file_storage_path(session_id: str) -> str:
    return os.path.join(FILE_STORAGE_PATH, f'{session_id}.json')


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
        """Adds data to the session

        Args:
            key (str): Data identifier
            value (any): The data

        Returns:
            self: Self
        """
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
    session_id = ''.join(random.choices(
        string.ascii_letters + string.digits, k=16))
    bottle.response.set_cookie('SID', session_id, secret=COOKIE_SECRET)

    # Initialize empty session data
    if not is_redis_enabled():
        os.makedirs(FILE_STORAGE_PATH, exist_ok=True)
        with open(get_file_storage_path(session_id), 'w') as file:
            json.dump({}, file)

    return session_id


def session_get_id(auto_start: bool = True) -> str | None:
    """
    Returns the session ID for the current session.

    :param auto_start: If True (the default), a new session will be started if necesary.
    :return: The session ID or None if no session is active and `auto_start` is False.
    """
    session_id = bottle.request.get_cookie('SID', secret=COOKIE_SECRET)
    if session_id is None:
        return session_start() if auto_start else None

    return str(session_id)


def session_get_data(session_id: str = None) -> SessionData:
    if not session_id:
        session_id = session_get_id(auto_start=False)

    if not session_id:
        raise RuntimeError('No valid session and no session_id provided!')

    if is_redis_enabled():
        redis_data = redis_client().get(redis_session_data_key(session_id))
        if redis_data:
            return SessionData.from_json(redis_data)
    else:
        try:
            with open(get_file_storage_path(session_id), 'r') as file:
                return SessionData(json.load(file))
        except FileNotFoundError:
            return SessionData()

    return SessionData()


def session_set_data(data: SessionData, session_id: str = None) -> bool:
    if not session_id:
        session_id = session_get_id(False)

    if not session_id:
        raise RuntimeError('No valid session and no session_id provided!')

    if is_redis_enabled():
        redis_key = redis_session_data_key(session_id)
        redis_data = data.to_json()
        return redis_client().set(name=redis_key, value=redis_data)
    else:
        os.makedirs(FILE_STORAGE_PATH, exist_ok=True)
        with open(get_file_storage_path(session_id), 'w') as file:
            json.dump(data.all(), file)
        return True


def session_get_oauth_token() -> tuple(SessionData, str):
    """
    Returns the SessionData instance and OAuth token for the current session.

    :return: A tuple containing the `SessionData` instance and OAuth token for the session.
    :raises HTTPError: If no session is active or OAuth token is unavailable for the session.
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
