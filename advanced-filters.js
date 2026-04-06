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

    loadPresets() {
        this.presets = {
            balanced:     { min_whale_score: 50, min_volume: 100, min_dte: 7,  max_dte: 45 },
            aggressive:   { min_whale_score: 70, min_iv: 50,  min_volume: 500, max_dte: 21 },
            conservative: { min_whale_score: 40, max_iv: 80,  min_dte: 14,    max_dte: 60 },
            high_iv:      { min_iv: 80, min_whale_score: 40 },
            near_term:    { max_dte: 14, min_volume: 100 },
            medium_term:  { min_dte: 15, max_dte: 60 }
        };
        console.log('Presets loaded (local):', this.presets);
    }

    applyFilters(opportunities, filters) {
        const result = opportunities.filter(opp => {
            if (filters.min_price      != null && (opp.option_price  || 0) < filters.min_price)      return false;
            if (filters.max_price      != null && (opp.option_price  || 0) > filters.max_price)      return false;
            if (filters.min_strike     != null && (opp.strike        || 0) < filters.min_strike)     return false;
            if (filters.max_strike     != null && (opp.strike        || 0) > filters.max_strike)     return false;
            if (filters.min_dte        != null && (opp.dte           || 0) < filters.min_dte)        return false;
            if (filters.max_dte        != null && (opp.dte           || 0) > filters.max_dte)        return false;
            if (filters.min_iv         != null && (opp.iv            || 0) * 100 < filters.min_iv)   return false;
            if (filters.max_iv         != null && (opp.iv            || 0) * 100 > filters.max_iv)   return false;
            if (filters.min_volume     != null && (opp.volume        || 0) < filters.min_volume)     return false;
            if (filters.max_volume     != null && (opp.volume        || 0) > filters.max_volume)     return false;
            if (filters.min_whale_score != null && (opp.whale_score  || 0) < filters.min_whale_score) return false;
            if (filters.max_whale_score != null && (opp.whale_score  || 0) > filters.max_whale_score) return false;
            return true;
        });
        console.log(`Filters applied: ${opportunities.length} → ${result.length}`);
        return result;
    }

    applyPreset(opportunities, presetName) {
        const presetFilters = this.presets[presetName] || {};
        return this.applyFilters(opportunities, presetFilters);
    }

    sortOpportunities(opportunities, sortBy = 'whale_score', ascending = false) {
        const fieldMap = {
            whale_score: 'whale_score', volume: 'volume', price: 'option_price',
            dte: 'dte', delta: 'delta', iv: 'iv', oi: 'open_interest', strike: 'strike'
        };
        const field = fieldMap[sortBy] || sortBy;
        return [...opportunities].sort((a, b) => {
            const va = a[field] ?? 0;
            const vb = b[field] ?? 0;
            return ascending ? va - vb : vb - va;
        });
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

function applyFiltersFromUI() {
    const filterManager = window.filterManager;
    if (!filterManager || !currentOptions) return;
    
    const filters = filterManager.buildFiltersFromUI();
    let results = filterManager.applyFilters(currentOptions, filters);
    
    // Apply sorting
    const sortBy = document.getElementById('sort-by-select')?.value || 'whale_score';
    const ascending = document.getElementById('sort-ascending')?.checked || false;
    results = filterManager.sortOpportunities(results, sortBy, ascending);
    
    filteredOptions = results;
    updateFilterStats(results);
    renderOptions(results);
}

function applyPresetFilter(presetName) {
    const filterManager = window.filterManager;
    if (!filterManager || !currentOptions) return;
    
    console.log(`Applying preset: ${presetName}`);
    
    let results = filterManager.applyPreset(currentOptions, presetName);
    
    const sortBy = document.getElementById('sort-by-select')?.value || 'whale_score';
    const ascending = document.getElementById('sort-ascending')?.checked || false;
    results = filterManager.sortOpportunities(results, sortBy, ascending);
    
    filteredOptions = results;
    updateFilterStats(results);
    renderOptions(results);
    
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
