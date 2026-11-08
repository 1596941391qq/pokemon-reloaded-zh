#!/usr/bin/env python3
"""图鉴行号 → 宝可梦：把游戏里 GetOrdenDex / GetOrdenDexEspecial / NamePokemon / NumeroPokemonEspecial
这几个只有 if/return 的脚本翻成 Python 求值，反推 dex_espec / dex_info 每一行对应 txt_pkmn 的哪一行。
输出 work/dexmap.json: {行号: {species, pkmn, en, zh}}"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD = os.path.join(ROOT, 'work', 'gm8dump', 'scripts')
IX = dict(json.load(open(os.path.join(ROOT, 'work', 'gm8dump', 'script_index.json'))))


def load(name):
    return [s.strip() for s in open(os.path.join(SD, name + '.gml'), encoding='latin-1').read().split(';') if s.strip()]


def pyexpr(e):
    e = e.replace('&&', ' and ').replace('||', ' or ')
    e = re.sub(r'\btrue\b', 'True', re.sub(r'\bfalse\b', 'False', e))
    e = re.sub(r'(?<![<>!=])=(?!=)', '==', e)
    e = re.sub(r'global\.STR_POK\[(.*)\]', r'POK(\1)', e)
    e = re.sub(r'ex\((\d+),', lambda m: f'EX({m.group(1)},', e)
    return e


class Script:
    def __init__(self, name):
        self.prog = []
        for st in load(name):
            if st.startswith('var '):
                continue
            m = re.match(r'if\((.*?)\)return\((.*)\)$', st)
            if m and m.group(1).count('(') == m.group(1).count(')'):
                self.prog.append(('ifret', pyexpr(m.group(1)), pyexpr(m.group(2)))); continue
            m = re.match(r'if\((.*)\)argument0-=(\d+)$', st)
            if m:
                self.prog.append(('ifsub', pyexpr(m.group(1)), int(m.group(2)))); continue
            m = re.match(r'return\((.*)\)$', st)
            if m:
                self.prog.append(('ret', pyexpr(m.group(1)))); continue
            m = re.match(r'(argument0|\w+)=(.*)$', st)
            if m:
                self.prog.append(('set', m.group(1), pyexpr(m.group(2)))); continue
            raise ValueError(f'{name}: 看不懂 {st[:80]}')
        self.name = name

    def __call__(self, a):
        env = {'argument0': a, 'POK': lambda i: ('POK', i), 'EX': EX}
        for op in self.prog:
            if op[0] == 'ifret':
                if eval(op[1], {}, env):
                    return eval(op[2], {}, env)
            elif op[0] == 'ifsub':
                if eval(op[1], {}, env):
                    env['argument0'] -= op[2]
            elif op[0] == 'ret':
                return eval(op[1], {}, env)
            elif op[0] == 'set':
                env[op[1]] = eval(op[2], {}, env)
        return 0


S = {}


def EX(idx, a):
    if idx == 7521:  # EsShiny：图鉴里不考虑闪光
        return False
    nm = IX[idx]
    if nm not in S:
        S[nm] = Script(nm)
    return S[nm](a)


def main():
    orden, esp = Script('GetOrdenDex'), Script('GetOrdenDexEspecial')
    name = Script('NamePokemon')
    pat = re.compile(r'argument0=(\d+)\)')
    cands = set(range(1, 5000))
    for nm in ('GetOrdenDexEspecial', 'NamePokemon'):
        cands |= {int(x) for x in pat.findall(open(os.path.join(SD, nm + '.gml'), encoding='latin-1').read())}
    rows = {}
    for i in range(1, 494):
        rows[i] = i
    for nm, lim in (('GetOrdenDex', 945), ('GetOrdenDexEspecial', 99999)):
        src = open(os.path.join(SD, nm + '.gml'), encoding='latin-1').read()
        for sp, r in re.findall(r'if\(argument0=(\d+)\)return\(\(?(\d+)\)?\)', src):
            if int(r) <= lim:
                rows.setdefault(int(r), int(sp))
    for s in sorted(cands):
        r = orden(s)
        if not r or r < 0 or r > 945:
            r = esp(s)
        if r and r > 0 and r not in rows:
            rows[r] = s
    pk = {r['id']: r for r in json.load(open(os.path.join(ROOT, 'translations', 'txt_pkmn.json'), encoding='utf-8'))}
    out = {}
    for r, s in sorted(rows.items()):
        n = name(s)
        idx = n[1] if isinstance(n, tuple) else None
        p = pk.get(idx, {})
        out[r] = {'species': s, 'pkmn': idx, 'en': p.get('en'), 'zh': p.get('zh')}
    json.dump(out, open(os.path.join(ROOT, 'work', 'dexmap.json'), 'w'), ensure_ascii=False, indent=0)
    print(len(out), '行; 缺行:', [i for i in range(1, 1239) if i not in out][:30])


if __name__ == '__main__':
    main()
