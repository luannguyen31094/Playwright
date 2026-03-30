import re

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Clean paths
text = text.replace("../assets/", "assets/")
text = text.replace("../dashboard/index.html", "#")

# 2. Replace Sidebar Menu
sidebar_start = text.find('<ul class="pc-navbar">')
sidebar_end = text.find('</ul>', sidebar_start) + 5

sidebar_html = """<ul class="pc-navbar">
        <li class="pc-item pc-caption">
          <label>Automation Dashboard</label>
        </li>
        <li class="pc-item">
          <a href="#" class="pc-link" onclick="switchTab('tab-scripts')">
            <span class="pc-micon"><i data-feather="film"></i></span>
            <span class="pc-mtext">Quản lý Kịch bản</span>
          </a>
        </li>
        <li class="pc-item">
          <a href="#" class="pc-link" onclick="switchTab('tab-scoring')">
            <span class="pc-micon"><i data-feather="crosshair"></i></span>
            <span class="pc-mtext">Chấm Điểm Đánh Giá</span>
          </a>
        </li>
        <li class="pc-item">
          <a href="#" class="pc-link" onclick="switchTab('tab-music')">
            <span class="pc-micon"><i data-feather="music"></i></span>
            <span class="pc-mtext">Kho Âm Nhạc</span>
          </a>
        </li>
        <li class="pc-item">
          <a href="#" class="pc-link" onclick="switchTab('tab-models')">
            <span class="pc-micon"><i data-feather="users"></i></span>
            <span class="pc-mtext">Danh Sách Người Mẫu</span>
          </a>
        </li>
        <li class="pc-item">
          <a href="#" class="pc-link" onclick="switchTab('tab-policies')">
            <span class="pc-micon"><i data-feather="shield"></i></span>
            <span class="pc-mtext">Policy Prompts</span>
          </a>
        </li>
        <li class="pc-item">
          <a href="#" class="pc-link" onclick="switchTab('tab-configs')">
            <span class="pc-micon"><i data-feather="settings"></i></span>
            <span class="pc-mtext">Cấu Hình Gốc</span>
          </a>
        </li>
      </ul>"""

text = text[:sidebar_start] + sidebar_html + text[sidebar_end:]

# 3. Inject our Tabs into pc-content
# Find the start of the grid content inside pc-content
main_content_start = text.find('<div class="page-header">')
main_content_end = text.find('</div>\n    </div>\n    <!-- [ Main Content ] end -->')

main_app_html = """
        <!-- LOGIN OVERLAY -->
        <div id="login-overlay" class="fixed inset-0 z-[1050] bg-theme-sidebarbg dark:bg-dark-500 flex flex-col justify-center items-center">
            <div class="card w-[400px] shadow-lg p-6 text-center">
                <img src="assets/images/logo-dark.svg" class="img-fluid logo logo-lg mx-auto mb-4" alt="logo" />
                <h4 class="mb-4">Hệ Thống Quản Trị Trung Tâm</h4>
                <div class="mb-4 text-left">
                    <label class="form-label">Ngrok Endpoint</label>
                    <input type="text" class="form-control" id="urlInput" placeholder="https://xxx.ngrok-free.app">
                </div>
                <div class="mb-4 text-left">
                    <label class="form-label">Secret API KEY</label>
                    <input type="password" class="form-control" id="apiKeyInput" placeholder="Nhập API Key...">
                </div>
                <p id="loginError" class="text-danger-500 text-sm hidden">Lỗi đăng nhập</p>
                <div class="grid mt-4">
                    <button id="btnConnect" class="btn btn-primary" onclick="connectN8N()">🚀 KẾT NỐI HỆ THỐNG</button>
                </div>
            </div>
        </div>

        <!-- MAIN APP CONTAINER -->
        <div id="app-container" class="hidden h-full">
            <!-- TAB 1: SCRIPTS -->
            <div id="tab-scripts" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header flex justify-between items-center py-3">
                        <h5 class="mb-0">Quản lý Kịch bản</h5>
                        <button class="btn btn-sm btn-success" onclick="createNewScript()">+ Kịch bản mới</button>
                    </div>
                    <div class="card-body p-4 grid grid-cols-12 gap-6 h-full overflow-hidden">
                        <div class="col-span-12 xl:col-span-4 border-r dark:border-themedark-border pr-4 h-full overflow-auto">
                            <ul id="scriptList" class="list-none p-0 m-0">
                                <li class="text-muted text-center pt-4">Đang tải...</li>
                            </ul>
                        </div>
                        <div class="col-span-12 xl:col-span-8 h-full overflow-auto pr-2">
                            <h5 id="s_title" class="mb-3">Chi tiết kịch bản</h5>
                            <div class="mb-3">
                                <label class="form-label text-sm text-muted">Tên Kịch Bản</label>
                                <input type="text" id="s_template_name" class="form-control" placeholder="Tên kịch bản">
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-sm text-muted">Script Gốc</label>
                                <textarea id="s_tiktok_script" class="form-control" rows="8" placeholder="TikTok Script..."></textarea>
                            </div>
                            <button id="btnSaveScript" class="btn btn-primary" onclick="saveActiveScript()">Lưu Kịch Bản</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- TAB 2: SCORING -->
            <div id="tab-scoring" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header flex justify-between items-center py-3">
                        <h5 class="mb-0">Chấm Điểm Đánh Giá</h5>
                        <button class="btn btn-sm btn-success" id="btnNewScoring">+ Thêm Tiêu Chí</button>
                    </div>
                    <div class="card-body p-4 grid grid-cols-12 gap-6 h-full overflow-hidden">
                        <div class="col-span-12 xl:col-span-4 border-r dark:border-themedark-border pr-4 h-full overflow-auto">
                            <ul id="scoringList" class="list-none p-0 m-0">
                                <li class="text-muted text-center pt-4">Đang tải...</li>
                            </ul>
                        </div>
                        <div class="col-span-12 xl:col-span-8 h-full overflow-auto">
                            <h5 class="mb-3">Chi tiết tiêu chí</h5>
                            <div class="mb-3">
                                <input type="text" id="score_name" class="form-control" placeholder="Tên tiêu chí (Vd: Chất lượng hình ảnh)">
                            </div>
                            <div class="mb-3">
                                <input type="number" id="score_weight" class="form-control" placeholder="Trọng số hệ số 1-10">
                            </div>
                            <button id="btnSaveScoring" class="btn btn-primary" onclick="saveScoring()">Lưu Hệ Số</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- TAB 3: MUSIC -->
            <div id="tab-music" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header flex justify-between items-center py-3">
                        <h5 class="mb-0">Kho Âm Nhạc</h5>
                        <button class="btn btn-sm btn-light" onclick="fetchMusicLibrary()">Làm Mới</button>
                    </div>
                    <div class="card-body p-4 overflow-auto h-full">
                        <div class="table-responsive">
                            <!-- Include DataTables custom styles for Tailwind properly -->
                            <table class="table table-hover w-full" id="musicDataTable">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Tên File Nhạc</th>
                                        <th>Lượt Dùng</th>
                                        <th>Danh Mục</th>
                                        <th>Google Sheet Link</th>
                                        <th>ON/OFF</th>
                                    </tr>
                                </thead>
                                <tbody></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- TAB 4: MODELS -->
            <div id="tab-models" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header flex justify-between items-center py-3">
                        <h5 class="mb-0">Danh Sách Người Mẫu</h5>
                        <button class="btn btn-sm btn-success" id="btnNewModel">+ Thêm Mẫu</button>
                    </div>
                    <div class="card-body p-4 grid grid-cols-12 gap-6 h-full overflow-hidden">
                        <div class="col-span-12 xl:col-span-4 border-r dark:border-themedark-border pr-4 h-full overflow-auto">
                            <ul id="modelsList" class="list-none p-0 m-0">
                                <li class="text-muted text-center pt-4">Đang tải...</li>
                            </ul>
                        </div>
                        <div class="col-span-12 xl:col-span-8 h-full overflow-auto">
                            <h5 class="mb-3">Hồ Sơ Mẫu</h5>
                            <input type="text" id="mdl_name" class="form-control mb-3" placeholder="Tên người mẫu">
                            <input type="text" id="mdl_gender" class="form-control mb-3" placeholder="Giới tính">
                            <button id="btnSaveModel" class="btn btn-primary" onclick="saveModel()">Lưu Hồ Sơ</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- TAB 6: CONFIGS -->
            <div id="tab-configs" class="tab-panel hidden h-full">
                <div class="card table-card h-[calc(100vh-100px)]">
                    <div class="card-header flex justify-between items-center py-3">
                        <h5 class="mb-0">Cấu Hình Gốc</h5>
                        <button class="btn btn-sm btn-success" id="btnNewConfig">+ Thêm Biến</button>
                    </div>
                    <div class="card-body p-4 grid grid-cols-12 gap-6 h-full overflow-hidden">
                        <div class="col-span-12 xl:col-span-4 border-r dark:border-themedark-border pr-4 h-full overflow-auto">
                            <ul id="configList" class="list-none p-0 m-0">
                                <li class="text-muted text-center pt-4">Đang tải...</li>
                            </ul>
                        </div>
                        <div class="col-span-12 xl:col-span-8 h-full overflow-auto">
                            <h5 class="mb-3">Sửa Cấu Hình Cốt Lõi</h5>
                            <input type="text" id="cfg_name" class="form-control mb-3" placeholder="Tên biến">
                            <input type="text" id="cfg_val" class="form-control mb-3" placeholder="Giá trị">
                            <textarea id="cfg_desc" class="form-control mb-3" rows="3" placeholder="Mô tả..."></textarea>
                            <button id="btnSaveConfig" class="btn btn-primary" onclick="saveConfig()">Lưu Cấu Hình</button>
                        </div>
                    </div>
                </div>
            </div>
            
        </div>
"""

text = text[:main_content_start] + main_app_html + text[main_content_end:]

# 4. Add JS Imports Custom Logic
script_marker = "</body>"
custom_scripts = """
  <!-- DataTables & jQuery & Custom Modules -->
  <link rel="stylesheet" href="DataTables/datatables.min.css">
  <script src="jquery-4.0.0.min.js"></script>
  <script src="DataTables/datatables.min.js"></script>
  
  <script src="js/auth.js?v=4"></script>
  <script src="js/ui.js?v=4"></script>
  <script src="js/tab_scripts.js?v=4"></script>
  <script src="js/tab_scoring.js?v=4"></script>
  <script src="js/tab_music.js?v=4"></script>
  <script src="js/tab_models.js?v=4"></script>
  <script src="js/tab_config.js?v=4"></script>
</body>"""

text = text.replace(script_marker, custom_scripts)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("✅ Rebuild index.html successful.")
