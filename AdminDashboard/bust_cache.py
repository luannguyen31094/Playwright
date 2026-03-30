import codecs
with codecs.open("index.html", "r", "utf-8") as f:
    text = f.read()
text = text.replace("src=\"js/tab_products.js?v=6.0\"", "src=\"js/tab_products.js?v=7.0\"")
with codecs.open("index.html", "w", "utf-8") as f:
    f.write(text)
print("Cache busted for tab_products.js to v7.0")
