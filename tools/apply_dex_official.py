#!/usr/bin/env python3
"""用 work/dexmap.json（图鉴行号→宝可梦）给 906 行以后补官方分类和官方图鉴文字。
分类：作者英文分类和官方英文分类一致才用官方。图鉴文字：只给第一次出现的原种（第九世代等），
超级进化、地区形态（和前面某行同名）不套，保留作者原文的翻译。"""
import csv, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
P = ROOT + '/ref/pokeapi/'
FIX = str.maketrans({'負': '负', '纏': '缠', '轍': '辙', '・': '·'})


def norm(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def clean(t):
    return t.replace('\xad\n', '').replace('\n', '').replace('\x0c', '').replace('　', '').replace(' ', '').translate(FIX)


sp_id, genus_en, genus_zh = {}, {}, {}
for r in csv.DictReader(open(P + 'pokemon_species_names.csv', encoding='utf-8')):
    i = int(r['pokemon_species_id'])
    if r['local_language_id'] == '9':
        sp_id[norm(r['name'])] = i
        genus_en[i] = r['genus'].replace(' Pokémon', '')
    if r['local_language_id'] == '12':
        genus_zh[i] = re.sub(r'宝可梦$', '', r['genus'].translate(FIX))
order = [34, 33, 41, 40, 39, 38, 37, 30, 29, 28, 27, 32, 31, 26, 25, 24, 23]
best = {}
for r in csv.DictReader(open(P + 'pokemon_species_flavor_text.csv', encoding='utf-8')):
    if r['language_id'] != '12':
        continue
    k, v = int(r['species_id']), int(r['version_id'])
    if v in order and (k not in best or order.index(v) < order.index(best[k][0])):
        best[k] = (v, clean(r['flavor_text']))

dm = {int(k): v for k, v in json.load(open(ROOT + '/work/dexmap.json', encoding='utf-8')).items()}
seen = set()
first_row = {}
for r in sorted(dm):
    first_row.setdefault(norm(dm[r]['en']), r)


def upd(fname, fn):
    path = f'{ROOT}/translations/{fname}.json'
    rows = json.load(open(path, encoding='utf-8'))
    n = 0
    for row in rows:
        if row.get('locked'):
            continue
        z = fn(row)
        if z and z[0] != row.get('zh'):
            row['zh'], n = z[0], n + 1
            row['note'] = z[1]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n]\n')
    print(fname, '改', n, '条')


genus_ok = set()


def g(row):
    i = row['id']
    m = dm.get(i)
    if i < 906 or not m or not m['en']:
        return None
    sid = sp_id.get(norm(re.sub(r'^Mega |\s[XYZ]$', '', m['en'])))
    if sid and norm(genus_en.get(sid)) == norm(row['en']) and genus_zh.get(sid):
        genus_ok.add(i)
        return genus_zh[sid], f'官方分类（PokeAPI，{m["zh"]}）'


def f(row):
    i = row['id']
    m = dm.get(i)
    if i not in genus_ok or m['en'].startswith('Mega ') or first_row.get(norm(m['en'])) != i:
        return None
    sid = sp_id.get(norm(m['en']))
    if sid in best:
        return best[sid][1], f'官方图鉴（PokeAPI，{m["zh"]}）'


upd('dex_espec', g)
upd('dex_info', f)
