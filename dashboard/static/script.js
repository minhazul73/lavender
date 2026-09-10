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
 * Sidebar toggle — collapse/expand with localStorage persistence
 */
function sidebarToggle() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const main = document.querySelector('.main');
    
    // Restore saved state
    const collapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    if (collapsed) {
        sidebar.classList.add('collapsed');
        if (main) main.classList.add('sidebar-collapsed');
        toggleBtn.classList.add('active');
    }
    
    toggleBtn.addEventListener('click', function() {
        const isCollapsed = sidebar.classList.toggle('collapsed');
        if (main) main.classList.toggle('sidebar-collapsed', isCollapsed);
        toggleBtn.classList.toggle('active', isCollapsed);
        localStorage.setItem('sidebar-collapsed', isCollapsed);
    });
}

/**
 * HTMX event handlers for common patterns
 */
document.addEventListener('DOMContentLoaded', function() {
    // If HTMX is loaded, process any declarative attributes
    if (window.htmx) {
        htmx.process(document.body);
    }

    sidebarToggle();
});

/**
 * ===== Cockpit-style Administrative Elevation Helpers =====
 */
let _pendingElevationCallback = null;

function openElevateModal(promptMessage, onElevated) {
    const modal = document.getElementById('elevate-modal');
    if (!modal) return;

    const promptEl = document.getElementById('elevate-prompt-text');
    if (promptEl && promptMessage) {
        promptEl.textContent = promptMessage;
    }

    const pwdInput = document.getElementById('elevate-password');
    const errEl = document.getElementById('elevate-error');
    if (pwdInput) pwdInput.value = '';
    if (errEl) errEl.style.display = 'none';

    _pendingElevationCallback = onElevated || null;
    modal.style.display = 'flex';
    if (pwdInput) {
        setTimeout(() => pwdInput.focus(), 50);
    }
}

function closeElevateModal() {
    const modal = document.getElementById('elevate-modal');
    if (modal) modal.style.display = 'none';
    _pendingElevationCallback = null;
}

async function submitElevation() {
    const pwdInput = document.getElementById('elevate-password');
    const errEl = document.getElementById('elevate-error');
    const submitBtn = document.getElementById('elevate-submit-btn');

    const password = pwdInput ? pwdInput.value : '';
    if (!password) {
        if (errEl) {
            errEl.textContent = 'Please enter your system password.';
            errEl.style.display = 'block';
        }
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Verifying…';
    }
    if (errEl) errEl.style.display = 'none';

    try {
        const res = await fetch('/auth/elevate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password }),
        });
        const data = await res.json();

        if (res.ok && data.success) {
            showToast('Administrative access granted', 'success');
            closeElevateModal();
            if (typeof _pendingElevationCallback === 'function') {
                const cb = _pendingElevationCallback;
                _pendingElevationCallback = null;
                cb();
            } else {
                window.location.reload();
            }
        } else {
            if (errEl) {
                errEl.textContent = data.detail || data.error || 'Authentication failed. Please check password.';
                errEl.style.display = 'block';
            }
            if (pwdInput) {
                pwdInput.focus();
                pwdInput.select();
            }
        }
    } catch (err) {
        if (errEl) {
            errEl.textContent = 'Network error while connecting to server.';
            errEl.style.display = 'block';
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Authenticate';
        }
    }
}

async function dropAdminAccess() {
    try {
        const res = await fetch('/auth/drop-admin', { method: 'POST' });
        if (res.ok) {
            showToast('Administrative access turned off', 'info');
            window.location.reload();
        }
    } catch (err) {
        showToast('Failed to drop admin access', 'error');
    }
}
