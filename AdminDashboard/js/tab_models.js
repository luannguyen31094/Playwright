// Tab 4: Models Logic
let cachedModels = [];
let currentModelId = null;
let dtModels = null;

async function fetchModels() {
    if(!NGROK_URL) return;
    
    try {
        const res = await fetch(`${NGROK_URL}/api/get-data?type=models`, { headers: getHeaders() });
        if(!res.ok) throw new Error("API Lỗi");
        cachedModels = await res.json();
        renderModelsList(cachedModels);
    } catch (err) {
        console.error("Failed to fetch models", err);
    }
}

function renderModelsList(list) {
    if ($.fn.DataTable.isDataTable('#modelsTable')) {
        $('#modelsTable').DataTable().destroy();
    }
    
    const tbody = document.querySelector('#modelsTable tbody');
    tbody.innerHTML = '';
    
    // Reverse sort list
    list = [...list].sort((a,b) => b.id - a.id);

    if(list.length === 0) {
        tbody.innerHTML = "<tr><td colspan='6' class='text-center text-muted'>Chưa có Model nào!</td></tr>";
        return;
    }

    list.forEach(m => {
        const tr = document.createElement('tr');
        tr.className = "cursor-pointer hover:bg-white/5";
        
        let genderIcon = m.gender === 'female' ? '<i class="ph ph-gender-female text-danger text-lg"></i> Nữ' : (m.gender === 'male' ? '<i class="ph ph-gender-male text-info text-lg"></i> Nam' : '<i class="ph ph-gender-intersex text-warning text-lg"></i> Phi Giới Tính');
        let statusBadge = m.is_active ? '<span class="badge bg-success/20 text-success border border-success/30 rounded-md px-2 py-1">Đang Kích Hoạt</span>' : '<span class="badge bg-danger/20 text-danger border border-danger/30 rounded-md px-2 py-1">Tạm Tắt</span>';

        tr.innerHTML = `
            <td class="font-bold text-white">${m.name || 'No Name'}</td>
            <td>${genderIcon}</td>
            <td>${m.age_range || '?'}</td>
            <td><span class="badge bg-secondary/30 text-gray-300 border border-gray-600">${m.style_tag || 'Mặc định'}</span></td>
            <td>${statusBadge}</td>
            <td class="sticky-col-right text-center">
                <button class="action-btn bg-indigo-50 text-indigo-600 hover:bg-indigo-500 hover:text-white border-0 transition" title="Chỉnh Sửa Người Mẫu" onclick="loadModelDetail(${m.id}); event.stopPropagation();">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                </button>
            </td>
        `;
        // Make the whole row click to edit
        tr.onclick = () => loadModelDetail(m.id);
        tbody.appendChild(tr);
    });
    
    // Init Datatable
    dtModels = $('#modelsTable').DataTable({
        scrollX: true,
        autoWidth: false,
        columnDefs: [
            { width: "90px", targets: -1 }
        ],
        pageLength: 10,
        lengthChange: false,
        language: { search: "Tìm kiếm Model:", info: "Hiển thị _START_ đến _END_ của _TOTAL_ mẫu", paginate: { previous: "Trước", next: "Sau" }},
        dom: '<"flex justify-between items-center mb-3"f>rt<"flex justify-between items-center mt-3"p>',
        destroy: true
    });
}

window.openModelModal = () => {
    currentModelId = null;
    document.getElementById('mod_name').value = '';
    document.getElementById('mod_gender').value = 'female';
    document.getElementById('mod_age').value = '';
    document.getElementById('mod_style').value = '';
    document.getElementById('mod_active').checked = true;
    
    const modal = document.getElementById('modal-model-form');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

window.loadModelDetail = function(id) {
    currentModelId = id;
    const m = cachedModels.find(x => x.id === id);
    if(m) {
        document.getElementById('mod_name').value = m.name || '';
        document.getElementById('mod_gender').value = m.gender || 'female';
        document.getElementById('mod_age').value = m.age_range || '';
        document.getElementById('mod_style').value = m.style_tag || '';
        document.getElementById('mod_active').checked = m.is_active;
        
        // Open Tailwind modal
        const modal = document.getElementById('modal-model-form');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }
}

window.saveModelAction = async () => {
    const btn = document.getElementById('btnSaveModel');
    btn.innerHTML = '<i class="ph ph-spinner ph-spin"></i> ĐANG LƯU...';
    btn.disabled = true;

    const payload = {
        type: 'models',
        id: currentModelId,
        name: document.getElementById('mod_name').value.trim(),
        gender: document.getElementById('mod_gender').value,
        age_range: document.getElementById('mod_age').value.trim(),
        style_tag: document.getElementById('mod_style').value.trim(),
        is_active: document.getElementById('mod_active').checked
    };

    if(!payload.name) {
        alert("Thiếu Tên Model!");
        btn.innerHTML = 'Lưu Xuống CSDL';
        btn.disabled = false;
        return;
    }

    try {
        const res = await fetch(`${NGROK_URL}/api/save-data`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify(payload)
        });
        if(!res.ok) throw new Error("Error saving");
        
        await fetchModels(); // reload list
        
        btn.innerHTML = '<i class="ph ph-check-circle text-success"></i> ĐÃ LƯU';
        setTimeout(() => {
            btn.innerHTML = 'Lưu Xuống CSDL';
            btn.disabled = false;
            // Close modal auto
            document.getElementById('modal-model-form').classList.add('hidden');
            document.getElementById('modal-model-form').classList.remove('flex');
        }, 1000);

    } catch (err) {
        console.error(err);
        btn.innerHTML = '<i class="ph ph-warning-circle text-danger"></i> LỖI MẠNG';
        setTimeout(() => {
            btn.innerHTML = 'Lưu Xuống CSDL';
            btn.disabled = false;
        }, 2000);
    }
};
