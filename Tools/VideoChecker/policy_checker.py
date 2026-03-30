import os
import sys
import subprocess
import base64
import requests
import json
import time
from pathlib import Path

# Thêm thư mục gốc vào sys.path để import tiktok_db
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Tools.TiktokScraper.tiktok_db import get_affiliate_connection

# Cấu hình API của Ollama chạy trên Local (Ollama hỗ trợ trực tiếp chuẩn OpenAI)
DOCKER_AI_API_URL = "http://localhost:11434/v1/chat/completions"
DOCKER_AI_MODEL_NAME = "moondream" 

def extract_frames(video_path, output_dir, fps=1):
    """
    Sử dụng ffmpeg để cắt video thành từng frame hình ảnh.
    fps=1 tức là mỗi giây cắt 1 hình.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"🎬 Đang cắt frame từ video: {video_path}")
    # Xoá các frame cũ nếu có
    for f in os.listdir(output_dir):
        if f.endswith('.jpg'):
            os.remove(os.path.join(output_dir, f))
            
    output_pattern = os.path.join(output_dir, "frame_%03d.jpg")
    
    # Lệnh ffmpeg cắt 1 frame mỗi giây
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"fps={fps}", 
        "-q:v", "2", # Chất lượng ảnh cao
        output_pattern
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"❌ Lỗi ffmpeg cắt frame: {result.stderr.decode('utf-8')}")
        return []
        
    # Lấy danh sách các frame đã cắt
    frames = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.jpg')])
    print(f"✅ Đã cắt xong {len(frames)} frames ảnh.")
    return frames

def encode_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def check_policy_with_smolvlm(frames_paths, rules_prompt):
    """
    Gửi danh sách các frame ảnh (dưới dạng Base64) kèm Text Rules cho SmolVLM đánh giá.
    """
    # Gửi TOÀN BỘ frames (mỗi giây 1 hình) không lọc bỏ
    selected_frames = frames_paths
    
    print(f"🕵️ Gửi TOÀN BỘ {len(selected_frames)} frames (1 khung hình/giây) cho AI phân tích...")
    
    content_array = [
        {"type": "text", "text": rules_prompt}
    ]
    for frame_path in selected_frames:
        b64_img = encode_image_base64(frame_path)
        content_array.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    messages = [
        {
            "role": "user",
            "content": content_array
        }
    ]

    payload = {
        "model": DOCKER_AI_MODEL_NAME,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.1
    }

    try:
        response = requests.post(DOCKER_AI_API_URL, json=payload, timeout=300)
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            return answer
        else:
            print(f"❌ Lỗi gửi API tới mô hình AI: {response.status_code} - {response.text}")
            return "ERROR_API"
    except Exception as e:
         print(f"❌ Lỗi không thể kết nối tới mô hình chạy Local Docker: {e}")
         return "ERROR_CONNECTION"

def process_campaign_video(campaign_id, video_path):
    """
    Hàm chính để chạy cho 1 campaign/video cụ thể.
    """
    if not os.path.exists(video_path):
        print(f"❌ Không tìm thấy file video: {video_path}")
        return False
        
    tmp_frames_dir = os.path.join(os.path.dirname(video_path), "tmp_frames")
    
    # 1. Cắt Frame
    frames = extract_frames(video_path, tmp_frames_dir)
    if not frames:
        return False
        
    # 2. Quy tắc chính sách cần kiểm tra
    instruction_rules = ""
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT instruction_active FROM ai_policy_rules WHERE platform = 'tiktok' AND is_active = TRUE LIMIT 1")
            row = cur.fetchone()
            if row and row[0]:
                instruction_rules = row[0]
                print(f"📖 Đã nạp thành công bộ luật 'tiktok' từ Database AI Policy!")
            else:
                print(f"⚠️ Không tìm thấy luật Policy cho 'tiktok' trong DB, sử dụng luật mặc định.")
        conn.close()
    except Exception as e:
        print(f"❌ Lỗi khi đọc luật từ DB: {e}")

    if not instruction_rules:
        # Fallback to the hardcoded prompt if DB query fails
        instruction_rules = (
            "1. Adult & Nudity: Sexually explicit content or overly revealing clothes.\n"
            "2. Prohibited Goods: Weapons, illicit drugs, medical devices, tobacco/e-cigarettes, hazardous materials, cash/coins, human parts, or live animals.\n"
            "3. Restricted E-commerce: Unapproved supplements, weight management, fresh foods, real estate, adult toys, or used goods.\n"
            "4. Intellectual Property: Counterfeit items, fake brands, or any unauthorized third-party watermarks/logos (e.g. Shopee, Lazada).\n"
            "5. Deceptive Behavior: Exaggerated claims, QR codes, or text redirecting off-TikTok.\n"
        )
        
    policy_prompt = (
        "You are an expert Content Moderator for TikTok. "
        "Review these frames from a video. Tell me if the video violates any of the following TikTok policies:\n"
        f"{instruction_rules}\n\n"
        "First, write a short explanation of what you see in the images and why it might violate the rules.\n"
        "Then, on a new line at the very end, write EXACTLY 'VERDICT: VIOLATION' if any rules are broken, or 'VERDICT: CLEAN' if the video is safe."
    )
    
    # 3. Yêu cầu AI kiểm tra bằng vòng lặp tránh tràn RAM
    MAX_TOTAL_FRAMES = 15
    if len(frames) > MAX_TOTAL_FRAMES:
        step = len(frames) / MAX_TOTAL_FRAMES
        selected_frames = [frames[int(i * step)] for i in range(MAX_TOTAL_FRAMES)]
    else:
        selected_frames = frames
        
    chunk_size = 5
    batch_index = 1
    total_batches = (len(selected_frames) + chunk_size - 1) // chunk_size
    
    status_to_update = "ready_to_upload" # Mặc định là sạch
    all_ai_results = []
    
    for i in range(0, len(selected_frames), chunk_size):
        chunk = selected_frames[i:i + chunk_size]
        print(f"\n🔄 Đang xử lý đợt {batch_index}/{total_batches} (Chứa {len(chunk)} frames trên tổng {len(selected_frames)})...")
        
        ai_result = check_policy_with_smolvlm(chunk, policy_prompt)
        print(f"🧠 AI Quyết định đợt {batch_index}: {ai_result}")
        all_ai_results.append(f"--- Đợt {batch_index} ---\n{ai_result}")
        
        if "VIOLATION" in ai_result.upper():
            print(f"🚫 Cảnh báo: Phát hiện Vi Phạm ở đợt {batch_index}! KHÓA VIDEO LẠI.")
            status_to_update = "policy_violation"
            break
        elif "ERROR" in ai_result.upper():
            status_to_update = "ai_check_failed"
            print(f"⚠️ Đợt {batch_index} AI gặp lỗi. Sẽ đánh dấu là Failed.")
            break
            
        batch_index += 1
    
    # 4. Cập nhật Database
    filename = os.path.basename(video_path)
    # Rút gọn trạng thái để lưu Audit Log
    if status_to_update == "policy_violation":
        ai_verdict = "VIOLATION"
    elif status_to_update == "ai_check_failed":
        ai_verdict = "ERROR"
    else:
        ai_verdict = "CLEAN"
        
    ai_explanation = "\n".join(all_ai_results)
    
    try:
        conn = get_affiliate_connection()
        with conn.cursor() as cur:
            # 1. Update trạng thái video
            cur.execute("""
                UPDATE aff_vid_campaigns 
                SET video_status = %s 
                WHERE id = %s
            """, (status_to_update, campaign_id))
            
            # 2. Lưu vết AI Policy Log
            cur.execute("""
                INSERT INTO ai_video_policy_logs (video_filename, project_source, reference_id, ai_verdict, ai_explanation)
                VALUES (%s, %s, %s, %s, %s)
            """, (filename, 'tiktok_affiliate', campaign_id, ai_verdict, ai_explanation))
            
            conn.commit()
            print(f"✔️ Đã cập nhật Campaign {campaign_id} thành: {status_to_update} và ghi chú Audit Log Policy thành công.")
        conn.close()
    except Exception as e:
        print(f"❌ Lỗi cập nhật Database (Update Campaign / Insert Log): {e}")
        
    return status_to_update

if __name__ == "__main__":
    print("🚀 Bắt đầu tool kiểm duyệt chính sách Video bằng SmolVLM")
