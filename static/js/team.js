/* ========================================
   SOLARIS — Team Member Switcher
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    const selectorHeads  = document.querySelectorAll('.team-selector-head');
    const bios           = document.querySelectorAll('.team-member-bio');
    const headsScroller  = document.querySelector('.team-selector-heads');
    const renderImg      = document.getElementById('team-render-img');
    const placeholder    = document.getElementById('team-render-placeholder');
    const prevBtn        = document.getElementById('team-prev');
    const nextBtn        = document.getElementById('team-next');

    if (selectorHeads.length === 0 || bios.length === 0) return;

    // Parse render URLs from data attribute (keyed by data-member / bio ID)
    let renders = [];
    if (renderImg && renderImg.dataset.renders) {
        try { renders = JSON.parse(renderImg.dataset.renders); } catch (e) {}
    }

    let currentListIndex = 0;

    // Preload renders, keyed by bio ID
    const imageExists = new Map();
    renders.forEach((url, bioId) => {
        const img = new Image();
        img.onload  = () => imageExists.set(bioId, true);
        img.onerror = () => imageExists.set(bioId, false);
        img.src = url;
    });

    function switchTo(listIndex) {
        if (listIndex < 0) listIndex = selectorHeads.length - 1;
        if (listIndex >= selectorHeads.length) listIndex = 0;
        currentListIndex = listIndex;

        const targetHead = selectorHeads[listIndex];
        // data-member is the bio ID — decoupled from the NodeList position
        // so commenting out members in HTML doesn't break the numbering
        const bioId = parseInt(targetHead.getAttribute('data-member'), 10);

        // Update active head
        selectorHeads.forEach(h => h.classList.remove('active'));
        targetHead.classList.add('active');

        // Scroll active head into view within the heads strip (mobile-friendly)
        targetHead.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });

        // Swap bio using CSS class — all bios stay in the DOM so card height
        // is always the height of the tallest bio and never jumps
        bios.forEach(bio => bio.classList.remove('active'));
        const targetBio = document.getElementById('team-bio-' + bioId);
        if (targetBio) targetBio.classList.add('active');

        // Swap render image
        if (renderImg && renders[bioId] !== undefined) {
            if (imageExists.get(bioId) === false) {
                renderImg.style.display = 'none';
                if (placeholder) placeholder.classList.add('visible');
            } else {
                renderImg.style.display = '';
                renderImg.src = renders[bioId];
                if (placeholder) placeholder.classList.remove('visible');
                renderImg.onerror = () => {
                    imageExists.set(bioId, false);
                    renderImg.style.display = 'none';
                    if (placeholder) placeholder.classList.add('visible');
                };
            }
        }
    }

    // Click on a head — use its NodeList position, not its data-member value
    selectorHeads.forEach((head, listIndex) => {
        head.addEventListener('click', () => switchTo(listIndex));
    });

    // Arrow buttons navigate through the NodeList (prev/next visible member)
    if (prevBtn) prevBtn.addEventListener('click', () => switchTo(currentListIndex - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => switchTo(currentListIndex + 1));

    // Initial render error guard
    if (renderImg) {
        renderImg.onerror = () => {
            renderImg.style.display = 'none';
            if (placeholder) placeholder.classList.add('visible');
        };
    }
});
