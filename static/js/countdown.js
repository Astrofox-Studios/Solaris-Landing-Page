(function () {
    var timers = document.querySelectorAll('.countdown-timer[data-target]');
    timers.forEach(function (timer) {
        var target = new Date(timer.dataset.target).getTime();
        if (isNaN(target)) return;

        var dEl = timer.querySelector('[data-unit="days"]');
        var hEl = timer.querySelector('[data-unit="hours"]');
        var mEl = timer.querySelector('[data-unit="minutes"]');
        var sEl = timer.querySelector('[data-unit="seconds"]');

        function pad(n) { return String(n).padStart(2, '0'); }

        function tick() {
            var diff = target - Date.now();
            if (diff <= 0) {
                if (dEl) dEl.textContent = '00';
                if (hEl) hEl.textContent = '00';
                if (mEl) mEl.textContent = '00';
                if (sEl) sEl.textContent = '00';
                return;
            }
            var d = Math.floor(diff / 86400000);
            var h = Math.floor((diff % 86400000) / 3600000);
            var m = Math.floor((diff % 3600000) / 60000);
            var s = Math.floor((diff % 60000) / 1000);
            if (dEl) dEl.textContent = pad(d);
            if (hEl) hEl.textContent = pad(h);
            if (mEl) mEl.textContent = pad(m);
            if (sEl) sEl.textContent = pad(s);
        }

        tick();
        setInterval(tick, 1000);
    });
}());
