// frontend/script.js - API calls & UI updates

// ==================== Configuration ====================
const API_BASE_URL = 'http://localhost:8000';

// ==================== State ====================
let currentUser = null;
let apiKey = localStorage.getItem('cg_api_key') || '';

// ==================== API Helper ====================
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const headers = {
        'Content-Type': 'application/json',
        ...(apiKey ? { 'X-API-Key': apiKey } : {}),
        ...options.headers
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `HTTP error ${response.status}`);
        }

        return data;
    } catch (error) {
        if (error.message.includes('Failed to fetch')) {
            throw new Error('Cannot connect to server. Make sure the backend is running on port 8000.');
        }
        throw error;
    }
}

// ==================== Toast Notifications ====================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== Authentication ====================
async function handleLogin() {
    const input = document.getElementById('api-key-input');
    const key = input.value.trim();

    if (!key) {
        showToast('Please enter an API key', 'error');
        return;
    }

    try {
        // Test the API key
        apiKey = key;
        const user = await apiRequest('/me');
        
        currentUser = user;
        localStorage.setItem('cg_api_key', key);
        
        document.getElementById('login-modal').classList.add('hidden');
        document.getElementById('main-app').classList.remove('hidden');
        
        updateUI();
        loadHistory();
        showToast(`Welcome, ${user.username}!`, 'success');
    } catch (error) {
        apiKey = '';
        showToast(error.message, 'error');
    }
}

function handleLogout() {
    currentUser = null;
    apiKey = '';
    localStorage.removeItem('cg_api_key');
    
    document.getElementById('login-modal').classList.remove('hidden');
    document.getElementById('main-app').classList.add('hidden');
    document.getElementById('api-key-input').value = '';
    
    showToast('Logged out successfully', 'info');
}

// ==================== UI Updates ====================
function updateUI() {
    if (!currentUser) return;

    // Update header
    document.getElementById('current-user').textContent = currentUser.username;
    document.getElementById('credit-display').textContent = currentUser.credits;
    
    const roleBadge = document.getElementById('role-badge');
    roleBadge.textContent = currentUser.role;
    roleBadge.className = `role-badge ${currentUser.role}`;

    // Show/hide admin tabs
    document.querySelectorAll('.nav-tab.admin-only').forEach(tab => {
        if (currentUser.role === 'admin') {
            tab.classList.add('visible');
        } else {
            tab.classList.remove('visible');
        }
    });
}

async function refreshCredits() {
    try {
        const data = await apiRequest('/credits');
        currentUser.credits = data.credits;
        document.getElementById('credit-display').textContent = data.credits;
    } catch (error) {
        console.error('Failed to refresh credits:', error);
    }
}

// ==================== Tab Navigation ====================
function switchTab(tabName) {
    // Hide all panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.add('hidden');
    });

    // Remove active from all tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected panel
    document.getElementById(`panel-${tabName}`).classList.remove('hidden');
    document.getElementById(`tab-${tabName}`).classList.add('active');

    // Load data for the tab
    switch (tabName) {
        case 'history':
            loadHistory();
            break;
        case 'rules':
            loadRules();
            break;
        case 'users':
            loadUsers();
            break;
        case 'audit':
            loadAuditLogs();
            break;
    }
}

// ==================== Commands ====================
async function submitCommand() {
    const input = document.getElementById('command-input');
    const command = input.value.trim();

    if (!command) {
        showToast('Please enter a command', 'error');
        return;
    }

    const submitBtn = document.querySelector('.submit-btn');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="spinner"></span> Executing...';
    submitBtn.disabled = true;

    try {
        const result = await apiRequest('/commands', {
            method: 'POST',
            body: JSON.stringify({ command })
        });

        displayResult(command, result);
        input.value = '';
        
        // Update credits
        if (result.credits_remaining !== undefined) {
            currentUser.credits = result.credits_remaining;
            document.getElementById('credit-display').textContent = result.credits_remaining;
        }

        // Refresh history
        loadHistory();
        loadRecentCommands();

        showToast(
            result.status === 'executed' ? 'Command executed' : 'Command rejected',
            result.status === 'executed' ? 'success' : 'error'
        );
    } catch (error) {
        showToast(error.message, 'error');
        displayResult(command, {
            status: 'rejected',
            message: error.message
        });
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

function displayResult(command, result) {
    const resultBox = document.getElementById('command-result');
    const isSuccess = result.status === 'executed';
    
    let outputHtml = '';
    if (result.command && result.command.result) {
        outputHtml = `<pre style="margin-top: 0.5rem; white-space: pre-wrap; color: var(--text-secondary);">${escapeHtml(result.command.result)}</pre>`;
    }

    resultBox.innerHTML = `
        <div class="result-command">
            <span class="prompt">$</span> ${escapeHtml(command)}
        </div>
        <div class="result-output ${isSuccess ? 'success' : 'error'}">
            <div class="result-status ${result.status}">[${result.status.toUpperCase()}]</div>
            <div>${escapeHtml(result.message || '')}</div>
            ${outputHtml}
        </div>
    `;
}

function setCommand(cmd) {
    document.getElementById('command-input').value = cmd;
    document.getElementById('command-input').focus();
}

async function loadRecentCommands() {
    const container = document.getElementById('recent-commands');
    
    try {
        const data = await apiRequest('/history?limit=5');
        
        if (data.commands.length === 0) {
            container.innerHTML = '<p class="empty-state">No commands submitted yet</p>';
            return;
        }

        container.innerHTML = data.commands.map(cmd => `
            <div class="recent-item">
                <span class="command">${escapeHtml(cmd.command_text)}</span>
                <span class="status-badge ${cmd.status}">${cmd.status}</span>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<p class="empty-state">Failed to load recent commands</p>';
    }
}

// ==================== History ====================
async function loadHistory() {
    const tbody = document.getElementById('history-table');
    const filter = document.getElementById('history-filter')?.value || 'all';

    try {
        // Use admin endpoint if admin, otherwise regular history
        const endpoint = currentUser?.role === 'admin' ? '/commands/all' : '/history';
        const data = await apiRequest(`${endpoint}?limit=100`);
        
        let commands = data.commands;
        
        // Apply filter
        if (filter !== 'all') {
            commands = commands.filter(cmd => cmd.status === filter);
        }

        if (commands.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No commands found</td></tr>';
            return;
        }

        tbody.innerHTML = commands.map(cmd => `
            <tr>
                <td>#${cmd.id}</td>
                <td class="mono truncate" title="${escapeHtml(cmd.command_text)}">${escapeHtml(cmd.command_text)}</td>
                <td><span class="status-badge ${cmd.status}">${cmd.status}</span></td>
                <td>${cmd.credits_deducted ? '-2' : '0'}</td>
                <td>${formatDate(cmd.created_at)}</td>
            </tr>
        `).join('');

        // Also update recent commands
        loadRecentCommands();
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Error: ${error.message}</td></tr>`;
    }
}

// ==================== Rules ====================
async function loadRules() {
    const tbody = document.getElementById('rules-table');

    try {
        const data = await apiRequest('/rules');
        
        if (data.rules.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No rules defined</td></tr>';
            return;
        }

        tbody.innerHTML = data.rules.map(rule => `
            <tr>
                <td>${rule.priority}</td>
                <td class="mono truncate" title="${escapeHtml(rule.pattern)}">${escapeHtml(rule.pattern)}</td>
                <td>
                    <span class="action-badge ${rule.action === 'AUTO_ACCEPT' ? 'accept' : 'reject'}">
                        ${rule.action}
                    </span>
                </td>
                <td>
                    ${currentUser?.role === 'admin' ? 
                        `<span class="link danger" onclick="deleteRule(${rule.id})">Delete</span>` : 
                        ''
                    }
                </td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-state">Error: ${error.message}</td></tr>`;
    }
}

async function addRule() {
    const pattern = document.getElementById('rule-pattern').value.trim();
    const action = document.getElementById('rule-action').value;
    const priority = parseInt(document.getElementById('rule-priority').value) || 10;

    if (!pattern) {
        showToast('Pattern is required', 'error');
        return;
    }

    try {
        await apiRequest('/rules', {
            method: 'POST',
            body: JSON.stringify({ pattern, action, priority })
        });

        document.getElementById('rule-pattern').value = '';
        document.getElementById('rule-priority').value = '10';
        
        loadRules();
        showToast('Rule created', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteRule(ruleId) {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    try {
        await apiRequest(`/rules/${ruleId}`, { method: 'DELETE' });
        loadRules();
        showToast('Rule deleted', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ==================== Users ====================
async function loadUsers() {
    const tbody = document.getElementById('users-table');

    try {
        const data = await apiRequest('/users');
        
        if (data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No users found</td></tr>';
            return;
        }

        tbody.innerHTML = data.users.map(user => `
            <tr>
                <td>${escapeHtml(user.username)}</td>
                <td><span class="role-badge ${user.role}">${user.role}</span></td>
                <td class="mono">${user.credits}</td>
                <td>${user.command_count || 0}</td>
                <td>
                    <span class="link" onclick="openCreditModal(${user.id}, ${user.credits})">Adjust Credits</span>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Error: ${error.message}</td></tr>`;
    }
}

async function createUser() {
    const username = document.getElementById('new-username').value.trim();
    const role = document.getElementById('new-user-role').value;
    const credits = parseInt(document.getElementById('new-user-credits').value) || 100;

    if (!username) {
        showToast('Username is required', 'error');
        return;
    }

    try {
        const result = await apiRequest('/users', {
            method: 'POST',
            body: JSON.stringify({ username, role, credits })
        });

        // Show API key
        document.getElementById('new-api-key').textContent = result.user.api_key;
        document.getElementById('new-api-key-display').classList.remove('hidden');

        document.getElementById('new-username').value = '';
        
        loadUsers();
        showToast('User created', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function openCreditModal(userId, currentCredits) {
    document.getElementById('credit-user-id').value = userId;
    document.getElementById('credit-amount').value = currentCredits;
    document.getElementById('credit-modal').classList.remove('hidden');
}

function closeCreditModal() {
    document.getElementById('credit-modal').classList.add('hidden');
}

async function saveCredits() {
    const userId = document.getElementById('credit-user-id').value;
    const credits = parseInt(document.getElementById('credit-amount').value);

    try {
        await apiRequest(`/users/${userId}/credits`, {
            method: 'PUT',
            body: JSON.stringify({ credits })
        });

        closeCreditModal();
        loadUsers();
        
        // Refresh current user credits if adjusting self
        if (currentUser && currentUser.id == userId) {
            await refreshCredits();
        }
        
        showToast('Credits updated', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ==================== Audit Logs ====================
async function loadAuditLogs() {
    const tbody = document.getElementById('audit-table');

    try {
        const data = await apiRequest('/audit-logs?limit=100');
        
        if (data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No audit logs found</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.map(log => `
            <tr>
                <td>${formatDate(log.created_at)}</td>
                <td>${escapeHtml(log.username || 'System')}</td>
                <td><span class="action-badge">${log.action}</span></td>
                <td class="mono truncate" title="${escapeHtml(log.command_text || '')}">${escapeHtml(log.command_text || '-')}</td>
                <td class="truncate" title="${escapeHtml(log.details || '')}">${escapeHtml(log.details || '-')}</td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Error: ${error.message}</td></tr>`;
    }
}

function exportAuditLogs() {
    // Simple CSV export
    apiRequest('/audit-logs?limit=1000')
        .then(data => {
            const headers = ['Timestamp', 'User', 'Action', 'Command', 'Details'];
            const rows = data.logs.map(log => [
                log.created_at,
                log.username || 'System',
                log.action,
                log.command_text || '',
                log.details || ''
            ]);

            const csv = [
                headers.join(','),
                ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
            ].join('\n');

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);

            showToast('Audit logs exported', 'success');
        })
        .catch(error => {
            showToast(error.message, 'error');
        });
}

// ==================== Utilities ====================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString();
}

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    // Check for saved API key
    if (apiKey) {
        // Try to authenticate with saved key
        apiRequest('/me')
            .then(user => {
                currentUser = user;
                document.getElementById('login-modal').classList.add('hidden');
                document.getElementById('main-app').classList.remove('hidden');
                updateUI();
                loadHistory();
                loadRecentCommands();
            })
            .catch(() => {
                // Invalid saved key, show login
                apiKey = '';
                localStorage.removeItem('cg_api_key');
            });
    }

    // Event listeners
    document.getElementById('command-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') submitCommand();
    });

    document.getElementById('api-key-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });
});
