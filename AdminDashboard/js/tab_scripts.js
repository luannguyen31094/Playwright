// ============================================
// MODULE: AFF_VIDEO_TEMPLATES
// ============================================
let currentScriptId = null;
let currentShots = [];

async function fetchVideoScripts() {
    try {
        const res = await fetch(`${NGROK_URL}/api/get-data?type=scripts`, { headers: getHeaders() });
        if(!res.ok) throw new Error("API Lỗi");
        const text = await res.text();
        const list = text ? JSON.parse(text) : [];
        renderScriptList(list);
    } catch(e) {
        console.error("Scripts fail:", e);
    }
}

function renderScriptList(list) {
    const ul = document.getElementById('scriptList');
    ul.innerHTML = "";
    
    // N8N có thể trả về { data: [...] } hoặc 1 Object đơn (First Entry JSON)
    if(list && list.data && Array.isArray(list.data)) list = list.data;
    else if(list && typeof list === 'object' && !Array.isArray(list)) list = [list];
    
    if(!Array.isArray(list) || list.length === 0) {
        ul.innerHTML = "<li class='text-muted small p-2 text-center'>Chưa có Kịch bản nào. Bấm Tạo mới!</li>";
        return;
    }
    
    list.forEach(item => {
        const li = document.createElement('li');
        // Thêm CSS class cho đẹp
        li.className = "p-2 mb-1 rounded bg-dark border border-secondary text-white";
        li.style.cursor = "pointer";
        li.innerText = item.template_name || "Kịch bản Trống";
        li.onclick = () => showScriptForm(item, li);
        ul.appendChild(li);
    });
}

function showScriptForm(item, liHtml) {
    document.querySelectorAll('#scriptList li').forEach(l => l.classList.remove('active'));
    if(liHtml) liHtml.classList.add('active');

    currentScriptId = item.id;
    document.getElementById('s_name').value = item.template_name || '';
    document.getElementById('s_cate').value = item.category || '';
    document.getElementById('s_gender').value = item.gender || 'Nam';
    document.getElementById('s_type').value = item.product_type_id || '';
    document.getElementById('s_style').value = item.style_slug || '';
    document.getElementById('s_active').checked = item.is_active !== false;
    document.getElementById('s_default').checked = item.is_default === true;
    
    currentShots = Array.isArray(item.shots_json) ? item.shots_json : [];
    renderShotsGrid();

    // Hiện Nút Lịch Sử nếu Kịch bản đã từng lưu (có ID)
    const btnHistory = document.getElementById('btnViewHistory');
    if (item.id) {
        btnHistory.style.display = 'flex';
        btnHistory.onclick = () => fetchScriptHistory(item.id);
    } else {
        btnHistory.style.display = 'none';
    }
}

async function fetchScriptHistory(scriptId) {
    const modalEl = document.getElementById('historyModal');
    const bsModal = new bootstrap.Modal(modalEl);
    bsModal.show();
    
    const ul = document.getElementById('historyList');
    ul.innerHTML = '<li class="list-group-item bg-transparent text-center text-muted border-secondary">Đang nạp từ N8N...</li>';

    try {
        const res = await fetch(`${NGROK_URL}/api/get-data?type=history&entity_type=scripts&entity_id=${scriptId}`, { headers: getHeaders() });
        if(!res.ok) throw new Error("API Lỗi");
        const list = await res.json();
        
        ul.innerHTML = "";
        if(!Array.isArray(list) || list.length === 0) {
            ul.innerHTML = '<li class="list-group-item bg-transparent text-center text-muted border-secondary">Chưa có bản lưu trước đó nào.</li>';
            return;
        }

        list.forEach((hist, idx) => {
            const time = new Date(hist.saved_at).toLocaleString('vi-VN');
            const snp = hist.snapshot_json || {};
            const li = document.createElement('li');
            li.className = "list-group-item bg-transparent text-white border-secondary border-opacity-25 d-flex justify-content-between align-items-center p-3 hover-bg-light";
            li.innerHTML = `
                <div>
                    <div style="font-weight:bold;">Bản lúc: <span class="text-info">${time}</span></div>
                    <div style="font-size:12px; margin-top:5px; color:#94a3b8;">Sửa bởi: ${hist.saved_by}</div>
                </div>
                <button class="btn btn-sm btn-outline-info" onclick='restoreHistorySnapshot(${JSON.stringify(snp).replace(/'/g, "\\'")})'>Phục hồi</button>
            `;
            ul.appendChild(li);
        });
    } catch(e) {
        ul.innerHTML = '<li class="list-group-item bg-transparent text-center text-danger border-secondary">Lỗi gọi API Lịch sử. Nhớ cài N8N Webhook "history"!</li>';
    }
}

window.restoreHistorySnapshot = function(histData) {
    // Ép Data Lịch sử ngược lên Giao diện nhưng chưa Lưu vào DB (phải bấm LƯU KỊCH BẢN NÀY LÊN DB mới ghi)
    document.getElementById('s_name').value = histData.template_name || '';
    document.getElementById('s_cate').value = histData.category || '';
    document.getElementById('s_gender').value = histData.gender || 'Nam';
    document.getElementById('s_type').value = histData.product_type_id || '';
    document.getElementById('s_style').value = histData.style_slug || '';
    document.getElementById('s_active').checked = histData.is_active !== false;
    document.getElementById('s_default').checked = histData.is_default === true;
    
    currentShots = Array.isArray(histData.shots_json) ? histData.shots_json : [];
    renderShotsGrid();
    
    bootstrap.Modal.getInstance(document.getElementById('historyModal')).hide();
    alert("Đã load Bản thiết kế Lịch sử. Bấm Ghi Đè (Save) nếu muốn khôi phục Vĩnh viễn!");
}

function renderShotsGrid() {
    const grid = document.getElementById('shotsGrid');
    grid.innerHTML = "";
    
    currentShots.forEach((shot, idx) => {
        const card = document.createElement('div');
        card.className = "shot-card";
        card.innerHTML = `
            <div class="shot-card-top">
                <span class="s-id">${shot.id || 'S'+(idx+1)}</span>
                <button class="btn-del" onclick="delShot(${idx})"><i class="ph ph-trash"></i></button>
            </div>
            <textarea class="shot-area" onchange="updateShot(${idx}, this.value)">${shot.act || ''}</textarea>
        `;
        grid.appendChild(card);
    });
}

window.delShot = (idx) => { currentShots.splice(idx, 1); currentShots.forEach((s, i) => s.id = "S"+(i+1)); renderShotsGrid(); }
window.updateShot = (idx, val) => currentShots[idx].act = val;

document.getElementById('btnAddShot').onclick = () => {
    currentShots.push({id: "S"+(currentShots.length+1), act: ""}); renderShotsGrid();
}

document.getElementById('btnNewScript').onclick = () => {
    showScriptForm({
        id: null, template_name: "Kịch bản Mới", gender: "Nam", is_active: true,
        shots_json: [{id: "S1", act: "Shot 1..."}, {id: "S2", act: "Shot 2..."}]
    });
}

document.getElementById('btnSaveScript').addEventListener('click', async () => {
    const payload = {
        type: "scripts",
        data: {
            id: currentScriptId,
            template_name: document.getElementById('s_name').value,
            category: document.getElementById('s_cate').value,
            gender: document.getElementById('s_gender').value,
            product_type_id: parseInt(document.getElementById('s_type').value) || null,
            style_slug: document.getElementById('s_style').value,
            is_active: document.getElementById('s_active').checked,
            is_default: document.getElementById('s_default').checked,
            shots_json: currentShots
        }
    };

    try {
        const res = await fetch(`${NGROK_URL}/api/save-data`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify(payload)
        });
        if(!res.ok) throw new Error("Error saving");
        alert("🎉 Đã Save Kịch bản thành công lên Database!");
        fetchVideoScripts();
    } catch(e) { alert("Lỗi ghi data: " + e.message); }
});
