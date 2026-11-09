#!/usr/bin/env python3
"""从 BDF 像素字体生成 GM8 背景图集（BGRA，白字透明底）和字符清单。"""
import math


class BDF:
    def __init__(self, path):
        self.glyphs = {}
        self.ascent = self.descent = 0
        cur = None
        bitmap = None
        for line in open(path, encoding='utf-8', errors='replace'):
            t = line.split()
            if not t:
                continue
            k = t[0]
            if k == 'FONT_ASCENT':
                self.ascent = int(t[1])
            elif k == 'FONT_DESCENT':
                self.descent = int(t[1])
            elif k == 'ENCODING':
                cur = {'cp': int(t[1])}
            elif k == 'DWIDTH' and cur is not None:
                cur['adv'] = int(t[1])
            elif k == 'BBX' and cur is not None:
                cur['bbx'] = tuple(int(x) for x in t[1:5])
            elif k == 'BITMAP' and cur is not None:
                bitmap = []
            elif k == 'ENDCHAR' and cur is not None:
                cur['rows'] = bitmap or []
                self.glyphs[cur['cp']] = cur
                cur = None
                bitmap = None
            elif bitmap is not None:
                bitmap.append(int(k, 16) if k else 0)
                cur.setdefault('rowbits', len(k) * 4)


def build_atlas(bdf: BDF, chars, cell_w, cell_h, cols=64, fallback=None):
    """chars: list of str (单字)。fallback=(BDF, cell_w, cell_h)：主字体缺字时从它最近邻缩放补字。
    返回 (width, height, bgra bytes, missing)。"""
    rows = max(1, math.ceil(len(chars) / cols))
    W, H = cols * cell_w, rows * cell_h
    px = bytearray(W * H * 4)
    missing = []
    for idx, ch in enumerate(chars):
        g = bdf.glyphs.get(ord(ch))
        if g is None:
            if fallback and ord(ch) in fallback[0].glyphs:
                _blit_scaled(px, W, (idx % cols) * cell_w, (idx // cols) * cell_h, cell_w, cell_h, fallback, ch)
            else:
                missing.append(ch)
            continue
        bw, bh, bx, by = g['bbx']
        nbits = g.get('rowbits', 8)
        ox = (idx % cols) * cell_w
        oy = (idx // cols) * cell_h
        top = bdf.ascent - (by + bh)  # 字形顶部相对单元格顶部
        adv = g.get('adv', cell_w)
        shift = max(0, (cell_w - adv) // 2)  # 窄字形居中
        for r, bits in enumerate(g['rows']):
            yy = top + r
            if not 0 <= yy < cell_h:
                continue
            for c in range(bw):
                if bits >> (nbits - 1 - c) & 1:
                    xx = bx + c + shift
                    if 0 <= xx < cell_w:
                        o = ((oy + yy) * W + ox + xx) * 4
                        px[o:o + 4] = b'\xff\xff\xff\xff'
    return W, H, bytes(px), missing


def _glyph_cell(bdf, ch, cw, chh):
    """把字形画进 cw x chh 的布尔网格。"""
    grid = [[0] * cw for _ in range(chh)]
    g = bdf.glyphs[ord(ch)]
    bw, bh, bx, by = g['bbx']
    nbits = g.get('rowbits', 8)
    top = bdf.ascent - (by + bh)
    for r, bits in enumerate(g['rows']):
        for c in range(bw):
            if bits >> (nbits - 1 - c) & 1 and 0 <= top + r < chh and 0 <= bx + c < cw:
                grid[top + r][bx + c] = 1
    return grid


def _blit_scaled(px, W, ox, oy, cell_w, cell_h, fallback, ch):
    fb, fw, fh = fallback
    src = _glyph_cell(fb, ch, fw, fh)
    for y in range(cell_h):
        for x in range(cell_w):
            if src[y * fh // cell_h][x * fw // cell_w]:
                o = ((oy + y) * W + ox + x) * 4
                px[o:o + 4] = b'\xff\xff\xff\xff'


def charset_from_texts(texts):
    """收集所有需要图集的字符（GBK 双字节字符），按 GBK 码排序。"""
    s = set()
    for t in texts:
        for ch in t:
            if ord(ch) < 0x80:
                continue
            try:
                b = ch.encode('gbk')
            except UnicodeEncodeError:
                continue
            if len(b) == 2:
                s.add(ch)
    return sorted(s, key=lambda c: c.encode('gbk'))


def gb2312_text(bdf: BDF):
    """GB2312 全部双字节字符里字体有字形的（6763 个汉字和全角符号）。
    玩家起名、给宝可梦起昵称会打出译文里没有的字，图集要备齐。
    只取两个字节都 >=0xA1 的区，不会和西文重音字母后面跟 ASCII 的组合撞码。"""
    out = []
    for hi in range(0xA1, 0xF8):
        for lo in range(0xA1, 0xFF):
            try:
                ch = bytes([hi, lo]).decode('gbk')  # 按游戏实际用的 GBK 解，比如 A1AA 是 —（U+2014）
            except UnicodeDecodeError:
                continue
            if ord(ch) in bdf.glyphs:
                out.append(ch)
    return ''.join(out)


def risky_chars(chars):
    """第二字节落在 ASCII 区的字（可能撞上 @ \\ 等控制符），需要人工确认。"""
    out = []
    for ch in chars:
        b = ch.encode('gbk')
        if b[1] < 0x80:
            out.append(ch)
    return out
