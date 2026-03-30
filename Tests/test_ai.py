import sys
sys.path.append('.')
import requests, base64
from Tools.VideoChecker.policy_checker import extract_frames, check_policy_with_smolvlm, DOCKER_AI_MODEL_NAME

print(f"[TEST] Dang ket noi vao Model [ {DOCKER_AI_MODEL_NAME} ] chay tren Windows Ollama goc...")

try:
    frames = extract_frames(r"D:\ChromeAutomation\MediaOutput\outputs\2video_final.mp4", r"D:\ChromeAutomation\MediaOutput\outputs\tmp_frames")
    
    policy_prompt = (
        "You are an expert Content Moderator for TikTok. "
        "Review these frames from a video. Tell me if the video violates any of the following TikTok policies:\\n"
        "1. Adult & Nudity: Sexually explicit content or overly revealing clothes.\\n"
        "2. Prohibited Goods: Weapons, illicit drugs, medical devices, tobacco/e-cigarettes, hazardous materials, cash/coins, human parts, or live animals.\\n"
        "3. Restricted E-commerce: Unapproved supplements, weight management, fresh foods, real estate, adult toys, or used goods.\\n"
        "4. Intellectual Property: Counterfeit items, fake brands, or any unauthorized third-party watermarks/logos (e.g. Shopee, Lazada).\\n"
        "5. Deceptive Behavior: Exaggerated claims, QR codes, or text redirecting off-TikTok.\\n\\n"
        "First, write a short explanation of what you see in the images and why it might violate the rules.\\n"
        "Then, on a new line at the very end, write EXACTLY 'VERDICT: VIOLATION' if any rules are broken, or 'VERDICT: CLEAN' if the video is safe."
    )
    
    print(f"[INFO] Da tach duoc {len(frames)} frames. Dang truyen vao AI de kiem duyet (10-20s do may Sep)...")
    result = check_policy_with_smolvlm(frames, policy_prompt)
    print("\n" + "="*50)
    print(f"[KET QUA] KET QUA AI TRA VE:\n{result}")
    print("="*50 + "\n")
    print("[SUCCESS] TUYET VOI! He thong da thong suot hoan toan!")
except Exception as e:
    print(f"❌ LỖI: {e}")
