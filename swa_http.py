from pprint import pprint

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
    return {
        'email':       session_data.email or '',
        'message_key': bottle.request.params.get('message') or False,
    }


@bottle.post('/login')
def do_login():
    session_id = session_get_id(auto_start=True)
    email = str(bottle.request.forms.get('email'))
    session_data = session_get_data(session_id).add('email', email)
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
    session_data = session_get_data()
    return {
        'username': session_data.email
    }


@bottle.get('/login/error')
@bottle.jinja2_view('login-error.html.j2')
def login_error():
    return {}


@bottle.get('/run')
def run():
    from spotipy import Spotify

    try:
        session_data = session_get_data()
    except RuntimeError:
        return bottle.redirect('/login?message=no-session')

    # Try to get the token from cache.
    token = access_token(email=session_data.email)
    if not token:
        bottle.redirect('/login?message=no-auth')

    spotify_client = Spotify(auth=token)
    SwaRunner(spotify_client).run()
    bottle.redirect('/run/finished')


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


def main():
    server_host, server_port = http_server_info()
    bottle.run(
        host=server_host, port=server_port,
        debug=True, reloader=True
    )


if __name__ == '__main__':
    main()
