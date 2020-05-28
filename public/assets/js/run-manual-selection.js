(function(window, document){
'use strict';

const displayNoneClass = 'd-none';
const playlistIdSelectEl = document.getElementById('select-playlist');
const playlistTextWrapperEl = document.getElementById('playlist-id-manual-input');
const previewWrapperEl = document.getElementById('playlist-preview-wrapper');
const playlistFrameEl = document.getElementById('playlist-preview');
const submitButtonEl = document.getElementById('playlist-submit');

const showPlaylistPreview = function(playlistId) {
    let playlist_url = 'https://open.spotify.com/embed/playlist/' + playlistId;
    playlistFrameEl.setAttribute('src', playlist_url);
    previewWrapperEl.classList.remove(displayNoneClass);
};

const hidePlaylistPreview = function() {
    previewWrapperEl.classList.add(displayNoneClass);
    playlistFrameEl.setAttribute('src', '');
};

const showPlaylistTextInputArea = function() {
    playlistTextWrapperEl.classList.remove(displayNoneClass);
};

const hidePlaylistTextInputArea = function() {
    playlistTextWrapperEl.classList.add(displayNoneClass);
};

const enableSubmitButton = function() {
    submitButtonEl.textContent = 'Confirm selection!';
    submitButtonEl.removeAttribute('disabled');
    playlistIdSelectEl.removeEventListener('change', enableSubmitButton);
};

const selectElChange = function(event) {
  let playlistId = this.value;
  if(playlistId === '_') {
    hidePlaylistPreview();
    showPlaylistTextInputArea();
  }
  else {
    hidePlaylistTextInputArea();
    showPlaylistPreview(playlistId);
  }
};

playlistIdSelectEl.addEventListener('change', selectElChange);
playlistIdSelectEl.addEventListener('change', enableSubmitButton);

})(window, window.document);