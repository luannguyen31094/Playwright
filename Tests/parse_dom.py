from bs4 import BeautifulSoup
soup = BeautifulSoup(open(r'C:\tmp\flow_dom.html', encoding='utf-8'), 'html.parser')
for i, b in enumerate(soup.find_all('button')):
    text = b.get_text(strip=True)[:30]
    aria = b.get('aria-label')
    title = b.get('title')
    classes = b.get('class')
    print(f"[{i}] Aria: {aria} | Title: {title} | Text: {text} | Class: {classes}")
