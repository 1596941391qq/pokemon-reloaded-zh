#!/usr/bin/env python3
"""图鉴说明：作者原文常把几个版本的官方图鉴拼在一起。用西语原文去匹配各版本的官方西语图鉴，
找出用了哪几条，按原文顺序拼接对应版本的官方简中图鉴。匹配覆盖率够高才替换。"""
import csv, json, os, re, sys, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = ROOT + '/ref/pokeapi/'
FIX = str.maketrans({'負': '负', '纏': '缠', '轍': '辙', '・': '·'})


def words(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.findall(r'[a-z0-9]+', s)


def clean_zh(t):
    return t.replace('\xad\n', '').replace('\n', '').replace('\x0c', '').replace('　', '').replace(' ', '').translate(FIX)


sp_id = {}
for r in csv.DictReader(open(P + 'pokemon_species_names.csv', encoding='utf-8')):
    if r['local_language_id'] == '9':
        sp_id[''.join(words(r['name']))] = int(r['pokemon_species_id'])
es, zh = {}, {}
for r in csv.DictReader(open(P + 'pokemon_species_flavor_text.csv', encoding='utf-8')):
    k, v = int(r['species_id']), int(r['version_id'])
    if r['language_id'] == '7':
        es.setdefault(k, {})[v] = r['flavor_text'].replace('\n', ' ').replace('\x0c', ' ')
    elif r['language_id'] == '12':
        zh.setdefault(k, {})[v] = clean_zh(r['flavor_text'])
dm = {int(k): v for k, v in json.load(open(ROOT + '/work/dexmap.json', encoding='utf-8')).items()}
first = {}
for r in sorted(dm):
    first.setdefault(''.join(words(dm[r]['en'])), r)

path = ROOT + '/translations/dex_info.json'
rows = json.load(open(path, encoding='utf-8'))
n = 0
for row in rows:
    i = row['id']
    m = dm.get(i)
    if row.get('locked') or not m or not m['en'] or m['en'].startswith('Mega '):
        continue
    key = ''.join(words(m['en']))
    if first.get(key) != i:
        continue  # 地区形态等重复行
    sid = sp_id.get(key)
    if not sid or sid not in es:
        continue
    aw = words(row['es'])
    if len(aw) < 5:
        continue
    text = ' '.join(aw)
    picks = []
    for v, t in es[sid].items():
        tw = words(t)
        if len(tw) < 4 or v not in zh.get(sid, {}):
            continue
        # 这条官方图鉴的词有多少出现在原文里
        hit = sum(1 for w in tw if w in set(aw)) / len(tw)
        if hit >= 0.85:
            # 位置：官方句前三个词在原文中的位置
            pos = text.find(' '.join(tw[:3]))
            picks.append((pos if pos >= 0 else 10 ** 6, v, set(tw)))
    if not picks:
        continue
    picks.sort()
    chosen, covered = [], set()
    for pos, v, tw in picks:
        if len(tw - covered) >= max(3, len(tw) * 0.5):
            chosen.append(v); covered |= tw
    cov = sum(1 for w in aw if w in covered) / len(aw)
    if cov < 0.75:
        continue
    new = ''.join(zh[sid][v] for v in chosen)
    if new != row.get('zh'):
        row['zh'] = new
        row['note'] = '官方图鉴拼接（PokeAPI 版本 %s，覆盖 %d%%）' % (','.join(map(str, chosen)), cov * 100)
        n += 1
with open(path, 'w', encoding='utf-8') as f:
    f.write('[\n' + ',\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n]\n')
print('图鉴说明改为官方拼接:', n)
