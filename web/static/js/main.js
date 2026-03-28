/**
 * Main JavaScript for Claude Code Capture
 * Modern UI utilities
 */

// Utility functions for formatting
function formatNumber(n) {
    if (n === undefined || n === null) return '-';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
}

function formatTokens(n) {
    if (n === undefined || n === null) return '-';
    if (n >= 1000000) return (n / 1000000).toFixed(2) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
}

function formatCost(c) {
    if (c === undefined || c === null) return '-';
    const num = typeof c === 'number' ? c : parseFloat(c);
    if (num >= 1) return '$' + num.toFixed(2);
    if (num >= 0.01) return '$' + num.toFixed(3);
    return '$' + num.toFixed(4);
}

function formatDateTime(d) {
    if (!d) return '-';
    const date = new Date(d);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined,
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatShortDate(d) {
    if (!d) return '-';
    const date = new Date(d);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatRelativeTime(d) {
    if (!d) return '-';
    const date = new Date(d);
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (seconds < 60) return 'just now';
    if (minutes < 60) return minutes + 'm ago';
    if (hours < 24) return hours + 'h ago';
    if (days < 30) return days + 'd ago';
    return formatShortDate(d);
}

function formatDuration(ms) {
    if (ms === undefined || ms === null) return '-';
    if (ms >= 1000) return (ms / 1000).toFixed(2) + 's';
    return ms + 'ms';
}

function formatModel(model) {
    if (!model) return '-';
    if (model.includes('opus')) return 'Claude 3 Opus';
    if (model.includes('sonnet')) return 'Claude 3 Sonnet';
    if (model.includes('haiku')) return 'Claude 3 Haiku';
    return model.split('-').slice(0, 2).join(' ');
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// API helper with error handling
async function fetchApi(endpoint) {
    try {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Copy to clipboard utility
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        return false;
    }
}

// Highlight active nav item based on current URL
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
});

// Mobile sidebar toggle (for future mobile support)
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
}
