import urllib.request
import json
import time
import sys

# Đợi 10s cho Playwright khởi động xong
print("Đợi 15s để Playwright Worker khởi động...")
time.sleep(15)

url = "http://127.0.0.1:8001/execute"
data = {
  "task_type": "image_gen_upload",
  "payload": {
    "prompt": "Một chú mèo con cực kỳ dễ thương đang đeo kính râm, uống trà sữa tại một quán cafe ở Sai Gon",
    "ref_ids": [],
    "ratio": "916",
    "outputs": 1
  }
}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method='POST')
req.add_header('Content-Type', 'application/json')

print("Gửi lệnh TẠO HÌNH tới Worker...")
try:
    with urllib.request.urlopen(req) as response:
        print("Mã HTTP:", response.getcode())
        print("Kết quả:", response.read().decode('utf-8'))
except Exception as e:
    print("LỖI GỌI API:", e)
