from os import getenv

from bottle import route, run, redirect, request, post, Bottle, ServerAdapter, get
from spotipy import SpotifyOAuth, Spotify

oauth_grants = "playlist-read-private playlist-modify-public playlist-modify-private"


def _sp_oauth() -> SpotifyOAuth:
    client_id = getenv("SPOTIPY_CLIENT_ID")
    client_secret = getenv("SPOTIPY_CLIENT_SECRET")

    server_host = getenv("SERVER_HOST")
    server_port = getenv("SERVER_PORT")

    return SpotifyOAuth(
        client_id,
        client_secret,
        cache_path='.cache-spotify-oauth',
        redirect_uri="http://%s:%s/success" % (server_host, server_port),
        scope=oauth_grants,
    )


def _get_access_token() -> str or None:
    tokens = _sp_oauth().get_cached_token()
    if not tokens or 'access_token' not in tokens:
        return None

    return tokens['access_token']


@get('/')
def _index():
    return '<p><center>You need to <a href="/login">log in using Spotify</a> to run this script.</center></p>'


@get('/login<:re:/?>')
def _login():
    sp_oauth = _sp_oauth()
    # Try to get the token from cache.
    if _get_access_token():
        redirect('/run')
    else:
        url = sp_oauth.get_authorize_url()
        redirect(url)


@get('/success<:re:/?>')
def _get_success():
    _oauth_return_endpoint()


@post('/success<:re:/?>')
def _post_success():
    _oauth_return_endpoint()


def _oauth_return_endpoint():
    code = request.params.get('code')
    token = _sp_oauth().get_access_token(code, as_dict=False, check_cache=False)
    if token:
        redirect('/run')
    else:
        return '<p>Could not get access token, <a href="/">try again.</a></p>'


@get('/run')
def _run():
    # Try to get the token from cache.
    token = _get_access_token()
    if not token:
        redirect('/login')

    from spotify_weekly import SwaRunner
    spotify_client = Spotify(auth=token)
    SwaRunner(spotify_client).run()
    redirect('/finished')


@get('/finished')
def _run():
    return '''
    <p>All done!</p>
    '''


def main():
    server_host = getenv("SERVER_HOST")
    server_port = getenv("SERVER_PORT")

    run(host=server_host, port=server_port)


if __name__ == '__main__':
    main()
