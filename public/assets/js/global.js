(function(window, document){
'use strict';
//
// Accessibility feature: Adds a 'a11y--focus-on' class to the body when a user starts using 'TAB' to navigate
//
let handleFirstTab = function(e) {
    if (e.keyCode === 9) { // the "I am a keyboard user" key
        document.body.classList.add('a11y--focus-on');
        window.removeEventListener('keydown', handleFirstTab);
    }
}
window.addEventListener('keydown', handleFirstTab);



})(window, window.document);