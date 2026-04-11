/* ========================================
   SOLARIS — Lightbox for Gallery Images
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxClose = document.getElementById('lightbox-close');
    const lightboxPrev = document.getElementById('lightbox-prev');
    const lightboxNext = document.getElementById('lightbox-next');

    if (!lightbox || !lightboxImg) return;

    const items = document.querySelectorAll('[data-lightbox]');
    const images = [];
    let currentIndex = 0;

    items.forEach((item) => {
        const img = item.querySelector('img');
        if (img) {
            images.push(img.src);
        }
    });

    if (images.length === 0) return;

    function openLightbox(index) {
        currentIndex = index;
        lightboxImg.src = images[currentIndex];
        lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
        lightbox.classList.remove('active');
        document.body.style.overflow = '';
    }

    function navigate(direction) {
        currentIndex = (currentIndex + direction + images.length) % images.length;
        lightboxImg.src = images[currentIndex];
    }

    // Open on click
    items.forEach((item, i) => {
        item.addEventListener('click', () => openLightbox(i));
    });

    // Close
    lightboxClose.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) closeLightbox();
    });

    // Navigate
    lightboxPrev.addEventListener('click', (e) => {
        e.stopPropagation();
        navigate(-1);
    });
    lightboxNext.addEventListener('click', (e) => {
        e.stopPropagation();
        navigate(1);
    });

    // Keyboard
    document.addEventListener('keydown', (e) => {
        if (!lightbox.classList.contains('active')) return;
        if (e.key === 'Escape') closeLightbox();
        if (e.key === 'ArrowLeft') navigate(-1);
        if (e.key === 'ArrowRight') navigate(1);
    });
});
