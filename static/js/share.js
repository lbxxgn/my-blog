// Share functionality
document.addEventListener('DOMContentLoaded', function() {
    const wechatBtn = document.querySelector('.share-btn.wechat');
    const copyBtn = document.querySelector('.share-btn.copy');
    const modal = document.querySelector('.modal-overlay');
    const modalClose = document.querySelector('.modal-close');
    const qrcodeImg = document.querySelector('.qrcode-img');
    const toast = document.querySelector('.copy-toast');

    // WeChat QR code
    if (wechatBtn && modal) {
        wechatBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            const url = window.location.href;

            try {
                const response = await fetch(`/api/share/qrcode?url=${encodeURIComponent(url)}`);
                const data = await response.json();

                if (data.qrcode) {
                    qrcodeImg.src = data.qrcode;
                    modal.classList.add('active');
                }
            } catch (error) {
                console.error('Failed to generate QR code:', error);
            }
        });
    }

    // Close modal
    if (modalClose) {
        modalClose.addEventListener('click', function() {
            modal.classList.remove('active');
        });
    }

    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    }

    // Copy link
    if (copyBtn) {
        copyBtn.addEventListener('click', async function(e) {
            e.preventDefault();

            try {
                await navigator.clipboard.writeText(window.location.href);

                // Show toast
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                }, 2000);
            } catch (error) {
                console.error('Failed to copy:', error);
            }
        });
    }
});
