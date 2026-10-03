let isCurrentLogsView = true;
let pollInterval = null;
const expandedSessions = new Set();

function fetchCommand(cmdType) {
    const outputBox = document.getElementById('command-output');
    if (!outputBox) return;
    
    outputBox.innerHTML = "<code>Executing command safely...</code>";
    fetch(`/api/host/${cmdType}`, { credentials: 'same-origin' })
        .then(response => response.json())
        .then(data => {
            outputBox.innerHTML = `<code>${escapeHtml(data.output || "No output returned.")}</code>`;
        })
        .catch(err => {
            outputBox.innerHTML = `<code class="text-danger">Error fetching command output: ${err}</code>`;
        });
}

// Simple HTML escaper for safety inside <code> tags
function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderLogsToTable(data) {
    const tbody = document.getElementById('cowrie-log-table');
    if (!tbody) return;
    
    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-5">No sessions found in this log file.</td></tr>';
        return;
    }
    
    let rowsHtml = '';
    data.forEach(session => {
        const loginsStr = session.logins && session.logins.length > 0 ? session.logins.join(', ') : 'None / Failed';
        const eventCount = session.events ? session.events.length : 0;
        const isExpanded = expandedSessions.has(session.session);
        
        let eventsHtml = '';
        if (session.events && session.events.length > 0) {
            session.events.forEach(ev => {
                eventsHtml += `<div class="mb-1 text-light"><code>[${escapeHtml(ev.timestamp)}]</code> <span class="text-info">${escapeHtml(ev.eventid)}</span>: ${escapeHtml(ev.message || '')}</div>`;
            });
        }

        // Main session row
        rowsHtml += `
            <tr class="log-row" style="cursor: pointer;" onclick="toggleSessionRow('${escapeHtml(session.session)}')">
                <td>${escapeHtml(session.timestamp)}</td>
                <td><code class="text-info font-monospace">${escapeHtml(session.session)}</code></td>
                <td><code>${escapeHtml(session.src_ip)}</code></td>
                <td>
                    <div><strong>Logins:</strong> <span class="text-warning">${escapeHtml(loginsStr)}</span> | <strong>Events:</strong> ${eventCount}</div>
                </td>
            </tr>
            <tr id="detail-row-${escapeHtml(session.session)}" class="session-detail-row" style="display: ${isExpanded ? 'table-row' : 'none'}; background-color: rgba(0,0,0,0.2);">
                <td colspan="4" class="p-3">
                    <div class="border border-secondary rounded p-3 bg-dark">
                        <h6 class="text-info small mb-2"><i class="fa-solid fa-terminal me-1"></i> Session Activity & Payloads (${eventCount} events):</h6>
                        <div class="bg-black p-2 rounded border border-secondary small font-monospace" style="max-height: 250px; overflow-y: auto;">
                            ${eventsHtml}
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = rowsHtml;
}

function toggleSessionRow(sessionId) {
    const detailRow = document.getElementById(`detail-row-${sessionId}`);
    if (!detailRow) return;

    if (expandedSessions.has(sessionId)) {
        expandedSessions.delete(sessionId);
        detailRow.style.display = 'none';
    } else {
        expandedSessions.add(sessionId);
        detailRow.style.display = 'table-row';
    }
}

function pollCurrentLogs() {
    if (!isCurrentLogsView) return;
    
    fetch('/api/cowrie/stream', { credentials: 'same-origin' })
        .then(response => response.json())
        .then(data => {
            if (data && data.length > 0) {
                renderLogsToTable(data);
            }
        })
        .catch(err => console.error("Error fetching current logs:", err));
}

function pollSuricataAlerts() {
    fetch('/api/suricata/alerts', { credentials: 'same-origin' })
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('#suricata tbody');
            if (!tbody || !data || data.length === 0) return;

            let html = '';
            data.forEach(alert => {
                html += `
                    <tr>
                        <td>${escapeHtml(alert.timestamp)}</td>
                        <td><code>${escapeHtml(alert.src_ip)}</code></td>
                        <td>${escapeHtml(alert.signature)}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        })
        .catch(err => console.error("Error polling Suricata alerts:", err));
}

function loadCowrieFiles() {
    fetch('/api/cowrie/files', { credentials: 'same-origin' })
        .then(res => res.json())
        .then(files => {
            const group = document.getElementById('file-list-group');
            if (!group) return;
            
            let html = `
                <button class="list-group-item list-group-item-action file-item active mb-1 rounded border" id="btn-current-logs" onclick="switchToCurrentLogs()">
                    <i class="fa-solid fa-file-waveform text-success me-2"></i> <strong>Current Logs</strong>
                </button>
            `;

            if (files && files.length > 0) {
                files.forEach(f => {
                    html += `
                        <button class="list-group-item list-group-item-action file-item mb-1 rounded border" onclick="loadHistoricalFile('${f.filename}', this)">
                            <i class="fa-regular fa-file-lines me-2 text-info"></i> ${escapeHtml(f.filename)}  
                            <br><small class="text-muted ms-4">(${Math.round(f.size/1024)} KB)</small>
                        </button>
                    `;
                });
            }
            group.innerHTML = html;
        });
}

function switchToCurrentLogs() {
    isCurrentLogsView = true;
    expandedSessions.clear();
    document.getElementById('active-view-title').innerHTML = '<i class="fa-solid fa-file-waveform me-2"></i> Current Cowrie Logs';
    document.getElementById('log-status-badge').style.display = 'inline-block';
    
    document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
    document.getElementById('btn-current-logs').classList.add('active');
    
    pollCurrentLogs();
}

function loadHistoricalFile(filename, btnElement) {
    isCurrentLogsView = false;
    expandedSessions.clear();
    document.getElementById('active-view-title').innerHTML = `<i class="fa-solid fa-file-shield me-2"></i> Archive: ${escapeHtml(filename)}`;
    document.getElementById('log-status-badge').style.display = 'none';

    document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
    if (btnElement) btnElement.classList.add('active');

    document.getElementById('cowrie-log-table').innerHTML = '<tr><td colspan="4" class="text-center text-muted py-5">Loading archive contents...</td></tr>';

    fetch(`/api/cowrie/file/${filename}`, { credentials: 'same-origin' })
        .then(res => res.json())
        .then(data => {
            renderLogsToTable(data);
        })
        .catch(err => {
            document.getElementById('cowrie-log-table').innerHTML = '<tr><td colspan="4" class="text-center text-danger py-5">Error loading file contents.</td></tr>';
        });
}

document.addEventListener('DOMContentLoaded', () => {
    loadCowrieFiles();
    pollInterval = setInterval(() => {
        pollCurrentLogs();
        pollSuricataAlerts();
    }, 3000);
});
