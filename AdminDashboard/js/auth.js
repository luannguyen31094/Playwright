let NGROK_URL = localStorage.getItem('sh_ngrokUrl') || '';
let API_KEY = localStorage.getItem('sh_apiKey') || '';

window.onload = async () => {
    document.getElementById('urlInput').value = NGROK_URL;
    document.getElementById('apiKeyInput').value = API_KEY;

    if (NGROK_URL && API_KEY) {
        await connectN8N();
    }
};

async function connectN8N() {
    const inUrl = document.getElementById('urlInput').value.trim();
    const inKey = document.getElementById('apiKeyInput').value.trim();
    const errText = document.getElementById('loginError');
    const btnConnect = document.getElementById('btnConnect');

    let url = inUrl;
    if (url && !url.startsWith('http')) url = 'https://' + url;
    if (url.endsWith('/')) url = url.slice(0, -1);

    NGROK_URL = url;
    API_KEY = inKey;

    if (!NGROK_URL || !API_KEY) {
        errText.innerText = '🚨 Lỗi Đăng Nhập: Vui lòng điền đủ 2 ô Link API và Mật khẩu!';
        errText.classList.remove('hidden');
        return;
    }

    errText.classList.add('hidden');
    btnConnect.disabled = true;
    btnConnect.innerText = "Đang kết nối...";

    try {
        const res = await fetch(`${NGROK_URL}/webhook/get-data?type=login`, { headers: getHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.success && data.server_signature === "TLAdmin_Automation_V1_Secured") {
            localStorage.setItem('sh_ngrokUrl', NGROK_URL);
            localStorage.setItem('sh_apiKey', API_KEY);

            // Chỉ set mặc định Light mode nếu người dùng KHÔNG CÓ TRẠNG THÁI (chưa từng chọn)
            if (!localStorage.getItem('theme')) {
                localStorage.setItem('theme', 'light');
                if(typeof layout_change === 'function') layout_change('light');
            }

            document.getElementById('login-overlay').classList.add('hidden');
            document.getElementById('app-container').classList.remove('hidden');

            // Default tab
            switchTab('tab-scripts');
        } else {
            throw new Error(data.error || "Máy chủ API giả mạo hoặc sai mât khẩu!");
        }
    } catch (e) {
        errText.innerText = `Lỗi Mạng Backend: ${e.message}`;
        errText.classList.remove('hidden');
    } finally {
        btnConnect.disabled = false;
        btnConnect.innerText = "🚀 KẾT NỐI HỆ THỐNG";
    }
}

function logout() {
    localStorage.removeItem('sh_apiKey');
    API_KEY = '';
    document.getElementById('app-container').classList.add('hidden');
    document.getElementById('login-overlay').classList.remove('hidden');
    document.getElementById('apiKeyInput').value = '';
}
