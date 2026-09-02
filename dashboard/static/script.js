/**
 * Device Dashboard — Minimal JS helpers
 * HTMX is loaded from CDN; this provides modal helpers and utilities
 */

/**
 * Open a modal by ID
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Close a modal by ID
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Close modal on backdrop click
 */
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-backdrop')) {
        const modal = e.target.closest('.modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
});

/**
 * Close modal on Escape key
 */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal[style*="display: flex"]').forEach(function(modal) {
            modal.style.display = 'none';
        });
    }
});

/**
 * Simple toast notification (optional utility)
 */
function showToast(message, type = 'info') {
    const colors = {
        info: '#58a6ff',
        success: '#3fb950',
        error: '#f85149',
        warning: '#d29922',
    };
    
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${colors[type] || colors.info};
        color: white;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 1001;
        opacity: 0;
        transform: translateY(10px);
        transition: all 0.2s;
    `;
    
    document.body.appendChild(toast);
    
    requestAnimationFrame(function() {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });
    
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(function() {
            toast.remove();
        }, 200);
    }, 3000);
}

/**
 * Format bytes to human-readable
 */
function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * HTMX event handlers for common patterns
 */
document.addEventListener('DOMContentLoaded', function() {
    // If HTMX is loaded, process any declarative attributes
    if (window.htmx) {
        htmx.process(document.body);
    }
});
