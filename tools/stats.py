#!/usr/bin/env python3
"""统计翻译进度，写进 README.md 的 <!-- progress --> 区块；顺便导出人物译名表 glossary/人物.csv。"""
import csv, glob, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESC = {
    'txt_menu': '菜单与系统提示', 'txt_pkmn': '宝可梦名', 'txt_attack': '招式名', 'txt_attack_desc': '招式说明',
    'txt_abilities': '特性名', 'txt_abilities_desc': '特性说明', 'txt_obj': '道具名', 'txt_obj_desc': '道具说明',
    'txt_obj_secret_base': '秘密基地物品', 'dex_espec': '图鉴分类', 'dex_info': '图鉴说明', 'txt_places': '地名',
    'txt_map': '地图名', 'txt_character': '人物与称号', 'txt_battle': '对战文本', 'txt_adjective': '个性描述',
    'txt_medals': '徽章与成就', 'txt_creditos': '制作人员', 'txt_dialog': '剧情对话', 'txt_quests': '任务',
    'txt_cartel': '告示牌', 'txt_exam': '考试题', 'txt_keyboard': '输入键盘',
}
GL = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'glossary', 'glossary.csv'), encoding='utf-8-sig')):
    f = {'宝可梦': 'txt_pkmn', '招式': 'txt_attack', '特性': 'txt_abilities', '道具': 'txt_obj'}.get(r['类别'])
    if f and r['来源'] == '官方':
        GL.setdefault(f, set()).add(int(r['游戏内编号']))
rows = []
srcdir = os.path.join(ROOT, 'work', 'src')
for path in sorted(glob.glob(os.path.join(srcdir, '*.json'))):
    name = os.path.basename(path)[:-5]
    if name.startswith('snd_'):
        continue
    src = [r for r in json.load(open(path, encoding='utf-8')) if (r['en'] or r['es']).strip()]
    tp = os.path.join(ROOT, 'translations', name + '.json')
    tr = {r['id']: r for r in json.load(open(tp, encoding='utf-8'))} if os.path.exists(tp) else {}
    done = sum(1 for r in src if tr.get(r['id'], {}).get('zh'))
    off = sum(1 for r in src if '官方' in (tr.get(r['id'], {}).get('note') or '') or r['id'] in GL.get(name, ()))
    rows.append((name, DESC.get(name, name), done, len(src), off))
rows.sort(key=lambda x: (-x[2] / max(x[3], 1), x[0]))
lines = ['| 文件 | 内容 | 已译 | 总数 | 进度 | 其中直接用官方原文 |', '|---|---|---:|---:|---:|---:|']
T = D = 0
for name, desc, done, tot, off in rows:
    T += tot; D += done
    lines.append(f'| `{name}` | {desc} | {done} | {tot} | {done * 100 // max(tot, 1)}% | {off} |')
lines.append(f'| **合计** | | **{D}** | **{T}** | **{D * 100 // T}%** | |')
table = '\n'.join(lines)
rp = os.path.join(ROOT, 'README.md')
s = open(rp, encoding='utf-8').read()
s = re.sub(r'<!-- progress -->.*?<!-- /progress -->', '<!-- progress -->\n' + table + '\n<!-- /progress -->', s, flags=re.S)
open(rp, 'w', encoding='utf-8').write(s)
print(table)
ch = json.load(open(os.path.join(ROOT, 'translations', 'txt_character.json'), encoding='utf-8'))
with open(os.path.join(ROOT, 'glossary', '人物.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['游戏内编号', '英文栏', '西语栏', '简体中文', '来源'])
    for r in ch:
        if r['en'].strip():
            w.writerow([r['id'], r['en'], r['es'], r['zh'], '官方（52poke 核对）' if '官方' in (r.get('note') or '') else '自译/官方类型'])
