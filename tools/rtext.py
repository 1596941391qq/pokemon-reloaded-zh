#!/usr/bin/env python3
"""Pokémon Reloaded 文本文件（data/text/<lang>/*.dll，其实是加密纯文本）的解码与编码。

格式：
- 每行一条，CRLF 分隔，行号就是游戏里的编号（从 1 开始）。
- 可打印 ASCII（32..126）逐字节做替换加密；>=128 的字节原样保留。
- 西语重音字母写成 &{e} 这类转义，游戏读入后换成 cp1252 单字节。
- 文本内的控制符：# 换行，@ 翻页，$par1$ / $prota$ 等是变量占位。

中文：按 GBK 编码，再对 32..126 范围的字节（含 GBK 第二字节落在 0x40..0x7E 的情况）做同样的替换加密。
"""
import json, os, sys

# 来自游戏脚本 ValuesAdjustment6：密文字节 -> 明文字节
DEC = {52: 32, 84: 33, 110: 34, 126: 35, 32: 36, 44: 37, 57: 38, 39: 39, 112: 40, 96: 41, 50: 42, 98: 43, 74: 44,
       120: 45, 108: 46, 80: 47, 100: 48, 75: 49, 119: 50, 102: 51, 78: 52, 104: 53, 37: 54, 101: 55, 95: 56,
       81: 57, 45: 58, 97: 59, 99: 60, 60: 61, 53: 62, 35: 63, 113: 64, 64: 65, 118: 66, 76: 67, 47: 68, 62: 69,
       116: 70, 85: 71, 121: 72, 59: 73, 72: 74, 106: 75, 115: 76, 103: 77, 40: 78, 86: 79, 36: 80, 109: 81,
       82: 82, 43: 83, 58: 84, 107: 85, 93: 86, 68: 87, 91: 88, 69: 89, 56: 90, 88: 91, 111: 92, 46: 93, 41: 94,
       66: 95, 48: 96, 125: 97, 34: 98, 51: 99, 89: 100, 117: 101, 33: 102, 73: 103, 122: 104, 54: 105, 94: 106,
       70: 107, 61: 108, 105: 109, 49: 110, 87: 111, 55: 112, 123: 113, 77: 114, 71: 115, 65: 116, 92: 117,
       42: 118, 90: 119, 67: 120, 38: 121, 63: 122, 79: 123, 83: 124, 124: 125, 114: 126}
ENC = {v: k for k, v in DEC.items()}
assert len(DEC) == 95 and len(ENC) == 95

# 来自游戏脚本 SpecialChars：转义 -> cp1252 字节
ESC = [('&{aa}', 0xe0), ('&{AA}', 0xc0), ('&{ee}', 0xe8), ('&{EE}', 0xc8), ('&{e2}', 0xea), ('&{E2}', 0xca),
       ('&{uu}', 0xfc), ('&{UU}', 0xdc), ('&{E1}', 0x80), ('&{o1}', 0xba), ('&{a1}', 0xaa), ('&{c1}', 0x92),
       ('&{c2}', 0xb4), ('&{i1}', 0xac), ('&{u2}', 0xa8), ('&{ss}', 0xa7),
       ('&{n}', 0xf1), ('&{N}', 0xd1), ('&{a}', 0xe1), ('&{e}', 0xe9), ('&{i}', 0xed), ('&{o}', 0xf3),
       ('&{u}', 0xfa), ('&{A}', 0xc1), ('&{E}', 0xc9), ('&{I}', 0xcd), ('&{O}', 0xd3), ('&{U}', 0xda),
       ('&{C}', 0xc7), ('&{c}', 0xe7), ('&{?}', 0xbf), ('&{!}', 0xa1), ('&{.}', 0x85)]


def crypt(data: bytes, table) -> bytes:
    return bytes(table.get(x, x) for x in data)


def read_lines(path):
    raw = open(path, 'rb').read()
    lines = raw.split(b'\r\n')
    if lines and lines[-1] == b'':
        lines.pop()
    return lines


def decode_line(enc: bytes) -> str:
    """密文行 -> 可读 Unicode（转义换成真字符）。"""
    s = crypt(enc, DEC).decode('cp1252', errors='replace')
    for e, byte in ESC:
        s = s.replace(e, bytes([byte]).decode('cp1252'))
    return s


def decode_raw(enc: bytes) -> str:
    """密文行 -> 明文，保留 &{x} 转义（用于原样写回西语/英语）。"""
    return crypt(enc, DEC).decode('cp1252', errors='replace')


def encode_zh(text: str) -> bytes:
    """中文译文 -> 游戏密文行（GBK）。"""
    return crypt(text.encode('gbk'), ENC)


def write_lines(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\r\n'.join(lines) + b'\r\n')


def cmd_export(text_dir, out_dir):
    """把 en/es 全部 .dll 导成 JSON：[{id, en, es}]。"""
    os.makedirs(out_dir, exist_ok=True)
    for name in sorted(os.listdir(os.path.join(text_dir, 'en'))):
        if not name.endswith('.dll') or name.startswith('ordenName'):
            continue
        en = [decode_line(l) for l in read_lines(os.path.join(text_dir, 'en', name))]
        es_path = os.path.join(text_dir, 'es', name)
        es = [decode_line(l) for l in read_lines(es_path)] if os.path.exists(es_path) else []
        rows = []
        for i in range(max(len(en), len(es))):
            rows.append({'id': i + 1, 'en': en[i] if i < len(en) else '', 'es': es[i] if i < len(es) else ''})
        with open(os.path.join(out_dir, name[:-4] + '.json'), 'w', encoding='utf-8') as f:
            f.write('[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n]\n')
        print(f'{name}: {len(rows)}')


if __name__ == '__main__':
    if sys.argv[1] == 'export':
        cmd_export(sys.argv[2], sys.argv[3])
