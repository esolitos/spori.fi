import sys
import json

import spotipy.util as util
from spotipy import Spotify


class SwaRunner:
    _cache: dict = {}
    user: str
    spy_client: Spotify
    special_playlist: dict = {
        'name': 'Discover Weekly Albums',
        'desc': 'Contains the "Discovery Weekly", but with albums',
    }

    def __init__(self, client: Spotify, user: str):
        self.spy_client = client
        self.user = user

    @staticmethod
    def main(user: str):
        token = SwaRunner.get_oauth_token(user)
        if not token:
            raise RuntimeError('Unable to get oauth token.')

        client = Spotify(auth=token)
        runner = SwaRunner(client, user)
        album_playlist = runner.prepare_weekly_album_playlist()
        album_ids = runner.get_weekly_albums_ids()
        tracks = runner.get_all_albums_tracks(album_ids)
        results = runner.add_tracks_to_playlist(album_playlist['id'], tracks)
        print(results)

    def get_user_playlists(self) -> dict:
        if 'user_pl' not in self._cache or self._cache['user_pl'] is None:
            self._cache['user_pl'] = self.spy_client.user_playlists(self.user)['items']

        return self._cache['user_pl']

    def get_playlist_by_name(self, name: str) -> dict or None:
        for playlist in self.get_user_playlists():
            if playlist['name'] == name:
                return playlist

        return None

    def get_discover_weekly(self) -> dict:
        playlist_name: str = 'Discover Weekly'
        if playlist_name not in self._cache or self._cache[playlist_name] is None:
            self._cache[playlist_name] = self.get_playlist_by_name(playlist_name)

        return self._cache[playlist_name]

    def prepare_weekly_album_playlist(self) -> dict:
        album_playlist = self.get_playlist_by_name(self.special_playlist['name'])
        if not album_playlist:
            print('Creating new playlist.')
            return self.spy_client.user_playlist_create(
                self.user,
                name=self.special_playlist['name'],
                description=self.special_playlist['desc'],
                public=False
            )

        print('Found existing playlist:', end=' ')
        if album_playlist['tracks']['total'] > 0:
            print("contains %s tracks to remove." % album_playlist['tracks']['total'])
            self.do_playlist_cleanup(album_playlist['id'])
        else:
            print("and is empty.")

        return album_playlist

    def do_playlist_cleanup(self, playlist_id: str):
        playlist_tracks = self.spy_client.playlist_tracks(playlist_id=playlist_id, fields='items(track(id))')
        print(playlist_tracks)

        if not playlist_tracks or len(playlist_tracks['items']) <= 0:
            return None

        tracks = [t['track']['id'] for t in playlist_tracks['items']]
        for tracks_chunk in list(SwaRunner.divide_chunks(tracks, 100)):
            self.spy_client.user_playlist_remove_all_occurrences_of_tracks(
                user=self.user,
                playlist_id=playlist_id,
                tracks=tracks_chunk
            )

    def get_weekly_albums_ids(self):
        playlist = self.get_discover_weekly()
        if not playlist:
            return []
        tracks = self.spy_client.playlist_tracks(playlist_id=playlist['id'], fields='items(track(id,album(id)))')
        return [t['track']['album']['id'] for t in tracks['items']]

    def get_all_albums_tracks(self, album_ids: list):
        tracks = []
        for album_id in album_ids:
            tracks.extend([t['id'] for t in self.spy_client.album_tracks(album_id)['items']])

        return tracks

    def add_tracks_to_playlist(self, playlist_id: str, tracks: list):
        for chunk in list(SwaRunner.divide_chunks(tracks, 100)):
            self.spy_client.user_playlist_add_tracks(user=self.user, playlist_id=playlist_id, tracks=chunk)

    @staticmethod
    def divide_chunks(items: list, size: int):
        for i in range(0, len(items), size):
            yield items[i:i + size]

    @staticmethod
    def get_oauth_token(username: str, scope: str = 'playlist-read-private playlist-modify-private'):
        from spotipy.util import prompt_for_user_token
        return prompt_for_user_token(username, scope)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        SwaRunner.main(sys.argv[1])
    else:
        print("Usage: %s username" % (sys.argv[0],))
        sys.exit(1)
