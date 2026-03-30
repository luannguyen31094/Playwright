import os
import shutil
import time
import undetected_chromedriver as uc
import winreg
import random
from selenium_stealth import stealth
from selenium.webdriver.common.by import By

# Khai báo URL Project Labs
BASE_PROJECT_VN_URL = "https://labs.google/fx/vi/tools/flow/project"
BASE_PROJECT_URL = "https://labs.google/fx/tools/flow/project"

def get_chrome_version():
    """Tự động lấy phiên bản Chrome đang cài trên Windows"""
    try:
        path = r"Software\Google\Chrome\BLBeacon"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
        version, _ = winreg.QueryValueEx(key, "version")
        return int(version.split('.')[0])
    except:
        return 144 

def setup_worker_profile(profile_name, user_data_dir):
    if not profile_name or not isinstance(profile_name, str):
        raise ValueError("profile_name (folder_name) không được trống - kiểm tra bảng client_registry cho Worker này")
    profile_folder = profile_name.replace(" ", "_")
    worker_path = os.path.join(user_data_dir, profile_folder)
    template_path = os.path.join(user_data_dir, "Profile_Template")
    
    if not os.path.exists(worker_path): 
        if os.path.exists(template_path):
            try:
                # Dùng dirs_exist_ok để nếu có lỡ trùng cũng không văng lỗi
                shutil.copytree(template_path, worker_path, dirs_exist_ok=True)
            except Exception as e:
                print(f"⚠️ Cảnh báo copy template: {e}")
                if not os.path.exists(worker_path): os.makedirs(worker_path)
        else:
            os.makedirs(worker_path)
    return worker_path

def clear_chrome_locks(worker_path):
    """Dọn dẹp triệt để các file khóa"""
    lock_files = ["SingletonLock", "Parent.lock", "lockfile", "lock"]
    for lock in lock_files:
        lp = os.path.join(worker_path, lock)
        if os.path.exists(lp):
            try: os.remove(lp)
            except: pass

def get_uc_options(worker_path, port):
    """Thiết lập tham số tàng hình & Chia 5 ô dọc bên trái màn hình"""
    options = uc.ChromeOptions()

    # 🚀 CHIÊU MỚI: Bật tính năng ghi lại Network Performance
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # 📏 QUY HOẠCH CỘT DỌC BÊN TRÁI (Cho màn 1920x1080)
    width = 450   # Chiều rộng vừa đủ nhìn
    height = 216  # Chiều cao chia đều 5 tầng (1080 / 5)
    
    # Tính số thứ tự 0, 1, 2, 3, 4 dựa trên Port
    index = (port % 10) - 1 
    
    x_pos = 0               # Sát mép trái
    y_pos = index * height  # Xếp chồng từ trên xuống dưới
    
    # Áp dụng kích thước và vị trí (Thay thế cho --start-maximized)
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument(f"--window-position={x_pos},{y_pos}")

    # 🛡️ BẢO HIỂM HIỆN THỊ: Ép UI nhỏ lại để không bị vỡ nút trong ô hẹp
    options.add_argument("--force-device-scale-factor=0.3")

    options.add_argument(f"--user-data-dir={worker_path}")
    options.add_argument("--profile-directory=Default")
    options.add_argument(f'--remote-debugging-port={port + 1000}')
    options.add_argument("--disable-extensions")
    
    flags = [
        "--no-first-run", 
        "--no-default-browser-check",
        "--password-store=basic",
        # 🚫 CHIÊU ĐỘC: Tắt cơ chế "Window Occlusion" - Chống đóng băng khi bị che hoặc thu nhỏ
        "--disable-features=SearchEngineChoiceScreen,IdentityConsistency,InProductHelp,IPH_GoogleFormsUpdate,CalculateNativeWinOcclusion",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        # ----------------------------------------------------------------------------------
        "--disable-first-run-ui",
        "--no-service-autorun",
        "--disable-notifications",
        "--disable-signin-promo",
        "--disable-dev-shm-usage",
        "--no-sandbox"
    ]
    for flag in flags: options.add_argument(flag)
    return options

def apply_stealth_masks(driver):
    """Đắp mặt nạ chống Bot Detection"""
    renderers = ["Intel Iris OpenGL Engine", "NVIDIA GeForce RTX 3060", "AMD Radeon RX 6700 XT"]
    stealth(driver,
        languages=["vi-VN", "vi"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer=random.choice(renderers),
        fix_hairline=True
    )   

def create_persistent_driver(profile_name, port, project_id, user_data_dir):
    try:
        if not profile_name:
            print("❌ Lỗi khởi tạo Factory: folder_name (profile) trống - Worker chưa được cấu hình trong bảng client_registry.")
            return None
        if not project_id:
            print("❌ Lỗi khởi tạo Factory: project_id trống - Kiểm tra cột project_id trong client_registry.")
            return None
        # 1. Tạo đường dẫn profile và copy template
        worker_path = setup_worker_profile(profile_name, user_data_dir)
        clear_chrome_locks(worker_path)
        
        # 🚀 CHIÊU MỚI: Tách biệt Driver thực thi để tránh WinError 183
        # Copy file chromedriver.exe vào folder riêng của worker nếu cần, 
        # hoặc dùng tham số 'driver_executable_path'
        
        options = get_uc_options(worker_path, port)
        
        # 🛡️ KHÓA TRANH CHẤP: Dùng lock file để đảm bảo tại 1 thời điểm chỉ 1 driver khởi tạo
        lock_path = os.path.join(user_data_dir, "factory_init.lock")
        
        # Chờ đến khi "đường thông"
        while os.path.exists(lock_path):
            time.sleep(random.uniform(0.2, 0.5))
            
        try:
            # Cắm cờ bắt đầu khởi tạo
            with open(lock_path, "w") as f: f.write(profile_name)
            
            print(f"🚀 Driver [{profile_name}]: Khởi tạo tại Port {port + 2000}...")
            
            driver = uc.Chrome(
                options=options, 
                port=port + 2000, 
                use_subprocess=True, 
                version_main=144, # Sếp nhớ check version chrome máy sếp nhé
                # browser_executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe"
            )
        finally:
            # Khởi tạo xong hoặc lỗi đều phải nhổ cờ để thằng khác vào
            if os.path.exists(lock_path): os.remove(lock_path)

        apply_stealth_masks(driver)
        target_url = f"https://labs.google/fx/vi/tools/flow/project/{project_id}"
        driver.get(target_url)
        return driver
        
    except Exception as e:
        print(f"❌ Lỗi khởi tạo Factory: {str(e)}")
        return None