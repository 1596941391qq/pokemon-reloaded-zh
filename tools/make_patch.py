#!/usr/bin/env python3
"""生成中文补丁：
  1. 读 translations/*.json（每条 {id, en, es, zh}），没译的回落英文，写出 data/text/zh/*.dll
  2. 收集用到的汉字，用像素字体生成 12px / 10px 图集
  3. 改游戏 exe：画字函数换成 zh_*，塞入图集和脚本，按原算法重新加密

用法: python3 -I tools/make_patch.py <原版游戏目录> <输出目录>
"""
import glob, json, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = getattr(sys, '_MEIPASS', None) or os.path.dirname(HERE)  # 打包成 exe 时数据在临时解包目录
sys.path.insert(0, HERE)
import rtext, zhfont, gm8_repack as gm  # noqa: E402

# 长文本文件：两个汉字之间插空格，让游戏原有的按空格断行逻辑能工作（空格在汉字之间不占宽度）
SPACED = {'txt_dialog', 'dex_info', 'txt_obj_desc', 'txt_attack_desc', 'txt_abilities_desc', 'txt_quests',
          'txt_cartel', 'txt_exam', 'txt_battle', 'txt_menu', 'txt_creditos', 'txt_obj_secret_base'}
LANG_LINE = 'zh 简体中文'

# 对原脚本的替换
CALL_SUBS = [
    (re.compile(rb'(?<![A-Za-z0-9_])draw_text\('), b'zh_draw_text('),
    (re.compile(rb'(?<![A-Za-z0-9_])draw_text_color\('), b'zh_draw_text_color('),
    (re.compile(rb'(?<![A-Za-z0-9_])string_width\('), b'zh_string_width('),
    (re.compile(rb'(?<![A-Za-z0-9_])draw_set_font\('), b'zh_set_font('),
    (re.compile(rb'(?<![A-Za-z0-9_])draw_set_halign\('), b'zh_set_halign('),
    (re.compile(rb'(?<![A-Za-z0-9_])draw_set_valign\('), b'zh_set_valign('),
]
FIXED_SUBS = [
    # 对话框每行最多 40 字节 → 120（汉字 2 字节 + 断行空格）
    (b'ctam<=40', b'ctam<=120'),
    (b'ctam2<=40', b'ctam2<=120'),
    # 图鉴按字母排序：中文用英文顺序
    (b'if(global.language="en")return ex(7760,argument0);', b'return ex(7760,argument0);'),
    # 招式记录前缀
    (b'dt="DT"; if(global.language="en")dt="TR";',
     'dt="DT"; if(global.language="en")dt="TR"; if(global.language="zh")dt="招式记录";'.encode('gbk')),
]

# 起名检查（NameValidator）：禁用字符改为只查汉字以外的部分；纯中文名不算「没有字母」
NAME_FIXES = [
    (b'var error, char;', b'var error, char, zh_s; zh_s=zh_name_strip(argument0);'),
    (b'if(ex(9765,string_letters(argument0))=0)error=11;',
     b'if(ex(9765,string_letters(zh_s))=0 && zh_s=argument0)error=11;'),
]
NAME_COUNT = re.compile(rb'string_count\(("[^"]*"|\'[^\']*\'),argument0\)')


def fix_name_validator(src):
    for a, b in NAME_FIXES:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    src, n = NAME_COUNT.subn(lambda m: b'string_count(' + m.group(1) + b',zh_s)', src)
    assert n >= 30, n
    return src


DBCS_RUN = re.compile(r'(?<=[⺀-鿿＀-￯　-〿—…“”‘’·])'
                      r'(?=[⺀-鿿＀-￯　-〿—…“”‘’·])')


# 断行禁则：标点不放行首（前面不插空格），开引号/开括号不留行尾（后面不插空格）
NO_BREAK_BEFORE = set('，。！？、；：）」』”’》〉】…—～·')
NO_BREAK_AFTER = set('（「『“‘《〈【')


def space_cjk(s):
    out = []
    for i, ch in enumerate(s):
        if i and DBCS_RUN.match(s, i) and ch not in NO_BREAK_BEFORE and s[i - 1] not in NO_BREAK_AFTER:
            out.append(' ')
        out.append(ch)
    return ''.join(out)


def load_translations():
    files = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'translations', '*.json'))):
        name = os.path.basename(path)[:-5]
        rows = json.load(open(path, encoding='utf-8'))
        files[name] = {r['id']: r for r in rows}
    return files


PAR_RE = re.compile(r'\$par\d\$')


def check_placeholders(translations):
    """译文的 $parN$ 必须和西语原文一致。游戏按西语排行号，英文版有几段自己错了位
    （比如 txt_dialog 10842/10843 英文对调了），照英文翻就会整句放错地方。"""
    bad = []
    for name, rows in translations.items():
        for i, r in rows.items():
            zh, es = r.get('zh'), r.get('es')
            if zh and es is not None and set(PAR_RE.findall(zh)) != set(PAR_RE.findall(es)):
                bad.append(f'{name}:{i}')
    if bad:
        raise AssertionError('译文和西语原文的 $parN$ 对不上（多半是错行）: ' + ', '.join(bad))


def zh_lines(game_text_dir, translations):
    """返回 {文件名: [密文行]} 和所有中文文本（用于收集字符）。"""
    out, texts = {}, []
    stats = {}
    for path in sorted(glob.glob(os.path.join(game_text_dir, 'en', '*.dll'))):
        name = os.path.basename(path)[:-4]
        en_lines = rtext.read_lines(path)
        tr = translations.get(name, {})
        by_en = {}  # 游戏更新后行号可能错位：按英文原文找回译文（只用唯一的）
        for r in tr.values():
            if r.get('zh') and r.get('en'):
                by_en.setdefault(r['en'], set()).add(r['zh'])
        lines, done = [], 0
        keep = KEEP_ORIGINAL.get(name, set())
        for i, enc in enumerate(en_lines, 1):
            if i in keep:
                lines.append(enc)
                continue
            row = tr.get(i)
            zh = row.get('zh', '') if row else ''
            cur = rtext.decode_line(enc)
            if row is None or (row.get('en') is not None and row['en'] != cur):
                cand = by_en.get(cur, set())
                zh = next(iter(cand)) if len(cand) == 1 else ''  # 原文变了且找不到，回落英文
            elif not zh and cur in by_en and len(by_en[cur]) == 1:
                zh = next(iter(by_en[cur]))  # 同一句原文在别处已经译过
            if zh:
                if name in SPACED:
                    zh = space_cjk(zh)
                texts.append(zh)
                try:
                    lines.append(rtext.encode_zh(zh))
                except UnicodeEncodeError as e:
                    print(f'  ! {name}:{i} GBK 编不了: {e}; 回落英文')
                    lines.append(enc)
                    continue
                done += 1
            else:
                lines.append(enc)  # 英文原密文
        out[name] = lines
        stats[name] = (done, len(en_lines))
    return out, texts, stats


# 游戏的反篡改自检（都在原版脚本里）：
#   1. sumando：每进一个房间，随机抽 5093 起的一段 150 个脚本（共 36 段，覆盖到 10493），
#      只要有脚本源码里换行超过 1 个（Jmp 除外），就把 1~99 号存档全写成空行（存档损坏）。
#   2. CheckEventosCalls / ExpGana：script_exists(1271*8)，即 10168 号脚本存在（原版最后一个是 10167）就给存档打标记。
# 所以新增脚本放进 5093 以下的空位（原版 0~5092 全空），并压成一行；脚本总数不变。
ZH_SLOT_BASE = 4000
TAMPER_NL_EXEMPT = {8163}  # Jmp，源码就是一个换行
# txt_cartel 445~451 是反作弊特征串（游戏拿它们去搜脚本源码），不是给玩家看的，保持原文
KEEP_ORIGINAL = {'txt_cartel': set(range(445, 452))}


def one_line(src):
    """GML 去掉 // 注释、压成一行（不能有换行，见上面的自检 1）。"""
    out = []
    for line in src.splitlines():
        if '//' in line:
            assert line.count('"', 0, line.index('//')) % 2 == 0, line  # 注释不在字符串里
            line = line[:line.index('//')]
        line = line.strip()
        if line:
            out.append(line)
    return ' '.join(out)


def check_anti_tamper(scripts, n_slots):
    assert len(scripts) == n_slots, '脚本总数变了（会触发 10168 号脚本检查）'
    for i, b in enumerate(scripts):
        sc = gm.parse_script(b)
        nl = sc[1].count(b'\n') if sc else 0
        if nl > 1 and i not in TAMPER_NL_EXEMPT:
            raise AssertionError(f'脚本 {i} {sc[0]!r} 有 {nl} 个换行，会触发存档清空自检')


class PatchError(Exception):
    """给玩家看的出错说明（不打印堆栈）。"""


def load_fonts():
    b12 = zhfont.BDF(os.path.join(ROOT, 'fonts', 'fusion-pixel-12px-proportional-zh_hans.bdf'))
    b10 = zhfont.BDF(os.path.join(ROOT, 'fonts', 'fusion-pixel-10px-proportional-zh_hans.bdf'))
    return b12, b10


def write_exe(path, data):
    """先写临时文件再替换，写完读回来核对。失败时原 exe 不动。"""
    name = os.path.basename(path)
    tmp = path + '.zh-new'
    try:
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)
    except OSError as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise PatchError(
            f'没能改写游戏程序 {name}（{e.strerror or e}）。\n'
            '常见原因：游戏还开着，或者被杀毒软件（360、火绒、Windows 安全中心等）拦了。\n'
            '请关掉游戏，在杀毒软件里允许本补丁（或把游戏文件夹加入信任），再运行一次补丁。\n'
            '这次没有改动游戏，游戏还是原样。')
    with open(path, 'rb') as f:
        ok = f.read() == data
    if not ok:
        raise PatchError(
            f'游戏程序 {name} 写进去以后又被改掉了，多半是杀毒软件拦截。\n'
            '请在杀毒软件里允许本补丁（或把游戏文件夹加入信任），再运行一次补丁。')


def patch_exe(exe_bytes, chars, fonts):
    t = time.time()
    g = gm.GM80(exe_bytes)
    print(f'  解密 {len(g.data)} 字节 ({time.time() - t:.1f}s)')
    secs = g.sections()
    d = g.data

    # 图集
    b12, b10 = fonts
    cols = 64
    w12, h12, px12, miss12 = zhfont.build_atlas(b12, chars, 12, 16, cols)
    w10, h10, px10, miss10 = zhfont.build_atlas(b10, chars, 10, 14, cols, fallback=(b12, 12, 16))
    if miss12 or miss10:
        print('  ! 字体缺字:', ''.join(sorted(set(miss12 + miss10))))
    print(f'  图集 {len(chars)} 字: 12px {w12}x{h12}, 10px {w10}x{h10}')
    backs = g.blob_list('backgrounds')
    backs.append(gm.background_blob(b'zh_atlas12', w12, h12, px12))
    backs.append(gm.background_blob(b'zh_atlas10', w10, h10, px10))

    # 脚本
    scripts = g.blob_list('scripts')
    n_changed = 0
    fixed_hits = {k: 0 for k, _ in FIXED_SUBS}
    names = set()
    fixed_name = False
    for i, blob in enumerate(scripts):
        sc = gm.parse_script(blob)
        if sc is None:
            continue
        name, src = sc
        names.add(name)
        new = src
        for pat, rep in CALL_SUBS:
            new = pat.sub(rep, new)
        if name == b'NameValidator':
            new = fix_name_validator(new)
            fixed_name = True
        for a, b in FIXED_SUBS:
            if a in new:
                fixed_hits[a] += new.count(a)
                new = new.replace(a, b)
        if new != src:
            scripts[i] = gm.script_blob(name, new)
            n_changed += 1
    assert fixed_name, '没找到 NameValidator'
    for a, n in fixed_hits.items():
        if n == 0:
            print('  ! 没找到要改的片段:', a.decode('latin-1'))
    charlist = ''.join(chars).encode('gbk')
    gml_dir = os.path.join(ROOT, 'patch', 'gml')
    added = []
    for path in sorted(glob.glob(os.path.join(gml_dir, '*.gml'))):
        nm = os.path.basename(path)[:-4]
        src = open(path, encoding='utf-8').read()
        src = src.replace('{{COLS12}}', str(cols)).replace('{{COLS10}}', str(cols))
        added.append((nm.encode(), one_line(src).encode('gbk')))
    added.append((b'zh_chars', b'return "' + charlist + b'";'))
    n_slots = len(scripts)
    for k, (nm, src) in enumerate(added):
        assert nm not in names, nm
        slot = ZH_SLOT_BASE + k
        assert gm.parse_script(scripts[slot]) is None, f'脚本空位 {slot} 被占了'
        scripts[slot] = gm.script_blob(nm, src)
    check_anti_tamper(scripts, n_slots)
    print(f'  改了 {n_changed} 个脚本，新增 {len(added)} 个脚本（放在空位 {ZH_SLOT_BASE} 起）、2 张图集')

    # 拼回去：backgrounds 在 scripts 前面，按偏移从后往前替换
    bs, be = secs['backgrounds']
    ss, se = secs['scripts']
    assert be < ss
    new_data = bytes(d[:bs]) + gm.pack_blobs(backs) + bytes(d[be:ss]) + gm.pack_blobs(scripts) + bytes(d[se:])
    t = time.time()
    out = g.build(new_data)
    print(f'  重新加密 ({time.time() - t:.1f}s)，exe {len(exe_bytes)} → {len(out)} 字节')
    return out


def build(game_dir, out_dir, exe_path=None):
    """game_dir: 原版游戏目录（读 data/text/en 和 lan.txt）；exe_path: 原版 exe（默认 game_dir 里唯一的 exe）。"""
    if exe_path is None:
        exe = [f for f in os.listdir(game_dir) if f.lower().endswith('.exe')]
        assert len(exe) == 1, exe
        exe_path = os.path.join(game_dir, exe[0])
    exe_name = os.path.basename(exe_path)
    text_dir = os.path.join(game_dir, 'data', 'text')
    translations = load_translations()
    check_placeholders(translations)
    lines, texts, stats = zh_lines(text_dir, translations)
    tot_done = sum(a for a, b in stats.values()); tot = sum(b for a, b in stats.values())
    print(f'文本: 已译 {tot_done}/{tot} 条')
    for k, (a, b) in sorted(stats.items()):
        if a:
            print(f'  {k}: {a}/{b}')
    fonts = load_fonts()
    extra = [LANG_LINE, '招式记录', '，。！？…—“”‘’：；（）·、《》～', zhfont.gb2312_text(fonts[0])]
    chars = zhfont.charset_from_texts(texts + extra)
    risky = zhfont.risky_chars(chars)
    if risky:
        print('  ! 第二字节在 ASCII 区的字（需确认）:', ''.join(risky))
    # 先改好 exe 再动文本：exe 写不进去（游戏开着、杀毒拦截）时什么都不改，
    # 免得落到「语言已经切成中文、exe 还是原版」——那样满屏汉字都显示不出来
    out = patch_exe(open(exe_path, 'rb').read(), chars, fonts)
    os.makedirs(out_dir, exist_ok=True)
    write_exe(os.path.join(out_dir, exe_name), out)
    # 写文本
    zh_dir = os.path.join(out_dir, 'data', 'text', 'zh')
    os.makedirs(zh_dir, exist_ok=True)
    for name, ls in lines.items():
        rtext.write_lines(os.path.join(zh_dir, name + '.dll'), ls)
    for extra_file in os.listdir(os.path.join(text_dir, 'en')):
        if not extra_file.endswith('.dll'):
            shutil.copy(os.path.join(text_dir, 'en', extra_file), os.path.join(zh_dir, extra_file))
    for f in ('ordenNameAbility.dll', 'ordenNameAttack.dll', 'ordenNamePokemon.dll'):
        if os.path.exists(os.path.join(text_dir, 'en', f)):
            shutil.copy(os.path.join(text_dir, 'en', f), os.path.join(zh_dir, f))
    flag = os.path.join(ROOT, 'patch', '_flag.png')
    if os.path.exists(flag):
        shutil.copy(flag, os.path.join(zh_dir, '_flag.png'))
    lan = open(os.path.join(text_dir, 'lan.txt'), 'rb').read().rstrip(b'\r\n').split(b'\r\n')
    lan = [l for l in lan if not l.startswith(b'zh ')] + [LANG_LINE.encode('gbk')]
    with open(os.path.join(out_dir, 'data', 'text', 'lan.txt'), 'wb') as f:
        f.write(b'\r\n'.join(lan))
    with open(os.path.join(out_dir, 'data', 'text', 'config.ini'), 'wb') as f:
        f.write((' %d' % (len(lan) - 1)).encode())  # 默认选中文
    print('输出:', out_dir)


def main():
    build(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
