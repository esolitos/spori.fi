import logging
import os
import re
import sys

from swa.spotifyoauthredis import *
from swa.utils import *
from swa.session import *
from swa.spotify_weekly import *


@bottle.get('/')
@bottle.jinja2_view('index.html.j2')
def index():
    return {}


@bottle.get('/login')
@bottle.jinja2_view('login.html.j2')
def login():
    session_data = session_get_data(session_get_id(auto_start=True))

    # Try to get the token from cache.
    if session_data.email and access_token(email=session_data.email):
        bottle.redirect('/login/success')

    return {
        'email':       session_data.email or '',
        'message_key': bottle.request.params.get('message') or False,
    }


@bottle.post('/login')
def do_login():
    session_id = session_get_id(auto_start=True)
    email = str(bottle.request.forms.get('email'))
    session_data = session_get_data(session_id).add('email', email)
    logging.debug(session_data)
    session_set_data(session_data)

    bottle.redirect(spotify_oauth(email).get_authorize_url())


@bottle.route('/oauth/callback', method=('GET', 'POST'))
def oauth_callback():
    error = bottle.request.params.get('error')
    if error is not None:
        return bottle.redirect('/login/error?error=%s'.format(error))

    session_id = session_get_id(auto_start=False)
    if not session_id:
        return bottle.redirect('/login?message=no-session')

    session_data = session_get_data(session_id)
    if not session_data.email:
        return bottle.redirect('/login?message=no-email')

    code = bottle.request.params.get('code')
    token = spotify_oauth(session_data.email).get_access_token(code, as_dict=False, check_cache=False)
    if token:
        bottle.redirect('/login/success')
    else:
        bottle.redirect('/login/error')


@bottle.get('/login/success')
@bottle.jinja2_view('login-success.html.j2')
def login_success():
    (session_data, token) = session_get_oauth_token()
    return {
        'username': session_data.email
    }


@bottle.get('/login/error')
@bottle.jinja2_view('login-error.html.j2')
def login_error():
    return {}


@bottle.get('/run')
def run():
    (session_data, token) = session_get_oauth_token()
    try:
        SwaRunner(Spotify(auth=token), session_data.playlist_id).run()
        bottle.redirect('/run/finished')
    except DiscoverWeeklyError:
        bottle.redirect('/run/manual-selection')


@bottle.get('/run/manual-selection')
@bottle.jinja2_view('run-manual-selection.html.j2')
def run_manual_selection():
    (session_data, token) = session_get_oauth_token()
    swa = SwaRunner(Spotify(auth=token))
    user = swa.get_user()
    try:
        playlists = {'Spotify': swa.get_discover_weekly(allow_multiple=True)}
    except DiscoverWeeklyError:
        playlists = swa.get_user_playlists(sort_by_author=True)

    return {
        'user':      user,
        'playlists': playlists,
    }


@bottle.post('/run/manual-selection')
# @bottle.jinja2_view('run-manual-selection.html.j2')
def do_run_manual_selection():
    (session_data, token) = session_get_oauth_token()

    playlist_id = str(bottle.request.forms.get('playlist_id'))
    if playlist_id == '_':
        playlist_address = str(bottle.request.forms.get('playlist_id_text'))
        playlist_id = extract_playlist_id(playlist_address)

    session_set_data(session_data.add('playlist_id', playlist_id))
    return bottle.redirect('/run')


def extract_playlist_id(addr: str) -> str or None:
    """
    Given a Spotify URI or ORL will return a playlist ID, if matched.
    Accepted formats:
      - https://open.spotify.com/playlist/37i9dQZF1DWWGFQLoP9qlv?si=4WX0XtWXTu-7EJ7eGaMPJg
      - spotify:playlist:3a4B7fTavHoTR6bvMfXKMk

    :param addr:
    :return:
    """
    if addr.startswith('http'):
        return extract_playlist_id_from_url(addr)
    elif addr.startswith('spotify'):
        return extract_playlist_id_from_uri(addr)
    else:
        bottle.redirect('/run/manual-selection?error')


def extract_playlist_id_from_url(url: str) -> str or None:
    # https://open.spotify.com/playlist/37i9dQZF1DWWGFQLoP9qlv?si=4WX0XtWXTu-7EJ7eGaMPJg
    id_regex = re.compile(r"^https?://open\.spotify\.com/playlist/(\w+)\??")
    match = id_regex.match(url)
    return match.groups()[0] if match else None


def extract_playlist_id_from_uri(uri: str) -> str or None:
    # spotify:playlist:3a4B7fTavHoTR6bvMfXKMk
    id_regex = re.compile(r"^spotify:playlist:(\w+)$")
    match = id_regex.match(uri)
    return match.groups()[0] if match else None


@bottle.get('/run/finished')
@bottle.jinja2_view('finished.html.j2')
def run_finished():
    session_data = session_get_data()
    return {
        'username': session_data.email
    }


@bottle.get('/page/<name>')
def static_pages(name: str):
    return bottle.static_file(
        filename=name + '.html',
        root='public/pages',
        mimetype='text/html',
        download=False,
    )


@bottle.get('/assets/<filename:path>')
def static_assets(filename: str):
    return bottle.static_file(
        filename=filename,
        root='public/assets',
    )


def check_requirements():
    required_vars = [
        "SPOTIPY_CLIENT_ID",
        "SPOTIPY_CLIENT_SECRET",
        "SPOTIPY_REDIRECT_URI",
        "REDIS_URL",
    ]
    for var in required_vars:
        if var not in os.environ:
            print(f"Error: {var} environment variable is not defined", file=sys.stderr)
            exit(1)


def main():
    server_host, server_port = http_server_info()
    enable_debug = bool(getenv('DEBUG', False))
    check_requirements()
    bottle.run(
        host=server_host, port=server_port,
        debug=enable_debug, reloader=(not is_prod())
    )


if __name__ == '__main__':
    main()
