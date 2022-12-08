from os import getenv

import redis

cookie_secret = str(getenv("SPOTIPY_CLIENT_SECRET"))


def redis_client() -> redis.Redis:
    c = redis.Redis().from_url(
        url=getenv('REDIS_URL'),
        decode_responses=True,
    )
    c.ping()
    return c


def redis_session_data_key(sid: str) -> str:
    return 'swa-session-data-{}'.format(sid)


def http_server_info() -> tuple:
    return getenv("LISTEN_IP", '127.0.1.1'), getenv("PORT", '8080')


def is_prod() -> bool:
    return getenv('APP_ENV', 'Dev') == 'Prod'
