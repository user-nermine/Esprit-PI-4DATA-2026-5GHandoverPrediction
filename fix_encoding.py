with open('src/models/dso1.py', encoding='utf-8') as f:
    content = f.read()

content = content.encode('cp1252', errors='replace').decode('cp1252')

with open('src/models/dso1.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")