/* ========================================
   SOLARIS — Team Member Switcher
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    const selectorHeads = document.querySelectorAll('.team-selector-head');
    const bios = document.querySelectorAll('.team-member-bio');
    const renderImg = document.getElementById('team-render-img');
    const placeholder = document.getElementById('team-render-placeholder');
    const prevBtn = document.getElementById('team-prev');
    const nextBtn = document.getElementById('team-next');

    if (selectorHeads.length === 0 || bios.length === 0) return;

    // Parse render URLs from data attribute
    let renders = [];
    if (renderImg && renderImg.dataset.renders) {
        try { renders = JSON.parse(renderImg.dataset.renders); } catch (e) {}
    }

    let currentIndex = 0;

    // Preload images to check which exist
    const imageExists = new Map();
    renders.forEach((url, i) => {
        const img = new Image();
        img.onload = () => imageExists.set(i, true);
        img.onerror = () => imageExists.set(i, false);
        img.src = url;
    });

    function switchTo(index) {
        if (index < 0) index = selectorHeads.length - 1;
        if (index >= selectorHeads.length) index = 0;
        currentIndex = index;

        // Update active head
        selectorHeads.forEach(h => h.classList.remove('active'));
        selectorHeads[index].classList.add('active');

        // Show the right bio
        bios.forEach(bio => bio.style.display = 'none');
        const targetBio = document.getElementById('team-bio-' + index);
        if (targetBio) targetBio.style.display = 'block';

        // Swap render image or show placeholder
        if (renderImg && renders[index]) {
            if (imageExists.get(index) === false) {
                renderImg.style.display = 'none';
                if (placeholder) placeholder.classList.add('visible');
            } else {
                renderImg.style.display = '';
                renderImg.src = renders[index];
                if (placeholder) placeholder.classList.remove('visible');

                // Handle load error for images not yet checked
                renderImg.onerror = () => {
                    imageExists.set(index, false);
                    renderImg.style.display = 'none';
                    if (placeholder) placeholder.classList.add('visible');
                };
            }
        }
    }

    // Click on heads
    selectorHeads.forEach((head) => {
        head.addEventListener('click', () => {
            const index = parseInt(head.getAttribute('data-member'), 10);
            switchTo(index);
        });
    });

    // Arrow navigation
    if (prevBtn) {
        prevBtn.addEventListener('click', () => switchTo(currentIndex - 1));
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', () => switchTo(currentIndex + 1));
    }

    // Check initial render
    if (renderImg) {
        renderImg.onerror = () => {
            renderImg.style.display = 'none';
            if (placeholder) placeholder.classList.add('visible');
        };
    }
});
