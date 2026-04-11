/* ========================================
   SOLARIS — Play Now Modal
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    const playBtn = document.getElementById('play-now-btn');
    const headerPlayBtn = document.getElementById('header-play-btn');
    const modal = document.getElementById('play-modal');
    const closeBtn = document.getElementById('play-modal-close');
    const copyBtn = document.getElementById('modal-copy-ip');

    if (!modal) return;

    function openModal() {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (playBtn) playBtn.addEventListener('click', openModal);
    if (headerPlayBtn) headerPlayBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);

    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) closeModal();
    });

    // Copy IP
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText('playsolaris.net').then(() => {
                copyBtn.textContent = 'Copied!';
                setTimeout(() => { copyBtn.textContent = 'Copy IP'; }, 2000);
            });
        });
    }
});
