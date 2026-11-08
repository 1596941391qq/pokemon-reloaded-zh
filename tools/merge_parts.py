#!/usr/bin/env python3
"""把 work/parts/<文件>[.X].json（[{id, zh}]）合并进 translations/<文件>.json。
默认只填 zh 为空的条目；--force 覆盖已有译文。合并前逐个跑 check_part 的同样校验。
用法: python3 -I tools/merge_parts.py [--force] [--dry] [part.json ...]（不给就合并 work/parts 下全部）"""
import glob, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
force, dry = '--force' in sys.argv, '--dry' in sys.argv
parts = args or sorted(p for p in glob.glob(os.path.join(ROOT, 'work', 'parts', '*.json'))
                       if not os.path.basename(p).startswith('_'))
for part in parts:
    base = os.path.basename(part)[:-5]
    name = base.split('.')[0]
    src_path = os.path.join(ROOT, 'work', 'src', name + '.json')
    if not os.path.exists(src_path):
        print(f'跳过 {base}: 没有源文件 {name}'); continue
    chk = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'check_part.py'), part, name],
                         capture_output=True, text=True)
    if chk.returncode:
        print(f'跳过 {base}: 校验没过\n' + chk.stdout[-1500:]); continue
    tr_path = os.path.join(ROOT, 'translations', name + '.json')
    if os.path.exists(tr_path):
        rows = json.load(open(tr_path, encoding='utf-8'))
    else:
        rows = [dict(r, zh='') for r in json.load(open(src_path, encoding='utf-8'))]
    by_id = {r['id']: r for r in rows}
    filled = kept = 0
    for p in json.load(open(part, encoding='utf-8')):
        zh = p.get('zh', '')
        r = by_id.get(p['id'])
        if not zh or r is None:
            continue
        if r.get('zh') and not force:
            kept += 1; continue
        r['zh'] = zh
        if p.get('note'):
            r['note'] = p['note']
        filled += 1
    done = sum(1 for r in rows if r.get('zh'))
    nonempty = sum(1 for r in rows if (r.get('en') or r.get('es')))
    print(f'{base} → {name}: 新填 {filled}，保留已有 {kept}；现在 {done}/{nonempty}')
    if not dry:
        with open(tr_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
