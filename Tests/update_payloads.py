import os
import re

filepath = r"C:\Users\Admin\DockerFL\n8n-selenium-bridge\Core\js_payloads.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

UNIFIED_UI = '''"""
const UI = {
    sleep: (ms) => new Promise(r => setTimeout(r, ms)),
    log: function(a, b) {
        let step = typeof a === 'number' ? `[Bước ${a}] ` : "";
        console.log(`%c[SaaS-Worker] ${step}${b || a}`, "color: #00e5ff; font-weight: bold;");
    },
    
    forceClick(el) {
        if (!el) throw new Error("Phần tử null.");
        el.scrollIntoView({ block: 'center', inline: 'center' });
        if (el.disabled) { el.removeAttribute('disabled'); el.disabled = false; }
        ['mousedown', 'mouseup', 'click'].forEach(t => el.dispatchEvent(new MouseEvent(t, { bubbles: true })));
        return true;
    },

    async setTab(label) { 
        this.log(1, `🔄 Đang chuyển sang tab chính: ${label}...`);
        let menuBtn = Array.from(document.querySelectorAll('button[aria-haspopup]')).find(b => 
            !b.innerText.toLowerCase().includes('veo') && 
            (b.innerText.toLowerCase().includes('video') || b.innerText.toLowerCase().includes('image') || b.innerText.toLowerCase().includes('x'))
        );
        if (!menuBtn) return;
        menuBtn.click();
        await this.sleep(1000);
        const dialog = document.querySelector('[role="menu"]') || document.querySelector('.DropdownMenuContent');
        if (dialog) {
            const tabs = Array.from(dialog.querySelectorAll('button[role="tab"]'));
            const isVideo = label.toLowerCase().includes("video");
            const targetTypeBtn = tabs.find(b => b.innerText.toLowerCase().includes(isVideo ? 'video' : 'image'));
            if (targetTypeBtn && targetTypeBtn.getAttribute('aria-selected') !== 'true') {
                targetTypeBtn.click(); await this.sleep(1000);
            }
        }
        menuBtn.click();
        await this.sleep(1000);
    },
    async setTool(toolName) { this.log(1, `(Bỏ qua setTool cũ) Cấu hình chung...`); },

    async setSettings(ratio, outputs) {
        this.log(1, `⚙️ Đang mở cài đặt: Tỉ lệ ${ratio || 'Auto'} - Outputs ${outputs || 'Auto'}...`);
        
        let menuBtn = Array.from(document.querySelectorAll('button[aria-haspopup]')).find(b => 
            !b.innerText.toLowerCase().includes('veo') && 
            (b.innerText.toLowerCase().includes('video') || b.innerText.toLowerCase().includes('image') || b.innerText.toLowerCase().includes('x'))
        );
        
        if (!menuBtn) {
            this.log(1, "⚠️ Không tìm thấy nút Popup cài đặt. Bỏ qua cấu hình!");
            return;
        }

        menuBtn.click();
        await this.sleep(1500);

        const dialog = document.querySelector('[role="menu"]') || document.querySelector('.DropdownMenuContent');
        if (!dialog) return;

        const tabs = Array.from(dialog.querySelectorAll('button[role="tab"]'));
        
        if (ratio) {
            const txt = ratio == '916' ? 'Dọc' : (ratio == '169' ? 'Ngang' : ratio);
            const iconClass = ratio == '916' ? 'crop_9_16' : 'crop_16_9';
            let ratioBtn = tabs.find(b => b.innerText.includes(txt) || b.innerText.toLowerCase().includes(ratio == '916'? 'portrait':'landscape') || (b.innerHTML && b.innerHTML.includes(iconClass)));
            if (!ratioBtn && ratio == '916') ratioBtn = tabs.find(b => b.innerHTML && b.innerHTML.includes('crop_9_16'));
            
            if (ratioBtn && ratioBtn.getAttribute('aria-selected') !== 'true') {
                ratioBtn.click(); await this.sleep(1000);
            }
        }

        if (outputs) {
            const outBtn = tabs.find(b => b.innerText.trim().toLowerCase() === `x${outputs}`);
            if (outBtn && outBtn.getAttribute('aria-selected') !== 'true') {
                outBtn.click(); await this.sleep(1000);
            }
        }

        menuBtn.click(); 
        await this.sleep(1500);
    },

    async generate(prompt) {
        this.log(2, "✍️ Đang nhập Prompt...");
        const tx = document.querySelector('div[role="textbox"][data-slate-editor="true"]') || document.querySelector('textarea') || document.querySelector('[contenteditable="true"]');
        if (tx) {
            tx.focus();
            try { tx.innerHTML = ""; } catch(e) {}
            document.execCommand('insertText', false, prompt);
            tx.dispatchEvent(new Event('input', { bubbles: true }));
            await this.sleep(1500);
        }

        const genBtns = Array.from(document.querySelectorAll('button'));
        const targetGen = genBtns.find(b => 
            (b.innerText.includes('arrow_forward') || (b.innerHTML && b.innerHTML.includes('arrow_forward'))) 
        );

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
"""'''

# Replace the giant blocks
content = re.sub(r'_JS_IMAGE_UI_FUNCTIONS\s*=\s*""".*?"""', f'_JS_IMAGE_UI_FUNCTIONS = {UNIFIED_UI}', content, flags=re.DOTALL)
content = re.sub(r'_JS_VIDEO_UI_FUNCTIONS\s*=\s*""".*?"""', f'_JS_VIDEO_UI_FUNCTIONS = {UNIFIED_UI}', content, flags=re.DOTALL)

# In _JS_UPLOAD, fix the generate button locator
content = content.replace(
    'let btn = document.querySelector(\'button[aria-label*="Generate"]\') || document.querySelector(\'.gdArnN\');',
    '''let btn = Array.from(document.querySelectorAll('button')).find(b => (b.innerText.includes('arrow_forward') || (b.innerHTML && b.innerHTML.includes('arrow_forward'))));'''
)

# In _JS_VIDEO_CHECK, fix the generate button locator
content = content.replace(
    'let btn = document.querySelector(\'button[aria-label*="Generate"]\') || document.querySelector(\'.gdArnN\');',
    '''let btn = Array.from(document.querySelectorAll('button')).find(b => (b.innerText.includes('arrow_forward') || (b.innerHTML && b.innerHTML.includes('arrow_forward'))));'''
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Update completed successfully!")
