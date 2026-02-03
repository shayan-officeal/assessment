/**
 * Atomic Wallet - Frontend Application
 * 
 * A modern JavaScript application for the wallet dashboard.
 * Connects to Django REST Framework backend with Basic Authentication.
 */

// ==========================================================================
// Configuration
// ==========================================================================

const API_BASE_URL = 'http://localhost:8000/api/wallet';

// ==========================================================================
// State Management
// ==========================================================================

const state = {
    isAuthenticated: false,
    credentials: null,
    user: null,
    balance: '0.00',
    transactions: [],
    users: []
};

// ==========================================================================
// DOM Elements
// ==========================================================================

const elements = {
    // Sections
    loginSection: document.getElementById('login-section'),
    dashboardSection: document.getElementById('dashboard-section'),

    // Login
    loginForm: document.getElementById('login-form'),
    usernameInput: document.getElementById('username'),
    passwordInput: document.getElementById('password'),
    loginError: document.getElementById('login-error'),

    // Dashboard
    navUsername: document.getElementById('nav-username'),
    logoutBtn: document.getElementById('logout-btn'),

    // Balance
    balanceValue: document.getElementById('balance-value'),
    refreshBalanceBtn: document.getElementById('refresh-balance'),

    // Actions
    showTransferBtn: document.getElementById('show-transfer-btn'),
    showDepositBtn: document.getElementById('show-deposit-btn'),

    // Transfer
    transferCard: document.getElementById('transfer-card'),
    closeTransferBtn: document.getElementById('close-transfer'),
    transferForm: document.getElementById('transfer-form'),
    receiverSelect: document.getElementById('receiver'),
    amountInput: document.getElementById('amount'),
    transferMessage: document.getElementById('transfer-message'),

    // Deposit
    depositCard: document.getElementById('deposit-card'),
    closeDepositBtn: document.getElementById('close-deposit'),
    depositForm: document.getElementById('deposit-form'),
    depositAmountInput: document.getElementById('deposit-amount'),
    depositMessage: document.getElementById('deposit-message'),

    // History
    transactionsList: document.getElementById('transactions-list'),
    refreshHistoryBtn: document.getElementById('refresh-history'),

    // Toast
    toastContainer: document.getElementById('toast-container')
};

// ==========================================================================
// API Functions
// ==========================================================================

/**
 * Make an authenticated API request
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (state.credentials) {
        headers['Authorization'] = `Basic ${state.credentials}`;
    }

    try {
        const response = await fetch(url, {
            ...options,
            headers,
            credentials: 'include'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || data.detail || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Authenticate user
 */
async function login(username, password) {
    state.credentials = btoa(`${username}:${password}`);

    try {
        const data = await apiRequest('/balance/');
        state.isAuthenticated = true;
        state.user = {
            id: data.user_id,
            username: data.username
        };
        state.balance = data.balance;
        return true;
    } catch (error) {
        state.credentials = null;
        state.isAuthenticated = false;
        throw error;
    }
}

/**
 * Fetch wallet balance
 */
async function fetchBalance() {
    const data = await apiRequest('/balance/');
    state.balance = data.balance;
    return data.balance;
}

/**
 * Fetch user list
 */
async function fetchUsers() {
    const data = await apiRequest('/users/');
    state.users = data.users;
    return data.users;
}

/**
 * Fetch transaction history
 */
async function fetchTransactions() {
    const data = await apiRequest('/transactions/');
    state.transactions = data.transactions;
    return data.transactions;
}

/**
 * Transfer funds
 */
async function transfer(receiverId, amount) {
    return await apiRequest('/transfer/', {
        method: 'POST',
        body: JSON.stringify({
            receiver_id: parseInt(receiverId),
            amount: amount
        })
    });
}

/**
 * Deposit funds
 */
async function deposit(amount) {
    return await apiRequest('/deposit/', {
        method: 'POST',
        body: JSON.stringify({ amount })
    });
}

// ==========================================================================
// UI Functions
// ==========================================================================

/**
 * Show a toast notification
 */
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success'
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';

    toast.innerHTML = `${icon}<span>${message}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    return parseFloat(amount).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Format timestamp
 */
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Update balance display
 */
function updateBalanceDisplay() {
    elements.balanceValue.textContent = formatCurrency(state.balance);
}

/**
 * Populate users dropdown
 */
function populateUsersDropdown() {
    elements.receiverSelect.innerHTML = '<option value="">Select a recipient...</option>';

    state.users.forEach(user => {
        const option = document.createElement('option');
        option.value = user.id;
        option.textContent = user.username;
        elements.receiverSelect.appendChild(option);
    });
}

/**
 * Render transaction history
 */
function renderTransactions() {
    if (state.transactions.length === 0) {
        elements.transactionsList.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
                    <rect x="9" y="3" width="6" height="4" rx="2"/>
                    <path d="M9 12h6"/>
                    <path d="M9 16h6"/>
                </svg>
                <p>No transactions yet</p>
            </div>
        `;
        return;
    }

    elements.transactionsList.innerHTML = state.transactions.map(tx => {
        const isSent = tx.type === 'sent';
        const iconClass = isSent ? 'sent' : 'received';
        const amountClass = isSent ? 'sent' : 'received';
        const amountPrefix = isSent ? '-' : '+';
        const actionText = isSent ? `To ${tx.counterparty}` : `From ${tx.counterparty}`;

        const icon = isSent
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>'
            : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>';

        return `
            <div class="transaction-item">
                <div class="transaction-info">
                    <div class="transaction-icon ${iconClass}">
                        ${icon}
                    </div>
                    <div class="transaction-details">
                        <h4>${actionText}</h4>
                        <p>${formatTimestamp(tx.timestamp)}</p>
                    </div>
                </div>
                <span class="transaction-amount ${amountClass}">
                    ${amountPrefix}$${formatCurrency(tx.amount)}
                </span>
            </div>
        `;
    }).join('');
}

/**
 * Show dashboard
 */
async function showDashboard() {
    elements.loginSection.classList.add('hidden');
    elements.dashboardSection.classList.remove('hidden');

    elements.navUsername.textContent = `Welcome, ${state.user.username}`;

    // Load initial data
    try {
        updateBalanceDisplay();
        await Promise.all([fetchUsers(), fetchTransactions()]);
        populateUsersDropdown();
        renderTransactions();
    } catch (error) {
        showToast('Failed to load data', 'error');
    }
}

/**
 * Show login
 */
function showLogin() {
    elements.dashboardSection.classList.add('hidden');
    elements.loginSection.classList.remove('hidden');

    // Reset state
    state.isAuthenticated = false;
    state.credentials = null;
    state.user = null;
    state.balance = '0.00';
    state.transactions = [];
    state.users = [];

    // Clear forms
    elements.loginForm.reset();
    elements.loginError.classList.add('hidden');
}

/**
 * Show message in form
 */
function showMessage(element, message, type = 'success') {
    element.textContent = message;
    element.className = `message ${type}`;
    element.classList.remove('hidden');

    setTimeout(() => {
        element.classList.add('hidden');
    }, 5000);
}

// ==========================================================================
// Event Handlers
// ==========================================================================

// Login form submit
elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = elements.usernameInput.value.trim();
    const password = elements.passwordInput.value;

    const submitBtn = elements.loginForm.querySelector('button[type="submit"]');
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    try {
        await login(username, password);
        showDashboard();
        showToast(`Welcome back, ${state.user.username}!`);
    } catch (error) {
        elements.loginError.textContent = error.message || 'Invalid credentials';
        elements.loginError.classList.remove('hidden');
    } finally {
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    }
});

// Logout
elements.logoutBtn.addEventListener('click', () => {
    showLogin();
    showToast('Logged out successfully');
});

// Refresh balance
elements.refreshBalanceBtn.addEventListener('click', async () => {
    elements.refreshBalanceBtn.classList.add('loading');
    try {
        await fetchBalance();
        updateBalanceDisplay();
        showToast('Balance updated');
    } catch (error) {
        showToast('Failed to refresh balance', 'error');
    } finally {
        elements.refreshBalanceBtn.classList.remove('loading');
    }
});

// Show transfer form
elements.showTransferBtn.addEventListener('click', () => {
    elements.transferCard.classList.remove('hidden');
    elements.depositCard.classList.add('hidden');
});

// Hide transfer form
elements.closeTransferBtn.addEventListener('click', () => {
    elements.transferCard.classList.add('hidden');
    elements.transferForm.reset();
    elements.transferMessage.classList.add('hidden');
});

// Show deposit form
elements.showDepositBtn.addEventListener('click', () => {
    elements.depositCard.classList.remove('hidden');
    elements.transferCard.classList.add('hidden');
});

// Hide deposit form
elements.closeDepositBtn.addEventListener('click', () => {
    elements.depositCard.classList.add('hidden');
    elements.depositForm.reset();
    elements.depositMessage.classList.add('hidden');
});

// Transfer form submit
elements.transferForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const receiverId = elements.receiverSelect.value;
    const amount = elements.amountInput.value;

    if (!receiverId) {
        showMessage(elements.transferMessage, 'Please select a recipient', 'error');
        return;
    }

    const submitBtn = elements.transferForm.querySelector('button[type="submit"]');
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    try {
        const result = await transfer(receiverId, amount);

        // Update balance and transactions
        await fetchBalance();
        await fetchTransactions();
        updateBalanceDisplay();
        renderTransactions();

        showMessage(elements.transferMessage, `Transfer successful! Transaction #${result.transaction_id}`, 'success');
        showToast(`Sent $${formatCurrency(amount)} successfully!`);

        elements.transferForm.reset();
    } catch (error) {
        showMessage(elements.transferMessage, error.message || 'Transfer failed', 'error');
        showToast(error.message || 'Transfer failed', 'error');
    } finally {
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    }
});

// Deposit form submit
elements.depositForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const amount = elements.depositAmountInput.value;

    const submitBtn = elements.depositForm.querySelector('button[type="submit"]');
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    try {
        await deposit(amount);

        // Update balance
        await fetchBalance();
        updateBalanceDisplay();

        showMessage(elements.depositMessage, `Deposited $${formatCurrency(amount)} successfully!`, 'success');
        showToast(`Deposited $${formatCurrency(amount)}!`);

        elements.depositForm.reset();
    } catch (error) {
        showMessage(elements.depositMessage, error.message || 'Deposit failed', 'error');
        showToast(error.message || 'Deposit failed', 'error');
    } finally {
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    }
});

// Refresh history
elements.refreshHistoryBtn.addEventListener('click', async () => {
    elements.refreshHistoryBtn.classList.add('loading');
    try {
        await fetchTransactions();
        renderTransactions();
        showToast('History updated');
    } catch (error) {
        showToast('Failed to refresh history', 'error');
    } finally {
        elements.refreshHistoryBtn.classList.remove('loading');
    }
});

// ==========================================================================
// Initialize
// ==========================================================================

// Check for saved credentials (optional - for demo purposes)
document.addEventListener('DOMContentLoaded', () => {
    // Start with login screen
    showLogin();
});
