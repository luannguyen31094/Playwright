// ============================================
// MODULE: SCORING CRITERIA
// ============================================
let currentScoringId = null;

async function fetchScoringRules() {
    const ul = document.getElementById('scoringList');
    if(!ul) return;
    ul.innerHTML = "<li class='text-muted small p-2 text-center'>Đang tải...</li>";
    
    try {
        const res = await fetch(`${NGROK_URL}/api/get-data?type=scoring`, { headers: getHeaders() });
        if(!res.ok) throw new Error("API Lỗi");
        const list = await res.json();
        renderScoringList(list);
    } catch(e) {
        ul.innerHTML = `<li class='text-danger small p-2 text-center'>Lỗi Load Data: ${e.message}</li>`;
    }
}

function renderScoringList(list) {
    const ul = document.getElementById('scoringList');
    if(!ul) return;
    ul.innerHTML = "";
    
    if(!Array.isArray(list) || list.length === 0) {
        ul.innerHTML = "<li class='text-muted small p-2 text-center'>Chưa có Luật nào. Bấm Tạo mới!</li>";
        return;
    }
    
    list.forEach(item => {
        const li = document.createElement('li');
        // Tô màu điểm
        const scoreColor = item.score > 0 ? 'text-success' : (item.score < 0 ? 'text-danger' : 'text-warning');
        
        li.className = "p-3 mb-2 rounded bg-dark border border-secondary text-white d-flex justify-content-between align-items-center hover-bg-light";
        li.style.cursor = "pointer";
        li.innerHTML = `
            <div>
                <span class="badge bg-secondary mb-1">${item.group_name || 'UNKNOWN'}</span>
                <div class="fw-bold">${item.item_key || 'Unknown Key'}</div>
                <div class="small text-muted">[${item.min_val} ➜ ${item.max_val}]</div>
            </div>
            <div class="fs-4 fw-bold ${scoreColor}">
                ${item.score > 0 ? '+' : ''}${item.score}
            </div>
        `;
        li.onclick = () => showScoringForm(item, li);
        ul.appendChild(li);
    });
}

function showScoringForm(item, liHtml) {
    document.querySelectorAll('#scoringList li').forEach(l => l.classList.remove('active'));
    if(liHtml) liHtml.classList.add('active');

    currentScoringId = item.id;
    document.getElementById('sc_group').value = item.group_name || 'FINANCE';
    document.getElementById('sc_key').value = item.item_key || '';
    document.getElementById('sc_min').value = item.min_val || 0;
    document.getElementById('sc_max').value = item.max_val || 0;
    document.getElementById('sc_score').value = item.score || 0;
    document.getElementById('sc_note').value = item.rank_bonus_note || '';
    document.getElementById('sc_active').checked = item.is_active !== false;
}

document.addEventListener("DOMContentLoaded", () => {
    // Buttons might not exist until full HTML load
    setTimeout(() => {
        if(document.getElementById('btnNewScoring')) {
            document.getElementById('btnNewScoring').onclick = () => {
                showScoringForm({
                    id: null, group_name: "FINANCE", item_key: "", min_val: 0, max_val: 0, score: 0, rank_bonus_note: "", is_active: true
                });
            }
        }

        if(document.getElementById('btnSaveScoring')) {
            document.getElementById('btnSaveScoring').addEventListener('click', async () => {
                const payload = {
                    type: "scoring",
                    data: {
                        id: currentScoringId,
                        group_name: document.getElementById('sc_group').value,
                        item_key: document.getElementById('sc_key').value.trim(),
                        min_val: parseFloat(document.getElementById('sc_min').value) || 0,
                        max_val: parseFloat(document.getElementById('sc_max').value) || 0,
                        score: parseInt(document.getElementById('sc_score').value) || 0,
                        rank_bonus_note: document.getElementById('sc_note').value.trim(),
                        is_active: document.getElementById('sc_active').checked
                    }
                };

                try {
                    const res = await fetch(`${NGROK_URL}/api/save-data`, {
                        method: 'POST', headers: getHeaders(), body: JSON.stringify(payload)
                    });
                    if(!res.ok) throw new Error("Error saving");
                    alert("🎉 Đã Save Luật Chấm Điểm AI thành công!");
                    fetchScoringRules(); 
                } catch(e) { alert("Lỗi ghi data: " + e.message); }
            });
        }
    }, 500);
});
