import sys

from spotipy import Spotify

from swa.utils import debug_log


class SwaRunner:
    _special_playlist: dict = {
        'name': 'Discover Weekly Albums',
        'desc': 'Contains the "Discovery Weekly", but with albums',
    }

    def __init__(self, client: Spotify):
        self._cache: dict = {}
        self._user: dict or None = None
        self._spy_client: Spotify = client

    def run(self):
        album_playlist = self.prepare_weekly_album_playlist()
        album_ids = self.get_weekly_albums_ids()
        tracks = self.get_all_albums_tracks(album_ids)
        self.add_tracks_to_playlist(album_playlist['id'], tracks)

    def get_user(self):
        if self._user is None:
            self._user = self._spy_client.current_user()
            debug_log('Fetch user data:')
            debug_log(self._user)
        return self._user

    def get_username(self):
        return self.get_user()['id']

    def get_user_playlists(self) -> dict:
        key: str = 'user_playlists'
        if key not in self._cache or self._cache[key] is None:
            self._cache[key] = self._spy_client.current_user_playlists()['items']

        return self._cache[key]

    def get_playlist_by_name(self, name: str) -> dict or None:
        for playlist in self.get_user_playlists():
            if playlist['name'] == name:
                debug_log("Playlist '{}': Found.".format(name))
                debug_log(playlist)
                return playlist

        debug_log("Playlist '{}': Not found.".format(name))
        return None

    def get_discover_weekly(self) -> dict:
        playlist_name: str = 'Discover Weekly'
        if playlist_name not in self._cache or self._cache[playlist_name] is None:
            self._cache[playlist_name] = self.get_playlist_by_name(playlist_name)

        return self._cache[playlist_name]

    def prepare_weekly_album_playlist(self) -> dict:
        album_playlist = self.get_playlist_by_name(self._special_playlist['name'])
        if not album_playlist:
            debug_log("Creating playlist: '{}'".format(self._special_playlist['name']))
            return self._spy_client.user_playlist_create(
                self.get_username(),
                name=self._special_playlist['name'],
                description=self._special_playlist['desc'],
                public=False
            )

        debug_log("Found playlist '%s:'".format(self._special_playlist['name']))
        if album_playlist['tracks']['total'] > 0:
            debug_log("Contains %s tracks to remove.".format(album_playlist['tracks']['total']))
            self._playlist_cleanup(album_playlist['id'])

        return album_playlist

    def _playlist_cleanup(self, playlist_id: str):
        debug_log('Cleaning up:', end=' ')
        while self._do_playlist_cleanup(playlist_id):
            debug_log('.', end='')
        debug_log('!')

    def _do_playlist_cleanup(self, playlist_id: str):
        playlist_tracks = self._spy_client.playlist_tracks(playlist_id=playlist_id, fields='items(track(id))')

        if not playlist_tracks or len(playlist_tracks['items']) <= 0:
            return None

        tracks = [t['track']['id'] for t in playlist_tracks['items']]
        return self._spy_client.user_playlist_remove_all_occurrences_of_tracks(
            user=self.get_username(),
            playlist_id=playlist_id,
            tracks=tracks
        )

    def get_weekly_albums_ids(self):
        playlist = self.get_discover_weekly()
        if not playlist:
            print("Could not find 'Discover weekly' playlist!")
            return []
        tracks = self._spy_client.playlist_tracks(playlist_id=playlist['id'], fields='items(track(id,album(id)))')
        return [t['track']['album']['id'] for t in tracks['items']]

    def get_all_albums_tracks(self, album_ids: list):
        tracks = []
        for album_id in album_ids:
            tracks.extend([t['id'] for t in self._spy_client.album_tracks(album_id)['items']])

        return tracks

    def add_tracks_to_playlist(self, playlist_id: str, tracks: list):
        for chunk in list(SwaRunner.divide_chunks(tracks, 100)):
            self._spy_client.user_playlist_add_tracks(user=self.get_username(), playlist_id=playlist_id, tracks=chunk)

    @staticmethod
    def divide_chunks(items: list, size: int):
        for i in range(0, len(items), size):
            yield items[i:i + size]

    @staticmethod
    def get_oauth_token(username: str, scope: str = 'user-read-email playlist-read-private playlist-modify-private'):
        from spotipy.util import prompt_for_user_token
        return prompt_for_user_token(username, scope)


# def main(user: str):
#     token = SwaRunner.get_oauth_token(user)
#     if not token:
#         raise RuntimeError('Unable to get oauth token.')
#
#     client = Spotify(auth=token)
#     SwaRunner(client).run()
#
#
# if __name__ == '__main__':
#     if len(sys.argv) > 1:
#         main(sys.argv[1])
#     else:
#         print("Usage: %s username" % (sys.argv[0],))
#         sys.exit(1)
