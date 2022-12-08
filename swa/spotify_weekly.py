import logging

from typing import Dict, List, Optional
from spotipy import Spotify

class SwaError(RuntimeError):
    """Generic App error."""

class PlaylistError(SwaError):
    """Playlist generic error."""

class DiscoverWeeklyError(PlaylistError):
    """Generic error about 'Discover Weekly' playlist."""

class DiscoverWeeklyNotFoundError(DiscoverWeeklyError):
    """Playlist 'Discover Weekly' not found."""

class DiscoverWeeklyMultipleMatchesError(DiscoverWeeklyError):
    """Playlist 'Discover Weekly' has multiple matches."""

class SwaRunner:
    """A class to run a script that fetches tracks from the user's "Discover Weekly" playlist,
    and adds them to a new playlist with only albums.

    Args:
        client (Spotify): The Spotify API client object.
        discover_weekly_id (str, optional): The ID of the "Discover Weekly" playlist.
            If not provided, the script will try to find it automatically.

    Attributes:
        _special_playlist (Dict[str, str]): The name description of the playlist to create.
        _cache (Dict[str, object]): A dictionary to store cached data from the API.
        _user (Dict): The user data.
        _spy_client (Spotify): The Spotify API client object.
        _discover_weekly_id (str): The ID of the "Discover Weekly" playlist.
    """
    _special_playlist: Dict[str, str] = {
        'name': 'Discover Weekly Albums',
        'desc': 'Contains the "Discovery Weekly", but with albums',
    }

    def __init__(self, client: Spotify, discover_weekly_id: Optional[str] = None):
        self._cache: Dict[str, object] = {}
        self._user: Optional[Dict] = None
        self._spy_client: Spotify = client
        self._discover_weekly_id = discover_weekly_id if discover_weekly_id else None

    def run(self):
        """
        Main runtime.
        """
        album_playlist = self.prepare_weekly_album_playlist()
        album_ids = self.get_weekly_albums_ids()
        tracks = self.get_all_albums_tracks(album_ids)
        self.add_tracks_to_playlist(album_playlist['id'], tracks)

    def get_user(self) -> Dict:
        """
        Will return a user dictionary.
        """
        if self._user is None:
            self._user = self._spy_client.current_user()
            logging.debug('Fetched user data:')
            logging.debug(self._user)
        return self._user

    def get_username(self) -> str:
        """Get the current user's username

        Returns:
            str: The username
        """
        return self.get_user()['id']

    def get_user_playlists(self, sort_by_author: bool = False) -> List[Dict]:
        """
        List all user playlists.
        """
        key: str = 'user_playlists'
        if key not in self._cache or self._cache[key] is None:
            self._cache[key] = self._spy_client.current_user_playlists()['items']

        if sort_by_author:
            return self._sort_playlists_by_author(self._cache[key])

        return self._cache[key]

    def get_playlist_by_name(self, name: str, multiple: bool = False) -> List[Dict]:
        """
        Gets a user playlist by it's name.
        """
        matches = []
        for playlist in self.get_user_playlists():
            if playlist['name'] == name:
                logging.debug("Playlist '%s': Found.", name)
                matches.append(playlist)

        if matches:
            return matches if multiple else matches[0]

        logging.debug("Playlist '%s': Not found.", name)
        return matches

    def get_discover_weekly(self, allow_multiple: bool = False) -> list or dict:
        """
        Attempts to find the "Discover weekly" playlist.
        """
        if self._discover_weekly_id:
            p = self._spy_client.playlist(self._discover_weekly_id)
            print('Got pre-selection: {self._discover_weekly_id}')
            print(p)
            return p

        playlist_name: str = 'Discover Weekly'
        if playlist_name not in self._cache or self._cache[playlist_name] is None:
            self._cache[playlist_name] = self.get_playlist_by_name(playlist_name, multiple=True)

        if len(self._cache[playlist_name]) <= 0:
            raise DiscoverWeeklyNotFoundError()
        elif len(self._cache[playlist_name]) > 1 and not allow_multiple:
            raise DiscoverWeeklyMultipleMatchesError()

        return self._cache[playlist_name] if allow_multiple else self._cache[playlist_name][0]

    def prepare_weekly_album_playlist(self) -> dict:
        """
        Attempts to find the "Weekly Album discovery", cleaning it up is needed.
        """
        album_playlist = self.get_playlist_by_name(self._special_playlist['name'])
        if not album_playlist:
            logging.debug("Creating playlist: '%s'", self._special_playlist['name'])
            return self._spy_client.user_playlist_create(
                self.get_username(),
                name=self._special_playlist['name'],
                description=self._special_playlist['desc'],
                public=False
            )

        logging.info("Found playlist '%s:'", self._special_playlist['name'])
        if album_playlist['tracks']['total'] > 0:
            logging.info("Contains %s tracks to remove.", album_playlist['tracks']['total'])
            self._playlist_cleanup(album_playlist['id'])

        return album_playlist

    def _playlist_cleanup(self, playlist_id: str):
        logging.info('Cleaning up:', end=' ')
        while self._do_playlist_cleanup(playlist_id):
            logging.info('.', end='')
        logging.info('!')

    def _do_playlist_cleanup(self, playlist_id: str):
        playlist_tracks = self._spy_client.playlist_tracks(
            playlist_id=playlist_id,
            fields='items(track(id))'
        )

        if not playlist_tracks or len(playlist_tracks['items']) <= 0:
            return None

        tracks = [t['track']['id'] for t in playlist_tracks['items']]
        return self._spy_client.user_playlist_remove_all_occurrences_of_tracks(
            user=self.get_username(),
            playlist_id=playlist_id,
            tracks=tracks
        )

    def get_weekly_albums_ids(self):
        """
        Gets all the album IDs for the songs contained in the Discover Weekly playlist
        """
        playlist = self.get_discover_weekly()
        tracks = self._spy_client.playlist_tracks(playlist_id=playlist['id'], fields='items(track(id,album(id)))')
        return [t['track']['album']['id'] for t in tracks['items']]

    def get_all_albums_tracks(self, album_ids: list):
        """
        Retrurns all the tracks for a list of album IDs
        """
        tracks = []
        for album_id in album_ids:
            tracks.extend([t['id'] for t in self._spy_client.album_tracks(album_id)['items']])

        return tracks

    def add_tracks_to_playlist(self, playlist_id: str, tracks: list):
        """
        Given a list of tracks and a playlists it appends them to such playloist.
        """
        for chunk in list(SwaRunner.divide_chunks(tracks, 100)):
            self._spy_client.user_playlist_add_tracks(
                user=self.get_username(),
                playlist_id=playlist_id,
                tracks=chunk
            )

    @staticmethod
    def divide_chunks(items: list, size: int):
        """
        Generator to split a list in chunks of a given size.
        """
        for i in range(0, len(items), size):
            yield items[i:i + size]

    @staticmethod
    def _sort_playlists_by_author(playlists: dict) -> dict:
        sorted_playlists = {}
        for playlist in playlists:
            author_name = playlist['owner']['display_name']

            if author_name not in sorted_playlists:
                sorted_playlists[author_name] = []

            sorted_playlists[author_name].append(playlist)

        return sorted_playlists
