import json, sys

with open('src/models/machine_learning_model_advanced_regression.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

keywords = ['read_csv', 'unified_dataset', 'fillna', 'dropna', 'price_offre', 'discount_pct', 'NaN']
for i, cell in enumerate(nb['cells']):
    ct = cell['cell_type']
    src = ''.join(cell['source'])
    if any(k in src for k in keywords):
        sys.stdout.buffer.write(f'--- Cell {i} ({ct}) ---\n'.encode('utf-8'))
        sys.stdout.buffer.write(src[:1000].encode('utf-8', errors='replace'))
        sys.stdout.buffer.write(b'\n\n')
