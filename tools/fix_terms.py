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
# 徽章：按原文英文名对照神奇宝贝百科「徽章」页的官方简中名（2026-11-08 核对）
BADGES = {
    'Zephyr': ('飞翼', '疾风'), 'Hive': ('昆虫', '虫之'), 'Plain': ('常规', '朴素 一般 普通'), 'Fog': ('幻影', '幽灵'),
    'Storm': ('打击', '风暴 冲击'), 'Glacier': ('冰雪', '冰川 冰柱 冰河'), 'Rising': ('升龙', '龙之 上升'),
    'Stone': ('岩石', '石头 原石'), 'Knuckle': ('拳击', '拳头'), 'Dynamo': ('电力', '发电 紫电'), 'Heat': ('烈焰', '热能 热力 热量'),
    'Balance': ('天秤', '平衡'), 'Feather': ('白羽', '羽毛'), 'Mind': ('心灵', '精神'), 'Rain': ('雨滴', '雨水'),
    'Cobble': ('铺石', '卵石 圆石 碎岩'), 'Fen': ('湿地', '沼泽'), 'Icicle': ('冰河', '冰柱 冰碴'),
    'Trio': ('三元', '三重'), 'Basic': ('基础', '基本'), 'Insect': ('甲虫', '昆虫'), 'Bolt': ('伏特', '电气 螺旋 电子'),
    'Quake': ('震动', '地震'), 'Jet': ('喷射', '喷气'), 'Freeze': ('冰柱', '冰冻 冻结'), 'Legend': ('传说', '传奇'),
    'Wave': ('海浪', '波浪'), 'Toxic': ('毒烟', '毒素'), 'Bug': ('虫虫', '虫'), 'Rumble': ('战斗', '喧闹'),
    'Psychic': ('超能', '超能力 精神'), 'Snowbelle': ('冰山', '冰雪'), 'Soul': ('粉红', '灵魂'), 'Marsh': ('金色', '金黄 沼泽'),
}
for k, (good, bad) in BADGES.items():
    for b in bad.split():
        RULES.append((r'\b%s Badge' % k, b + '徽章', good + '徽章'))
p = sys.argv[1]
rows = json.load(open(p, encoding='utf-8'))
n = 0
for r in rows:
    s = r if 'en' in r else src.get(r['id'], {'en': '', 'es': ''})
    z = r['zh']
    for cond, a, b in RULES:
        if a in z and (cond is None or re.search(cond, s['en'] + ' ' + s['es'])):
            pre = b[:len(b) - len(a)] if b.endswith(a) else ''  # 新名以旧名结尾（虫徽章→虫虫徽章）时别重复替换
            z = re.sub((('(?<!%s)' % re.escape(pre)) if pre else '') + re.escape(a), b, z)
    if z != r['zh']:
        r['zh'] = z; n += 1
if n: json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1 if rows and 'en' in rows[0] else 0)
print(os.path.basename(p), '统一译名', n, '条')
