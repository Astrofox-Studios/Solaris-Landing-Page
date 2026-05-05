/* ========================================
   SOLARIS — Beta Page JavaScript
   Particles, form handling, scroll reveals
   ======================================== */

(function () {
    'use strict';

    // ---- Particle canvas ----
    const canvas = document.getElementById('beta-particles');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let particles = [];
        let raf;

        function resize() {
            canvas.width  = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
        }

        function makeParticle() {
            return {
                x:            Math.random() * canvas.width,
                y:            Math.random() * canvas.height,
                r:            Math.random() * 1.4 + 0.3,
                vx:           (Math.random() - 0.5) * 0.25,
                vy:           (Math.random() - 0.5) * 0.25,
                alpha:        Math.random() * 0.55 + 0.08,
                alphaDir:     Math.random() > 0.5 ? 1 : -1,
                alphaSpeed:   Math.random() * 0.004 + 0.001,
            };
        }

        function init() {
            resize();
            // Density: ~1 particle per 6000 px²  (scales with viewport)
            const count = Math.floor((canvas.width * canvas.height) / 6000);
            particles = Array.from({ length: Math.min(count, 180) }, makeParticle);
        }

        function tick() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            for (let i = 0; i < particles.length; i++) {
                const p = particles[i];

                p.x += p.vx;
                p.y += p.vy;
                p.alpha += p.alphaDir * p.alphaSpeed;

                // Bounce off edges
                if (p.x < 0 || p.x > canvas.width)  { p.vx *= -1; p.x = Math.max(0, Math.min(p.x, canvas.width)); }
                if (p.y < 0 || p.y > canvas.height) { p.vy *= -1; p.y = Math.max(0, Math.min(p.y, canvas.height)); }

                // Fade in/out
                if (p.alpha < 0.06 || p.alpha > 0.65) p.alphaDir *= -1;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(180, 210, 255, ${p.alpha})`;
                ctx.fill();
            }

            raf = requestAnimationFrame(tick);
        }

        init();
        tick();

        // Throttled resize
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                cancelAnimationFrame(raf);
                init();
                tick();
            }, 200);
        });
    }

    // ---- Beta form submit ----
    const betaForm    = document.getElementById('beta-form');
    const betaSuccess = document.getElementById('beta-success');
    const betaCard    = document.querySelector('.beta-signup-card');

    if (betaForm && betaSuccess) {
        betaForm.addEventListener('submit', (e) => {
            e.preventDefault();

            const submitBtn  = betaForm.querySelector('.beta-submit-btn');
            const emailInput = betaForm.querySelector('.beta-email-input');

            // Basic validation
            if (!emailInput.value || !emailInput.checkValidity()) {
                emailInput.focus();
                emailInput.style.borderColor = '#ef4444';
                emailInput.style.boxShadow   = '0 0 0 4px rgba(239, 68, 68, 0.2)';
                setTimeout(() => {
                    emailInput.style.borderColor = '';
                    emailInput.style.boxShadow   = '';
                }, 2200);
                return;
            }

            // Loading state
            submitBtn.disabled = true;
            submitBtn.querySelector('.beta-btn-label').textContent = 'Joining…';

            // TODO: replace with real mailing-list API call
            setTimeout(() => {
                betaForm.style.display  = 'none';
                betaSuccess.classList.add('show');

                // Gently scroll the card into view on mobile
                if (betaCard) {
                    betaCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }, 700);
        });
    }

    // ---- Scroll-reveal (mirrors main.js pattern) ----
    const fadeEls = document.querySelectorAll('.fade-in');
    if (fadeEls.length && 'IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((entry, idx) => {
                if (!entry.isIntersecting) return;
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, idx * 80);
                io.unobserve(entry.target);
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -50px 0px' });

        fadeEls.forEach(el => io.observe(el));
    }

})();
