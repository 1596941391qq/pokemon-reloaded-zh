#!/usr/bin/env python3
"""术语一致性检查：原文（英文或西语）里出现的宝可梦/招式/特性/道具/地名，译文里应该出现对应的中文译名。
用法: python3 -I tools/term_check.py [文件名 ...] [--tsv 输出路径]"""
import csv, glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_FILES = {'dex_espec', 'txt_pkmn', 'txt_attack', 'txt_abilities', 'txt_obj', 'txt_places', 'txt_map'}
STOP = {'Normal', 'Return', 'Rest', 'Protect', 'Bind', 'Wrap', 'Swift', 'Growth', 'Charge', 'Present', 'Memento',
        'Switcheroo', 'Recycle', 'Pursuit', 'Retaliate', 'Round', 'Defog', 'Snatch', 'Spite', 'Trick', 'Block',
        'Detect', 'Endure', 'Encore', 'Taunt', 'Torment', 'Safeguard', 'Rage', 'Disable', 'Fling', 'Bounce', 'Flash',
        'Surf', 'Cut', 'Strength', 'Fly', 'Dive', 'Pound', 'Tackle', 'Scratch', 'Leer', 'Growl', 'Glare', 'Thief',
        'Covet', 'Pluck', 'Bug Bite', 'Teleport', 'Transform', 'Conversion', 'Splash', 'Celebrate', 'Hold Hands',
        'Confusion', 'Poison', 'Burn', 'Freeze', 'Sleep', 'Paralysis', 'Pressure', 'Levitate', 'Static', 'Guts',
        'Run Away', 'Pickup', 'Stench', 'Damp', 'Oblivious', 'Honey', 'Escape Rope', 'Revive', 'Potion', 'Bike',
        'Light Ball', 'Normalize', 'Klutz', 'Moody', 'Pastel Veil', 'Mold Breaker', 'Mirror', 'Star', 'Galar',
        'Moon', 'Sun', 'Hail', 'Snow', 'Rain', 'Sandstorm', 'Captivate', 'Sketch', 'Mimic', 'Struggle', 'Gravity',
        'Water', 'Fire', 'Ice', 'Grass', 'Rock', 'Ground', 'Electric', 'Dragon', 'Dark', 'Steel', 'Fairy', 'Ghost',
        'Bug', 'Flying', 'Psychic', 'Fighting', 'Dig', 'Explosion', 'Lock-On', 'Magnet', 'Bide', 'Metronome'}


def load_terms():
    terms = []
    for r in csv.DictReader(open(os.path.join(ROOT, 'glossary', 'glossary.csv'), encoding='utf-8-sig')):
        terms.append((r['类别'], r['英文'], r['西班牙文'], r['简体中文']))
    for line in open(os.path.join(ROOT, 'glossary', 'places.tsv'), encoding='utf-8'):
        t = line.rstrip('\n').split('\t')
        if len(t) >= 2 and t[0] and not t[0].startswith('#') and t[0] != 'en':
            terms.append(('地名', t[0], '', t[1]))
    seen, out = set(), []
    for cat, en, es, zh in terms:
        if not zh or len(en) < 4 or en in STOP or en in seen:
            continue
        seen.add(en)
        pat = re.compile(r'(?<![A-Za-z])' + re.escape(en) + r'(?![A-Za-z])')
        pes = re.compile(r'(?<![A-Za-zÀ-ÿ])' + re.escape(es) + r'(?![A-Za-zÀ-ÿ])') if es and len(es) >= 4 and es not in STOP else None
        out.append((cat, en, zh, pat, pes))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    tsv = sys.argv[sys.argv.index('--tsv') + 1] if '--tsv' in sys.argv else None
    if tsv in args:
        args.remove(tsv)
    terms = load_terms()
    files = args or [os.path.basename(p)[:-5] for p in sorted(glob.glob(os.path.join(ROOT, 'translations', '*.json')))]
    rows_out = []
    dm = json.load(open(os.path.join(ROOT, 'work', 'dexmap.json'), encoding='utf-8'))
    for name in files:
        if name in NAME_FILES:
            continue
        for r in json.load(open(os.path.join(ROOT, 'translations', name + '.json'), encoding='utf-8')):
            zh = r.get('zh') or ''
            if not zh:
                continue
            for cat, en, tzh, pat, pes in terms:
                hit = pat.search(r.get('en') or '') or (pes and pes.search(r.get('es') or ''))
                if hit and name == 'dex_info' and en == re.sub(r'^Mega | [XYZ]$', '', dm.get(str(r['id']), {}).get('en') or ''):
                    continue  # 图鉴里提到自己，官方中文常省略
                if hit and tzh not in zh:
                    rows_out.append((name, r['id'], cat, en, tzh, zh))
    by = {}
    for x in rows_out:
        by[x[0]] = by.get(x[0], 0) + 1
    print('疑似译名不一致:', len(rows_out), by)
    if tsv:
        with open(tsv, 'w', encoding='utf-8') as f:
            f.write('file\tid\tcat\ten\tglossary_zh\tzh\n')
            for x in rows_out:
                f.write('\t'.join(str(v) for v in x) + '\n')


if __name__ == '__main__':
    main()
