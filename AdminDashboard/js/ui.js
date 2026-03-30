function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-API-KEY': API_KEY,
        'ngrok-skip-browser-warning': 'true'
    };
}

function switchTab(tabId) {
    // Hide all panels
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    
    // Show target panel
    const targetPanel = document.getElementById(tabId);
    if(targetPanel) {
        targetPanel.classList.remove('hidden');
    }

    // Update sidebar active state
    document.querySelectorAll('.pc-item').forEach(el => el.classList.remove('active'));
    const activeLink = document.querySelector(`a[onclick*="switchTab('${tabId}')"]`);
    if(activeLink && activeLink.closest('.pc-item')) {
        activeLink.closest('.pc-item').classList.add('active');
    }
    
    // Load Data based on newly selected Tab
    if (!NGROK_URL || !API_KEY) return;
    
    // OPERATIONS TABS
    if (tabId === 'tab-products') {
        if(typeof fetchProducts === 'function') fetchProducts();
    }
    else if (tabId === 'tab-campaigns') {
        if(typeof fetchCampaigns === 'function') fetchCampaigns();
    }
    else if (tabId === 'tab-scripts') {
        if(typeof fetchVideoScripts === 'function') fetchVideoScripts();
    }
    else if (tabId === 'tab-models') {
        // Models is now using DataTables
        if(typeof fetchModels === 'function') fetchModels();
    }
    else if (tabId === 'tab-music') {
        if(typeof fetchMusicLibrary === 'function') fetchMusicLibrary();
    }
    
    // TECHNICAL TABS
    else if (tabId === 'tab-radar') {
        if(typeof fetchRadarLogs === 'function') fetchRadarLogs();
    }
    else if (tabId === 'tab-policies') {
        if(typeof fetchPolicies === 'function') fetchPolicies();
    }
    else if (tabId === 'tab-scoring') {
        if(typeof fetchScoringRules === 'function') fetchScoringRules();
    }
    else if (tabId === 'tab-configs') {
        if(typeof fetchConfigs === 'function') fetchConfigs();
    }
}
