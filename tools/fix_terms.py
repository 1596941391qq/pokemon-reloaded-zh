#!/usr/bin/env python3
"""对 part 文件做统一的译名替换（子代理各自定的叫法 → 已定译名）。用法: python3 -I tools/fix_terms.py work/parts/x.json"""
import json, re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = {r['id']: r for r in json.load(open(os.path.join(ROOT, 'work', 'src', 'txt_dialog.json'), encoding='utf-8'))}
# (原文里要出现的词(英或西), 旧, 新)；原文条件为 None 表示无条件替换
RULES = [
    (r'Symbol|S[ií]mbolo', '符号', '纹章'), (r'Symbol|S[ií]mbolo', '印记', '纹章'),
    (None, '前线咖啡厅', '前线咖啡馆'), (None, '星辰对战开拓区', '星之开拓区'), (None, '星辰开拓区', '星之开拓区'),
    (r'€', '欧元', '元'), (None, '雷奇姆', '安魂'), (None, '水舰队', '海洋队'), (None, '天蝎大楼', '天蝎大厦'),
    (None, '活力微粒', '活力粒子'), (None, '开拓头脑', '王牌'), (None, '黄铁矿道馆', '黑金道馆'), (None, '黄铁矿市', '黑金市'), (None, '熔岩之浪', '熔岩浪潮'), (None, '大贤者长老', '大贤者'), (None, '优惠券', '折价券'), (None, '神秘剑士们', '圣剑士'), (None, '神秘剑士', '圣剑士'),
]
p = sys.argv[1]
rows = json.load(open(p, encoding='utf-8'))
n = 0
for r in rows:
    s = src.get(r['id'], {'en': '', 'es': ''})
    z = r['zh']
    for cond, a, b in RULES:
        if a in z and (cond is None or re.search(cond, s['en'] + ' ' + s['es'])):
            z = z.replace(a, b)
    if z != r['zh']:
        r['zh'] = z; n += 1
json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(os.path.basename(p), '统一译名', n, '条')
