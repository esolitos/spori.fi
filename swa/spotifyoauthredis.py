import json
import logging
from os import getenv

import spotipy

from swa.utils import http_server_info, redis_client

oauth_grants = "playlist-read-private playlist-modify-public playlist-modify-private"


class UserDataStorage:
    """
    Redis based data storage.
    """
    _key_prefix = 'swa-user'
    _client = redis_client()

    @classmethod
    def _redis_key(cls, name: str) -> str:
        """
        Builds a key used for storage in the redis DB.

        :param name: The plain key string.
        :return: The actual key, including prefix.
        """
        return '-'.join((cls._key_prefix, name))

    @classmethod
    def get_user_data(cls, email: str):
        redis_data = cls._client.get(cls._redis_key(email))
        if redis_data is None:
            redis_data = {}
        elif type(redis_data) is str:
            redis_data = json.loads(redis_data)

        return redis_data

    @classmethod
    def store_user_data(cls, email: str, data: dict):
        if 'email' not in data:
            data['email'] = email

        return cls._client.set(
            name=cls._redis_key(email),
            value=json.dumps(data),
        )


class SpotifyOauthRedis(spotipy.SpotifyOAuth):
    """Extends SpotifyOAuth using Redis as backend storage"""

    def __init__(self, username: str,
                 client_id=None, client_secret=None, redirect_uri=None, state=None, scope=None, proxies=None,
                 show_dialog=False, requests_session=True, requests_timeout=None):
        super(SpotifyOauthRedis, self).__init__(client_id, client_secret, redirect_uri, state, scope, None, username,
                                                proxies, show_dialog, requests_session, requests_timeout)
        self.username = username
        self._redis = UserDataStorage()

    def _redis_get_user_token(self) -> dict or None:
        redis_data = self._redis.get_user_data(self.username)
        if redis_data and 'oauth_token' in redis_data:
            return dict(redis_data['oauth_token'])

        return None

    def _redis_store_user_token(self, token_info: dict):
        redis_data = self._redis.get_user_data(self.username)
        redis_data['oauth_token'] = token_info
        self._redis.store_user_data(self.username, redis_data)

    def get_cached_token(self):
        token_info = self._redis_get_user_token()
        # if scopes don't match, then bail
        if (not token_info
                or "scope" not in token_info
                or not self._is_scope_subset(self.scope, token_info["scope"])):
            return None

        if self.is_token_expired(token_info):
            token_info = self.refresh_access_token(token_info["refresh_token"])

        return token_info

    def _save_token_info(self, token_info):
        self._redis_store_user_token(token_info)


def spotify_oauth(email: str) -> SpotifyOauthRedis:
    if not email:
        raise RuntimeError('Email parameter is mandatory.')

    client_id = getenv("SPOTIPY_CLIENT_ID")
    client_secret = getenv("SPOTIPY_CLIENT_SECRET")
    hostname = str(getenv('REDIRECT_HOST', "%s:%s" % http_server_info()))
    redirect_url = 'http://%s/oauth/callback' % hostname

    return SpotifyOauthRedis(
        username=email,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_url,
        scope=oauth_grants,
    )


def access_token(email: str) -> str or None:
    tokens = spotify_oauth(email).get_cached_token()
    logging.debug('Cached tokens:')
    logging.debug(tokens)
    if (not tokens) or ('access_token' not in tokens):
        return None

    return str(tokens['access_token'])
