# pylint: disable=E1101
"""
This module defines the routes for the web application.

It contains functions for rendering the pages for the index, login, login success and error,
as well as for handling the redirect from Spotify after authorization, copying tracks from
Discover Weekly to the user's playlist,
and displaying the page for manual selection of the playlist to copy tracks from.
"""
import logging
import os
import re
import sys

import bottle

import swa.session as sws
import swa.spotifyoauthredis as swoauth
import swa.spotify_weekly as sw
import swa.utils as swutil

@bottle.get('/')
@bottle.jinja2_view('index.html.j2')
def index():
    """Renders the index page."""
    return {}


@bottle.get('/login')
@bottle.jinja2_view('login.html.j2')
def login():
    """Renders the login page and checks for cached access tokens."""
    session_data = sws.session_get_data(sws.session_get_id(auto_start=True))

    # Try to get the token from cache.
    if session_data.email and swoauth.access_token(email=session_data.email):
        bottle.redirect('/login/success')

    return {
        'email':       session_data.email or '',
        'message_key': bottle.request.params.get('message') or False,
    }


@bottle.post('/login')
def do_login():
    """Handles user login and redirects to Spotify authorization page."""
    session_id = sws.session_get_id(auto_start=True)
    email = str(bottle.request.forms.get('email'))
    session_data = sws.session_get_data(session_id).add('email', email)
    logging.debug(session_data)
    sws.session_set_data(session_data)

    bottle.redirect(swoauth.spotify_oauth(email).get_authorize_url())


@bottle.route('/oauth/callback', method=('GET', 'POST'))
def oauth_callback():
    """Handles the redirect from Spotify after authorization and stores the tokens in cache."""
    error = bottle.request.params.get('error')
    if error is not None:
        return bottle.redirect(f'/login/error?error={error}')

    session_id = sws.session_get_id(auto_start=False)
    if not session_id:
        return bottle.redirect('/login?message=no-session')

    session_data = sws.session_get_data(session_id)
    if not session_data.email:
        return bottle.redirect('/login?message=no-email')

    code = bottle.request.params.get('code')
    token = swoauth.spotify_oauth(session_data.email).get_access_token(
        code,
        as_dict=False,
        check_cache=False
    )

    path = 'success' if token else 'error'
    return bottle.redirect(f"/login/{path}")


@bottle.get('/login/success')
@bottle.jinja2_view('login-success.html.j2')
def login_success():
    """Renders the page after successful login and retrieves the access token from cache."""
    (session_data,) = sws.session_get_oauth_token()
    return {
        'username': session_data.email
    }


@bottle.get('/login/error')
@bottle.jinja2_view('login-error.html.j2')
def login_error():
    """Renders the page if there is an error during login."""
    return {}


@bottle.get('/run')
def run():
    """Runs the main program to copy tracks from Discover Weekly to the user's playlist."""
    (session_data, token) = sws.session_get_oauth_token()
    try:
        sw.SwaRunner(sw.Spotify(auth=token), session_data.playlist_id).run()
        bottle.redirect('/run/finished')
    except sw.DiscoverWeeklyError:
        bottle.redirect('/run/manual-selection')


@bottle.get('/run/manual-selection')
@bottle.jinja2_view('run-manual-selection.html.j2')
def run_manual_selection():
    """Renders the page for manual selection of the playlist to copy tracks from."""
    (_, token) = sws.session_get_oauth_token()
    swa = sw.SwaRunner(sw.Spotify(auth=token))
    user = swa.get_user()
    try:
        playlists = {'Spotify': swa.get_discover_weekly(allow_multiple=True)}
    except sw.DiscoverWeeklyError:
        playlists = swa.get_user_playlists(sort_by_author=True)

    return {
        'user':      user,
        'playlists': playlists,
    }


@bottle.post('/run/manual-selection')
# @bottle.jinja2_view('run-manual-selection.html.j2')
def do_run_manual_selection():
    """
    Handles the selection of the playlist to copy tracks from and runs the main program.
    """
    (session_data, _) = sws.session_get_oauth_token()

    playlist_id = str(bottle.request.forms.get('playlist_id'))
    if playlist_id == '_':
        playlist_address = str(bottle.request.forms.get('playlist_id_text'))
        playlist_id = extract_playlist_id(playlist_address)

    sws.session_set_data(session_data.add('playlist_id', playlist_id))
    return bottle.redirect('/run')


def extract_playlist_id(addr: str) -> str or None:
    """
    Given a Spotify URI or URL, this function returns the corresponding playlist ID if matched.

    :param addr: A Spotify URI or URL. Accepted formats:
        - "https://open.spotify.com/playlist/<playlist_id>"
        - "spotify:playlist:<playlist_id>"
    :return: The playlist ID if matched, or None if no match was found.
    """
    if addr.startswith('http'):
        return extract_playlist_id_from_url(addr)

    if addr.startswith('spotify'):
        return extract_playlist_id_from_uri(addr)

    return bottle.redirect('/run/manual-selection?error')


def extract_playlist_id_from_url(url: str) -> str or None:
    """
    Extracts the playlist ID from a Spotify URL.

    Args:
        url (str): The Spotify URL to extract the playlist ID from.
            The URL must have the format "https://open.spotify.com/playlist/<playlist_id>".
            The URL may optionally contain additional query parameters after the playlist ID.

    Returns:
        str or None: The playlist ID if it is found in the URL, otherwise None.
    """
    id_regex = re.compile(r"^https?://open\.spotify\.com/playlist/(\w+)\??")
    match = id_regex.match(url)
    return match.groups()[0] if match else None


def extract_playlist_id_from_uri(uri: str) -> str or None:
    """
    Extracts the playlist ID from a Spotify URI.

    Args:
        uri (str): The Spotify URI to extract the playlist ID from.
            The URI must have the format "spotify:playlist:<playlist_id>".

    Returns:
        str or None: The playlist ID if it is found in the URI, otherwise None.
    """
    id_regex = re.compile(r"^spotify:playlist:(\w+)$")
    match = id_regex.match(uri)
    return match.groups()[0] if match else None


@bottle.get('/run/finished')
@bottle.jinja2_view('finished.html.j2')
def run_finished():
    """
    Handles the page to show when the process is complete.
    """
    session_data = sws.session_get_data()
    return {
        'username': session_data.email
    }


@bottle.get('/page/<name>')
def static_pages(name: str):
    """
    Serves static pages simply stored as html files.
    """
    return bottle.static_file(
        filename=name + '.html',
        root='public/pages',
        mimetype='text/html',
        download=False,
    )


@bottle.get('/assets/<filename:path>')
def static_assets(filename: str):
    """
    Serves static assets stored public files.
    """
    return bottle.static_file(
        filename=filename,
        root='public/assets',
    )


def check_requirements():
    """
    Checks if all requirements are met or quits.
    """
    required_vars = [
        "SPOTIPY_CLIENT_ID",
        "SPOTIPY_CLIENT_SECRET",
        "SPOTIPY_REDIRECT_URI",
        "REDIS_URL",
    ]
    for var in required_vars:
        if var not in os.environ:
            print(f"Error: {var} environment variable is not defined", file=sys.stderr)
            sys.exit(1)


def main():
    """
    Main function
    """
    server_host, server_port = swutil.http_server_info()
    enable_debug = bool(os.getenv('DEBUG'))
    check_requirements()
    bottle.run(
        host=server_host, port=server_port,
        debug=enable_debug, reloader=(not swutil.is_prod())
    )


if __name__ == '__main__':
    main()
