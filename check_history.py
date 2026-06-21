import json
data = json.load(open('data/history_strategies.json', encoding='utf-8'))
print(f'Total: {len(data)} items')
for x in data:
    t = x.get('type','strategy')
    n = x.get('name','???')
    print(f'  [{t}] {n}')
