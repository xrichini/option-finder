/**
 * Advanced Filtering Module
 * Manages filter UI, presets, and real-time filtering
 */

class AdvancedFilterManager {
    constructor() {
        this.presets = {};
        this.currentFilters = {};
        this.filterPresets = [
            'balanced', 'aggressive', 'conservative', 
            'high_iv', 'near_term', 'medium_term'
        ];
        this.loadPresets();
    }

    async loadPresets() {
        try {
            const response = await fetch('/api/filtering/presets');
            if (response.ok) {
                this.presets = await response.json();
                console.log('Presets loaded:', this.presets);
            }
        } catch (error) {
            console.error('Error loading presets:', error);
        }
    }

    async applyFilters(opportunities, filters) {
        try {
            const response = await fetch('/api/filtering/apply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    opportunities: opportunities,
                    filters: filters
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log(`Filters applied: ${result.original_count} → ${result.filtered_count}`);
                return result.opportunities;
            }
        } catch (error) {
            console.error('Error applying filters:', error);
            return opportunities;
        }
    }

    async applyPreset(opportunities, presetName) {
        try {
            const response = await fetch(`/api/filtering/apply-preset?preset_name=${presetName}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(opportunities)
            });
            
            if (response.ok) {
                const result = await response.json();
                return result.opportunities;
            }
        } catch (error) {
            console.error('Error applying preset:', error);
            return opportunities;
        }
    }

    async sortOpportunities(opportunities, sortBy = 'whale_score', ascending = false) {
        try {
            const params = new URLSearchParams({
                sort_by: sortBy,
                ascending: ascending
            });
            
            const response = await fetch(`/api/filtering/sort?${params}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(opportunities)
            });
            
            if (response.ok) {
                const result = await response.json();
                return result.opportunities;
            }
        } catch (error) {
            console.error('Error sorting opportunities:', error);
            return opportunities;
        }
    }

    getPresetDetails(presetName) {
        return this.presets[presetName] || null;
    }

    getAllPresets() {
        return this.presets;
    }

    // Build filter object from UI inputs
    buildFiltersFromUI() {
        return {
            min_strike: this.getInputValue('filter-min-strike'),
            max_strike: this.getInputValue('filter-max-strike'),
            min_dte: this.getInputValue('filter-min-dte'),
            max_dte: this.getInputValue('filter-max-dte'),
            min_iv: this.getInputValue('filter-min-iv'),
            max_iv: this.getInputValue('filter-max-iv'),
            min_volume: this.getInputValue('filter-min-volume'),
            max_volume: this.getInputValue('filter-max-volume'),
            min_whale_score: this.getInputValue('filter-min-whale-score'),
            max_whale_score: this.getInputValue('filter-max-whale-score'),
            min_price: this.getInputValue('filter-min-price'),
            max_price: this.getInputValue('filter-max-price')
        };
    }

    getInputValue(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return null;
        const value = element.value;
        return value === '' ? null : parseFloat(value) || value;
    }

    saveFiltersToLocalStorage(filters) {
        localStorage.setItem('savedFilters', JSON.stringify(filters));
    }

    loadFiltersFromLocalStorage() {
        const saved = localStorage.getItem('savedFilters');
        return saved ? JSON.parse(saved) : null;
    }

    resetFilters() {
        document.querySelectorAll('[id^="filter-"]').forEach(input => {
            input.value = '';
        });
        this.currentFilters = {};
    }
}

/**
 * WebSocket Manager for Real-Time Updates
 */
class WebSocketManager {
    constructor(onMessage = null) {
        this.ws = null;
        this.onMessage = onMessage;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.isConnecting = false;
    }

    connect() {
        if (this.ws || this.isConnecting) return;
        
        this.isConnecting = true;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('WebSocket message:', message);
                    if (this.onMessage) {
                        this.onMessage(message);
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.ws = null;
                this.isConnecting = false;
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            this.isConnecting = false;
            this.attemptReconnect();
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.warn('Max reconnect attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        console.log(`Attempting reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => this.connect(), delay);
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, queuing message');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('ws-connection-status');
        if (indicator) {
            indicator.className = connected ? 'connected' : 'disconnected';
            indicator.title = connected ? 'Connected' : 'Disconnected';
        }
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

/**
 * Initialize Advanced Filtering UI
 */
function initializeAdvancedFilters() {
    // Create filter panel if it doesn't exist
    createFilterPanel();
    
    // Load saved filters
    const filterManager = window.filterManager || new AdvancedFilterManager();
    window.filterManager = filterManager;
    
    // Setup filter event listeners
    setupFilterEventListeners();
    
    // Setup preset buttons
    setupPresetButtons();
    
    console.log('Advanced filtering initialized');
}

function createFilterPanel() {
    const filterPanel = document.getElementById('advanced-filter-panel');
    if (filterPanel) return; // Already exists
    
    const panel = document.createElement('div');
    panel.id = 'advanced-filter-panel';
    panel.className = 'advanced-filter-panel';
    panel.innerHTML = `
        <div class="filter-header">
            <h3>Filtres Avancés</h3>
            <button id="toggle-filters" class="toggle-btn">▼</button>
        </div>
        
        <div class="filter-content" id="filter-content" style="display: none;">
            <!-- Presets -->
            <div class="filter-section">
                <label>Presets</label>
                <div class="preset-buttons">
                    <button class="preset-btn" data-preset="balanced">Équilibré</button>
                    <button class="preset-btn" data-preset="aggressive">Agressif</button>
                    <button class="preset-btn" data-preset="conservative">Conservateur</button>
                    <button class="preset-btn" data-preset="high_iv">IV Élevée</button>
                    <button class="preset-btn" data-preset="near_term">Court Terme</button>
                    <button class="preset-btn" data-preset="medium_term">Moyen Terme</button>
                </div>
            </div>
            
            <!-- Price Range -->
            <div class="filter-row">
                <div class="filter-col">
                    <label>Prix Min ($)</label>
                    <input type="number" id="filter-min-price" step="0.1" placeholder="0">
                </div>
                <div class="filter-col">
                    <label>Prix Max ($)</label>
                    <input type="number" id="filter-max-price" step="0.1" placeholder="100">
                </div>
            </div>
            
            <!-- Strike Range -->
            <div class="filter-row">
                <div class="filter-col">
                    <label>Strike Min</label>
                    <input type="number" id="filter-min-strike" step="1" placeholder="0">
                </div>
                <div class="filter-col">
                    <label>Strike Max</label>
                    <input type="number" id="filter-max-strike" step="1" placeholder="500">
                </div>
            </div>
            
            <!-- DTE Range -->
            <div class="filter-row">
                <div class="filter-col">
                    <label>DTE Min</label>
                    <input type="number" id="filter-min-dte" min="0" max="365" placeholder="0">
                </div>
                <div class="filter-col">
                    <label>DTE Max</label>
                    <input type="number" id="filter-max-dte" min="0" max="365" placeholder="45">
                </div>
            </div>
            
            <!-- IV Range -->
            <div class="filter-row">
                <div class="filter-col">
                    <label>IV Min (%)</label>
                    <input type="number" id="filter-min-iv" step="1" placeholder="0">
                </div>
                <div class="filter-col">
                    <label>IV Max (%)</label>
                    <input type="number" id="filter-max-iv" step="1" placeholder="300">
                </div>
            </div>
            
            <!-- Volume Range -->
            <div class="filter-row">
                <div class="filter-col">
                    <label>Volume Min</label>
                    <input type="number" id="filter-min-volume" min="0" placeholder="0">
                </div>
                <div class="filter-col">
                    <label>Volume Max</label>
                    <input type="number" id="filter-max-volume" placeholder="999999">
                </div>
            </div>
            
            <!-- Whale Score -->
            <div class="filter-row">
                <div class="filter-col">
                    <label>Score Whale Min</label>
                    <input type="number" id="filter-min-whale-score" min="0" max="100" step="5" placeholder="0">
                </div>
                <div class="filter-col">
                    <label>Score Whale Max</label>
                    <input type="number" id="filter-max-whale-score" min="0" max="100" step="5" placeholder="100">
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div class="filter-actions">
                <button id="apply-filters-btn" class="btn-primary">Appliquer les filtres</button>
                <button id="reset-filters-btn" class="btn-secondary">Réinitialiser</button>
                <button id="save-filters-btn" class="btn-secondary">Enregistrer</button>
                <button id="load-filters-btn" class="btn-secondary">Charger</button>
            </div>
            
            <!-- Sorting -->
            <div class="filter-section">
                <label>Tri</label>
                <div class="sort-controls">
                    <select id="sort-by-select">
                        <option value="whale_score">Score Whale</option>
                        <option value="volume">Volume</option>
                        <option value="price">Prix</option>
                        <option value="dte">DTE</option>
                        <option value="delta">Delta</option>
                        <option value="iv">IV</option>
                        <option value="oi">Open Interest</option>
                        <option value="strike">Strike</option>
                    </select>
                    <label>
                        <input type="checkbox" id="sort-ascending"> Ascendant
                    </label>
                </div>
            </div>
            
            <!-- Stats Display -->
            <div class="filter-stats" id="filter-stats">
                <div class="stat-item">
                    <span class="stat-label">Total:</span>
                    <span class="stat-value" id="stat-total">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Avg Score:</span>
                    <span class="stat-value" id="stat-avg-score">0</span>
                </div>
            </div>
        </div>
    `;
    
    const mainContent = document.querySelector('main') || document.body;
    mainContent.insertBefore(panel, mainContent.firstChild);
}

function setupFilterEventListeners() {
    // Toggle filter panel
    const toggleBtn = document.getElementById('toggle-filters');
    const filterContent = document.getElementById('filter-content');
    
    if (toggleBtn && filterContent) {
        toggleBtn.addEventListener('click', () => {
            const isHidden = filterContent.style.display === 'none';
            filterContent.style.display = isHidden ? 'block' : 'none';
            toggleBtn.textContent = isHidden ? '▲' : '▼';
        });
    }
    
    // Apply filters button
    const applyBtn = document.getElementById('apply-filters-btn');
    if (applyBtn) {
        applyBtn.addEventListener('click', applyFiltersFromUI);
    }
    
    // Reset filters button
    const resetBtn = document.getElementById('reset-filters-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetFiltersUI);
    }
    
    // Save filters button
    const saveBtn = document.getElementById('save-filters-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveFiltersToStorage);
    }
    
    // Load filters button
    const loadBtn = document.getElementById('load-filters-btn');
    if (loadBtn) {
        loadBtn.addEventListener('click', loadFiltersFromStorage);
    }
    
    // Sort dropdown
    const sortSelect = document.getElementById('sort-by-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            applyFiltersFromUI();
        });
    }
    
    const sortAscending = document.getElementById('sort-ascending');
    if (sortAscending) {
        sortAscending.addEventListener('change', () => {
            applyFiltersFromUI();
        });
    }
}

function setupPresetButtons() {
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const preset = btn.dataset.preset;
            applyPresetFilter(preset);
        });
    });
}

async function applyFiltersFromUI() {
    const filterManager = window.filterManager;
    if (!filterManager || !currentOptions) return;
    
    const filters = filterManager.buildFiltersFromUI();
    let results = await filterManager.applyFilters(currentOptions, filters);
    
    // Apply sorting
    const sortBy = document.getElementById('sort-by-select')?.value || 'whale_score';
    const ascending = document.getElementById('sort-ascending')?.checked || false;
    results = await filterManager.sortOpportunities(results, sortBy, ascending);
    
    filteredOptions = results;
    updateFilterStats(results);
    renderOptions(results);
}

async function applyPresetFilter(presetName) {
    const filterManager = window.filterManager;
    if (!filterManager || !currentOptions) return;
    
    console.log(`Applying preset: ${presetName}`);
    
    // Apply the preset
    let results = await filterManager.applyPreset(currentOptions, presetName);
    
    // Apply sorting if configured
    const sortBy = document.getElementById('sort-by-select')?.value || 'whale_score';
    const ascending = document.getElementById('sort-ascending')?.checked || false;
    results = await filterManager.sortOpportunities(results, sortBy, ascending);
    
    filteredOptions = results;
    updateFilterStats(results);
    renderOptions(results);
    
    // Show notification
    showNotification(`Preset "${presetName}" applied: ${results.length} results`);
}

function resetFiltersUI() {
    const filterManager = window.filterManager;
    if (filterManager) {
        filterManager.resetFilters();
        filteredOptions = currentOptions;
        updateFilterStats(currentOptions);
        renderOptions(currentOptions);
        showNotification('Filters reset');
    }
}

function saveFiltersToStorage() {
    const filterManager = window.filterManager;
    if (filterManager) {
        const filters = filterManager.buildFiltersFromUI();
        filterManager.saveFiltersToLocalStorage(filters);
        showNotification('Filters saved to browser');
    }
}

function loadFiltersFromStorage() {
    const filterManager = window.filterManager;
    if (filterManager) {
        const filters = filterManager.loadFiltersFromLocalStorage();
        if (filters) {
            // Populate UI with saved filters
            Object.entries(filters).forEach(([key, value]) => {
                const element = document.getElementById(`filter-${key}`);
                if (element && value !== null) {
                    element.value = value;
                }
            });
            applyFiltersFromUI();
            showNotification('Filters loaded from browser');
        } else {
            showNotification('No saved filters found');
        }
    }
}

function updateFilterStats(opportunities) {
    if (!opportunities || opportunities.length === 0) {
        document.getElementById('stat-total').textContent = '0';
        document.getElementById('stat-avg-score').textContent = '0';
        return;
    }
    
    const totalScore = opportunities.reduce((sum, opp) => sum + (opp.whale_score || 0), 0);
    const avgScore = (totalScore / opportunities.length).toFixed(1);
    
    document.getElementById('stat-total').textContent = opportunities.length;
    document.getElementById('stat-avg-score').textContent = avgScore;
}

function showNotification(message) {
    console.log(message);
    // You can enhance this with a toast notification UI
}

// Export for global use
window.AdvancedFilterManager = AdvancedFilterManager;
window.WebSocketManager = WebSocketManager;
