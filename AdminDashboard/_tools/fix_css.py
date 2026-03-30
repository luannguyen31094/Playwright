with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Remove dangerous rules using simple string replacement or basic parsing
# To be safe, let's just write a clean custom CSS
safe_css = """
:root {
    --bg-main: #09090b;
    --bg-glass: rgba(15, 23, 42, 0.6);
    --bg-panel: rgba(255, 255, 255, 0.03);
    --border-glass: rgba(255, 255, 255, 0.08);
    --primary: #3b82f6;
    --primary-glow: rgba(59, 130, 246, 0.5);
    --accent: #8b5cf6;
    --text: #f8fafc;
    --text-muted: #94a3b8;
}

/* Grid Card Góc Quay */
.shots-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
.shot-card { background: var(--bg-panel); border: 1px solid var(--border-glass); border-radius: 16px; padding: 20px; padding-bottom: 5px; transition: 0.2s; display: flex; flex-direction: column;}
.shot-card:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.4); border-color: rgba(255,255,255,0.15); }
.shot-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--border-glass); padding-bottom: 10px; }
.s-id { background: rgba(139,92,246,0.2); color: #c084fc; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 12px; }
textarea.shot-area { width: 100%; height: 80px; background: transparent; border: none; color: inherit; resize: none; outline: none; font-family: inherit; font-size: 14px; line-height: 1.5; }
.btn-del { background: none; border: none; color: #ef4444; font-size: 18px; cursor: pointer; transition: 0.2s; }
.btn-del:hover { transform: scale(1.1); }

/* Buttons */
.btn-glow {
    background: linear-gradient(135deg, var(--accent) 0%, #d946ef 100%);
    color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4); transition: 0.2s; display: inline-flex; align-items: center; gap: 8px;
}
.btn-glow:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(139, 92, 246, 0.6); }

.btn-dashed {
    background: transparent; border: 2px dashed var(--border-glass); color: var(--text-muted);
    padding: 16px; border-radius: 12px; cursor: pointer; font-weight: bold; transition: 0.2s;
}
.btn-dashed:hover { background: rgba(255,255,255,0.03); border-color: var(--primary); color: white; }
"""

with open('style_custom.css', 'w', encoding='utf-8') as f:
    f.write(safe_css)

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('<link rel="stylesheet" href="assets/css/style.css" id="main-style-link" />', '<link rel="stylesheet" href="assets/css/style.css" id="main-style-link" />\n    <link rel="stylesheet" href="style_custom.css" />')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
