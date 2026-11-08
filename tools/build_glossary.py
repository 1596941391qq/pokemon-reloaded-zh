#!/usr/bin/env python3
"""生成专有名词译名：人工表 glossary/manual.tsv > PokeAPI 官方简中 > 规则（超级进化/超极巨化/学习器）。
输出 translations/<文件>.json 里的 zh，以及 glossary/glossary.csv（可查的对照表）。"""
import csv, json, os, re, sys, unicodedata
ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
P = ROOT + '/ref/pokeapi/'
FIX = str.maketrans({'負': '负', '纏': '缠', '轍': '辙', '・': '·'})  # PokeAPI 简中数据里混入的繁体/日文中点


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def api_index(fname, idcol, extra_tsv=None):
    by = {}
    for r in csv.DictReader(open(P + fname, encoding='utf-8')):
        by.setdefault(r[idcol], {})[r['local_language_id']] = r['name']
    idx = {}
    for v in by.values():
        if '12' in v:
            for lang in ('9', '7'):
                if lang in v:
                    idx.setdefault(norm(v[lang]), v['12'].translate(FIX))
    if extra_tsv:
        for r in csv.DictReader(open(ROOT + '/ref/52poke/' + extra_tsv, encoding='utf-8'), delimiter='\t'):
            idx.setdefault(norm(r['en']), r['zh'])
    return idx


API = {
    'pkmn': api_index('pokemon_species_names.csv', 'pokemon_species_id'),
    'attack': api_index('move_names.csv', 'move_id', 'moves_920plus.tsv'),
    'abilities': api_index('ability_names.csv', 'ability_id', 'abilities_268plus.tsv'),
    'obj': api_index('item_names.csv', 'item_id'),
}
MANUAL = {}
for r in csv.DictReader(open(ROOT + '/glossary/manual.tsv', encoding='utf-8'), delimiter='\t'):
    MANUAL[(r['kind'], norm(r['en']))] = (r['zh'], r['note'])


def lookup(kind, en, es=''):
    m = MANUAL.get((kind, norm(en)))
    if m:
        return m[0], m[1]
    zh = API[kind].get(norm(en)) or (API[kind].get(norm(es)) if es else None)
    if zh:
        return zh, '官方'
    if kind == 'pkmn':
        mm = re.match(r'^Mega (.+?)(?: ([XYZA]))?$', en)
        if mm:
            base = lookup('pkmn', mm.group(1))
            if base[0]:
                return '超级' + base[0] + (mm.group(2) or ''), '规则：超级××'
        mm = re.match(r'^(.+) Gigamax$', en)
        if mm:
            base = lookup('pkmn', mm.group(1))
            if base[0]:
                return '超极巨化' + base[0], '规则：超极巨化××'
    if kind == 'obj':
        mm = re.match(r'^(TM|HM)(\d+) (.+)$', en)
        if mm:
            mv = lookup('attack', mm.group(3))
            if mv[0]:
                pre = '招式学习器' if mm.group(1) == 'TM' else '秘传学习器'
                return f'{pre}{int(mm.group(2)):02d} {mv[0]}', '规则：学习器+招式名'
    return '', ''


FILES = [('txt_pkmn', 'pkmn'), ('txt_attack', 'attack'), ('txt_abilities', 'abilities'), ('txt_obj', 'obj')]
KIND_ZH = {'pkmn': '宝可梦', 'attack': '招式', 'abilities': '特性', 'obj': '道具'}
gloss = []
for fname, kind in FILES:
    src = json.load(open(f'{ROOT}/work/src/{fname}.json', encoding='utf-8'))
    tpath = f'{ROOT}/translations/{fname}.json'
    old = {r['id']: r for r in json.load(open(tpath, encoding='utf-8'))} if os.path.exists(tpath) else {}
    rows, miss = [], []
    for r in src:
        if not (r['en'] or r['es']):
            continue
        zh, note = lookup(kind, r['en'], r['es'])
        prev = old.get(r['id'], {})
        if prev.get('locked'):  # 人工改过并锁定的，不覆盖
            zh, note = prev['zh'], prev.get('note', '人工')
        row = {'id': r['id'], 'en': r['en'], 'es': r['es'], 'zh': zh}
        if note and note != '官方':
            row['note'] = note
        rows.append(row)
        if not zh:
            miss.append(f"{r['id']}:{r['en']}")
        gloss.append([KIND_ZH[kind], r['id'], r['en'], r['es'], zh, note or ''])
    with open(tpath, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n]\n')
    print(fname, '已配', len(rows) - len(miss), '/', len(rows), '缺:', ' | '.join(miss[:40]))
with open(f'{ROOT}/glossary/glossary.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['类别', '游戏内编号', '英文', '西班牙文', '简体中文', '来源'])
    seen = set()
    for g in gloss:
        key = (g[0], g[2])
        if key in seen:
            continue
        seen.add(key)
        w.writerow(g)
print('glossary rows', len(seen))
