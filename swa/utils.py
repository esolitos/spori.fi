"""
Module containing utility functions used by the main application.
"""
from os import getenv
import redis

COOKIE_SECRET = str(getenv("SPOTIPY_CLIENT_SECRET", "default"))

def redis_client() -> redis.Redis:
    """
    Returns a Redis client instance.
    """
    rclient = redis.Redis().from_url(
        url=getenv('REDIS_URL'),
        decode_responses=True,
    )
    rclient.ping()
    return rclient

def redis_session_data_key(sid: str) -> str:
    """
    Returns a Redis key for the session data with the given session ID.

    :param sid: The session ID.
    :return: The Redis key for the session data.
    """
    return f'swa-session-data-{sid}'

def http_server_info() -> tuple:
    """
    Returns the IP address and port number that the HTTP server should listen on.
    """
    return getenv("LISTEN_IP", '127.0.1.1'), getenv("PORT", '8080')

def is_prod() -> bool:
    """
    Returns True if the application is running in production, or False for any other environment.
    """
    return getenv('APP_ENV', 'Dev') == 'Prod'
