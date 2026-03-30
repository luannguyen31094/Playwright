import json

# =============================================================
# 1. TEMPLATE "HÌNH ẢNH": GIỮ NGUYÊN THEO Ý SẾP (UI)
# =============================================================
_JS_IMAGE_UI_FUNCTIONS = """
var UI = {
    sleep: (ms) => new Promise(r => setTimeout(r, ms)),
    log: function(a, b) {
        let step = typeof a === 'number' ? `[Bước ${a}] ` : "";
        console.log(`%c[SaaS-Worker] ${step}${b || a}`, "color: #00e5ff; font-weight: bold;");
    },
    
    forceClick(el) {
        if (!el) throw new Error("Phần tử null.");
        el.scrollIntoView({ block: 'center', inline: 'center' });
        if (el.disabled) { el.removeAttribute('disabled'); el.disabled = false; }
        ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click'].forEach(t => {
            try { el.dispatchEvent(new PointerEvent(t, { bubbles: true, cancelable: true, pointerId: 1, isPrimary: true })); } catch(e) {}
            try { el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true })); } catch(e) {}
        });
        return true;
    },

    async setTab(label) { this.log(1, `(Bỏ qua setTab cũ) Chờ setup chung...`); },
    async setTool(toolName) { this.log(1, `(Bỏ qua setTool cũ) Chờ setup chung...`); },

    async setSettings(tabName, ratio, outputs) {
        this.log(1, `⚙️ Đang MỞ POPUP CÀI ĐẶT (Tab: ${tabName}, Tỉ lệ: ${ratio}, Outputs: ${outputs})...`);
        
        let menuBtn = Array.from(document.querySelectorAll('button[aria-haspopup]')).find(b => 
            b.innerText.match(/(crop_|x[1-4]|[1-4]x|Auto|16:9|9:16|1:1)/i) ||
            b.innerHTML.match(/(crop_|x[1-4]|[1-4]x)/i)
        );
        
        if (!menuBtn) {
            this.log("⚠️", "Không tìm thấy nút Popup cài đặt. Bỏ qua cấu hình!");
            return;
        }

        this.forceClick(menuBtn);
        await this.sleep(1500);

        const dialog = document.querySelector('[role="menu"]') || document.querySelector('.DropdownMenuContent') || document.querySelector('[role="dialog"]') || document.body;
        if (!dialog) {
            this.log("⚠️", "Popup Menu không bật lên!");
            return;
        }

        // 1. CHỌN TAB HÌNH ẢNH / VIDEO TRONG POPUP
        if (tabName) {
            const tabs = Array.from(dialog.querySelectorAll('button[role="tab"], button, .mat-tab-label'));
            const isVideo = tabName.toLowerCase().includes("video");
            const targetTypeBtn = tabs.find(b => b.innerText.toLowerCase().includes(isVideo ? 'video' : 'image') || b.innerText.toLowerCase().includes(isVideo ? 'video' : 'hình ảnh'));
            if (targetTypeBtn && targetTypeBtn.getAttribute('aria-selected') !== 'true' && targetTypeBtn.getAttribute('aria-checked') !== 'true') {
                this.log("✅", `Đã click chọn kiểu: ${targetTypeBtn.innerText.trim()}`);
                this.forceClick(targetTypeBtn); await this.sleep(1000);
            }
        }
        
        // 2. CHỌN TỶ LỆ (RATIO)
        if (ratio) {
            const txt = ratio == '916' ? 'Dọc' : (ratio == '169' ? 'Ngang' : 'Vuông');
            let ratioBtn = Array.from(dialog.querySelectorAll('button, [role="radio"], [role="menuitem"]')).find(b => 
                b.innerText.toLowerCase().includes(txt.toLowerCase()) || 
                b.innerText.toLowerCase().includes(ratio == '916'? 'portrait':'landscape') || 
                (b.innerHTML && (b.innerHTML.includes(ratio == '916'? 'crop_9_16':'crop_16_9')))
            );
            if (ratioBtn) {
                this.log("✅", `Đã click Ratio...`);
                this.forceClick(ratioBtn); await this.sleep(1000);
            }
        }

        // 3. CHỌN SỐ LƯỢNG OUTPUT
        if (outputs) {
            let outBtn = Array.from(dialog.querySelectorAll('button, [role="radio"], [role="menuitem"]')).find(b => 
                b.innerText.trim().toLowerCase() === `x${outputs}` || b.innerText.trim().toLowerCase() === `${outputs}x` || (b.innerText.trim() === `${outputs}` && b.getAttribute('role')==='radio')
            );
            if (outBtn) {
                this.log("✅", `Đã click Outputs: ${outputs}`);
                this.forceClick(outBtn); await this.sleep(1000);
            }
        }

        // Đóng popup
        this.forceClick(menuBtn); 
        await this.sleep(1500);
    },

    async autoClickIngredient(refNames = []) {
        this.log("1.5", "🖱️ Bắt đầu thủ tục Nạp Ảnh Mồi (Thêm nội dung nghe nhìn)...");
        
        // Tìm đúng nút Thêm Media (add) thay vì nút Tạo dự án chung (add_2)
        let pickBtn = document.querySelector('button.jQayrS') || Array.from(document.querySelectorAll('button[aria-haspopup="menu"]')).find(b => 
            b.innerHTML.includes('>add<') || b.innerText.toLowerCase().includes('nghe nhìn') || b.innerText.toLowerCase().includes('add media')
        );

        if (pickBtn) {
            this.log("✅", "Đã khóa mục tiêu mở Popup Danh Sách. Đang Click...");
            this.forceClick(pickBtn);
            await this.sleep(2500); // Chờ popup bung ra và render list JSON
        }

        this.log("1.6", "🖱️ Tiến hành chọc 1 tấm ảnh trong danh sách...");
        
        let targetBtn = null;

        // 🎯 Ưu tiên 1: TÌM ĐÍCH DANH BẰNG TÊN ẢNH (Nếu N8N truyền xuống đổi tên)
        if (refNames && refNames.length > 0) {
            this.log("🎯", `Đang Scan tìm ảnh có tên: ${refNames[0]}`);
            let textElem = Array.from(document.querySelectorAll('div, span, p')).find(e => 
                e.children.length === 0 && e.innerText && e.innerText.includes(refNames[0])
            );
            if (!textElem) {
                textElem = Array.from(document.querySelectorAll('img')).find(img => 
                    (img.alt && img.alt.includes(refNames[0])) || (img.title && img.title.includes(refNames[0]))
                );
            }
            if (textElem) {
                targetBtn = textElem.closest('button') || textElem.closest('[role="menuitem"]') || textElem.closest('[role="button"]') || textElem;
                if (targetBtn) this.log("✅", "Tuyệt vời! Đã gắp trúng đích danh tấm ảnh!");
            }
        }

        // 🎲 Ưu tiên 2: Fallback Bốc đại tấm ảnh đầu tiên trên cùng (Mới nhất)
        if (!targetBtn) {
            let activePopups = Array.from(document.querySelectorAll('[role="dialog"], [role="menu"], [data-state="open"]')).filter(p => p.offsetHeight > 0 && !p.innerText.includes('Tín dụng AI'));
            let rawImages = [];
            for (let p of activePopups) {
                rawImages.push(...Array.from(p.querySelectorAll('img, video')));
            }
            if (rawImages.length === 0) {
                rawImages = Array.from(document.querySelectorAll('img')).filter(i => 
                    (i.src.includes('googleusercontent') || i.src.includes('blob:')) && 
                    !i.src.includes('avatar') && !i.src.includes('/a/') && !i.src.includes('=s')
                );
            }
            if (rawImages.length > 0) {
                // Tấm mới upload thường nằm ở đầu list (index 0)
                let targetImg = rawImages[0]; 
                targetBtn = targetImg.closest('button') || targetImg.closest('[role="button"]') || targetImg.closest('[role="menuitem"]') || targetImg;
                this.log("✅", "Đã gắp tấm ảnh mới nhất trên cùng!");
            }
        }

        if (targetBtn) {
            this.forceClick(targetBtn);
            await this.sleep(1500);
            if (pickBtn) this.forceClick(document.body); // Đóng popup
            return true;
        }
        
        this.log("⚠️", "Popup đã mở nhưng KHÔNG THẤY THẺ <img> NÀO! Có thể Workspace chưa có hình!");
        if (pickBtn) this.forceClick(document.body); // Đóng popup để chống kẹt nút Generate
        return false;
    },

    async generate(prompt) {
        this.log(2, "✍️ Đang nhập Prompt...");
        const tx = document.querySelector('div[role="textbox"][data-slate-editor="true"]') || document.querySelector('textarea') || document.querySelector('[contenteditable="true"]');
        if (tx) {
            tx.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            await this.sleep(200);
            
            const dt = new DataTransfer();
            dt.setData('text/plain', prompt + " ");
            tx.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
            document.execCommand('insertText', false, prompt + " ");
            tx.dispatchEvent(new Event('input', { bubbles: true }));
            await this.sleep(1500);
        }

        let targetGen = null;
        for (let i = 0; i < 30; i++) {
            const genBtns = Array.from(document.querySelectorAll('button'));
            targetGen = genBtns.find(b => {
                const inner = (b.innerText + " " + (b.innerHTML || "")).toLowerCase();
                return inner.includes('arrow_forward') && !inner.includes('arrow_forward_ios');
            });
            if (targetGen) break;
            await this.sleep(500);
        }

        if (targetGen) {
            this.log(3, "✅ Phát lệnh TẠO...");
            this.forceClick(targetGen);
        } else {
            throw new Error("UI_ERR_GENERATE_BTN_NOT_FOUND");
        }
    }
};
window.UI = UI;
window.UI_V = UI;
"""

# --- ĐÂY LÀ FILE PYTHON (.py), NÊN PHẢI DÙNG NHÁY BA ĐỂ CHỨA CODE JS ---
_JS_ERROR_SENTRY = """
// Khởi tạo biến chứa lỗi toàn cục để các hàm Task dễ dàng kiểm tra
window.HIJACK_ERROR = null;

const setupErrorSentry = (originalFetch, on403) => {
    return async (...args) => {
        const response = await originalFetch(...args);
        
        // 🎯 CHẶN ĐỨNG 403: Nếu dính gậy, đánh dấu lỗi và gọi callback thoát ngay
        if (response.status === 403) {
            console.error("⛔ [SENTRY] Phát hiện 403 Forbidden/reCAPTCHA!");
            window.HIJACK_ERROR = { 
                status: "error", 
                error_type: "FORBIDDEN", 
                message: "403_RECAPTCHA_DETECTED" 
            };
            on403(window.HIJACK_ERROR); 
        }
        return response;
    };
};
"""


# =============================================================
# 2. TEMPLATE "VIDEO": BẢN MỚI CHUYÊN BIỆT (UI_V)
# =============================================================
_JS_VIDEO_UI_FUNCTIONS = """
var UI_V = {
    sleep: (ms) => new Promise(r => setTimeout(r, ms)),
    log: function(a, b) {
        let step = typeof a === 'number' ? `[Bước ${a}] ` : "";
        console.log(`%c[SaaS-Worker] ${step}${b || a}`, "color: #00e5ff; font-weight: bold;");
    },
    
    forceClick(el) {
        if (!el) throw new Error("Phần tử null.");
        el.scrollIntoView({ block: 'center', inline: 'center' });
        if (el.disabled) { el.removeAttribute('disabled'); el.disabled = false; }
        ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click'].forEach(t => {
            try { el.dispatchEvent(new PointerEvent(t, { bubbles: true, cancelable: true, pointerId: 1, isPrimary: true })); } catch(e) {}
            try { el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true })); } catch(e) {}
        });
        return true;
    },

    async setTab(label) { this.log(1, `(Bỏ qua setTab cũ) Chờ setup chung...`); },
    async setTool(toolName) { this.log(1, `(Bỏ qua setTool cũ) Chờ setup chung...`); },

    async setSettings(tabName, ratio, outputs, subTab) {
        this.log(1, `⚙️ Đang MỞ POPUP CÀI ĐẶT (Tab: ${tabName}, Tỉ lệ: ${ratio}, Outputs: ${outputs}, SubTab: ${subTab})...`);
        
        let menuBtn = Array.from(document.querySelectorAll('button[aria-haspopup]')).find(b => 
            b.innerText.match(/(crop_|x[1-4]|[1-4]x|Auto|16:9|9:16|1:1)/i) ||
            b.innerHTML.match(/(crop_|x[1-4]|[1-4]x)/i)
        );
        
        if (!menuBtn) {
            this.log("⚠️", "Không tìm thấy nút Popup cài đặt. Bỏ qua cấu hình!");
            return;
        }

        this.forceClick(menuBtn);
        await this.sleep(1500);

        const dialog = document.querySelector('[role="menu"]') || document.querySelector('.DropdownMenuContent') || document.querySelector('[role="dialog"]') || document.body;
        if (!dialog) {
            this.log("⚠️", "Popup Menu không bật lên!");
            return;
        }

        // 1. CHỌN TAB HÌNH ẢNH / VIDEO TRONG POPUP
        if (tabName) {
            const tabs = Array.from(dialog.querySelectorAll('button[role="tab"], button, .mat-tab-label'));
            const isVideo = tabName.toLowerCase().includes("video");
            const targetTypeBtn = tabs.find(b => b.innerText.toLowerCase().includes(isVideo ? 'video' : 'image') || b.innerText.toLowerCase().includes(isVideo ? 'video' : 'hình ảnh'));
            if (targetTypeBtn && targetTypeBtn.getAttribute('aria-selected') !== 'true' && targetTypeBtn.getAttribute('aria-checked') !== 'true') {
                this.log("✅", `Đã click chọn kiểu: ${targetTypeBtn.innerText.trim()}`);
                this.forceClick(targetTypeBtn); await this.sleep(1000);
            }
        }
        
        // 1.5. CHỌN SUB-TAB (Khung hình / Thành phần)
        if (subTab) {
            const subTabs = Array.from(dialog.querySelectorAll('button[role="tab"], button, .mat-tab-label'));
            const targetSubBtn = subTabs.find(b => b.innerText.toLowerCase().includes(subTab.toLowerCase()));
            if (targetSubBtn && targetSubBtn.getAttribute('aria-selected') !== 'true' && targetSubBtn.getAttribute('aria-checked') !== 'true') {
                this.log("✅", `Đã click Mode (SubTab): ${targetSubBtn.innerText.trim()}`);
                this.forceClick(targetSubBtn); await this.sleep(1000);
            }
        }
        
        // 2. CHỌN TỶ LỆ (RATIO)
        if (ratio) {
            const txt = ratio == '916' ? 'Dọc' : (ratio == '169' ? 'Ngang' : 'Vuông');
            let ratioBtn = Array.from(dialog.querySelectorAll('button, [role="radio"], [role="menuitem"]')).find(b => 
                b.innerText.toLowerCase().includes(txt.toLowerCase()) || 
                b.innerText.toLowerCase().includes(ratio == '916'? 'portrait':'landscape') || 
                (b.innerHTML && (b.innerHTML.includes(ratio == '916'? 'crop_9_16':'crop_16_9')))
            );
            if (ratioBtn) {
                this.log("✅", `Đã click Ratio...`);
                this.forceClick(ratioBtn); await this.sleep(1000);
            }
        }

        // 3. CHỌN SỐ LƯỢNG OUTPUT
        if (outputs) {
            let outBtn = Array.from(dialog.querySelectorAll('button, [role="radio"], [role="menuitem"]')).find(b => 
                b.innerText.trim().toLowerCase() === `x${outputs}` || b.innerText.trim().toLowerCase() === `${outputs}x` || (b.innerText.trim() === `${outputs}` && b.getAttribute('role')==='radio')
            );
            if (outBtn) {
                this.log("✅", `Đã click Outputs: ${outputs}`);
                this.forceClick(outBtn); await this.sleep(1000);
            }
        }

        // Đóng popup
        this.forceClick(menuBtn); 
        await this.sleep(1500);
    },

    async autoClickIngredient(refNames = []) {
        this.log("1.5", "🖱️ Bắt đầu thủ tục Nạp Ảnh Mồi (Thêm nội dung nghe nhìn)...");
        
        // Tìm đúng nút Thêm Media (add) thay vì nút Tạo dự án chung (add_2)
        let pickBtn = document.querySelector('button.jQayrS') || Array.from(document.querySelectorAll('button[aria-haspopup="menu"]')).find(b => 
            b.innerHTML.includes('>add<') || b.innerText.toLowerCase().includes('nghe nhìn') || b.innerText.toLowerCase().includes('add media')
        );

        if (pickBtn) {
            this.log("✅", "Đã khóa mục tiêu mở Popup Danh Sách. Đang Click...");
            this.forceClick(pickBtn);
            await this.sleep(2500); // Chờ popup bung ra và render list JSON
        }

        this.log("1.6", "🖱️ Tiến hành chọc 1 tấm ảnh trong danh sách...");
        
        let targetBtn = null;

        // 🎯 Ưu tiên 1: TÌM ĐÍCH DANH BẰNG TÊN ẢNH (Nếu N8N truyền xuống đổi tên)
        if (refNames && refNames.length > 0) {
            this.log("🎯", `Đang Scan tìm ảnh có tên: ${refNames[0]}`);
            let textElem = Array.from(document.querySelectorAll('div, span, p')).find(e => 
                e.children.length === 0 && e.innerText && e.innerText.includes(refNames[0])
            );
            if (!textElem) {
                textElem = Array.from(document.querySelectorAll('img')).find(img => 
                    (img.alt && img.alt.includes(refNames[0])) || (img.title && img.title.includes(refNames[0]))
                );
            }
            if (textElem) {
                targetBtn = textElem.closest('button') || textElem.closest('[role="menuitem"]') || textElem.closest('[role="button"]') || textElem;
                if (targetBtn) this.log("✅", "Tuyệt vời! Đã gắp trúng đích danh tấm ảnh!");
            }
        }

        // 🎲 Ưu tiên 2: Fallback Bốc đại tấm ảnh đầu tiên trên cùng (Mới nhất)
        if (!targetBtn) {
            let activePopups = Array.from(document.querySelectorAll('[role="dialog"], [role="menu"], [data-state="open"]')).filter(p => p.offsetHeight > 0 && !p.innerText.includes('Tín dụng AI'));
            let rawImages = [];
            for (let p of activePopups) {
                rawImages.push(...Array.from(p.querySelectorAll('img, video')));
            }
            if (rawImages.length === 0) {
                rawImages = Array.from(document.querySelectorAll('img')).filter(i => 
                    (i.src.includes('googleusercontent') || i.src.includes('blob:')) && 
                    !i.src.includes('avatar') && !i.src.includes('/a/') && !i.src.includes('=s')
                );
            }
            if (rawImages.length > 0) {
                // Tấm mới upload thường nằm ở đầu list (index 0)
                let targetImg = rawImages[0]; 
                targetBtn = targetImg.closest('button') || targetImg.closest('[role="button"]') || targetImg.closest('[role="menuitem"]') || targetImg;
                this.log("✅", "Đã gắp tấm ảnh mới nhất trên cùng!");
            }
        }

        if (targetBtn) {
            this.forceClick(targetBtn);
            await this.sleep(1500);
            if (pickBtn) this.forceClick(document.body); // Đóng popup
            return true;
        }
        
        this.log("⚠️", "Popup đã mở nhưng KHÔNG THẤY THẺ <img> NÀO! Có thể Workspace chưa có hình!");
        return false;
    },

    async generate(prompt) {
        if (prompt && typeof prompt === 'string') {
            this.log(2, "✍️ Đang nhập Prompt...");
            const tx = document.querySelector('div[role="textbox"][data-slate-editor="true"]') || document.querySelector('textarea') || document.querySelector('[contenteditable="true"]');
            if (tx) {
                tx.focus();
                try {
                    const range = document.createRange();
                    range.selectNodeContents(tx);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                } catch(e) {
                    document.execCommand('selectAll', false, null); // Fallback
                }
                document.execCommand('delete', false, null);
                await this.sleep(500);
                
                const dt = new DataTransfer();
                dt.setData('text/plain', prompt + " ");
                tx.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
                document.execCommand('insertText', false, prompt + " ");
                tx.dispatchEvent(new Event('input', { bubbles: true }));
                // Fix: React SlateJS Event Sync Fallback
                tx.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: ' ', code: 'Space' }));
                await this.sleep(1500);
            }
        } else {
            this.log(2, "⏭️ Bỏ qua nhập Prompt (Dùng Prompt mồi gốc đã có sẵn để giữ trạng thái React)...");
        }

        let targetGen = null;
        for (let i = 0; i < 15; i++) {
            let genBtns = Array.from(document.querySelectorAll('button'));
            targetGen = genBtns.find(b => {
                if (b.disabled || b.getAttribute('aria-disabled') === 'true') return false;
                const inner = (b.innerText + " " + (b.innerHTML || "")).toLowerCase();
                return inner.includes('arrow_forward') && !inner.includes('arrow_forward_ios');
            });
            if (targetGen) break;
            await this.sleep(1000);
        }

        if (targetGen) {
            this.log(3, "✅ Phát lệnh TẠO...");
            this.forceClick(targetGen);
        } else {
            throw new Error("UI_ERR_GENERATE_BTN_NOT_FOUND");
        }
    }
};
window.UI_V = UI_V;
window.UI = UI_V;
"""

# =============================================================
# 1. MẪU JAVASCRIPT: UPLOAD
# =============================================================
_JS_UPLOAD = _JS_IMAGE_UI_FUNCTIONS + """
const callback = arguments[arguments.length - 1];
const targetEndpoint = "__ENDPOINT__"; 
const uploadPayload = __PAYLOAD__;

async function runUploadHijack() {
    try {
        const originalFetch = window.fetch;
        let captured = null;
        let authHeaders = null;

        window.fetch = async (...args) => {
            const urlStr = (args[0] || "").toString();
            const hasBody = args[1] && typeof args[1].body === 'string';
            const isBatch = (urlStr.includes("batch") || urlStr.includes("predict") || urlStr.includes("generate") || urlStr.includes("async"))
                             && urlStr.includes("v1") && !urlStr.includes("log") 
                             && hasBody && args[1].body.includes("{");
            
            if (isBatch && args[1]) {
                UI.log("📡 Bắt được gói tin từ UI. Xử lý ép Upload...");
                if (args[1].headers) authHeaders = { ...args[1].headers };

                // Tự động moi Project ID từ thanh địa chỉ để đắp vào Payload Mới
                const pathMatch = window.location.pathname.match(/\/project\/([a-zA-Z0-9-]+)/);
                const projectId = pathMatch ? pathMatch[1] : "";
                
                // Lấy Cấu trúc N8N gửi (Hỗ trợ cả dạng cũ imageInput và dạng Phẳng API mới)
                let basePayload = uploadPayload.imageInput ? uploadPayload.imageInput : uploadPayload;
                
                let rawB64 = basePayload.rawImageBytes || basePayload.imageBytes || "";
                if (rawB64.includes("base64,")) {
                    rawB64 = rawB64.split("base64,")[1]; // Lọc bỏ header của N8N
                }
                
                // Tự động rinh nguyên mâm cỗ JSON mà N8N gửi đẩy vào Payload
                const newPayload = { ...basePayload };
                delete newPayload.rawImageBytes; // Xoá biến dư thừa
                
                const prevTool = (uploadPayload.clientContext && uploadPayload.clientContext.tool) || (basePayload.clientContext && basePayload.clientContext.tool) || "PINHOLE";
                
                // Ép tĩnh các Biến Hệ Thống bắt buộc phải có để giữ kết nối UI
                newPayload.clientContext = newPayload.clientContext || {};
                newPayload.clientContext.projectId = projectId;
                newPayload.clientContext.tool = prevTool;
                
                newPayload.imageBytes = rawB64;
                
                // Dự phòng nếu DB/N8N lười khai báo
                if (!newPayload.fileName) newPayload.fileName = "N8N_Up_" + Date.now() + ".jpeg";
                if (newPayload.isHidden === undefined) newPayload.isHidden = false;
                if (newPayload.isUserUploaded === undefined) newPayload.isUserUploaded = true;
                if (!newPayload.mimeType) newPayload.mimeType = "image/jpeg";

                args[0] = "https://aisandbox-pa.googleapis.com/v1/flow/uploadImage";
                args[1].body = JSON.stringify(newPayload);
                args[1].method = "POST";
            }
            
            const res = await originalFetch(...args);
            
            if (args[0].includes("uploadImage")) {
                (async () => {
                    try {
                        const text = await res.clone().text();
                        let rawJson = {};
                        try { rawJson = JSON.parse(text); } catch(e) {}
                        
                        // ⚠️ QUAN TRỌNG: MOCK ĐỊNH DẠNG CŨ để N8N KHÔNG BỊ CRASH DO ĐỔI CẤU TRÚC
                        if (rawJson.media && rawJson.media.name) {
                            captured = { image: { name: rawJson.media.name } };
                            
                            // --- ĐỔI TÊN ẢNH THÀNH UUID ĐỂ TIỆN CHO VIC SEARCH LẠI VỀ SAU ---
                            if (rawJson.workflow && rawJson.workflow.name) {
                                try {
                                    const pathMatch = window.location.pathname.match(/\/project\/([a-zA-Z0-9-]+)/);
                                    const projectId = pathMatch ? pathMatch[1] : "";
                                    const patchHeaders = authHeaders ? authHeaders : { 'Content-Type': 'application/json' };
                                    if (!patchHeaders['Content-Type']) patchHeaders['Content-Type'] = 'application/json';
                                    
                                    await originalFetch(`https://aisandbox-pa.googleapis.com/v1/flowWorkflows/${rawJson.workflow.name}`, {
                                        method: 'PATCH',
                                        headers: patchHeaders,
                                        body: JSON.stringify({
                                            workflow: { name: rawJson.workflow.name, projectId: projectId, metadata: { displayName: rawJson.media.name } },
                                            updateMask: "metadata.displayName"
                                        })
                                    });
                                    UI.log("✅ Lệnh Rename DisplayName thành UUID: " + rawJson.media.name);
                                } catch(e) {}
                            }
                        } else if (!captured && rawJson.error) {
                            captured = rawJson; // CATCH ALL ERRORS TỪ GOOGLE
                            UI.log("⚠️ Lỗi Google API (Sẽ đẩy về n8n): " + JSON.stringify(rawJson));
                        } else if (!captured) {
                            UI.log("⚠️ Bỏ qua gói mạng trả về không chứa Hình: " + text.slice(0, 100));
                        }
                    } catch(e) {
                        UI.log("🚨 Lỗi khi parse Upload Response: " + e.message);
                    }
                })();
                
                // 🛡️ CHỐNG CRASH REACT (MÀN HÌNH ĐEN): 
                // Trả về cho giao diện web Google một vỏ bọc mảng rỗng để React không bị lỗi "Application error: a client-side exception..."
                return new Response(JSON.stringify({ generatedImages: [], media: [] }), { 
                    status: 200, 
                    headers: { 'Content-Type': 'application/json' } 
                });
            }
            return res;
        };

        // 2. Kích hoạt UI (GIỮ NGUYÊN PROMPT TỰ NHIÊN ĐỂ NÚT GENERATE KHÔNG BỊ XÁM)
        await UI.generate(null);

        let timeout = 0;
        while (!captured && timeout < 300) { 
            await UI.sleep(500);
            timeout++;
        }

        window.fetch = originalFetch;
        callback(captured || { status: "error", message: "150s_TIMEOUT_UPLOAD_OR_FETCH_MASK_MISMATCH" });
    } catch (e) {
        callback({ status: "error", message: e.message });
    }
}
runUploadHijack();
"""

# =============================================================
# 3. MẪU JAVASCRIPT: TẠO ẢNH (LOG CHI TIẾT & CẤU TRÚC MẢNG)
# =============================================================
_JS_IMAGE_GEN = _JS_IMAGE_UI_FUNCTIONS + """
const callback = arguments[arguments.length - 1];
const input = __PAYLOAD__; 

async function runImageGen() {
    try {
        const originalFetch = window.fetch;
        let captured = null;

        // 1. HIJACK FETCH: Tự lắp ráp linh kiện, n8n không cần gửi nữa
        window.fetch = async (...args) => {
            const urlStr = (args[0] || "").toString();
            const hasBody = args[1] && typeof args[1].body === 'string';
            const isImage = (urlStr.includes("batch") || urlStr.includes("predict") || urlStr.includes("generate") || urlStr.includes("async"))
                             && urlStr.includes("v1") && !urlStr.includes("log") && hasBody && args[1].body.includes("{");

            if (isImage && args[1]) {
                let parsed = JSON.parse(args[1].body);
                
                // Lấy mảng ID từ n8n (sếp đã khai báo là ref_ids)
                const ids = Array.isArray(input.ref_ids) ? input.ref_ids : [];

                if (parsed.requests) {
                    parsed.requests.forEach(req => {
                        if (ids.length > 0) {
                            // ✅ CẤU TRÚC "CÓ HÌNH": Dùng imageInputs và key "name"
                            req.imageInputs = ids.map(id => ({
                                name: id, 
                                imageInputType: "IMAGE_INPUT_TYPE_REFERENCE"
                            }));
                            // Không xóa imageGenerationRequestData vì nó chứa prompt
                        } else {
                            // 🔄 CẤU TRÚC "THUẦN PROMPT": Giữ nguyên mặc định của Google
                            req.imageInputs = [];
                        }

                        if (input.prompt) {
                            req.prompt = input.prompt;
                            if (req.imageGenerationRequestData) {
                                req.imageGenerationRequestData.textInput = req.imageGenerationRequestData.textInput || {};
                                req.imageGenerationRequestData.textInput.prompt = input.prompt;
                                if (req.imageGenerationRequestData.textInput.structuredPrompt && req.imageGenerationRequestData.textInput.structuredPrompt.parts) {
                                    try { req.imageGenerationRequestData.textInput.structuredPrompt.parts[0].text = input.prompt; } catch(e){}
                                } else {
                                    req.imageGenerationRequestData.textInput.structuredPrompt = { parts: [{ text: input.prompt }] };
                                }
                            }
                        }
                    });

                    args[1].body = JSON.stringify(parsed);
                    UI.log(`🧬 Đã tiêm ${ids.length} ảnh mồi vào gói tin (Cấu trúc: ${ids.length > 0 ? 'imageInputs' : 'Default'})`);
                }
            }
            const response = await originalFetch(...args);
            if (isImage) { 
                (async () => {
                    try {
                        let text = await response.clone().text();
                        let tempJson = {};
                        try { tempJson = JSON.parse(text); } catch(e) {}
                        
                        if (tempJson && (tempJson.media || tempJson.generatedImages || (tempJson.message && tempJson.message.media) || tempJson.error)) {
                            captured = tempJson;
                        } else {
                            if (text.includes('"media"') || text.includes('"generatedImages"')) {
                                UI.log("⚠️ Có vẻ JSON dạng đặc biệt / mảng: " + text.slice(0, 100));
                                // Hack: If it's pure array of images
                                if (text.startsWith('[') && text.includes('"mediaId"')) captured = { generatedImages: JSON.parse(text) };
                            } else {
                                UI.log("⚠️ Bỏ qua gói tin phụ rác (Không có chuỗi media)");
                            }
                        }
                    } catch(e) { UI.log("🚨 Lỗi parser: " + e.message); }
                })();
            }
            return response;
        };

        // 2. THỰC THI UI
        await UI.setTab("Image"); // Sửa lại thành Image cho chuẩn tiếng Anh
        await UI.setTool("Tạo hình ảnh");
        await UI.setSettings("Image", input.ratio, input.outputs || 1);
        if (input.ref_ids && input.ref_ids.length > 0) {
            await UI.autoClickIngredient(input.ref_ids);
        }
        await UI.generate(input.prompt);

        // 3. CHỜ KẾT QUẢ
        let wait = 0;
        while (!captured && wait < 150) { if (wait % 5 === 0) UI.log(`⏳ Đang chờ ảnh về... (${wait}s)`); await UI.sleep(1000); wait++; }

        // 4. HẬU KỲ: Update Ingredient (Để Video Worker dùng được ảnh này)
        if (captured && captured.generatedImages) {
            UI.log(`🛠️ Đang khai báo nguyên liệu cho ${captured.generatedImages.length} ảnh...`);
            for (let img of captured.generatedImages) {
                const mediaName = img.image?.name || img.name;
                if (!mediaName) continue;

                await originalFetch("https://labs.google/fx/api/trpc/videoFx.updateFlowMedia", {
                    method: "POST",
                    headers: { "content-type": "application/json" },
                    body: JSON.stringify({ 
                        json: { 
                            media: { name: mediaName, mediaMetadata: { isIngredient: true } }, 
                            updateMask: "media.media_metadata.is_ingredient" 
                        } 
                    })
                });
            }
        }

        window.fetch = originalFetch; 
        callback(captured || { status: "error", message: "CHECK_TIMEOUT" });

    } catch (e) { callback({ status: "error", message: e.message }); }
}
runImageGen();
"""

_JS_IMAGE_GEN_UPLOAD = _JS_IMAGE_UI_FUNCTIONS + """
const callback = arguments[arguments.length - 1];
const input = __PAYLOAD__; 

const logMe = (icon, msg) => {
    const text = `[${icon}] ${msg}`;
    console.log(text); 
    if (typeof UI !== 'undefined' && UI.log) UI.log(icon, msg); 
};

const findCAMa = (obj) => {
    const str = JSON.stringify(obj);
    const match = str.match(/CAMa[a-zA-Z0-9_-]+/g);
    return match ? match[0] : null;
};

async function runImageGenAndUpload() {
    // ✅ KHAI BÁO BIẾN Ở ĐÂY ĐỂ TRÁNH LỖI SCOPE
    const originalFetch = window.fetch;
    let capturedGen = null;
    let savedHeaders = null;
    let authError = null; // 🚩 Biến quan trọng để bắt lỗi 403

    try {
        logMe("🚀", "Khởi động Hijack Fetch & Injector...");
        window.fetch = async (...args) => {
            const urlStr = (args[0] || "").toString();
            const hasBody = args[1] && typeof args[1].body === 'string';
            const isImage = (urlStr.includes("batch") || urlStr.includes("predict") || urlStr.includes("generate") || urlStr.includes("async"))
                             && urlStr.includes("v1") && !urlStr.includes("log") && hasBody && args[1].body.includes("{");
            
            if (isImage && args[1]) {
                logMe("📡", "Bắt được gói tin tạo hình. Đang xử lý nạp hình...");
                
                // 🔑 Bước 1: Lưu Headers để lách lỗi 401
                if (args[1].headers) {
                    savedHeaders = { ...args[1].headers };
                    logMe("🔑", "Đã lưu Headers Auth.");
                }

                // 🧬 Bước 2: TIÊM HÌNH MỒI (REF_IDS)
                let parsed = JSON.parse(args[1].body);
                const ids = Array.isArray(input.ref_ids) ? input.ref_ids : [];
                if (ids.length > 0 && parsed.requests) {
                    logMe("🧬", `Đang tiêm ${ids.length} mã CAMa mồi vào gói tin...`);
                    parsed.requests.forEach(req => {
                        // Kỹ thuật Clone Động (Bắt chước ảnh mồi mà UI vừa mới tự click)
                        if (req.imageInputs && req.imageInputs.length > 0) {
                            const template = req.imageInputs[0];
                            const originalKeys = Object.keys(template);
                            req.imageInputs = ids.map(id => {
                                let newItem = {};
                                originalKeys.forEach(key => { newItem[key] = (key === 'name') ? id : template[key]; });
                                return newItem;
                            });
                        } else if (req.imageGenerationRequestData && req.imageGenerationRequestData.imageInputs) { // Clone từ trong vỏ bọc
                            const template = req.imageGenerationRequestData.imageInputs[0];
                            const originalKeys = Object.keys(template || {});
                            req.imageGenerationRequestData.imageInputs = ids.map(id => {
                                let newItem = {};
                                originalKeys.forEach(key => { newItem[key] = (key === 'name') ? id : template[key]; });
                                return newItem;
                            });
                        } else { // Fallback mù
                            req.imageInputs = ids.map(id => ({ name: id, imageInputType: "IMAGE_INPUT_TYPE_REFERENCE" }));
                        }
                        
                        if (input.prompt) {
                            req.prompt = input.prompt;
                            if (req.imageGenerationRequestData) {
                                req.imageGenerationRequestData.textInput = req.imageGenerationRequestData.textInput || {};
                                req.imageGenerationRequestData.textInput.prompt = input.prompt;
                                if (req.imageGenerationRequestData.textInput.structuredPrompt && req.imageGenerationRequestData.textInput.structuredPrompt.parts) {
                                    try { req.imageGenerationRequestData.textInput.structuredPrompt.parts[0].text = input.prompt; } catch(e){}
                                } else {
                                    req.imageGenerationRequestData.textInput.structuredPrompt = { parts: [{ text: input.prompt }] };
                                }
                            }
                        }
                    });
                    args[1].body = JSON.stringify(parsed);
                }
            }

            const response = await originalFetch(...args);

             // Không block UI khi chờ API Google load (Có khi tới 90s)
            if (isImage) { 
                (async () => {
                    try {
                        // 🛑 BẮT LỖI 403 TẠI ĐÂY - TRẢ VỀ CHO WORKER
                        if (response.status === 403) {
                            authError = "LỖI 403: permission_denied - Google chặn quyền truy cập.";
                            logMe("🚫", authError);
                            capturedGen = { error: true }; // Thoát vòng lặp chờ nhanh
                            return;
                        }

                        let text = await response.clone().text();
                        let tempJson = {};
                        try { tempJson = JSON.parse(text); } catch(e) {}
                        
                        if (tempJson && (tempJson.media || tempJson.generatedImages || (tempJson.message && tempJson.message.media) || tempJson.error)) {
                            capturedGen = tempJson;
                            logMe("📥", "Đã nhận JSON API Chính (Có Media): " + JSON.stringify(capturedGen).substring(0, 200));
                        } else {
                            if (text.includes('"media"') || text.includes('"generatedImages"')) {
                                logMe("⚠️", "Có vẻ JSON dạng đặc biệt / mảng: " + text.slice(0, 100));
                                if (text.startsWith('[') && text.includes('"mediaId"')) capturedGen = { generatedImages: JSON.parse(text) };
                            } else {
                                logMe("⚠️", "Bỏ qua gói tin phụ rác (Không có chuỗi media/error): " + text.substring(0, 100));
                            }
                        }
                    } catch(e) { logMe("🚨", "Lỗi parser gói tin: " + e.message); }
                })();
            }
            return response;
        };

        // 3. THỰC THI UI
        logMe("🖱️", "Đang điều khiển UI...");
        await UI.setTab("Image");
        await UI.setTool("Tạo hình ảnh");
        await UI.setSettings("Image", input.ratio, input.outputs || 1);
        
        // Mấu chốt Selenium cũ: Phải cho nó bấm đại 1 ảnh trên UI thì gói tin Google mới chịu mở khóa Array
        if (input.ref_ids && input.ref_ids.length > 0) {
            await UI.autoClickIngredient(input.ref_ids);
        }
        
        await UI.generate(input.prompt);

        // 4. CHỜ KẾT QUẢ
        let wait = 0;
        while (!capturedGen && wait < 150) { 
            if (authError) break; // Thoát ngay nếu dính 403
            if (wait % 5 === 0) logMe("⏳", `Đang chờ ảnh về... (${wait}s)`);
            await UI.sleep(1000); 
            wait++; 
        }

        // 🔙 XỬ LÝ TRẢ VỀ CHO WORKER (TRỌNG TÂM - FIX 403)
        if (authError) {
            window.fetch = originalFetch;
            return callback({ 
                status: "error", 
                error_type: "PERMISSION_DENIED", 
                message: authError 
            });
        }

        // 5. HẬU KỲ "VÍT GA" (SỬ DỤNG UUID GỐC, KHÔNG RE-UPLOAD NỮA)
        let finalAssets = [];
        if (capturedGen && !capturedGen.error) {
            const imagesList = capturedGen.media || capturedGen.generatedImages || (capturedGen.message && capturedGen.message.media);
            
            if (imagesList && imagesList.length > 0) {
                logMe("🖼️", `Tìm thấy ${imagesList.length} ảnh. Nạp trực tiếp UUID vào chuỗi cung ứng!`);
                for (let [idx, img] of imagesList.entries()) {
                    const camsId = img.name || (img.image && img.image.name);
                    if (!camsId) continue;
                    
                    logMe("✅", `THÀNH CÔNG! UID Sinh ra: ${camsId}`);
                    // Cấp thẳng UUID này vào luồng Downstream của n8n, không cần vắt Base64 Re-upload rườm rà nữa!
                    finalAssets.push({ cams: camsId, cama: camsId, url: (img.image?.generatedImage?.fifeUrl || "") });
                }
            }
        }

        window.fetch = originalFetch; 
        logMe("🏁", `Batch xong. Trả về ${finalAssets.length} Assets.`);
        
        if (finalAssets.length === 0) {
            callback({ status: "error", assets: [], message: "Mảng rỗng (Có thể do Timeout / Google đổi tên API API Fetch / Safety Filter Cấm)" });
        } else {
            callback({ status: "success", assets: finalAssets });
        }

    } catch (e) { 
        window.fetch = originalFetch;
        logMe("🚨", `CRASH: ${e.message}`);
        callback({ status: "error", message: e.message }); 
    }
}
runImageGenAndUpload();
"""

# =============================================================
# 4. check video vào cuối file
# =============================================================
_JS_VIDEO_CHECK = """
const callback = arguments[arguments.length - 1];
const checkPayload = __PAYLOAD__; // Mảng [{"name": "ticket_id"}] do Gateway truyền xuống

async function runCheckHijack() {
    try {
        const originalFetch = window.fetch;
        let captured = null;
        const targetEndpoint = "v1/video:batchCheckAsyncVideoGenerationStatus";

        // Lấy chính xác projectId từ URL của giao diện web hiện tại
        const projectIdUrl = window.location.pathname.split('project/')[1];
        const currentProjectId = projectIdUrl ? projectIdUrl.split('/')[0] : "";

        // Format lại Payload nhồi nhét projectId vào từng object
        const finalPayload = {
            media: (checkPayload.operations || checkPayload).map(op => ({
                name: op.name,
                projectId: currentProjectId
            }))
        };

        window.fetch = async (...args) => {
            if (args[0].includes("batch") || args[0].includes("video")) {
                console.log("[SaaS-Check] 🎯 Đang tráo gói tin để Check Video theo format MỚI...");
                args[0] = "https://aisandbox-pa.googleapis.com/" + targetEndpoint;
                args[1].body = JSON.stringify(finalPayload);
                args[1].method = "POST";
            }

            const res = await originalFetch(...args);

            if (args[0].includes(targetEndpoint)) {
                const clone = res.clone();
                let tempCaptured = await clone.json();
                console.log("[SaaS-Check] ✅ Đã bắt được trạng thái Video!");
                
                try {
                    if (tempCaptured && tempCaptured.media) {
                        for (let item of tempCaptured.media) {
                            if (item.mediaMetadata && item.mediaMetadata.mediaStatus && item.mediaMetadata.mediaStatus.mediaGenerationStatus === "MEDIA_GENERATION_STATUS_SUCCESSFUL") {
                                let ticket = item.name;
                                console.log("[SaaS-Check] 🔗 Đang lùng sục URL MP4 gốc cho ticket: " + ticket);
                                // Fetch ngầm để Browser tự Follow Redirect lấy link GCS ẩn
                                let trpcRes = await originalFetch("https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name=" + ticket, { redirect: "follow" });
                                if (trpcRes.url && trpcRes.url.includes("storage.googleapis.com")) {
                                    item.resolved_url = trpcRes.url;
                                    console.log("[SaaS-Check] 🎈 Tìm thấy link Video: " + item.resolved_url);
                                }
                            }
                        }
                    }
                } catch(e) {
                    console.log("[SaaS-Check] ❌ Lỗi giải mã Redirect URL:", e);
                }
                
                captured = tempCaptured; // Gán chốt hạ để Vòng lặp While bên dưới biết là đã xử lý xong URL!

                // FAKE A 500 ERROR SO REACT REJECTS GRACEFULLY INSTEAD OF CRASHING ON INVALID BATCH_CHECK SCHEMA
                return new Response(JSON.stringify({error: "Bypass Validation"}), { 
                    status: 500, 
                    headers: { 'Content-Type': 'application/json' } 
                });
            }
            return res;
        };

        let input = null;
        let timeout_input = 0;
        while (!input && timeout_input < 20) { // Đợi tối đa 10s cho UI load xong lúc mới Rebirth
            input = document.querySelector('textarea') || document.querySelector('[contenteditable="true"]');
            if (!input) {
                await new Promise(r => setTimeout(r, 500));
                timeout_input++;
            }
        }
        if (!input) throw new Error("UI_NOT_READY");
        
        // MẸO CỨU MẠNG: Đâm thủng React bằng cách Click đè 6 lớp Parent của ảnh cuối cùng để đảm bảo kích hoạt Event OnClick
        const assets = Array.from(document.querySelectorAll('div[role="button"]'))
            .filter(d => d.querySelector('img') && !d.innerHTML.includes('Google Account'));
            
        if (assets.length > 0) {
            let p = assets[assets.length - 1].querySelector('img'); 
            for(let i=0; i<6; i++) {
                if(p && p !== document.body) {
                    try { p.click(); } catch(e){}
                    p = p.parentElement;
                }
            }
            await new Promise(r => setTimeout(r, 800));
            await new Promise(r => setTimeout(r, 800));
        } else {
            // KHÔNG CÓ ẢNH TRONG THƯ VIỆN -> Đổi sang Tab "Văn bản" để khỏi cần ảnh
            const tabs = Array.from(document.querySelectorAll('div[role="tab"]'));
            const textTab = tabs.find(t => t.innerText && (t.innerText.toLowerCase().includes('văn bản') || t.innerText.toLowerCase().includes('text')));
            if (textTab) textTab.click();
            await new Promise(r => setTimeout(r, 800));
        }
        
        input.focus();
        // Nhồi thật nhiều chữ cho chắc ăn qua bài test độ dài (nếu có)
        document.execCommand('insertText', false, "Check-Video-" + Date.now() + " - " + Math.random().toString(36).substring(7));
        input.dispatchEvent(new Event('input', { bubbles: true }));

        // POLL TÌM NÚT GENERATE SÁNG TRONG 20S (Giống _JS_VIDEO_GEN)
        let timeout_btn = 0;
        let btn = null;
        while (!btn && timeout_btn < 40) {
            const genBtns = Array.from(document.querySelectorAll('button'));
            btn = genBtns.find(b => {
                const inner = (b.innerText + " " + (b.innerHTML || "")).toLowerCase();
                return (inner.includes('arrow_forward') || inner.includes('auto_awesome') || inner.includes('✨')) && 
                       !inner.includes('arrow_forward_ios') && 
                       !b.disabled;
            });
            if (!btn) {
                await new Promise(r => setTimeout(r, 500));
                timeout_btn++;
            }
        }
        
        if (!btn) throw new Error("BTN_NOT_FOUND_OR_DISABLED");
        btn.click();


        // Chờ kết quả trả về
        let timeout = 0;
        while (!captured && timeout < 40) { // Check status thì đợi 20s là quá đủ
            await new Promise(r => setTimeout(r, 500));
            timeout++;
        }

        window.fetch = originalFetch; // Trả lại fetch nguyên bản
        callback(captured || { status: "error", message: "CHECK_TIMEOUT" });

    } catch (e) {
        callback({ status: "error", message: e.message });
    }
}
runCheckHijack();
"""
# =============================================================
# CÁC MẪU JAVASCRIPT THỰC THI (Đã đổi sang UI_V cho Video)
# =============================================================

_JS_VIDEO_GEN_FRAME = _JS_VIDEO_UI_FUNCTIONS + """
const callback = arguments[arguments.length - 1];
const payload = __PAYLOAD__; // Đây chính là cái payload phẳng từ n8n của sếp

async function runVideoGen() {
    try {
        UI_V.log(0, "🎣 Đang kích hoạt bẫy Hijack (Mapping n8n -> Google)...");
        const originalFetch = window.fetch;
        let captured = null;
        let fakeStartId = null;
        let fakeEndId = null;

        window.fetch = async (...args) => {
            const currentUrl = args[0];
            const isVid = currentUrl.includes("batchAsyncGenerateVideoStartAndEndImage");
            
            if (isVid && args[1]) {
                let body = JSON.parse(args[1].body);
                UI_V.log("4.1", "🎯 Đã bắt được gói tin, đang 'đổ' dữ liệu n8n vào...");

                // Map dữ liệu từ payload n8n vào cấu trúc Google
                if (body.requests && body.requests[0]) {
                    let req = body.requests[0];
                    
                    // 1. Prompt & Seed
                    req.textInput = req.textInput || {};
                    req.textInput.prompt = payload.prompt || "";
                    if (req.textInput.structuredPrompt && req.textInput.structuredPrompt.parts && req.textInput.structuredPrompt.parts.length > 0) {
                        try { req.textInput.structuredPrompt.parts[0].text = payload.prompt || ""; } catch(e) {}
                    } else {
                        req.textInput.structuredPrompt = { parts: [{ text: payload.prompt || "" }] };
                    }
                    req.seed = parseInt(payload.seed) || Math.floor(Math.random() * 100000);
                    
                    // 2. Aspect Ratio (Dịch từ 916 sang Enum của Google)
                    req.aspectRatio = payload.ratio === "916" ? "VIDEO_ASPECT_RATIO_PORTRAIT" : "VIDEO_ASPECT_RATIO_LANDSCAPE";
                    
                    // 3. Image IDs (Quan trọng nhất)
                    if (req.startImage) {
                        fakeStartId = req.startImage.mediaId;
                        req.startImage.mediaId = payload.start_image_id;
                    }
                    if (req.endImage) {
                        fakeEndId = req.endImage.mediaId;
                        req.endImage.mediaId = payload.end_image_id;
                    }
                    
                    // Giữ nguyên clientContext, modelKey và metadata của Google để không bị Forbidden
                }

                args[1].body = JSON.stringify(body);
                UI_V.log("4.2", "🚀 Đã tráo xong Payload chuẩn! Đang gửi...");
            }

            const res = await originalFetch(...args);
            if (isVid) {
                const result = await res.clone().json().catch(() => ({}));
                captured = result.error ? { status: "error", message: result.error.message } : result;
                
                let text = JSON.stringify(result);
                if (fakeStartId && payload.start_image_id) text = text.split(payload.start_image_id).join(fakeStartId);
                if (fakeEndId && payload.end_image_id) text = text.split(payload.end_image_id).join(fakeEndId);

                return new Response(text, { 
                    status: res.status || 200, 
                    headers: { 'Content-Type': 'application/json' } 
                });
            }
            return res;
        };

        // 2. THỰC THI UI
        await UI_V.setTab("Video");
        await UI_V.setTool("Tạo video từ văn bản");
        await UI_V.setSettings("Video", payload.ratio, payload.outputs, "khung hình");
        
        // Click 2 ảnh (Start và End) để mở khóa nút Tạo
        const refIds = [payload.start_image_id, payload.end_image_id].filter(id => id);
        for (let id of refIds) {
            await UI_V.autoClickIngredient([id]);
        }
        
        // Kích nổ: Bấm nút Tạo
        await UI_V.generate(payload.prompt, "video_gen_frame");

        let t = 0; while (!captured && t++ < 150) await UI_V.sleep(1000);
        window.fetch = originalFetch;
        callback(captured || { status: "error", message: "TIMEOUT_VIDEO_GEN" });

    } catch (e) { 
        console.error("❌ Lỗi:", e);
        callback({ status: "error", message: e.message }); 
    }
}
runVideoGen();
"""

JS_VIDEO_GEN_START_ONLY = _JS_VIDEO_UI_FUNCTIONS + """
const callback = arguments[arguments.length - 1];
const payload = __PAYLOAD__; 

async function runVideoGen() {
    try {
        UI_V.log(0, "🎣 Đang kích hoạt bẫy Hijack (Chế độ: Start Image Only)...");
        const originalFetch = window.fetch;
        let captured = null;
        let fakeStartId = null;

        window.fetch = async (...args) => {
            const currentUrl = args[0];
            // 1. ĐỔI ENDPOINT: Chuyển sang StartImage duy nhất
            const isVid = currentUrl.includes("batchAsyncGenerateVideoStartImage");
            
            if (isVid && args[1]) {
                let body = JSON.parse(args[1].body);
                UI_V.log("4.1", "🎯 Đã bắt được gói tin StartImage, đang tráo dữ liệu...");

                if (body.requests && body.requests[0]) {
                    let req = body.requests[0];
                    
                    // 2. MAPPING DỮ LIỆU TỪ n8n
                    req.textInput = req.textInput || {};
                    req.textInput.prompt = payload.prompt || "";
                    if (req.textInput.structuredPrompt && req.textInput.structuredPrompt.parts && req.textInput.structuredPrompt.parts.length > 0) {
                        try { req.textInput.structuredPrompt.parts[0].text = payload.prompt || ""; } catch(e) {}
                    } else {
                        req.textInput.structuredPrompt = { parts: [{ text: payload.prompt || "" }] };
                    }
                    req.seed = parseInt(payload.seed) || Math.floor(Math.random() * 100000);
                    
                    // Map tỷ lệ khung hình chuẩn Enum
                    req.aspectRatio = payload.ratio === "916" ? "VIDEO_ASPECT_RATIO_PORTRAIT" : "VIDEO_ASPECT_RATIO_LANDSCAPE";
                    
                    // 3. IMAGE ID: Chỉ nạp ảnh bắt đầu (Bỏ qua endImage)
                    if (req.startImage) {
                        fakeStartId = req.startImage.mediaId;
                        req.startImage.mediaId = payload.start_image_id;
                    }

                    // Lưu ý: Giữ nguyên videoModelKey (ví dụ: veo_3_1_...) để tránh bị Token Invalid
                }

                args[1].body = JSON.stringify(body);
                UI_V.log("4.2", "🚀 Payload 1 ảnh đã sẵn sàng! Đang gửi...");
            }

            const res = await originalFetch(...args);
            if (isVid) {
                const result = await res.clone().json().catch(() => ({}));
                captured = result.error ? { status: "error", message: result.error.message } : result;
                
                let text = JSON.stringify(result);
                if (fakeStartId && payload.start_image_id) text = text.split(payload.start_image_id).join(fakeStartId);

                return new Response(text, { 
                    status: res.status || 200, 
                    headers: { 'Content-Type': 'application/json' } 
                });
            }
            return res;
        };

        // --- QUY TRÌNH THAO TÁC UI ---
        await UI_V.setTab("Video");
        await UI_V.setTool("Tạo video từ hình ảnh"); 
        await UI_V.setSettings("Video", payload.ratio, payload.outputs, "khung hình");
        
        // Click ảnh Start để mở khóa nút Tạo
        if (payload.start_image_id) {
            await UI_V.autoClickIngredient([payload.start_image_id]);
        }
        
        // Bấm nút tạo
        await UI_V.generate(payload.prompt, "video_gen_start_image");

        let t = 0; while (!captured && t++ < 150) await UI_V.sleep(1000);
        window.fetch = originalFetch;
        callback(captured || { status: "error", message: "TIMEOUT_START_IMAGE_GEN" });

    } catch (e) { 
        console.error("❌ Lỗi Hijack:", e);
        callback({ status: "error", message: e.message }); 
    }
}
runVideoGen();
"""

_JS_VIDEO_GEN_REF = _JS_VIDEO_UI_FUNCTIONS + """
const callback = arguments[arguments.length - 1];
const payload = __PAYLOAD__; 

async function runVideoRefGen() {
    try {
        // Lấy danh sách ID từ payload (nếu n8n gửi lẻ thì gom lại thành mảng cho chắc)
        const imageIds = payload.images || [payload.start_image_id, payload.end_image_id].filter(id => id);
        const frameCount = Math.max(imageIds.length, 1); // Tối thiểu nạp 1 hình mồi

        UI_V.log(0, `🎣 Hijack khởi động: Xử lý ${frameCount} ảnh Reference...`);
        const originalFetch = window.fetch;
        let captured = null;
        let fakeId = null;

        window.fetch = async (...args) => {
            const currentUrl = args[0];
            const isRef = currentUrl.includes("batchAsyncGenerateVideo"); // Bắt mọi biến thể API video
            
            if (isRef && args[1]) {
                let body = JSON.parse(args[1].body);
                if (body.requests && body.requests[0]) {
                    let req = body.requests[0];
                    
                    // 🚀 KỸ THUẬT CLONE ĐỘNG (Bất tử trước mọi thay đổi key)
                    if (req.referenceImages && req.referenceImages.length > 0 && imageIds.length > 0) {
                        // 1. Lấy cái object đầu tiên làm "khuôn mẫu" (đã có sẵn mọi key mà Google yêu cầu)
                        const template = req.referenceImages[0];
                        fakeId = template.mediaId;
                        const originalKeys = Object.keys(template); // Lấy danh sách các key: ['mediaId', 'imageUsageType', ...]

                        // 2. Chạy vòng lặp theo số lượng imageIds của sếp
                        req.referenceImages = imageIds.map((id) => {
                            let newItem = {};
                            // 3. Copy y xì các key cũ, chỉ "đè" giá trị mới vào mediaId
                            originalKeys.forEach(key => {
                                newItem[key] = (key === 'mediaId') ? id : template[key];
                            });
                            return newItem;
                        });

                        UI_V.log("4.2", `🎯 Đã nhân bản ${imageIds.length} object theo khuôn mẫu gốc!`);
                    }
                    
                    req.textInput = req.textInput || {};
                    req.textInput.prompt = payload.prompt || "";
                    if (req.textInput.structuredPrompt && req.textInput.structuredPrompt.parts && req.textInput.structuredPrompt.parts.length > 0) {
                        try { req.textInput.structuredPrompt.parts[0].text = payload.prompt || ""; } catch(e) {}
                    } else {
                        req.textInput.structuredPrompt = { parts: [{ text: payload.prompt || "" }] };
                    }
                    req.seed = parseInt(payload.seed) || 0;
                }
                args[1].body = JSON.stringify(body);
            }

            const res = await originalFetch(...args);
            if (isRef) {
                captured = await res.clone().json().catch(() => ({}));
                
                let text = JSON.stringify(captured);
                if (fakeId) {
                    for (let id of imageIds) {
                        if (id) text = text.split(id).join(fakeId);
                    }
                }
                return new Response(text, { 
                    status: res.status || 200, 
                    headers: { 'Content-Type': 'application/json' } 
                });
            }
            return res;
        };

        // --- QUY TRÌNH UI ---
        await UI_V.setTab("Video");
        await UI_V.setTool(payload.type || "Tạo video từ các thành phần"); 
        await UI_V.setSettings("Video", payload.ratio, payload.outputs, "thành phần");
        
        // Call autoClickIngredient cho từng ảnh mồi để UI hợp lệ
        for (let idx = 0; idx < frameCount; idx++) {
            let targetId = imageIds[idx];
            if (targetId) await UI_V.autoClickIngredient([targetId]);
            else await UI_V.autoClickIngredient([]); // fallback click đại 1 tấm
        }
        
        // Gọi lệnh tạo
        await UI_V.generate(payload.prompt, "video_ref_gen", frameCount);

        let t = 0; while (!captured && t++ < 150) await UI_V.sleep(1000);
        window.fetch = originalFetch;
        callback(captured || { status: "error", message: "TIMEOUT_VIDEO_REF" });
    } catch (e) { callback({ status: "error", message: e.message }); }
}
runVideoRefGen();
"""

_JS_VIDEO_GEN_TEXT = _JS_VIDEO_UI_FUNCTIONS + """
const callback = arguments[arguments.length - 1];
const payload = __PAYLOAD__; 

async function runVideoTextGen() {
    try {
        UI_V.log(0, "🎣 Đang kích hoạt bẫy Hijack (Chế độ: Text Only)...");
        const originalFetch = window.fetch;
        let captured = null;

        window.fetch = async (...args) => {
            const currentUrl = args[0];
            const isVid = currentUrl.includes("batchAsyncGenerateVideo");
            
            if (isVid && args[1]) {
                let body = JSON.parse(args[1].body);
                if (body.requests && body.requests[0]) {
                    let req = body.requests[0];
                    req.textInput = req.textInput || {};
                    req.textInput.prompt = payload.prompt || "";
                    if (req.textInput.structuredPrompt && req.textInput.structuredPrompt.parts && req.textInput.structuredPrompt.parts.length > 0) {
                        try { req.textInput.structuredPrompt.parts[0].text = payload.prompt || ""; } catch(e) {}
                    } else {
                        req.textInput.structuredPrompt = { parts: [{ text: payload.prompt || "" }] };
                    }
                    req.seed = parseInt(payload.seed) || Math.floor(Math.random() * 100000);
                    req.aspectRatio = payload.ratio === "916" ? "VIDEO_ASPECT_RATIO_PORTRAIT" : "VIDEO_ASPECT_RATIO_LANDSCAPE";
                }
                args[1].body = JSON.stringify(body);
            }

            const res = await originalFetch(...args);
            if (isVid) {
                const result = await res.clone().json().catch(() => ({}));
                captured = result.error ? { status: "error", message: result.error.message } : result;
            }
            return res;
        };

        await UI_V.setTab("Video");
        await UI_V.setTool("Tạo video từ văn bản");
        await UI_V.setSettings("Video", payload.ratio, payload.outputs);
        
        await UI_V.generate(payload.prompt, "video_gen_text");

        let t = 0; while (!captured && t++ < 150) await UI_V.sleep(1000);
        window.fetch = originalFetch;
        callback(captured || { status: "error", message: "TIMEOUT_TEXT_GEN" });

    } catch (e) { callback({ status: "error", message: e.message }); }
}
runVideoTextGen();
"""

_JS_TOTAL_HACK = """
async function totalVisibilityHack() {
    console.log("🚀 [MẮT THẦN] Đang kích hoạt bùa hộ mệnh Visibility...");
    
    const ghostProp = { get: () => 'visible', configurable: true };
    Object.defineProperty(document, 'visibilityState', ghostProp);
    Object.defineProperty(document, 'webkitVisibilityState', ghostProp);
    Object.defineProperty(document, 'hidden', { get: () => false, configurable: true });

    window.IntersectionObserver = class {
        constructor(callback) { this.callback = callback; }
        observe(target) {
            this.callback([{ isIntersecting: true, intersectionRatio: 1, target: target }]);
            return null;
        }
        unobserve() { return null; }
        disconnect() { return null; }
    };

    setInterval(() => {
        document.dispatchEvent(new Event('visibilitychange'));
        window.focus(); 
    }, 500);
}
// Thực thi luôn ngay khi nạp vào
await totalVisibilityHack();
"""

# =============================================================
# HÀM ĐIỀU PHỐI (MAIN DISPATCHER)
# =============================================================
def get_morphing_js(task_type, endpoint, payload, project_id=""):
    safe_data = json.dumps(payload)

    # --- PHẦN LOGIC CHUNG CHO MỌI TASK ---
    # Mình sẽ luôn đính kèm cái Hack này vào đầu mọi script trả về
    header_js = _JS_TOTAL_HACK
    
    prompt = payload.get('prompt', '').replace('`', '\\`') # Tránh lỗi nếu prompt có dấu `
    
    # 1. Nhóm tạo nội dung (Dùng logic UI chuyên biệt)
    if task_type == "image_gen":
        return _JS_IMAGE_GEN.replace("__PAYLOAD__", safe_data)
    elif task_type == "image_gen_upload":
        return _JS_IMAGE_GEN_UPLOAD.replace("__PAYLOAD__", safe_data) 
    elif task_type in ["video_gen_text", "video_gen_frame", "video_ref_gen","video_gen_start_image"]:
        if task_type == "video_gen_text":
            js_template = _JS_VIDEO_GEN_TEXT
        elif task_type == "video_gen_frame":
            js_template = _JS_VIDEO_GEN_FRAME
        elif task_type == "video_gen_start_image":
            js_template = JS_VIDEO_GEN_START_ONLY
        else:
            js_template = _JS_VIDEO_GEN_REF

        # TRẢ VỀ SẠCH SẼ: Chỉ ghép Functions và Template
        # Không tự ý gọi UI_V.generate ở đây nữa
        return f"""
        {_JS_VIDEO_UI_FUNCTIONS}
        {js_template.replace("__PAYLOAD__", safe_data)}
        """

    # 2. Nhóm tác vụ hệ thống
    elif task_type == "upload":
        return _JS_UPLOAD.replace("__ENDPOINT__", endpoint).replace("__PAYLOAD__", safe_data)
        
    elif task_type == "video_check":
        return _JS_VIDEO_CHECK.replace("__PAYLOAD__", safe_data)

    return ""