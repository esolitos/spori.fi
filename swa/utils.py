from os import getenv

import bottle
import redis

cookie_secret = str(getenv("SPOTIPY_CLIENT_SECRET"))


def redis_client() -> redis.Redis:
    c = redis.Redis().from_url(
        url=getenv('REDISCLOUD_URL'),
        decode_responses=True,
    )
    # Test connection
    c.ping()
    return c


def redis_session_data_key(sid: str) -> str:
    return 'swa-session-data-{}'.format(sid)


def http_server_info() -> tuple:
    return getenv("LISTEN_IP", '127.0.1.1'), getenv("PORT", '8080')


def is_debug_mode() -> bool:
    return bool(getenv('DEBUG', False))


def is_prod() -> bool:
    return getenv('APP_ENV', 'Dev') == 'Prod'


def debug_log(message, **kwargs):
    """
    If debug mode is enable will print the passed message/object.

    :param message: Any string, object or primitive.
    """
    if not is_debug_mode():
        return

    if type(message) == str:
        print(message, **kwargs)
    else:
        from pprint import pprint
        pprint(message, **kwargs)
