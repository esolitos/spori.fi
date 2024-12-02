# Spotify Discovery Weekly Albums


> [!WARNING]  
> Due to recent [changes on Spotify's Web API](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) this application is now useless.
>
> Not happy? Feel free to join the [crowd of people yelling at the wall in Spotify's forum](https://community.spotify.com/t5/Spotify-for-Developers/Changes-to-Web-API/td-p/6540414). 

This repo will now be archived, as it serves no purpouse anymore.

---

This simple script offers the ability to create a *"Discover Weekly Albums"*
playlist containing the albums of the songs from Spotify's *"Discover Weekly"*.

## How to run

There are a couple of ways to run this script, you could simply run it via CLI
or you can do all via a browser. The first option still requires a browser to
run the OAuth authentication process 'tho.

In either of the two configurations you'll need [Pipenv](https://pipenv.pypa.io/en/latest/)
to install the required libraries.
 provide the OAuth client id and
secret as required by  [Spotipy](https://spotipy.readthedocs.io/), those should
be passed as environment variables:

```shell script
export SPOTIPY_CLIENT_ID='your-spotify-client-id'
export SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
```

### Running without http server (only CLI)

The script `spotify_weekly.py` can be run via

```shell script
export REDIRECT_HOST='localhost:80'
```

## Configuration overview

*All configuration is done via environment variables*

| Name                      | Required  | Description |
|---------------------------|-----------|-------------|
| `SPOTIPY_CLIENT_ID`       | Yes       | Oauth Client ID, by Spotify |
| `SPOTIPY_CLIENT_SECRET`   | Yes       | Oauth Client Secret, by Spotify |
| `OAUTH_CACHE_FILE`        | No        | *(Only HTTP)* Sets the oauth cache file path. Must be writable. |
| `SERVER_HOST`             | No        | *(Only HTTP)* Http server IP (Default: `127.0.1.1`) |
| `SERVER_PORT`             | No        | *(Only HTTP)* Http server Port (Default: `8080` |
| `REDIRECT_HOST`           | No        | *(Only HTTP)* Redirect hostname for Spotify oauth. (Default: "`$SERVER_HOST:$SERVER_PORT`") |
