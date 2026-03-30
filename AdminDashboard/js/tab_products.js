// js/tab_products.js
let productsTable;
let currentProductsData = [];

function fetchProducts() {
    const url = localStorage.getItem('sh_ngrokUrl') || (typeof NGROK_URL !== 'undefined' ? NGROK_URL : '');
    const apiKey = localStorage.getItem('sh_apiKey') || (typeof API_KEY !== 'undefined' ? API_KEY : '');
    if (!url || !apiKey) return;

    const filters = new URLSearchParams({
        type: 'products',
        categoryid: $('#filter_categoryid').val() || '',
        final_rank: $('#filter_final_rank').val() || '',
        fromdate: $('#filter_fromdate').val() || '',
        todate: $('#filter_todate').val() || '',
        statusvideo: $('#filter_statusvideo').val() || ''
    }).toString();

    $('#productsTable tbody').html('<tr><td colspan="6" class="text-center py-4">Đang tải và lọc dữ liệu... Xin đợi chút!</td></tr>');

    fetch(`${url}/api/get-data?${filters}`, {
        headers: getHeaders()
    })
        .then(r => r.json())
        .then(data => {
            currentProductsData = data;
            renderProductsTable(data);
        })
        .catch(err => {
            console.error("Fetch Products Error:", err);
            $('#productsTable tbody').html(`<tr><td colspan="6" class="text-center text-danger-500 py-4">Lỗi tải dữ liệu: Vui lòng kiểm tra lại kết nối Ngrok</td></tr>`);
        });
}

function renderProductsTable(data) {
    if (productsTable) {
        productsTable.destroy();
    }

    const tbody = $('#productsTable tbody');
    tbody.empty();

    data.forEach(item => {
        let title = item.title || 'Sản Phẩm Chưa Rõ Tên';

        let price = item.sale_price ? parseFloat(item.sale_price).toLocaleString('vi-VN') + ' đ' : 'N/A';
        let commission = item.commission_amount ? parseFloat(item.commission_amount).toLocaleString('vi-VN') + ' đ' : 'N/A';
        let sold = item.total_sold ? Number(item.total_sold).toLocaleString('de-DE') : '0';
        let rank = item.final_rank || '-';
        let score = item.total_hard_score || 0;

        let rankHtml = '';
        if (rank === 'S - SUPER') rankHtml = `<span class="badge px-2 py-1 rounded font-bold shadow-sm" style="background-color: #ef4444; color: white;">Hạng S</span>`;
        else if (rank === 'A - HIGH') rankHtml = `<span class="badge px-2 py-1 rounded font-bold shadow-sm" style="background-color: #f59e0b; color: white;">Hạng A</span>`;
        else if (rank === 'B - MEDIUM') rankHtml = `<span class="badge px-2 py-1 rounded shadow-sm" style="background-color: #3b82f6; color: white;">Hạng B</span>`;
        else if (rank === 'C - LOW') rankHtml = `<span class="badge px-2 py-1 rounded shadow-sm" style="background-color: #6b7280; color: white;">Hạng C</span>`;
        else if (rank === 'F - TRASH') rankHtml = `<span class="badge px-2 py-1 rounded shadow-sm" style="background-color: #374151; color: white;">Hạng F</span>`;
        else rankHtml = `<span class="badge px-2 py-1 rounded" style="background-color: #9ca3af; color: white;">Chưa Xếp Hạng</span>`;

        let images = item.image_urls || [];
        // Extract array from jsonb if needed, sometimes python parses it
        if (typeof images === 'string') {
            try { images = JSON.parse(images); } catch (e) { }
        }
        let thumbUrl = Array.isArray(images) && images.length > 0 ? images[0] : 'img/placeholder.jpg';

        let urlHtml = item.canonical_url ? `<a href="${item.canonical_url}" target="_blank" class="text-blue-500 hover:text-blue-700 underline flex items-center gap-1 transition" title="Mở link TikTok Shop"><svg class="w-3 h-3 shrink-0" style="width:14px; height:14px; min-width:14px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg> <span class="truncate">ID: ${item.tiktok_product_id}</span></a>` : `<span class="text-gray-500 border border-gray-200 px-1 py-0.5 rounded text-[10px]">ID: ${item.tiktok_product_id}</span>`;
        
        let dateObj = new Date(item.captured_at || item.created_at || new Date());
        let dateStr = !isNaN(dateObj) ? dateObj.toLocaleDateString("vi-VN", {day:"2-digit", month:"2-digit", year:"numeric"}) : "N/A";

        let statusBadge = '';
        switch(item.status) {
            case 'RAW': statusBadge = `<span class="badge px-2 py-1 rounded" style="background-color: #64748b; color: white; display: inline-block;">Dữ Liệu Thô</span>`; break;
            case 'ELIGIBLE': statusBadge = `<span class="badge px-2 py-1 rounded" style="background-color: #3b82f6; color: white; display: inline-block;">Đủ ĐK tạo Video</span>`; break;
            case 'SHOWCASE': statusBadge = `<span class="badge px-2 py-1 rounded" style="background-color: #a855f7; color: white; display: inline-block;">T.Bày Showcase</span>`; break;
            case 'READY': statusBadge = `<span class="badge px-2 py-1 rounded" style="background-color: #eab308; color: white; display: inline-block;">Sẵn sàng Video</span>`; break;
            case 'PROCESSED': case 'DONE': statusBadge = `<span class="badge px-2 py-1 rounded" style="background-color: #22c55e; color: white; display: inline-block;">Đã tạo Video</span>`; break;
            default: statusBadge = `<span class="badge px-2 py-1 rounded" style="background-color: #9ca3af; color: white; display: inline-block;">${item.status || 'Chưa rõ'}</span>`;
        }
        
        // Setup Rate Display
        let commRate = item.commission_rate ? item.commission_rate + '%' : '0%';

        tbody.append(`
            <tr class="align-middle hover:bg-gray-50/50 dark:hover:bg-gray-800/50 transition">
                <td class="w-[70px]"><img src="${thumbUrl}" class="w-[50px] h-[50px] object-cover rounded shadow ring-1 ring-gray-200" onerror="this.src='https://placehold.co/100?text=No+Image'"></td>
                <td style="min-width:200px; max-width:250px; white-space: normal;">
                    <div class="font-bold text-sm text-gray-800 dark:text-gray-100 line-clamp-2" title="${title}">${title}</div>
                    <div class="mt-2 font-mono text-[11px]">
                        ${urlHtml}
                    </div>
                </td>
                <td class="w-[120px]">
                    <span class="text-[11px] bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-1 rounded font-semibold border border-gray-200 dark:border-gray-600 block max-w-full truncate" title="${item.category || 'N/A'}">${item.category || 'N/A'}</span>
                </td>
                <td>
                    <div class="text-[13px] font-bold text-success-600">${price}</div>
                    <div class="text-[12px] text-gray-500 mt-1 rounded bg-gray-50 inline-block px-1 border border-gray-100">HH: <b class="text-danger-500">${commission}</b></div>
                    <div class="text-[11px] text-gray-400 mt-1">Tỷ lệ: <span class="text-purple-600 font-bold">${commRate}</span></div>
                </td>
                <td>
                    <div class="text-[13px] font-bold text-gray-700 dark:text-gray-200">${sold} Lượt Bán</div>
                    <div class="text-[12px] text-warning-500 mt-1 font-bold">⭐ ${item.product_rating || 'N/A'} <span class="text-gray-400 font-normal">(${item.review_count || 0})</span></div>
                </td>
                <td class="w-[120px]">
                    <div class="flex flex-col gap-1 items-start">
                        ${rankHtml}
                        <span class="text-[11px] font-semibold text-blue-500 hover:text-blue-700 hover:underline cursor-pointer mt-1 uppercase tracking-wide flex items-center gap-1 transition" onclick="openProductModal(${item.id})" title="Xem chi tiết chấm điểm">
                            Điểm AI: ${score}
                            <svg class="w-3 h-3 shrink-0" style="width:12px; height:12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </span>
                    </div>
                </td>
                <td class="w-[100px]"><div class="text-[12px] text-gray-600 dark:text-gray-400 font-mono">${dateStr}</div></td>
                <td class="w-[120px]">${statusBadge}</td>
                <td class="sticky-col-right text-center" style="width: 90px; min-width: 90px; max-width: 90px;">
                    <button class="action-btn bg-indigo-50 text-indigo-600 hover:bg-indigo-500 hover:text-white border-0 transition" title="Xem Chi Tiết Mổ Xẻ" onclick="openProductModal(${item.id})">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
                    </button>
                </td>
            </tr>
        `);
    });

    productsTable = $('#productsTable').DataTable({
        "scrollX": true,
        "autoWidth": false,
        "columnDefs": [
            { "width": "90px", "targets": -1 }
        ],
        "pageLength": 10,
        "language": {
            "search": "🔍 Tìm kiếm sản phẩm:",
            "info": "Đang soi _START_ đến _END_ trên tổng _TOTAL_ Siêu Phẩm",
            "paginate": {
                "first": "Đầu",
                "last": "Cuối",
                "next": "▶",
                "previous": "◀"
            },
            "lengthMenu": "Hiện _MENU_ món"
        },
        "order": [], // Let the DB ordering persist
        "columnDefs": [
            { "orderable": false, "targets": [0, 5] }
        ],
        "drawCallback": function () {
            // Tailwind pagination classes injection
            $('.dataTables_paginate .paginate_button').addClass('px-3 py-1 bg-white border border-gray-200 rounded text-sm text-gray-600 cursor-pointer hover:bg-gray-100');
            $('.dataTables_paginate .paginate_button.current').addClass('bg-primary-50 text-primary-600 font-bold border-primary-200').removeClass('bg-white text-gray-600');
        }
    });
}

function openProductModal(id) {
    const item = currentProductsData.find(m => m.id === id);
    if (!item) return;

    $('#pModal_title').text(item.title || 'Chưa có tên');
    $('#pModal_id').text(item.tiktok_product_id || 'N/A');
    $('#pModal_status').html(item.status ? `<span class="badge bg-info-100 text-info-700 px-2 py-1 uppercase text-xs rounded">${item.status}</span>` : '<span class="badge bg-gray-100 text-gray-500 px-2 py-1 rounded">Mới Cào</span>');

    let aiScore = item.ai_score !== null ? item.ai_score : 'N/A';
    $('#pModal_ai_score').text(aiScore);
    $('#pModal_total_score').text(item.total_hard_score || 0);

    let images = item.image_urls || [];
    if (typeof images === 'string') {
        try { images = JSON.parse(images); } catch (e) { }
    }
    let thumbUrl = Array.isArray(images) && images.length > 0 ? images[0] : 'img/placeholder.jpg';
    $('#pModal_img').attr('src', thumbUrl);

    let price = item.sale_price ? parseFloat(item.sale_price).toLocaleString('vi-VN') + ' VNĐ' : 'N/A';
    let commission = item.commission_amount ? parseFloat(item.commission_amount).toLocaleString('vi-VN') + ' VNĐ' : 'N/A';
    let sold = item.total_sold ? Number(item.total_sold).toLocaleString('de-DE') : '0';
    let discount = item.discount_percent ? parseFloat(item.discount_percent) : 0;

    $('#pModal_price').text(price);
    $('#pModal_discount').text(discount > 0 ? `Sale ${discount}%` : 'Không Sale');
    $('#pModal_commission').text(commission);
    $('#pModal_sold').text(sold);
    $('#pModal_rating').html(`⭐ ${item.product_rating || '0'} (${item.review_count || 0} reviews)`);

    let note = item.ai_analysis_note || 'AI chưa đưa ra nhận xét gì, sản phẩm có vẻ ổn định.';
    $('#pModal_ai_note').val(note);

    $('#pModal_score_breakdown').addClass('hidden');
    
    // Fetch individual score breakdown
    const url = localStorage.getItem('sh_ngrokUrl') || (typeof NGROK_URL !== 'undefined' ? NGROK_URL : '');
    const apiKey = localStorage.getItem('sh_apiKey') || (typeof API_KEY !== 'undefined' ? API_KEY : '');
    
    if (url && apiKey) {
        fetch(`${url}/api/get-data?type=product_score_details&product_id=${id}`, {
            headers: getHeaders()
        })
        .then(res => res.json())
        .then(data => {
            if (data.score_amount !== undefined) {
                $('#sd_amount').text(data.score_amount + ' đ');
                $('#sd_rate').text(data.score_rate + ' đ');
                $('#sd_sold').text(data.score_sold + ' đ');
                $('#sd_prating').text(data.score_prating + ' đ');
                $('#sd_srating').text(data.score_srating + ' đ');
                $('#sd_stock').text(data.score_stock + ' đ');
                $('#pModal_score_breakdown').removeClass('hidden');
            }
        }).catch(err => console.error('Lỗi khi fetch breakdown score:', err));
    }

    $('#productDetailModal').removeClass('hidden').addClass('flex');
}

function closeProductModal() {
    $('#productDetailModal').removeClass('flex').addClass('hidden');
}

// Ensure the button in the HTML binds to fetch event on click
document.addEventListener("DOMContentLoaded", function () {
    const btnSyncProducts = document.getElementById("btnSyncProducts");
    if (btnSyncProducts) {
        btnSyncProducts.addEventListener("click", fetchProducts);
    }
});
