import subprocess
import sys
import os
import signal
import threading
import time
from queue import Queue, Empty

# Ensure project root is in PYTHONPATH so module imports work
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ["PYTHONPATH"] = PROJECT_ROOT

from Core import db_manager

# Ép stdout ra UTF-8 để không bị chết khi print Emoji
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    """Thread-safe print function to prevent reentrant calls."""
    with print_lock:
        print(*args, **kwargs)

class SystemManager:
    def __init__(self):
        self.processes = []
        self.output_queue = Queue()
        self.is_running = True

    def start_process(self, name, command):
        """Khởi chạy một tiến trình con và tự động phục hồi nếu nó tử vong"""
        def watcher():
            while self.is_running:
                try:
                    env = os.environ.copy()
                    env["PYTHONIOENCODING"] = "utf-8"
                    env["PYTHONUNBUFFERED"] = "1" 
                    
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, 
                        text=True,
                        encoding='utf-8',
                        bufsize=1, 
                        shell=True,
                        cwd=PROJECT_ROOT,
                        env=env
                    )
                    self.processes.append(process)

                    try:
                        for line in iter(process.stdout.readline, ''):
                            if line:
                                self.output_queue.put(f"[{name}] {line.strip()}")
                    except ValueError: 
                        pass
                    finally:
                        if process.stdout:
                            process.stdout.close()
                            
                    process.wait()
                    if process in self.processes:
                        self.processes.remove(process)
                        
                except Exception as e:
                    safe_print(f"❌ Lỗi watcher {name}: {e}")
                
                if not self.is_running:
                    break
                    
                code = process.returncode if 'process' in locals() else 'Unknown'
                safe_print(f"[{time.strftime('%H:%M:%S')}] ⚠️ [{name}] Worker sập nguồn (Code {code}). Hệ thống tự kích điện hồi sinh sau 3s...")
                time.sleep(3)
                
                # Check lại lần nữa sau khi ngủ dậy để tránh Hồi Sinh Ma (Phantom Resurrection) lúc đang hỏa hoạn
                if not self.is_running:
                    break
                    
                # Khởi động lại
                safe_print(f"[{time.strftime('%H:%M:%S')}] ⚡ [{name}] BAT DAU HOI SINH...")

        thread = threading.Thread(target=watcher, daemon=True)
        thread.start()
        return thread

    def run_pre_tasks(self):
        safe_print("======================================================")
        safe_print("    DANG KHOI DONG HE THONG SAAS V8.2 - LUAN ULTRA    ")
        safe_print("     (Quan ly Profile và Project qua PostgreSQL)      ")
        safe_print("======================================================")
        
        # 1. Dọn rác
        safe_print(f"[{time.strftime('%H:%M:%S')}] 🧹 Dang tieu diet Chrome 'zombie'...")
        subprocess.run("taskkill /F /IM chrome.exe /T >nul 2>&1", shell=True)
        subprocess.run("taskkill /F /IM chromedriver.exe /T >nul 2>&1", shell=True)
        subprocess.run("taskkill /F /FI \"WINDOWTITLE eq Sign in to Chrome\" /T >nul 2>&1", shell=True)
        
        safe_print(f"[{time.strftime('%H:%M:%S')}] 🗑️ Dang chay lao cong xoa rac...")
        subprocess.run(["python", os.path.join(PROJECT_ROOT, "Tools", "Diagnostics", "cleanup_profiles.py")], cwd=PROJECT_ROOT)
        time.sleep(2)

        # 2. Check DB
        safe_print(f"[{time.strftime('%H:%M:%S')}] 🗄️ Dang check ket noi Postgres...")
        res = subprocess.run(["python", "-m", "Tools.Diagnostics.check_db"], cwd=PROJECT_ROOT)
        if res.returncode != 0:
            safe_print("[!] LOI: Chua ket noi duoc Database! He thong dung lai.")
            sys.exit(1)

    def spawn_workers(self):
        # 2. Mở Media Workers
        safe_print(f"[{time.strftime('%H:%M:%S')}] 🎥 Dang mo Media Worker (Port 9000)...")
        self.start_process("MEDIA_9000", "python Workers/media_worker.py")
        time.sleep(1)

        safe_print(f"[{time.strftime('%H:%M:%S')}] 🎞️ Dang mo Custom Media Worker (Port 9001)...")
        self.start_process("MEDIA_9001", "python Workers/custom_media.py 9001")
        time.sleep(1)

        # 3. Lọc danh sách Playwright Worker từ DB
        safe_print(f"[{time.strftime('%H:%M:%S')}] 🤖 Dang doc danh sach Playwright Worker tu Database...")
        try:
            active_workers = db_manager.get_active_selenium_workers()
            if not active_workers:
                safe_print("⚠️ Khong tim thay worker nao dang bat (status = 'On') trong Database!")
            else:
                for worker_id, port in active_workers:
                    worker_name = worker_id.upper()
                    safe_print(f"[{time.strftime('%H:%M:%S')}] 🚀 Khoi dong {worker_name} tren port {port}...")
                    self.start_process(worker_name, f"python Workers/playwright_worker.py {worker_id} {port}")
                    time.sleep(2) # Giãn cách khởi động để máy không bị sốc RAM
        except Exception as e:
            safe_print(f"❌ Lỗi truy vấn DB: {e}")

    def stream_logs(self):
        safe_print("\n------------------------------------------------------")
        safe_print(f"[{time.strftime('%H:%M:%S')}] 💥 HE THONG DA SAN SANG! Dang log output...")
        safe_print("------------------------------------------------------\n")
        
        while self.is_running:
            try:
                # Tránh treo vòng lặp vô hạn, dùng timeout
                log_line = self.output_queue.get(timeout=0.1)
                safe_print(log_line)
            except Empty:
                pass
            except KeyboardInterrupt:
                raise # Bắn ngược lỗi lên hàm Bố (main) để gọi shutdown()

    def shutdown(self):
        safe_print("\n🛑 Nhan lenh DUNG he thong! Dang giet cac tien trinh con (Sieu toc)...")
        self.is_running = False
        
        # 1. Quét sạch tất cả tiến trình con thông qua PID Tree của Windows để không dính "Not Responding"
        for p in self.processes:
            try:
                subprocess.run(f"taskkill /F /T /PID {p.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                p.kill() # Dự phòng
                
        # 2. Xóa sổ triệt để hậu duệ của Chrome nếu PID tree của Playwright chạy ngầm bị sót
        subprocess.run("taskkill /F /IM chrome.exe /T >nul 2>&1", shell=True)
        subprocess.run("taskkill /F /IM chromedriver.exe /T >nul 2>&1", shell=True)
        
        safe_print("✅ Da dong cua tat ca he thong an toan va sach se!")

def main():
    manager = SystemManager()

    # Nhúng thêm hàm tắt OS-level Windows Handler bằng ctypes. Ghi đè sự kiện Bấm X tắt màn hình Đen
    try:
        import ctypes, os
        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
        def os_exit_handler(dwCtrlType):
            safe_print("\n[HỆ THỐNG] Phát hiện lệnh Tắt Màn Hình Đen (Nút X)!")
            manager.shutdown()
            os._exit(0)
            return True
        ctypes.windll.kernel32.SetConsoleCtrlHandler(os_exit_handler, True)
    except Exception as e:
        safe_print(f"Lỗi hook CMD X: {e}")
    
    try:
        manager.run_pre_tasks()
        manager.spawn_workers()
        manager.stream_logs()
    except KeyboardInterrupt:
        # Bắt dính cục diện Phím Ctrl+C ở đây
        safe_print("\n[HỆ THỐNG] Đã bắt được phím Ctrl+C!")
    finally:
        # Dù hệ thống vỡ lỗi, hay người dùng bấm Ctrl+C, hàm Shutdown BẮT BUỘC phải thực thi
        manager.shutdown()

if __name__ == "__main__":
    main()
