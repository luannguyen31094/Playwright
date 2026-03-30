// Tab 6: System Configs Logic
let cachedConfigs = [];
let currentConfigId = null;

async function fetchConfigs() {
    if(!NGROK_URL) return;
    const ul = document.getElementById('configList');
    ul.innerHTML = "<li class='text-muted small p-2 text-center'>Đang tải máy chủ...</li>";
    
    try {
        const res = await fetch(`${NGROK_URL}/api/get-data?type=config`, { headers: getHeaders() });
        if(!res.ok) throw new Error("API Lỗi");
        cachedConfigs = await res.json();
        renderConfigsList(cachedConfigs);
    } catch (err) {
        ul.innerHTML = "<li class='text-danger small p-2 text-center'>Lỗi kết nối!</li>";
    }
}

function renderConfigsList(list) {
    const ul = document.getElementById('configList');
    ul.innerHTML = '';
    
    if(list.length === 0) {
        ul.innerHTML = "<li class='text-warning small p-2 text-center'>Chưa có Biến nào!</li>";
        return;
    }

    list.forEach(c => {
        const li = document.createElement('li');
        li.className = `list-group-item cursor-pointer text-white d-flex justify-content-between align-items-center mb-1 rounded ${c.id === currentConfigId ? 'bg-danger bg-opacity-25 border-danger' : 'bg-dark bg-opacity-50 border-secondary'}`;
        
        li.innerHTML = `
            <div class="w-100 overflow-hidden text-truncate">
                <span class="text-danger fw-bold">${c.variable_name}</span>
                <div class="small text-muted text-truncate">${c.variable_value || ''}</div>
            </div>
        `;
        li.onclick = () => loadConfigDetail(c.id);
        ul.appendChild(li);
    });
}

function loadConfigDetail(id) {
    currentConfigId = id;
    renderConfigsList(cachedConfigs);
    
    const c = cachedConfigs.find(x => x.id === id);
    if(c) {
        document.getElementById('cfg_name').value = c.variable_name || '';
        document.getElementById('cfg_val').value = c.variable_value || '';
        document.getElementById('cfg_desc').value = c.description || '';
    }
}

document.getElementById('btnNewConfig').addEventListener('click', () => {
    currentConfigId = null;
    document.getElementById('cfg_name').value = '';
    document.getElementById('cfg_val').value = '';
    document.getElementById('cfg_desc').value = '';
    renderConfigsList(cachedConfigs);
});

document.getElementById('btnSaveConfig').addEventListener('click', async () => {
    const btn = document.getElementById('btnSaveConfig');
    btn.innerHTML = '<i class="ph ph-spinner ph-spin"></i> ĐANG LƯU...';
    btn.disabled = true;

    const payload = {
        type: 'config',
        id: currentConfigId,
        variable_name: document.getElementById('cfg_name').value.trim(),
        variable_value: document.getElementById('cfg_val').value.trim(),
        description: document.getElementById('cfg_desc').value.trim()
    };

    if(!payload.variable_name) {
        alert("Thiếu Tên Biến!");
        btn.innerHTML = '<i class="ph ph-floppy-disk"></i> LƯU CẤU HÌNH';
        btn.disabled = false;
        return;
    }

    try {
        const res = await fetch(`${NGROK_URL}/api/save-data`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify(payload)
        });
        if(!res.ok) throw new Error("Error saving");
        
        await fetchConfigs(); // reload list
        
        btn.innerHTML = '<i class="ph ph-check-circle text-success"></i> ĐÃ LƯU';
        setTimeout(() => {
            btn.innerHTML = '<i class="ph ph-floppy-disk"></i> LƯU CẤU HÌNH';
            btn.disabled = false;
        }, 1500);

    } catch (err) {
        console.error(err);
        btn.innerHTML = '<i class="ph ph-warning-circle text-danger"></i> LỖI MẠNG';
        setTimeout(() => {
            btn.innerHTML = '<i class="ph ph-floppy-disk"></i> LƯU CẤU HÌNH';
            btn.disabled = false;
        }, 2000);
    }
});
