/* ========================================
   SOLARIS — Server IP Copy to Clipboard
   ======================================== */

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-ip]').forEach(button => {
        button.addEventListener('click', async () => {
            const ip = button.getAttribute('data-ip');
            const textEl = button.querySelector('.btn-text');
            const originalText = textEl ? textEl.textContent : '';

            try {
                await navigator.clipboard.writeText(ip);

                button.classList.add('copied');
                if (textEl) textEl.textContent = 'Copied!';

                setTimeout(() => {
                    button.classList.remove('copied');
                    if (textEl) textEl.textContent = originalText;
                }, 2000);
            } catch (err) {
                // Fallback: select and copy from a temporary input
                const input = document.createElement('input');
                input.value = ip;
                document.body.appendChild(input);
                input.select();
                document.execCommand('copy');
                document.body.removeChild(input);

                button.classList.add('copied');
                if (textEl) textEl.textContent = 'Copied!';

                setTimeout(() => {
                    button.classList.remove('copied');
                    if (textEl) textEl.textContent = originalText;
                }, 2000);
            }
        });
    });
});
