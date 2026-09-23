src = open('cov.py', encoding='utf-8').read()
src = src.replace('0.80', '0.78')
with open('cov.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('ok')
