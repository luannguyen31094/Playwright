// Tab 3: Music Library Logic

let musicTableInstance = null;

async function fetchMusicLibrary() {
    if(!NGROK_URL) return;
    
    try {
        const res = await fetch(`${NGROK_URL}/api/get-data?type=music`, { headers: getHeaders() });
        if(!res.ok) throw new Error("API Lỗi");
        const list = await res.json();
        
        // Destory previous instance if exists to re-initialize
        if ($.fn.DataTable.isDataTable('#musicDataTable')) {
            $('#musicDataTable').DataTable().clear().destroy();
        }

        // Initialize DataTable
        musicTableInstance = $('#musicDataTable').DataTable({
            data: list,
            pageLength: 20,
            responsive: true,
            language: {
                search: "Lọc File:",
                lengthMenu: "Hiển thị _MENU_ bài",
                info: "Đang coi _START_ tới _END_ của _TOTAL_ bài",
                paginate: { next: "Tới", previous: "Lùi" },
                emptyTable: "Không có dữ liệu trong kho nhạc"
            },
            columns: [
                { data: 'id', render: (d) => `<span class="text-secondary fw-bold">#${d}</span>` },
                { data: 'file_name', render: (d) => `<span class="text-info">${d || ''}</span>` },
                { data: 'usage_count', render: (d) => `<span class="badge bg-warning text-dark">${d || 0} Lượt</span>` },
                { data: 'catalogue_id', render: (d) => `<span class="small text-muted">ID: ${d || '-'}</span>` },
                { data: 'gsheet_link', render: (d) => d ? `<a href="${d}" target="_blank" class="btn btn-sm btn-outline-info p-1"><i class="ph ph-link"></i> Mở</a>` : '' },
                { 
                    data: null, 
                    render: (data) => {
                        const checked = data.is_active ? 'checked' : '';
                        const cl = data.is_active ? 'bg-success border-success' : 'bg-danger border-danger';
                        return `
                            <div class="form-check form-switch cursor-pointer">
                                <input class="form-check-input ${cl}" type="checkbox" role="switch" ${checked} onchange="saveMusicState(${data.id}, this)">
                            </div>
                        `;
                    }
                }
            ]
        });

    } catch (err) {
        console.error("Lỗi:", err);
        alert("Lỗi tải Danh sách nhạc!");
    }
}

async function saveMusicState(id, checkboxObj) {
    const isActive = checkboxObj.checked;
    
    if (isActive) {
        checkboxObj.classList.remove('bg-danger', 'border-danger');
        checkboxObj.classList.add('bg-success', 'border-success');
    } else {
        checkboxObj.classList.remove('bg-success', 'border-success');
        checkboxObj.classList.add('bg-danger', 'border-danger');
    }

    try {
        const payload = {
            type: 'music_toggle',
            id: id,
            is_active: isActive
        };

        const res = await fetch(`${NGROK_URL}/api/save-data`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify(payload)
        });
        if(!res.ok) throw new Error("Error saving");
        
    } catch(err) {
        console.error(err);
        alert("Lỗi lưu trạng thái nhạc!");
        checkboxObj.checked = !isActive;
        if (!isActive) {
            checkboxObj.classList.remove('bg-danger', 'border-danger');
            checkboxObj.classList.add('bg-success', 'border-success');
        } else {
            checkboxObj.classList.remove('bg-success', 'border-success');
            checkboxObj.classList.add('bg-danger', 'border-danger');
        }
    }
}

async function saveMusicState(id, checkboxObj) {
    const isActive = checkboxObj.checked;
    
    if (isActive) {
        checkboxObj.classList.remove('bg-danger', 'border-danger');
        checkboxObj.classList.add('bg-success', 'border-success');
    } else {
        checkboxObj.classList.remove('bg-success', 'border-success');
        checkboxObj.classList.add('bg-danger', 'border-danger');
    }

    try {
        const payload = {
            type: 'music_toggle',
            id: id,
            is_active: isActive
        };

        const res = await fetch(`${NGROK_URL}/api/save-data`, {
            method: 'POST', headers: getHeaders(), body: JSON.stringify(payload)
        });
        if(!res.ok) throw new Error("Error saving");
        
    } catch(err) {
        console.error(err);
        alert("Lỗi lưu trạng thái nhạc!");
        checkboxObj.checked = !isActive;
        if (!isActive) {
            checkboxObj.classList.remove('bg-danger', 'border-danger');
            checkboxObj.classList.add('bg-success', 'border-success');
        } else {
            checkboxObj.classList.remove('bg-success', 'border-success');
            checkboxObj.classList.add('bg-danger', 'border-danger');
        }
    }
}
