# resize_cmd_window.py - Dat cua so CMD hien tai nho lai va day sang ben phai man hinh
# Goi tu trong CMD: python Tools/resize_cmd_window.py [slot 0-8]
# Slot 0-5=Worker_01..06, 6=Media9000, 7=Media9001, 8=Gateway (xep doc ben phai)
import sys
import ctypes

try:
    slot = int(sys.argv[1]) if len(sys.argv) > 1 else 0
except (ValueError, IndexError):
    slot = 0
slot = max(0, min(8, slot))

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

hwnd = kernel32.GetConsoleWindow()
if not hwnd:
    sys.exit(0)

screen_w = user32.GetSystemMetrics(0)
screen_h = user32.GetSystemMetrics(1)

# 9 cua so xep doc ben phai (Media, Custom Media, Worker 1-6, Gateway)
num_slots = 9
width = 380
height = (screen_h - 20) // num_slots
x = screen_w - width - 20
y = slot * height + 10

user32.MoveWindow(hwnd, x, y, width, height, True)
