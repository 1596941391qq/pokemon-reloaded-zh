#!/usr/bin/env python3
"""只读解析 GameMaker 8.0 exe：导出扩展、脚本、字体信息。不运行任何程序。
格式参照 OpenGMK gm8exe (GPL-2.0)。用法: python3 -I gm80_dump.py <game.exe> <out_dir>
"""
import io, json, os, struct, sys, zlib

exe_path, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
b = bytearray(open(exe_path, 'rb').read())


class R:
    def __init__(self, buf, pos=0):
        self.b, self.p = buf, pos

    def u32(self):
        v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v

    def i32(self):
        v = struct.unpack_from('<i', self.b, self.p)[0]; self.p += 4; return v

    def bytes(self, n):
        v = bytes(self.b[self.p:self.p + n]); self.p += n; return v

    def pstr(self):
        n = self.u32(); return self.bytes(n).decode('latin-1')


r = R(b)
r.p = struct.unpack_from('<I', b, 0x144AC0)[0]
while r.u32() != 1234321:
    r.p += 10000 - 4
assert r.u32() == 800
r.p += 8
settings_len = r.u32(); r.p += settings_len
r.pstr()  # dll name
n = r.u32(); r.p += n  # dll data

# --- GM8.0 decrypt (in place) ---
g1 = r.u32() * 4; g2 = r.u32() * 4
r.p += g1
swap = r.bytes(256)
r.p += g2
rev = [0] * 256
for i in range(256): rev[swap[i]] = i
ln = r.u32(); pos = r.p
d = b
for i in range(pos + ln, pos + 1, -1):
    d[i - 1] = (rev[d[i - 1]] - ((d[i - 2] + (i - (pos + 1))) & 0xFF)) & 0xFF
for i in range(pos + ln - 1, pos - 1, -1):
    j = max(i - swap[(i - pos) & 0xFF], pos)
    d[i], d[j] = d[j], d[i]

n = r.u32(); r.p += n * 4  # garbage
pro, game_id = r.u32(), r.u32()
r.p += 16

# --- extensions ---
assert r.u32() == 700
exts = []
for _ in range(r.u32()):
    r.p += 4
    name, folder = r.pstr(), r.pstr()
    files = []
    for _ in range(r.u32()):
        r.p += 4
        fname = r.pstr(); kind = r.u32(); init = r.pstr(); fin = r.pstr()
        funcs = []
        for _ in range(r.u32()):
            r.p += 4
            fn = r.pstr(); ext_name = r.pstr(); conv = r.u32(); fid = r.u32(); argc = r.i32()
            argt = [r.u32() for _ in range(17)]; ret = r.u32()
            funcs.append({'name': fn, 'external': ext_name, 'argc': argc, 'args': argt[:max(argc, 0)], 'ret': ret})
        consts = []
        for _ in range(r.u32()):
            r.p += 4
            consts.append((r.pstr(), r.pstr()))
        files.append({'name': fname, 'kind': kind, 'init': init, 'final': fin, 'functions': funcs, 'consts': consts})
    clen = r.u32() - 4; r.u32(); r.p += clen
    exts.append({'name': name, 'folder': folder, 'files': files})
json.dump(exts, open(os.path.join(out, 'extensions.json'), 'w'), ensure_ascii=False, indent=1)


def refs():
    out_ = []
    for _ in range(r.u32()):
        n = r.u32(); out_.append(bytes(b[r.p:r.p + n])); r.p += n
    return out_


def assets():
    res = []
    for blob in refs():
        data = zlib.decompress(blob)
        if struct.unpack_from('<I', data, 0)[0] == 0:
            res.append(None)
        else:
            res.append(R(bytearray(data), 4))
    return res


assert r.u32() == 800; refs()  # triggers
assert r.u32() == 800
consts = [(r.pstr(), r.pstr()) for _ in range(r.u32())]
json.dump(consts, open(os.path.join(out, 'constants.json'), 'w'), ensure_ascii=False, indent=0)
for sec in ('sounds', 'sprites', 'backgrounds', 'paths'):
    assert r.u32() == 800, sec
    refs()

assert r.u32() == 800
sdir = os.path.join(out, 'scripts'); os.makedirs(sdir, exist_ok=True)
names = []
for i, a in enumerate(assets()):
    if a is None: continue
    name = a.pstr(); a.u32(); src = a.pstr()
    names.append((i, name))
    open(os.path.join(sdir, f'{name}.gml'), 'w', encoding='latin-1', newline='').write(src)

json.dump(names, open(os.path.join(out, 'script_index.json'), 'w'), ensure_ascii=False)
assert r.u32() == 800
fonts = []
for i, a in enumerate(assets()):
    if a is None: continue
    name = a.pstr(); a.u32(); sysn = a.pstr(); size = a.u32(); bold = a.u32(); ital = a.u32()
    rs = a.u32(); re_ = a.u32()
    fonts.append({'index': i, 'name': name, 'sys_name': sysn, 'size': size, 'bold': bold, 'italic': ital,
                  'range': [rs & 0xFFFF, re_], 'charset_bits': rs >> 16})
json.dump(fonts, open(os.path.join(out, 'fonts.json'), 'w'), ensure_ascii=False, indent=1)
print('extensions', len(exts), [e['name'] for e in exts])
print('scripts', len(names))
print('fonts', len(fonts))
for f in fonts: print('  ', f)


def action(a):
    a.u32(); lib = a.u32(); aid = a.u32(); kind = a.u32(); a.u32(); a.u32(); a.u32(); a.u32()
    fn = a.pstr(); fcode = a.pstr(); pc = a.u32(); a.u32()
    pt = [a.u32() for _ in range(8)]
    applies = a.i32(); rel = a.u32(); a.u32()
    ps = [a.pstr() for _ in range(8)]
    a.u32()
    return {'lib': lib, 'id': aid, 'kind': kind, 'fn': fn, 'params': ps[:pc]}


def code_of(acts):
    out_ = []
    for x in acts:
        if x['kind'] == 7 and x['params']:  # execute code
            out_.append(x['params'][0])
        elif x['params']:
            out_.append('/* action %d.%d %s */ ' % (x['lib'], x['id'], x['fn']) + ' | '.join(x['params']))
    return '\n'.join(out_)


assert r.u32() == 800
tdir = os.path.join(out, 'timelines'); os.makedirs(tdir, exist_ok=True)
for i, a in enumerate(assets()):
    if a is None: continue
    name = a.pstr(); a.u32()
    parts = []
    for _ in range(a.u32()):
        m = a.u32(); a.u32()
        acts = [action(a) for _ in range(a.u32())]
        parts.append('// moment %d\n%s' % (m, code_of(acts)))
    open(os.path.join(tdir, f'{name}.gml'), 'w', encoding='latin-1', newline='').write('\n'.join(parts))

assert r.u32() == 800
odir = os.path.join(out, 'objects'); os.makedirs(odir, exist_ok=True)
nobj = 0
for i, a in enumerate(assets()):
    if a is None: continue
    name = a.pstr(); a.u32()
    spr, solid, vis, depth, pers, parent, mask = a.i32(), a.u32(), a.u32(), a.i32(), a.u32(), a.i32(), a.i32()
    n_ev = a.u32()
    parts = ['// object %d %s parent=%d' % (i, name, parent)]
    for etype in range(n_ev + 1):
        while True:
            sub = a.i32()
            if sub < 0: break
            a.u32()
            acts = [action(a) for _ in range(a.u32())]
            parts.append('// event %d/%d\n%s' % (etype, sub, code_of(acts)))
    open(os.path.join(odir, f'{name}.gml'), 'w', encoding='latin-1', newline='').write('\n'.join(parts))
    nobj += 1
print('objects', nobj)
