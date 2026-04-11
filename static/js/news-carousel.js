/* ========================================
   SOLARIS — News Carousel
   Animated transitions, alternating layout,
   random shape dots
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    const slides = document.querySelectorAll('.news-slide');
    const dotsContainer = document.getElementById('news-dots');
    const prevBtn = document.getElementById('news-prev');
    const nextBtn = document.getElementById('news-next');

    if (!slides.length || !dotsContainer) return;

    const shapes = ['diamond', 'square'];
    let current = 0;
    let animating = false;

    // Assign alternating layout to even slides
    slides.forEach((slide, i) => {
        if (i % 2 === 1) slide.classList.add('layout-alt');
    });

    // Build dots with random shapes
    slides.forEach((_, i) => {
        const dot = document.createElement('button');
        dot.className = 'news-dot' + (i === 0 ? ' active' : '');
        dot.setAttribute('aria-label', 'Slide ' + (i + 1));
        // Each dot gets a random shape when active
        dot.dataset.activeShape = shapes[Math.floor(Math.random() * shapes.length)];
        if (i === 0) dot.dataset.shape = dot.dataset.activeShape;
        dot.addEventListener('click', () => goTo(i));
        dotsContainer.appendChild(dot);
    });

    const dots = dotsContainer.querySelectorAll('.news-dot');

    // Show first slide immediately
    slides[0].classList.add('visible');

    function goTo(index) {
        if (animating || index === current) return;
        animating = true;

        const oldSlide = slides[current];
        const newIndex = (index + slides.length) % slides.length;
        const newSlide = slides[newIndex];

        // Fade out current
        oldSlide.classList.remove('visible');
        oldSlide.classList.add('slide-out');

        // Update dots
        dots[current].classList.remove('active');
        dots[current].removeAttribute('data-shape');
        dots[newIndex].classList.add('active');
        dots[newIndex].dataset.shape = dots[newIndex].dataset.activeShape;

        // After fade out, swap slides
        setTimeout(() => {
            oldSlide.classList.remove('active', 'slide-out');
            newSlide.classList.add('active');

            // Force reflow for transition
            void newSlide.offsetWidth;

            // Fade in new slide
            requestAnimationFrame(() => {
                newSlide.classList.add('visible');
            });

            current = newIndex;
            animating = false;
        }, 300);
    }

    if (prevBtn) prevBtn.addEventListener('click', () => goTo(current - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => goTo(current + 1));
});
