"""
This module contains functions for handling Spotify OAuth and cached access tokens.
"""

import logging
from os import getenv

import spotipy
import redis

from swa.utils import http_server_info

OAUTH_GRANTS = "playlist-read-private playlist-modify-public playlist-modify-private"

def spotify_oauth(email: str) -> spotipy.SpotifyOAuth:
    """
    Get a SpotifyOAuth object using the provided email.

    Args:
        email (str): The email address of the user.

    Returns:
        spotipy.SpotifyOAuth: A SpotifyOAuth object.

    Raises:
        RuntimeError: If the email parameter is not provided.
    """
    if not email:
        raise RuntimeError('Email parameter is mandatory.')

    client_id = getenv("SPOTIPY_CLIENT_ID")
    client_secret = getenv("SPOTIPY_CLIENT_SECRET")
    hostname = str(getenv('REDIRECT_HOST', ":".join(http_server_info())))
    redirect_url = f'http://{hostname}/oauth/callback'

    cache_handler = None
    if getenv('REDIS_URL') != None:
        rclient = redis.Redis().from_url(url=getenv('REDIS_URL'),decode_responses=True)
        cache_handler = spotipy.cache_handler.RedisCacheHandler(
            rclient,
            '-'.join(('swa-user', email)),
        )

    return spotipy.SpotifyOAuth(
        username=email,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_url,
        scope=OAUTH_GRANTS,
        cache_handler=cache_handler
    )


def access_token(email: str) -> str or None:
    """
    Get the cached access token for the provided email.

    Args:
        email (str): The email address of the user.

    Returns:
        str or None: The access token if found, otherwise None.
    """
    tokens = spotify_oauth(email).get_cached_token()
    logging.debug('Cached tokens:')
    logging.debug(tokens)
    if (not tokens) or ('access_token' not in tokens):
        return None

    return str(tokens['access_token'])
