(function () {
    'use strict';

    var COOKIE_KEY = 'solaris-cookies';
    var banner = document.getElementById('cookie-banner');

    if (!banner) return;

    var stored = localStorage.getItem(COOKIE_KEY);
    if (stored) return;

    requestAnimationFrame(function () {
        setTimeout(function () { banner.classList.add('visible'); }, 600);
    });

    document.getElementById('cookie-accept').addEventListener('click', function () {
        localStorage.setItem(COOKIE_KEY, 'accepted');
        banner.classList.remove('visible');
    });

    document.getElementById('cookie-optout').addEventListener('click', function () {
        localStorage.setItem(COOKIE_KEY, 'opted_out');
        banner.classList.remove('visible');
    });
})();
