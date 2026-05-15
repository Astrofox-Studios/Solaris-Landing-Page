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
        let errorDiv = document.getElementById('beta-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'beta-error';
            errorDiv.style.cssText = 'color:#ef4444;font-size:0.9rem;margin-bottom:12px;display:none;';
            const submitBtn = betaForm.querySelector('.beta-submit-btn');
            betaForm.insertBefore(errorDiv, submitBtn);
        }

        function showError(msg) {
            errorDiv.textContent = msg;
            errorDiv.style.display = 'block';
        }

        function hideError() {
            errorDiv.style.display = 'none';
            errorDiv.textContent = '';
        }

        betaForm.addEventListener('submit', (e) => {
            e.preventDefault();
            hideError();

            const submitBtn  = betaForm.querySelector('.beta-submit-btn');
            const emailInput = betaForm.querySelector('.beta-email-input');

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

            submitBtn.disabled = true;
            submitBtn.querySelector('.beta-btn-label').textContent = 'Joining…';

            const fd = new FormData(betaForm);
            const cookieConsent = localStorage.getItem('solaris-cookies') === 'accepted' ? 'true' : 'false';
            fd.set('ip_consent', cookieConsent);

            fetch('/beta-signup', { method: 'POST', body: fd })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        betaForm.style.display = 'none';
                        betaSuccess.classList.add('show');
                        if (betaCard) {
                            betaCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                    } else {
                        submitBtn.disabled = false;
                        submitBtn.querySelector('.beta-btn-label').textContent = 'Join Early Access';
                        if (data.error === 'already_signed_up') {
                            showError("You're already on the list! Check your email.");
                        } else if (data.error === 'too_many_attempts') {
                            showError('Too many signup attempts from your location.');
                        } else if (data.error === 'invalid_email') {
                            showError('Please enter a valid email address.');
                        } else if (data.error === 'turnstile_failed') {
                            showError('Security check failed. Please try again.');
                        } else {
                            showError('Something went wrong. Please try again.');
                        }
                    }
                })
                .catch(() => {
                    submitBtn.disabled = false;
                    submitBtn.querySelector('.beta-btn-label').textContent = 'Join Early Access';
                    showError('Something went wrong. Please try again.');
                });
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
