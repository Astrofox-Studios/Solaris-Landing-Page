/* ========================================
   SOLARIS — Season Preview Carousel
   Vertical icon selector + image swap
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    const icons = document.querySelectorAll('.season-preview-icon-btn');
    const img = document.getElementById('season-preview-img');
    const title = document.getElementById('season-preview-title');
    const desc = document.getElementById('season-preview-desc');
    const caption = document.getElementById('season-preview-caption');

    if (!icons.length || !img) return;

    icons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            icons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Fade out
            img.style.opacity = '0';
            img.style.transform = 'scale(0.98)';

            setTimeout(() => {
                // Swap content
                img.src = btn.dataset.img;
                if (title) title.textContent = btn.dataset.title;
                if (desc) desc.textContent = btn.dataset.desc;

                // Update badge
                const badge = caption.querySelector('.season-preview-badge');
                if (badge) {
                    badge.className = 'season-preview-badge ' + btn.dataset.badge;
                    badge.textContent = btn.dataset.badge === 'free' ? 'Free' : 'Pass';
                }

                // Fade in
                img.style.opacity = '1';
                img.style.transform = 'scale(1)';
            }, 250);
        });
    });
});
