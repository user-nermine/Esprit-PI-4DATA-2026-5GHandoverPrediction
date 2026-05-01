import re

files = [
    'src/models/dso2.py',
    'src/models/dso3.py',
    'src/models/dso4.py',
]

replacements = {
    '\u2192': '->',   # →
    '\u2014': '--',   # —
    '\u2500': '-',    # ─
    '\u00e9': 'e',    # é
}

for fp in files:
    with open(fp, encoding='utf-8') as f:
        content = f.read()
    for bad, good in replacements.items():
        content = content.replace(bad, good)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed: {fp}")

print("Done")

