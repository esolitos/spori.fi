from os import getenv
import redis

cookie_secret = str(getenv("SPOTIPY_CLIENT_SECRET"))

def redis_client() -> redis.Redis:
    """
    Returns a Redis client instance.
    """
    c = redis.Redis().from_url(
        url=getenv('REDIS_URL'),
        decode_responses=True,
    )
    c.ping()
    return c

def redis_session_data_key(sid: str) -> str:
    """
    Returns a Redis key for the session data with the given session ID.

    :param sid: The session ID.
    :return: The Redis key for the session data.
    """
    return 'swa-session-data-{}'.format(sid)

def http_server_info() -> tuple:
    """
    Returns the IP address and port number that the HTTP server should listen on.
    """
    return getenv("LISTEN_IP", '127.0.1.1'), getenv("PORT", '8080')

def is_prod() -> bool:
    """
    Returns True if the application is running in production mode, or False if it is running in development mode.
    """
    return getenv('APP_ENV', 'Dev') == 'Prod'
