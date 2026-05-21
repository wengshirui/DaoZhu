/**
 * AccoBot — Main Entry Point
 * Initialization, shared utilities, panel toggle.
 * Loads: business.js (left panel), chat.js (center), agent.js (right panel + status)
 */

// ===== Shared Utilities =====
function formatContent(t) {
    if (!t) return '';
    let h = esc(t);
    h = h.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/`(.*?)`/g, '<code>$1</code>');
    h = h.replace(/\n/g, '<br>');
    return h;
}

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
function handleKeyDown(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
function autoResize(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px'; }

// ===== Panel Toggle =====
function togglePanel(side) {
    const panel = document.getElementById(`panel-${side}`);
    const expandBtn = document.getElementById(`expand-${side}`);
    panel.classList.toggle('collapsed');
    expandBtn.classList.toggle('visible', panel.classList.contains('collapsed'));
}

// ===== App Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    // Business layer
    fetchStatus();
    loadCompanies();
    loadTodos();

    // Chat layer
    checkAndShowSettings().then(() => { connectWebSocket(); });

    // Agent layer
    loadCapabilities();

    // Chat sessions
    (async function() {
        await loadChatSessions();
        if (!chatSessions.length) await createNewSession();
        else { currentSessionId = chatSessions[0].id; renderChatHistory(); }
    })();

    // Data overview (if company selected)
    setTimeout(() => {
        const sel = document.getElementById('current-company');
        if (sel && sel.value) loadDataOverview();
    }, 500);
});
