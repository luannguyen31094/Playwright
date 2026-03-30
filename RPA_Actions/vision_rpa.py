import sys
import time

try:
    import pyautogui
    from PIL import ImageGrab
    import pyperclip
except ImportError:
    print("RPA dependencies not fully installed yet.")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Commands: capture, focus <window_name>, click <x> <y>, type <text>")
    sys.exit(1)

cmd = sys.argv[1]

# Cấu hình an toàn
pyautogui.FAILSAFE = True

if cmd == 'focus':
    import subprocess
    window_name = " ".join(sys.argv[2:])
    ps_cmd = f'(New-Object -ComObject WScript.Shell).AppActivate("{window_name}")'
    subprocess.run(["powershell", "-Command", ps_cmd])
    time.sleep(1) # Chờ 1 giây để cửa sổ nổi lên hoàn toàn
    print(f"OK: Focused window {window_name}")
elif cmd == 'capture':
    ImageGrab.grab().save('screen.png')
    print("OK: Screenshot saved to screen.png in current directory.")
elif cmd == 'click':
    try:
        x, y = int(sys.argv[2]), int(sys.argv[3])
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click(x, y)
        print(f"OK: Clicked at {x}, {y}")
    except Exception as e:
        print(f"Error clicking: {e}")
elif cmd == 'type':
    text = " ".join(sys.argv[2:])
    try:
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)
        pyautogui.press('enter')
        print(f"OK: Typed text using clipboard")
    except Exception as e:
        print(f"Error typing: {e}")
else:
    print("Unknown command")
