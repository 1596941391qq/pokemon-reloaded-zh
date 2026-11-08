#!/usr/bin/env python3
"""招式说明、特性说明、图鉴分类、图鉴文字：能对上官方的，直接用官方简中原文。"""
import csv, json, os, re, sys, unicodedata
ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
P = ROOT + '/ref/pokeapi/'
FIX = str.maketrans({'負': '负', '纏': '缠', '轍': '辙', '・': '·'})


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def clean(t):
    t = t.replace('­\n', '').replace('\n', '').replace('\x0c', '').replace('　', '').replace(' ', '')
    return t.translate(FIX)


def name_to_id(fname, idcol):
    m = {}
    for r in csv.DictReader(open(P + fname, encoding='utf-8')):
        if r['local_language_id'] in ('9', '7'):
            m.setdefault(norm(r['name']), r[idcol])
    return m


def flavor(fname, idcol, vcol, order):
    best = {}
    for r in csv.DictReader(open(P + fname, encoding='utf-8')):
        if r['language_id'] != '12':
            continue
        k, v = r[idcol], int(r[vcol])
        if k not in best or order.index(v) < order.index(best[k][0]):
            if v in order:
                best[k] = (v, clean(r['flavor_text']))
    return {k: v[1] for k, v in best.items()}


def save(fname, rows):
    path = f'{ROOT}/translations/{fname}.json'
    old = {r['id']: r for r in json.load(open(path, encoding='utf-8'))} if os.path.exists(path) else {}
    out = []
    for r in rows:
        prev = old.get(r['id'])
        if prev and prev.get('locked'):
            r = prev
        out.append(r)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(json.dumps(x, ensure_ascii=False) for x in out) + '\n]\n')
    print(fname, sum(1 for r in out if r.get('zh')), '/', len(out))


def src(fname):
    return [r for r in json.load(open(f'{ROOT}/work/src/{fname}.json', encoding='utf-8')) if r['en'] or r['es']]


# 招式 / 特性说明：和名称文件按行对齐
for desc_f, name_f, nfile, idcol, ffile in [
        ('txt_attack_desc', 'txt_attack', 'move_names.csv', 'move_id', 'move_flavor_text.csv'),
        ('txt_abilities_desc', 'txt_abilities', 'ability_names.csv', 'ability_id', 'ability_flavor_text.csv')]:
    ids = name_to_id(nfile, idcol)
    fl = flavor(ffile, idcol, 'version_group_id', [20, 19, 18, 17])
    names = {r['id']: r for r in src(name_f)}
    rows = []
    for r in src(desc_f):
        n = names.get(r['id'], {})
        mid = ids.get(norm(n.get('en', ''))) or ids.get(norm(n.get('es', '')))
        zh = fl.get(mid, '') if mid else ''
        row = {'id': r['id'], 'en': r['en'], 'es': r['es'], 'zh': zh}
        if zh:
            row['note'] = '官方说明（PokeAPI）'
        rows.append(row)
    save(desc_f, rows)

# 图鉴：按全国编号对齐，用分类英文名核对
genus_en, genus_zh = {}, {}
for r in csv.DictReader(open(P + 'pokemon_species_names.csv', encoding='utf-8')):
    if r['local_language_id'] == '9':
        genus_en[int(r['pokemon_species_id'])] = r['genus'].replace(' Pokémon', '')
    if r['local_language_id'] == '12':
        genus_zh[int(r['pokemon_species_id'])] = r['genus'].translate(FIX)
fl = flavor('pokemon_species_flavor_text.csv', 'species_id', 'version_id', [34, 33, 30, 29, 28, 27, 32, 31])
esp = src('dex_espec')
ok = set()
rows = []
for r in esp:
    i = r['id']
    zh = ''
    if i in genus_en and norm(genus_en[i]) == norm(r['en']) and genus_zh.get(i):
        zh = re.sub(r'宝可梦$', '', genus_zh[i])
        ok.add(i)
    row = {'id': i, 'en': r['en'], 'es': r['es'], 'zh': zh}
    if zh:
        row['note'] = '官方分类（PokeAPI）'
    rows.append(row)
save('dex_espec', rows)
rows = []
for r in src('dex_info'):
    i = r['id']
    zh = fl.get(str(i), '') if i in ok else ''
    row = {'id': i, 'en': r['en'], 'es': r['es'], 'zh': zh}
    if zh:
        row['note'] = '官方图鉴（PokeAPI）'
    rows.append(row)
save('dex_info', rows)
print('genus mismatch ids (前 40):', [r['id'] for r in esp if r['id'] not in ok][:40])
