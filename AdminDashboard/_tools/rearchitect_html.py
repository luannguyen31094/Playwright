import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update the tabs in pc-content
# Find the start and end of tabs
start_idx = text.find('<!-- [ Main Content ] start -->')
end_idx = text.find('<!-- [ Main Content ] end -->')

content = text[start_idx:end_idx]

# List of all tabs we need to have. We will wrap existing ones in new divs except we'll rewrite tab-models completely

new_content = """<!-- [ Main Content ] start -->
    <div class="pc-container">
        <div class="pc-content h-full p-4">

            <!-- TAB: PRODUCTS -->
            <div id="tab-products" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header flex justify-between items-center py-3">
                        <h5 class="mb-0">Kho Sản Phẩm (Đã cào)</h5>
                        <button class="btn btn-sm btn-primary" id="btnSyncProducts"><i data-feather="refresh-cw"></i> Đồng Bộ Lại</button>
                    </div>
                    <div class="card-body p-0 h-full overflow-auto">
                        <table id="productsTable" class="table table-hover w-full">
                            <thead>
                                <tr>
                                    <th>Ảnh</th>
                                    <th>Cơ Bản</th>
                                    <th>Tiềm Năng AI</th>
                                    <th>Trạng Thái Video</th>
                                    <th>Hành Động</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Populate by JS -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: CAMPAIGNS -->
            <div id="tab-campaigns" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header py-3"><h5 class="mb-0">Luồng Xử Lý Sản Xuất Video</h5></div>
                    <div class="card-body p-4 h-full"><i>Đang xây dựng...</i></div>
                </div>
            </div>

            <!-- TAB: RADAR -->
            <div id="tab-radar" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header py-3"><h5 class="mb-0">Giám Sát Playwright / N8N</h5></div>
                    <div class="card-body p-4 h-full"><i>Đang xây dựng...</i></div>
                </div>
            </div>
            
            <!-- TAB: POLICIES -->
            <div id="tab-policies" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header py-3"><h5 class="mb-0">Luật AI Học Việc</h5></div>
                    <div class="card-body p-4 h-full"><i>(Đang gom từ giao diện cũ)</i></div>
                </div>
            </div>

            <!-- TAB: MODELS -->
            <div id="tab-models" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header flex justify-between items-center py-3">
                        <h5 class="mb-0">Kho Người Mẫu AI</h5>
                        <button class="btn btn-sm btn-success" id="btnNewModel" onclick="openModelModal()">+ Thêm Người Mẫu Mới</button>
                    </div>
                    <div class="card-body p-0 h-full overflow-auto">
                        <table id="modelsTable" class="table table-hover w-full m-0">
                            <thead>
                                <tr>
                                    <th>Tên Mẫu</th>
                                    <th>Giới tính</th>
                                    <th>Tuổi</th>
                                    <th>Style</th>
                                    <th>Status</th>
                                    <th>Thao Tác</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Rendered by DataTables JS -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

"""

# Retain old tabs just putting them back in (scripts, scoring, music, configs)
# Regex to extract specific tabs
def get_tab(html, tab_id):
    s = html.find(f'<div id="{tab_id}"')
    if s == -1: return ""
    # find exactly matched div end
    depth = 0
    i = s
    while i < len(html):
        if html[i:i+4] == '<div': depth += 1
        elif html[i:i+5] == '</div':
            depth -= 1
            if depth == 0:
                return html[s:i+6]
        i += 1
    return ""

old_scripts = get_tab(content, "tab-scripts")
old_scoring = get_tab(content, "tab-scoring")
old_music = get_tab(content, "tab-music")
old_configs = get_tab(content, "tab-configs")

new_content += "\n".join([old_scripts, old_scoring, old_music, old_configs])
new_content += """
        </div>
    </div>
"""

# 2. Inject Modal templates right before footer
modal_html = """
    <!-- DUAL-PERSONA GLOBAL MODALS -->
    <!-- Model Form Modal -->
    <div class="modal fade" id="modal-model-form" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Cập nhật Hồ Sơ Người Mẫu</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <input type="hidden" id="mod_id_hidden">
                    <div class="mb-3">
                        <label class="form-label text-muted">Tên Mẫu</label>
                        <input type="text" id="mod_name" class="form-control" placeholder="Tên VD: Anna">
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-muted">Giới tính</label>
                        <select id="mod_gender" class="form-select text-white bg-dark">
                            <option value="female">Nữ</option>
                            <option value="male">Nam</option>
                            <option value="intersex">Phi Giới Tính</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-muted">Tuổi ước tính</label>
                        <input type="number" id="mod_age" class="form-control" placeholder="Độ tuổi">
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-muted">Phân Loại Phong Cách</label>
                        <input type="text" id="mod_style" class="form-control" placeholder="asian, elegant, street...">
                    </div>
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="mod_active" checked>
                        <label class="form-check-label" for="mod_active">Sẵn sàng kích hoạt làm video</label>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>
                    <button type="button" class="btn btn-primary" onclick="saveModel()">Lưu Xuống CSDL</button>
                </div>
            </div>
        </div>
    </div>
"""

text = text[:start_idx] + new_content + text[end_idx:]
footer_idx = text.find('<footer class="pc-footer">')
text = text[:footer_idx] + modal_html + text[footer_idx:]

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Layout Updated successfully in index.html!")
