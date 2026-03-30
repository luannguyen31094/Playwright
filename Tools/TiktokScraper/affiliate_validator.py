import os
import sys
import time
import traceback
import subprocess
import re
import random
import requests
from ppadb.client import Client as AdbClient

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
import Tools.TiktokScraper.tiktok_db as tiktok_db

# --- CONFIG ---
DEVICE_SERIAL = os.environ.get("DEVICE_SERIAL", "R5CXA22PV7T") # Samsung S24
ADB_HOST = "127.0.0.1"
ADB_PORT = 5037
ZALO_WEBHOOK = os.environ.get("WEBHOOK_URL", "https://n8n.luan031094.online/webhook/tiktok_notification")

def now(): return time.strftime('%H:%M:%S')

class AndroidDeviceValidator:
    def __init__(self, serial):
        self.serial = serial
        self.adb_client = AdbClient(host=ADB_HOST, port=ADB_PORT)
        self.device = None
        
    def connect_device(self):
        print(f"[{now()}] 🚀 Kết nối tới thiết bị Android: {self.serial}")
        
        try:
            # Khởi động ADB server nếu chưa chạy
            subprocess.run(["adb", "start-server"], check=False, stdout=subprocess.DEVNULL)
            
            self.device = self.adb_client.device(self.serial)
            
            if not self.device:
                print(f"[{now()}] ❌ Không thể kết nối ADB tới thiết bị {self.serial}. Vui lòng cắm cáp hoặc kiểm tra adb devices.")
                return False
                
            print(f"[{now()}] ✅ Đã kết nối ADB tới thiết bị: {self.serial}")
            return True
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi kết nối ADB: {e}")
            return False

    def disconnect_device(self):
        print(f"[{now()}] 🛑 Kết thúc phiên làm việc với thiết bị: {self.serial}")

    def get_first_product_tap_coords(self):
        """Tính toán toạ độ tap dựa trên % kích thước màn hình thiết bị (25% Width, 49% Height)"""
        try:
            output = self.device.shell("wm size").strip()
            # Ví dụ: "Physical size: 1080x2340"
            match = re.search(r'(\d+)x(\d+)', output)
            if match:
                w, h = map(int, match.groups())
                # Nằm ở 1/4 bên trái, và ngay giữa màn hình (49% chiều cao để né chữ)
                return int(w * 0.25), int(h * 0.49)
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi lấy kích thước màn hình: {e}")
            
        print(f"[{now()}] ⚠️ Sử dụng toạ độ mặc định (250, 1150)")
        return 250, 1150 # Fallback cho S24

    def extract_commission(self, retry=3):
        """Bốc dữ liệu hoa hồng bằng XML Dump"""
        for i in range(1, retry + 1):
            popup_opened = False
            try:
                # Cắn XML lần đầu
                xml_dump = self.device.shell("uiautomator dump /dev/tty")
                
                # Né lỗi Video auto-play chặn uiautomator
                scroll_attempts = 0
                while xml_dump and "ERROR" in xml_dump and scroll_attempts < 4:
                    print(f"[{now()}] ⚠️ Video TikTok đang chạy chặn XML Dump, cuộn nhẹ màn hình ({scroll_attempts+1}/4)...")
                    # Cuộn một đoạn ngắn (300px) để đẩy video khuất dần nhưng vẫn giữ lại Banner Hoa Hồng
                    self.device.shell("input swipe 500 1500 500 1200 300")
                    time.sleep(1.5)
                    xml_dump = self.device.shell("uiautomator dump /dev/tty")
                    scroll_attempts += 1
                
                if xml_dump and "ERROR" in xml_dump:
                    print(f"[{now()}] ❌ Không thể vượt qua lỗi Idle Video. Bỏ qua lần này.")
                    pass
                else:
                    print(f"[{now()}] ✅ Dump UI thành công, đang phân tích nội dung...")
                
                # Gom toàn bộ chữ trên UI thành một chuỗi duy nhất để regex không bị đứt đoạn bởi tag XML
                texts = re.findall(r'(?:text|content-desc)="([^"]+)"', xml_dump if xml_dump else "")
                full_text = " ".join(texts)
                
                if getattr(self, "debug", False):
                    print(f"[{now()}] 🔍 Full text từ UI:\n{full_text}")
                
                # Regex lấy tiền hoa hồng từ text đã nối trên trang chính (không cần Popup)
                match = re.search(r'Ki[eế]m\s*([\d.,]+)\s*[đ₫]', full_text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace('.', '').replace(',', '')
                    return int(amount_str)
                else:
                    print(f"[{now()}] 🔍 Không tìm thấy mẫu 'Kiếm ...đ' trong màn hình hiện tại.")
                        
            except Exception as e:
                pass
            
            print(f"[{now()}] 🔄 Thử lại lần {i}/{retry}...")
            time.sleep(2)
            
        return None

    def capture_and_alert(self, product_id):
        """Chụp màn hình khi lỗi và báo Zalo"""
        try:
            timestamp = int(time.time())
            screenshot_path = f"D:/TiktokScraper/Screenshots/err_{product_id}_{timestamp}.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            
            result = self.device.screencap()
            with open(screenshot_path, "wb") as fp:
                fp.write(result)
                
            print(f"[{now()}] 📸 Đã lưu ảnh lỗi: {screenshot_path}")
            
            # Bắn Webhook Zalo
            requests.post(ZALO_WEBHOOK, json={
                "message": f"❌ Lỗi tìm hoa hồng sản phẩm!\nProductID: {product_id}\nThiết bị: {self.serial}\nĐường dẫn ảnh: {screenshot_path}",
                "type": "error"
            })
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi chụp ảnh/gửi Zalo: {e}")

    def run_validation(self, min_sales=50):
        print(f"[{now()}] 🔍 BẮT ĐẦU KIỂM TRA HOA HỒNG (ADB - THIẾT BỊ {self.serial}) - NGƯỠNG BÁN: {min_sales}")
        products_to_check = tiktok_db.get_high_sales_products_to_check(min_sales)
        
        if not products_to_check:
            print(f"[{now()}] 💤 Không có sản phẩm cần kiểm tra hôm nay.")
            return
            
        print(f"[{now()}] 🎯 Tìm thấy {len(products_to_check)} sản phẩm cần kiểm tra.")
        
        if not self.connect_device():
            return
            
        try:
            for index, product in enumerate(products_to_check):
                tiktok_p_id = product["tiktok_product_id"]
                sold = product["total_sold"]
                print(f"\n[{now()}] 🛒 [{index+1}/{len(products_to_check)}] SP: {tiktok_p_id} (Đã bán: {sold})")
                
                # Đánh thức App Tiktok trước phòng trường hợp bị force close
                self.device.shell("monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1")
                time.sleep(2.0)
                
                # Sử dụng Web Link kết hợp App Links của Android để điều hướng (Sẽ tự mở App)
                cmd = f"am start -W -a android.intent.action.VIEW -d https://shop.tiktok.com/view/product/{tiktok_p_id}"
                self.device.shell(cmd)
                
                # Đợi danh sách sản phẩm load (App tự nhảy về Search List thay vì Detail)
                print(f"[{now()}] ⏳ Cầu nối web mở danh sách sản phẩm, chờ 8.0s...")
                time.sleep(8.0)
                
                # Auto-tap bấm vào tâm ảnh sản phẩm đầu tiên bên trái dựa trên độ phân giải
                x, y = self.get_first_product_tap_coords()
                print(f"[{now()}] 👆 Bấm vào giữa ảnh Sản phẩm đầu tiên trên Danh sách ({x}, {y})...")
                self.device.shell(f"input tap {x} {y}")
                
                # Đợi Product Detail load (Hoa hồng thường load chậm hơn UI 1 nhịp)
                wait_time = random.uniform(5.0, 7.0)
                print(f"[{now()}] ⏳ Bấm xong, chờ {wait_time:.1f}s cho hệ thống nạp số Dư Hoa Hồng...")
                time.sleep(wait_time)
                
                # Extract bằng XML Dump
                commission_amount = self.extract_commission()
                
                if commission_amount is not None:
                    # Giả định rate là 0.0 do chưa trích xuất được số Tỷ lệ %, chỉ lưu số Tiền Mặt
                    print(f"[{now()}] 💸 🎉 THÀNH CÔNG! Bốc được giá Hoa hồng: {commission_amount}đ cho Product {tiktok_p_id}")
                    tiktok_db.update_product_commission(tiktok_p_id, 0.0, commission_amount, True)
                else:
                    print(f"[{now()}] ❌ 👻 Trượt cấu trúc XML! Rất có thể Văng Acc, Lag hoặc Bị chặn.")
                    self.capture_and_alert(tiktok_p_id)
                    # Cannot confirm if not affiliate or login block, mark false tạm thời và None amount
                    tiktok_db.update_product_commission(tiktok_p_id, 0.0, None, False)
                    
                # Back về tránh dồn stack Activity trong Android gây tràn RAM
                self.device.shell("input keyevent 4")
                time.sleep(1)
                
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi thoát vòng lặp Validator: {e}")
            traceback.print_exc()
        finally:
            self.disconnect_device()
            print(f"[{now()}] ✅ Hoàn tất kịch bản. Chào thân ái.")

    def test_single_product(self, tiktok_product_id):
        """Hàm dùng riêng để test thử 1 sản phẩm"""
        print(f"[{now()}] 🧪 BẮT ĐẦU TEST SẢN PHẨM RIÊNG LẺ: {tiktok_product_id}")
        if not self.connect_device():
            return
            
        try:
            # Đánh thức App Tiktok trước phòng trường hợp bị force close
            self.device.shell("monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1")
            time.sleep(2.0)
            
            # Sử dụng Web Link kết hợp App Links của Android để điều hướng (Sẽ tự mở App)
            cmd = f"am start -W -a android.intent.action.VIEW -d https://shop.tiktok.com/view/product/{tiktok_product_id}"
            self.device.shell(cmd)
            
            # Đợi danh sách sản phẩm load
            print(f"[{now()}] ⏳ Cầu nối web mở danh sách sản phẩm, chờ 8.0s...")
            time.sleep(8.0)
            
            # Auto-tap bấm vào tâm ảnh sản phẩm đầu tiên bên trái dựa trên độ phân giải
            x, y = self.get_first_product_tap_coords()
            print(f"[{now()}] 👆 Bấm vào giữa ảnh Sản phẩm đầu tiên trên Danh sách ({x}, {y})...")
            self.device.shell(f"input tap {x} {y}")
            
            # Đợi App load trang chi tiết
            wait_time = random.uniform(5.0, 7.0)
            print(f"[{now()}] ⏳ Bấm xong, chờ {wait_time:.1f}s cho hệ thống nạp số Dư Hoa Hồng...")
            time.sleep(wait_time)
            
            # Extract bằng XML Dump
            commission_amount = self.extract_commission()
            
            if commission_amount is not None:
                print(f"[{now()}] 💸 🎉 THÀNH CÔNG! Bốc được giá Hoa hồng: {commission_amount}đ cho Product {tiktok_product_id}")
                # Không lưu vào DB lúc test thử để tránh rác DB
            else:
                print(f"[{now()}] ❌ 👻 Trượt cấu trúc XML! Rất có thể Văng Acc, Lag hoặc Bị chặn.")
                # self.capture_and_alert(tiktok_product_id) # Optionally alert on test
                
            # Back về
            self.device.shell("input keyevent 4")
            time.sleep(1)
            
        except Exception as e:
            print(f"[{now()}] ❌ Lỗi thoát vòng lặp Test: {e}")
            traceback.print_exc()
        finally:
            self.disconnect_device()
            print(f"[{now()}] ✅ Hoàn tất kịch bản test. Chào thân ái.")

if __name__ == "__main__":
    import sys
    validator = AndroidDeviceValidator(DEVICE_SERIAL)
    
    # Nếu truyền mã sản phẩm qua command line (vd: python affiliate_validator.py 1730032906806037048) thì test 1 cái
    if len(sys.argv) > 1:
        test_id = sys.argv[1]
        validator.test_single_product(test_id)
    else:
        # Chế độ chạy thực tế cào loạt
        try:
            validator.run_validation(min_sales=50)
            print(f"[{now()}] 🎉 Hoàn tất kiểm tra Hoa hồng trên App Tiktok.")
            
            # Gửi Webhook thành công
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "task_code": "STEP_3_COMMISSION_CHECK",
                        "status": "success",
                        "data": {},
                        "message": "Hoàn tất kiểm tra Hoa hồng trên App Tiktok"
                    }
                    import json
                    r = requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                    print(f"[{now()}] 📲 Đã gửi Webhook N8N! (HTTP {r.status_code})")
                except Exception as e:
                    print(f"[{now()}] ❌ Lỗi gửi Webhook kết thúc: {e}")
        except Exception as e:
            traceback.print_exc()
            
            # Webhook lỗi
            webhook_url = os.environ.get("WEBHOOK_URL")
            if webhook_url:
                try:
                    payload = {
                        "task_code": "STEP_3_COMMISSION_CHECK",
                        "status": "error",
                        "data": {"error": str(e)},
                        "message": "Có lỗi bất ngờ khi đồng kiểm tra Hoa hồng trên App Tiktok."
                    }
                    import json
                    requests.get(webhook_url, params={"data": json.dumps(payload)}, timeout=5)
                except:
                    pass
