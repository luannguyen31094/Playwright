import os

filepath = r"C:\Users\Admin\DockerFL\n8n-selenium-bridge\AdminDashboard\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "<!-- Tailwind Modal for Product Details -->" in line:
        start_idx = i
    elif "<!-- TAB: CAMPAIGNS -->" in line and start_idx != -1:
        end_idx = i - 1
        while lines[end_idx].strip() == "":
            end_idx -= 1
        end_idx += 1
        break

if start_idx != -1 and end_idx != -1:
    modal_chunk = lines[start_idx:end_idx]
    new_lines = lines[:start_idx] + lines[end_idx:]
    target_idx = -1
    for i, line in enumerate(new_lines):
        if "<!-- DUAL-PERSONA GLOBAL MODALS -->" in line:
            target_idx = i
            break
            
    if target_idx != -1:
        final_lines = new_lines[:target_idx] + ["\n"] + modal_chunk + ["\n"] + new_lines[target_idx:]
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(final_lines)
        print("SUCCESS MODAL MOVED")
    else:
        print("Target not found")
else:
    print("Chunk not found")
