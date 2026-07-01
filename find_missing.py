import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

matches = re.findall(r'on(?:click|change)="([a-zA-Z][^"]+)"', c)
for m in set(matches):
    if not m.startswith('window.'):
        print(m)
