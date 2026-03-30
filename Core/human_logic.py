import time
import random
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

class HumanLogic:
    def __init__(self, driver):
        self.driver = driver

    def random_sleep(self, min_s=1, max_s=3):
        """Nghỉ ngẫu nhiên để không tạo ra quy luật"""
        time.sleep(random.uniform(min_s, max_s))

    def type_like_human(self, element, text):
        """Gõ phím từng chữ một với tốc độ và nhịp điệu ngẫu nhiên"""
        self.driver.execute_script("arguments[0].focus();", element)
        for char in text:
            element.send_keys(char)
            # Độ trễ giữa các phím từ 0.05s đến 0.2s (tốc độ gõ người thật)
            time.sleep(random.uniform(0.05, 0.2))
        self.random_sleep(0.5, 1.5)

    def move_to_and_click(self, element):
        """Rê chuột đến phần tử trước khi click (tránh click nhảy cóc)"""
        actions = ActionChains(self.driver)
        # Di chuyển chuột đến phần tử
        actions.move_to_element(element).perform()
        self.random_sleep(0.5, 1.2)
        # Click
        actions.click().perform()
        self.random_sleep(1, 2)

    def natural_scroll(self):
        """Cuộn trang nhẹ nhàng như đang đọc nội dung"""
        scroll_amount = random.randint(200, 500)
        self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self.random_sleep(1, 2)

    def wait_and_find(self, selector, by=By.CSS_SELECTOR, timeout=10):
        """Tìm phần tử và chờ đợi một cách tự nhiên"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                element = self.driver.find_element(by, selector)
                if element.is_displayed():
                    return element
            except:
                pass
            time.sleep(0.5)
        return None

class PlaywrightCaptchaSolver:
    def __init__(self, page):
        self.page = page
        
    def detect_captcha_type(self):
        """Nhận diện loại Captcha dựa trên DOM"""
        # Ưu tiên bắt Text trước để xác định chính xác
        if self.page.locator("xpath=//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '2 đối tượng') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '2 identical') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'same shape') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'similar objects')]").count() > 0:
            return 'match'
            
        # Nếu có thanh kéo thì chốt luôn là Slide (Ưu tiên kiểm tra class trượt trước khi check text xoay dễ bị nhầm lẫn)
        if self.page.locator('.secsdk-captcha-drag-icon, .captcha_verify_img_slide').count() > 0 or self.page.locator("xpath=//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'trượt') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'drag the puzzle piece')]").count() > 0:
            return 'slide'

        if self.page.locator("xpath=//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'xoay') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'rotate')]").count() > 0 or self.page.locator('.rotate-captcha').count() > 0:
            return 'rotate'
        
        # Fallback chung
        if self.page.locator('.captcha-verify-container, .captcha_verify_container, #captcha-verify-image').count() > 0:
            return 'unknown'
            
        return None

    def solve(self, context=None):
        """Thực thi giải mã Captcha tích hợp 2Captcha và Tracking Log"""
        import time
        import os
        from Tools.TiktokScraper import tiktok_db
        
        if context is None:
            context = {}

        captcha_type = self.detect_captcha_type()
        
        log_data = {
            'module_name': context.get('module_name', 'Unknown'),
            'worker_id': context.get('worker_id', 'Unknown'),
            'target_type': context.get('target_type', 'Unknown'),
            'target_id': context.get('target_id', 'Unknown'),
            'captcha_id': None,
            'captcha_type': captcha_type or 'Unknown',
            'status': 'Failed',
            'recognition_time': 0,
            'cost': 0.0,
            'result_raw': None,
            'page_url': self.page.url,
            'ip_address': None # Optional
        }

        if not captcha_type:
            return False
            
        print(f"[{time.strftime('%H:%M:%S')}] >>> Phát hiện Captcha loại: {captcha_type.upper()}. Đang gọi đệ tử 2Captcha để giải...")
        start_time = time.time()
        
        try:
            from twocaptcha import TwoCaptcha
            import tempfile
            
            api_key = os.environ.get("TWOCAPTCHA_API_KEY", "65630cea55805ecfdb977d61950470d9")
            if not api_key:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Không tìm thấy biến môi trường TWOCAPTCHA_API_KEY. Bỏ qua giải tự động.")
                return False
                
            solver = TwoCaptcha(api_key)
            
            # Chọn khối Captcha
            captcha_container = self.page.locator('.captcha-verify-container, .captcha_verify_container, #captcha-verify-image')
            if captcha_container.count() > 0:
                captcha_element = captcha_container.first
                img_path = os.path.join(tempfile.gettempdir(), f'tiktok_captcha_{int(time.time())}.png')
                captcha_element.screenshot(path=img_path)
                print(f"[{time.strftime('%H:%M:%S')}] 📸 Đã chụp ảnh màn hình vùng Captcha. Đang gửi lên hệ thống 2Captcha...")
                
                # Gọi 2Captcha tuỳ theo loại
                try:
                        if captcha_type == 'slide' or captcha_type == 'unknown':
                            # TikTok Slide uses coordinates.
                            # We instruct the worker to click the destination of the puzzle piece
                            result = solver.coordinates(img_path, textinstructions="Click the center of the missing puzzle piece hole on the right")
                            print(f"[{time.strftime('%H:%M:%S')}] 🎯 Đã nhận lời giải từ AI (Coordinates): {result}")
                            code_str = result.get('code')
                            
                            log_data['captcha_id'] = result.get('captchaId')
                            log_data['result_raw'] = str(result)
                            # 2Captcha usually charges $0.001 for normal image resolving unless stated otherwise
                            log_data['cost'] = 0.001
                            
                            if code_str:
                                # code is usually list of dicts like [{'x': '136', 'y': '51'}] or a string "x=136,y=51"
                                target_x_raw = 0
                                # Try to grab the exact distance from the result dictionary first if it was resolved as 'canvas'
                                # But we used 'coordinates'. If 'coordinates', it usually sends 'code: x=100,y=20'
                                import re
                                
                                # If the AI sends multiple coordinates (e.g. x=57,y=187;x=272,y=178)
                                # It might have misunderstood as a Click Captcha. We will just use the horizontal distance.
                                if isinstance(code_str, str) and ';' in code_str:
                                    coords = re.findall(r'x=([0-9]+)', code_str)
                                    if len(coords) >= 2:
                                        # The distance is the difference between the two X points
                                        target_x_raw = abs(int(coords[1]) - int(coords[0]))
                                else:
                                    match = re.search(r'x=([0-9]+)', str(code_str).lower())
                                    if match:
                                        target_x_raw = int(match.group(1))
                                    else:
                                        clean_num = ''.join(filter(str.isdigit, str(code_str)))
                                        target_x_raw = int(clean_num) if clean_num else 0

                                # Normalize coordinates based on Device Pixel Ratio
                                dpr = self.page.evaluate("window.devicePixelRatio") or 1
                                target_x = target_x_raw / dpr
                                        
                                print(f"[{time.strftime('%H:%M:%S')}] 🤖 Toạ độ X đích từ AI: {target_x_raw} (CSS pixel: {target_x:.2f})")
                                    
                                drag_handle = self.page.locator('.secsdk-captcha-drag-icon, .captcha_verify_img_slide').first
                                if drag_handle.count() > 0:
                                    box = drag_handle.bounding_box()
                                    container_box = captcha_element.bounding_box()
                                    
                                    try:
                                        if box and container_box:
                                            # Move to center of drag handle
                                            start_x = box['x'] + box['width'] / 2
                                            start_y = box['y'] + box['height'] / 2
                                            
                                            # Tọa độ tuyệt đối của đích đến trên màn hình (target_x tính từ mép trái container)
                                            target_screen_x = container_box['x'] + target_x
                                            
                                            # Thực tế khoảng cách kéo = Đích đến (screen X) - Vị trí hiện tại thanh kéo (screen X)
                                            drag_distance = target_screen_x - start_x
                                            
                                            print(f"[{time.strftime('%H:%M:%S')}] 🤖 Thanh trượt sẽ được kéo (Drag Distance): {drag_distance:.2f} px")
                                            
                                            # Draw a visual red dot so user can debug
                                            self.page.evaluate(f'''
                                                (() => {{
                                                    const dot = document.createElement('div');
                                                    dot.style.position = 'absolute';
                                                    dot.style.left = '{target_screen_x}px';
                                                    dot.style.top = '{start_y}px';
                                                    dot.style.width = '12px';
                                                    dot.style.height = '12px';
                                                    dot.style.backgroundColor = 'red';
                                                    dot.style.border = '2px solid white';
                                                    dot.style.borderRadius = '50%';
                                                    dot.style.zIndex = '2147483647';
                                                    dot.style.transform = 'translate(-50%, -50%)';
                                                    dot.style.pointerEvents = 'none';
                                                    document.body.appendChild(dot);
                                                    setTimeout(() => dot.remove(), 5000);
                                                }})()
                                            ''')
                                            
                                            self.page.mouse.move(start_x, start_y)
                                            self.page.mouse.down()
                                            time.sleep(0.5)
                                            
                                            # Drag parameters
                                            overshoot = random.uniform(3, 8)
                                            total_drag = drag_distance + overshoot
                                            
                                            # Phase 1: Fast ease-out to overshoot point
                                            steps = random.randint(25, 40)
                                            import math
                                            # Khởi tạo độ cong Y trơn tru (không giật cục)
                                            y_curve_amplitude = random.uniform(2, 6)
                                            y_curve_direction = random.choice([-1, 1])
                                            
                                            for i in range(1, steps + 1):
                                                # Sine ease-out
                                                progress = math.sin((i / steps) * (math.pi / 2))
                                                current_x = start_x + (total_drag * progress)
                                                
                                                # Tạo ra một hình vòng cung mượt mà thay vì giật ngẫu nhiên mỗi frame
                                                curve_progress = math.sin((i / steps) * math.pi) # 0 -> 1 -> 0
                                                smooth_y = start_y + (curve_progress * y_curve_amplitude * y_curve_direction)
                                                
                                                self.page.mouse.move(current_x, smooth_y)
                                                time.sleep(random.uniform(0.01, 0.04))
                                                
                                            time.sleep(random.uniform(0.1, 0.3)) # Micro-pause when recognizing overshoot
                                            
                                            # Phase 2: Slow correction back to target
                                            correction_steps = random.randint(5, 10)
                                            for i in range(1, correction_steps + 1):
                                                # Linear or ease back
                                                progress = i / correction_steps
                                                current_x = (start_x + total_drag) - (overshoot * progress)
                                                self.page.mouse.move(current_x, start_y)
                                                time.sleep(random.uniform(0.02, 0.05))
                                                
                                            self.page.mouse.up()
                                            time.sleep(2)
                                            log_data['status'] = 'Success'
                                            log_data['recognition_time'] = int(time.time() - start_time)
                                            tiktok_db.insert_captcha_log(log_data)
                                            return True
                                        else:
                                            print(f"[{time.strftime('%H:%M:%S')}] ❌ Không lấy được toạ độ bounding box của thanh kéo.")
                                            log_data['result_raw'] = str(result) + " (Failed to find drag handle box)"
                                    except Exception as e:
                                         print(f"[{time.strftime('%H:%M:%S')}] ❌ Lỗi phân tích toạ độ hoặc kéo thả: {e}")
                                         log_data['result_raw'] = str(result) + f" (Exception: {e})"
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] ❌ Không tìm thấy thanh trượt trên DOM.")
                                    log_data['result_raw'] = str(result) + " (Failed to find drag handle DOM)"
                                     
                        elif captcha_type == 'rotate':
                            result = solver.coordinates(img_path)
                            print(f"[{time.strftime('%H:%M:%S')}] 🎯 Đã nhận toạ độ từ AI: {result}")
                            
                            log_data['captcha_id'] = result.get('captchaId')
                            log_data['result_raw'] = str(result)
                            log_data['cost'] = 0.001
                            
                            log_data['status'] = 'Success'
                            log_data['recognition_time'] = int(time.time() - start_time)
                            tiktok_db.insert_captcha_log(log_data)
                            return True
                            
                        elif captcha_type == 'match':
                            # Chụp ảnh và gửi lên 2Captcha với yêu cầu tìm 2 hình giống nhau
                            result = solver.coordinates(img_path, textinstructions="Click on the 2 identical objects")
                            print(f"[{time.strftime('%H:%M:%S')}] 🎯 Đã nhận toạ độ từ AI (Match): {result}")
                            code_str = result.get('code')
                            
                            log_data['captcha_id'] = result.get('captchaId')
                            log_data['result_raw'] = str(result)
                            log_data['cost'] = 0.001
                            
                            if code_str:
                                coords_list = []
                                if isinstance(code_str, list):
                                    coords_list = code_str
                                else:
                                    import re
                                    matches = re.findall(r'x=([0-9]+),y=([0-9]+)', str(code_str).lower())
                                    for match in matches:
                                        coords_list.append({'x': match[0], 'y': match[1]})
                                
                                if len(coords_list) >= 2:
                                    dpr = self.page.evaluate("window.devicePixelRatio") or 1
                                    container_box = captcha_element.bounding_box()
                                    if container_box:
                                        for pt in coords_list[:2]:
                                            target_x = int(pt['x']) / dpr
                                            target_y = int(pt['y']) / dpr
                                            
                                            click_x = container_box['x'] + target_x
                                            click_y = container_box['y'] + target_y
                                            
                                            self.page.mouse.move(click_x, click_y)
                                            time.sleep(random.uniform(0.1, 0.3))
                                            self.page.mouse.down()
                                            time.sleep(random.uniform(0.05, 0.15))
                                            self.page.mouse.up()
                                            time.sleep(random.uniform(0.5, 1.0))
                                            
                                        print(f"[{time.strftime('%H:%M:%S')}] 👆 Đã click xong 2 điểm giống nhau. Đang tìm nút Xác nhận (nếu có)...")
                                        
                                        confirm_btn = self.page.locator(".captcha-verify-container button:has-text('Confirm'), .captcha-verify-container button:has-text('Xác nhận'), .captcha_verify_container button:has-text('Confirm'), .captcha_verify_container button:has-text('Xác nhận'), .verify-captcha-submit-button").first
                                        if confirm_btn.count() > 0:
                                            # Wait for button to be enabled (aria-disabled="false" or not disabled)
                                            for _ in range(5):
                                                if confirm_btn.get_attribute("aria-disabled") == "false" or not confirm_btn.is_disabled():
                                                    print(f"[{time.strftime('%H:%M:%S')}] 🖱️ Đã thấy nút Xác nhận sáng lên, tiến hành Click!")
                                                    confirm_btn.click(force=True)
                                                    break
                                                time.sleep(1)
                                            else:
                                                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Nút Xác nhận không sáng lên, thử force-click luôn!")
                                                confirm_btn.click(force=True)
                                        else:
                                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Không tìm thấy nút Xác nhận, có thể tự động Verify hoặc giao diện khác.")
                                            
                                        time.sleep(2)
                                        log_data['status'] = 'Success'
                                        log_data['recognition_time'] = int(time.time() - start_time)
                                        tiktok_db.insert_captcha_log(log_data)
                                        return True
                                    else:
                                        print(f"[{time.strftime('%H:%M:%S')}] ❌ Không lấy được bounding_box của Captcha.")
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] ❌ 2Captcha trả về thiếu tọa độ (< 2 điểm): {code_str}")
                                    
                except Exception as solver_e:
                    print(f"[{time.strftime('%H:%M:%S')}] ❌ 2Captcha API từ chối hoặc thất bại: {solver_e}")
                    log_data['result_raw'] = f"Solver Exception: {solver_e}"
                    
        except ImportError:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Thiếu thư viện giải mã! Xin chạy lệnh lệnh: pip install 2captcha-python")
            log_data['result_raw'] = "ImportError: 2captcha-python missing"
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ Lỗi ngoại lệ hệ thống Captcha: {e}")
            log_data['result_raw'] = f"Exception: {e}"
            
        log_data['recognition_time'] = int(time.time() - start_time)
        tiktok_db.insert_captcha_log(log_data)
        return False