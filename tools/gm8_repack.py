#!/usr/bin/env python3
"""GameMaker 8.0 exe 的解密 / 修改 / 重新加密（只做数据处理，不运行游戏）。
格式参照 OpenGMK gm8exe (https://github.com/OpenGMK/OpenGMK, GPL-2.0)。
"""
import struct, zlib


def _u32(b, p):
    return struct.unpack_from('<I', b, p)[0]


class GM80:
    def __init__(self, exe: bytes):
        self.exe = bytes(exe)
        b = self.exe
        p = _u32(b, 0x144AC0)
        while _u32(b, p) != 1234321:
            p += 10000
        assert _u32(b, p + 4) == 800, 'not GM8.0'
        p += 16
        p += 4 + _u32(b, p)  # settings
        p += 4 + _u32(b, p)  # dll name
        p += 4 + _u32(b, p)  # dll data
        g1 = _u32(b, p) * 4; g2 = _u32(b, p + 4) * 4
        p += 8 + g1
        self.swap = b[p:p + 256]
        p += 256 + g2
        self.len_off = p
        ln = _u32(b, p)
        self.pos = p + 4
        self.end = self.pos + ln
        self.tail = b[self.end:]
        rev = [0] * 256
        for i in range(256):
            rev[self.swap[i]] = i
        self.rev = rev
        self.data = self._decrypt(b[self.pos:self.end])

    # ---- crypto (positions relative to start of encrypted block) ----
    def _decrypt(self, enc: bytes) -> bytearray:
        d = bytearray(enc)
        n = len(d)
        rev, swap = self.rev, self.swap
        for k in range(n - 1, 0, -1):
            d[k] = (rev[d[k]] - ((d[k - 1] + k) & 0xFF)) & 0xFF
        for i in range(n - 1, -1, -1):
            j = max(i - swap[i & 0xFF], 0)
            d[i], d[j] = d[j], d[i]
        return d

    def _encrypt(self, plain: bytes) -> bytes:
        d = bytearray(plain)
        n = len(d)
        swap = self.swap
        for i in range(n):
            j = max(i - swap[i & 0xFF], 0)
            d[i], d[j] = d[j], d[i]
        for k in range(1, n):
            d[k] = swap[(d[k] + d[k - 1] + k) & 0xFF]
        return bytes(d)

    def build(self, data: bytes) -> bytes:
        enc = self._encrypt(data)
        return self.exe[:self.len_off] + struct.pack('<I', len(enc)) + enc + self.tail

    # ---- section walking over decrypted data ----
    def sections(self):
        """返回 {name: (start, end)}，start 指向资源列表的 count 字段。"""
        d = self.data
        p = 0
        p += 4 + _u32(d, p) * 4  # garbage
        p += 8 + 16  # pro flag, game id, guid
        assert _u32(d, p) == 700; p += 4
        n_ext = _u32(d, p); p += 4

        def pstr(p):
            return p + 4 + _u32(d, p)
        for _ in range(n_ext):
            p += 4; p = pstr(p); p = pstr(p)
            nf = _u32(d, p); p += 4
            for _ in range(nf):
                p += 4; p = pstr(p); p += 4; p = pstr(p); p = pstr(p)
                nfn = _u32(d, p); p += 4
                for _ in range(nfn):
                    p += 4; p = pstr(p); p = pstr(p); p += 4 * (3 + 17 + 1)
                nc = _u32(d, p); p += 4
                for _ in range(nc):
                    p += 4; p = pstr(p); p = pstr(p)
            p += 4 + _u32(d, p)  # contents length (含 seed) + contents
        secs = {}

        def blobs(p):
            n = _u32(d, p); q = p + 4
            for _ in range(n):
                q += 4 + _u32(d, q)
            return q
        assert _u32(d, p) == 800; p += 4
        secs['triggers'] = (p, blobs(p)); p = secs['triggers'][1]
        assert _u32(d, p) == 800; p += 4
        nc = _u32(d, p); q = p + 4
        for _ in range(nc):
            q = pstr(q); q = pstr(q)
        secs['constants'] = (p, q); p = q
        for name in ('sounds', 'sprites', 'backgrounds', 'paths', 'scripts', 'fonts', 'timelines', 'objects', 'rooms'):
            assert _u32(d, p) == 800, name
            p += 4
            secs[name] = (p, blobs(p)); p = secs[name][1]
        return secs

    def blob_list(self, sec):
        s, e = self.sections()[sec]
        d = self.data
        n = _u32(d, s); q = s + 4; out = []
        for _ in range(n):
            ln = _u32(d, q); out.append(bytes(d[q + 4:q + 4 + ln])); q += 4 + ln
        return out


def pack_blobs(blobs):
    return struct.pack('<I', len(blobs)) + b''.join(struct.pack('<I', len(x)) + x for x in blobs)


def pas(s: bytes) -> bytes:
    return struct.pack('<I', len(s)) + s


def script_blob(name: bytes, source: bytes) -> bytes:
    raw = struct.pack('<I', 1) + pas(name) + struct.pack('<I', 800) + pas(source)
    return zlib.compress(raw)


def parse_script(blob: bytes):
    raw = zlib.decompress(blob)
    if _u32(raw, 0) == 0:
        return None
    p = 4
    n = _u32(raw, p); name = raw[p + 4:p + 4 + n]; p += 4 + n
    p += 4
    n = _u32(raw, p); src = raw[p + 4:p + 4 + n]
    return name, src


def background_blob(name: bytes, w: int, h: int, bgra: bytes) -> bytes:
    assert len(bgra) == w * h * 4
    raw = (struct.pack('<I', 1) + pas(name) + struct.pack('<II', 710, 800) + struct.pack('<II', w, h)
           + struct.pack('<I', len(bgra)) + bgra)
    return zlib.compress(raw)


if __name__ == '__main__':
    import sys, time
    t = time.time()
    g = GM80(open(sys.argv[1], 'rb').read())
    print('decrypted', len(g.data), 'tail', len(g.tail), '%.1fs' % (time.time() - t))
    out = g.build(bytes(g.data))
    print('roundtrip identical:', out == g.exe)
    secs = g.sections()
    for k, v in secs.items():
        print(k, v, _u32(g.data, v[0]))
