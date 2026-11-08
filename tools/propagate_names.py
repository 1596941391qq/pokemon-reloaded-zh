#!/usr/bin/env python3
"""人物译名改了以后，同步到其他文件：比较 work/parts/txt_character.json（原译）和 translations/txt_character.json（现译），
在原文提到这个人物（英文或西语名）的行里，把旧译名换成新译名。单字旧名不自动换，只列出来。
用法: python3 -I tools/propagate_names.py [--dry]"""
import glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dry = '--dry' in sys.argv
old = {r['id']: r['zh'] for r in json.load(open(os.path.join(ROOT, 'work', 'parts', 'merged', 'txt_character.json'), encoding='utf-8'))}
cur = json.load(open(os.path.join(ROOT, 'translations', 'txt_character.json'), encoding='utf-8'))
EXTRA = [  # (英文, 西语, 旧, 新) 非人物表里的
    ('Team Aqua', 'Team Aqua', '水舰队', '海洋队'),
]
NO_SYNC = {'Mars', 'Saturn', 'Jupiter'}  # 和行星岛名同词，不同步
changes = list(EXTRA)
for r in cur:
    o = old.get(r['id'])
    if o and r.get('zh') and o != r['zh'] and r['en'].strip() not in NO_SYNC:
        changes.append((r['en'].strip(), r['es'].strip(), o, r['zh']))
print('改名', len(changes))
for path in sorted(glob.glob(os.path.join(ROOT, 'translations', '*.json'))):
    name = os.path.basename(path)[:-5]
    if name == 'txt_character':
        continue
    rows = json.load(open(path, encoding='utf-8'))
    n = 0
    for row in rows:
        zh = row.get('zh') or ''
        if not zh:
            continue
        for en, es, o, new in changes:
            if o not in zh or new in zh:
                continue
            hit = any(x and re.search(r'(?<![A-Za-zÀ-ÿ])' + re.escape(x) + r'(?![A-Za-zÀ-ÿ])', row.get(k) or '')
                      for x, k in ((en, 'en'), (es, 'es'), (en, 'es'), (es, 'en')))
            if not hit:
                continue
            if len(o) < 2:
                print(f'  手动: {name}:{row["id"]} {o}→{new} | {zh[:50]}'); continue
            print(f'  {name}:{row["id"]} {o}→{new} | {zh[:60]}')
            zh = zh.replace(o, new); n += 1
        if zh != row.get('zh'):
            row['zh'] = zh
    print(f'{name}: 改 {n} 处')
    if n and not dry:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
