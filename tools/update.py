#!/usr/bin/env python3
"""游戏出新版本 → 新版中文补丁 的流水线。完整步骤和人工把关点见 README「更新流程」。

  python3 -I tools/update.py check [--feed 文件]       查作者博客。有新版本时退出码 10，打印文件名、来源、大小（不下载）
  python3 -I tools/update.py fetch <版本> [--from 压缩包] hacking 同意后才运行：下载到空目录，只解出 exe 和 data/text，不运行任何 exe
  python3 -I tools/update.py diff <版本>               导出新版文本，和旧版逐行对比，写「待翻行.md」和翻译子代理的任务
  python3 -I tools/update.py merge <版本> [--force]     旧译文迁到新版行号，合并子代理译文，跑校验
  python3 -I tools/update.py build <版本>              用新版试打补丁（只读写文件，不运行游戏），确认 exe 还改得动
  python3 -I tools/update.py release <版本> [--no-push] 补 KNOWN、改 README、刷新进度表、提交并推送
  python3 -I tools/update.py status [版本]
  python3 -I tools/update.py decline <版本>            hacking 说这个版本不跟：以后 check 不再提醒

工作目录 work/update/<版本>/：download/（压缩包）、game/（解出的 exe + data/text）、src/（导出的文本）、
align.json（新旧行对应）、待翻行.md、todo/（翻译任务）、prompts/（子代理提示词）、parts/（子代理交回的译文）、out/（试打的补丁）。
"""
import contextlib, datetime, difflib, glob, hashlib, io, json, os, re, shutil, subprocess, sys, zipfile
import urllib.parse, urllib.request, base64, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rtext, update_check  # noqa: E402

UPD = os.path.join(ROOT, 'work', 'update')
STATE = os.path.join(UPD, 'state.json')
UA = {'User-Agent': 'Mozilla/5.0'}
CHUNK = 120        # 每个任务文件最多几行
BATCH = 300        # 每个子代理最多几行
SIMILAR = 0.6      # 改动块里新旧两行相似度达到这个值，算「改动」而不是「新增」
SKIP_FILES = ('snd_',)  # 音乐名、作者名，不翻


# ---------- 小工具 ----------

def die(msg, code=1):
    print('✗ ' + msg)
    sys.exit(code)


def p(*parts):
    """相对仓库根目录的路径；绝对路径原样返回。"""
    return os.path.join(ROOT, *parts) if not os.path.isabs(parts[0]) else os.path.join(*parts)


def vdir(ver):
    if not re.fullmatch(r'\d+(\.\d+)+', ver):
        die(f'版本号不对: {ver}')
    return os.path.join(UPD, ver)


def jload(path, default=None):
    if default is not None and not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def jsave(path, obj, indent=1):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, path)


def state():
    st = jload(STATE, {})
    if not st:
        cur = max(update_check.known(), key=update_check.key)
        st = {'current': cur, 'game_dir': 'game', 'src_dir': 'work/src'}
    return st


def info_path(ver):
    return os.path.join(vdir(ver), 'info.json')


def load_info(ver):
    return jload(info_path(ver), {'version': ver})


def save_info(ver, info):
    jsave(info_path(ver), info)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def human(n):
    return f'{n / 1048576:.1f} MB（{n:,} 字节）' if n else '未知'


def game_exe(gdir):
    exes = [f for f in os.listdir(gdir) if f.lower().endswith('.exe')]
    if len(exes) != 1:
        die(f'{gdir} 根目录应该只有一个 exe，现在是 {exes}')
    return os.path.join(gdir, exes[0])


def is_empty_row(r):
    return not (r.get('en') or '').strip() and not (r.get('es') or '').strip()


# ---------- check：查博客 ----------

def b64d(s):
    s = s.replace('-', '+').replace('_', '/').replace(',', '')
    return base64.b64decode(s + '=' * (-len(s) % 4))


def mega_keys(url):
    m = re.search(r'mega\.nz/(?:file/|#!)([\w-]+)[#!]([\w-]+)', url)
    if not m:
        raise ValueError('不是 MEGA 文件链接')
    handle, keystr = m.groups()
    k = struct.unpack('>8I', b64d(keystr))
    key = struct.pack('>4I', k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7])
    iv = struct.pack('>4I', k[4], k[5], 0, 0)
    return handle, key, iv


def mega_api(req):
    r = urllib.request.Request('https://g.api.mega.co.nz/cs?id=1', data=json.dumps([req]).encode(),
                               headers=dict(UA, **{'Content-Type': 'application/json'}))
    res = json.loads(urllib.request.urlopen(r, timeout=30).read())
    res = res[0] if isinstance(res, list) else res
    if isinstance(res, int):
        raise RuntimeError(f'MEGA 接口返回错误码 {res}')
    return res


def openssl(args, data=None):
    return subprocess.run(['openssl', 'enc'] + args, input=data, capture_output=True, check=True).stdout


def mega_info(url, want_dl=False):
    """只查文件名和大小（want_dl=True 时顺带拿下载地址），不下载文件。"""
    handle, key, iv = mega_keys(url)
    req = {'a': 'g', 'p': handle}
    if want_dl:
        req['g'] = 1
    r = mega_api(req)
    name = None
    try:
        attr = openssl(['-d', '-aes-128-cbc', '-nopad', '-K', key.hex(), '-iv', '0' * 32], b64d(r['at']))
        name = json.loads(attr.rstrip(b'\0').decode('utf-8')[4:])['n']
    except Exception as e:  # 文件名解不出来不影响下载
        print('  （MEGA 文件名解不出来:', e, '）')
    return {'name': name, 'size': r.get('s'), 'dl': r.get('g'), 'key': key, 'iv': iv}


def http_info(url):
    name = urllib.parse.unquote(url.rstrip('/').rsplit('/', 1)[-1])
    size = None
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA, method='HEAD'), timeout=15)
        if 'html' in (r.headers.get('Content-Type') or ''):
            print(f'  （{urllib.parse.urlsplit(url).netloc} 返回的是网页不是文件，大小未知，可能要在浏览器里点）')
        else:
            size = int(r.headers.get('Content-Length') or 0) or None
    except Exception as e:
        print(f'  （{urllib.parse.urlsplit(url).netloc} 查不到大小: {e}）')
    return {'name': name, 'size': size}


def find_links(html):
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        url = m.group(1).replace('&amp;', '&')
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        low = urllib.parse.unquote(url).lower()
        if 'librer' in low or 'librer' in text.lower():
            continue  # 「Librerías Reloaded」是运行库，不需要
        if 'mega.nz/' in url:
            out.append({'source': 'MEGA', 'url': url})
        elif 'gofile.io/' in url:
            out.append({'source': 'gofile', 'url': url})
    return out


def cmd_check(feed=None):
    if feed:
        data = jload(feed)
    else:
        data = json.loads(urllib.request.urlopen(urllib.request.Request(update_check.FEED, headers=UA),
                                                 timeout=30).read())
    seen = {}
    for e in data['feed'].get('entry', []):
        content = e.get('content', {}).get('$t', '')
        for v in update_check.VER.findall(e['title']['$t'] + ' ' + content[:20000]):
            seen.setdefault(v, e)
    if not seen:
        die('没在博客最近的文章里找到版本号（博客格式可能变了，请人工看一眼）')
    latest = max(seen, key=update_check.key)
    known = update_check.known()
    print('博客最新版本:', latest, '| 补丁已支持:', ', '.join(sorted(known, key=update_check.key)))
    if not all(update_check.key(latest) > update_check.key(x) for x in known):
        print('→ 没有新版本')
        return 0
    info = load_info(latest)
    status = info.get('status')
    if status == 'declined':
        print(f'→ {latest} hacking 已说不跟，不再提醒')
        return 0
    if status in ('fetched', 'diffed', 'merged', 'built'):
        print(f'→ {latest} 正在更新中，进行到: {status}。下一步见 python3 -I tools/update.py status {latest}')
        return 11
    e = seen[latest]
    links = find_links(e.get('content', {}).get('$t', ''))
    for lk in links:
        try:
            lk.update({k: v for k, v in (mega_info(lk['url']) if lk['source'] == 'MEGA' else http_info(lk['url'])).items()
                       if k in ('name', 'size')})
        except Exception as ex:
            lk['error'] = str(ex)
    post_url = next((l['href'] for l in e.get('link', []) if l.get('rel') == 'alternate'), '')
    info.update({'version': latest, 'status': 'reported', 'checked_at': datetime.datetime.now().isoformat(timespec='seconds'),
                 'post': {'date': e['published']['$t'][:10], 'title': e['title']['$t'], 'url': post_url}, 'links': links})
    save_info(latest, info)
    print(f'\n发现新版本 The Last Beta {latest}（博客 {info["post"]["date"]}《{info["post"]["title"]}》 {post_url}）')
    if not links:
        print('  文章里没找到 MEGA / gofile 下载链接，需要人工看一眼')
    for i, lk in enumerate(links):
        print(f'  {"下载" if i == 0 else "备用"}: {lk.get("name") or "（文件名未知）"}')
        print(f'        来源 {lk["source"]}  {lk["url"]}')
        print(f'        大小 {human(lk.get("size"))}' + (f'  ！{lk["error"]}' if lk.get('error') else ''))
    print(f'\n等 hacking 同意后再下载: python3 -I tools/update.py fetch {latest}')
    return 10


def cmd_decline(ver):
    info = load_info(ver)
    info['status'] = 'declined'
    save_info(ver, info)
    print(f'已记下：{ver} 不跟，check 不再提醒')


# ---------- fetch：下载 + 解包（不运行任何 exe） ----------

def mega_download(lk, out_dir):
    mi = mega_info(lk['url'], want_dl=True)
    name = os.path.basename(mi['name'] or 'download.zip').strip() or 'download.zip'
    out = os.path.join(out_dir, name)
    print(f'从 MEGA 下载 {name}（{human(mi["size"])}）…')
    proc = subprocess.Popen(['openssl', 'enc', '-d', '-aes-128-ctr', '-K', mi['key'].hex(), '-iv', mi['iv'].hex(),
                             '-out', out], stdin=subprocess.PIPE)
    got, step = 0, max((mi['size'] or 1) // 10, 1)
    with urllib.request.urlopen(urllib.request.Request(mi['dl'], headers=UA), timeout=60) as r:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            proc.stdin.write(b)
            if got // step != (got + len(b)) // step:
                print(f'  {min(100, (got + len(b)) * 100 // (mi["size"] or 1))}%')
            got += len(b)
    proc.stdin.close()
    if proc.wait():
        die('openssl 解密失败')
    return out, mi['size']


def http_download(lk, out_dir):
    name = os.path.basename(urllib.parse.unquote(lk['url'].rstrip('/').rsplit('/', 1)[-1])) or 'download.zip'
    out = os.path.join(out_dir, name)
    print(f'从 {lk["source"]} 下载 {name} …')
    with urllib.request.urlopen(urllib.request.Request(lk['url'], headers=UA), timeout=60) as r:
        if 'html' in (r.headers.get('Content-Type') or ''):
            raise RuntimeError('返回的是网页不是文件（可能要在浏览器里点）')
        with open(out, 'wb') as f:
            shutil.copyfileobj(r, f, 1 << 20)
    return out, lk.get('size')


def archive_members(archive):
    if zipfile.is_zipfile(archive):
        return zipfile.ZipFile(archive).namelist()
    r = subprocess.run(['bsdtar', '-tf', archive], capture_output=True, text=True, check=True)
    return r.stdout.splitlines()


def extract(archive, gdir):
    """只解出根目录的 exe / txt 和 data/text/，其它（音乐、图片、附带的小工具 exe）不碰。"""
    names = archive_members(archive)
    hit = next((n for n in names if re.search(r'(^|/)data/text/en/[^/]+\.dll$', n)), None)
    if not hit:
        die('压缩包里没找到 data/text/en/*.dll，游戏目录结构可能变了，需要人工看')
    prefix = hit[:hit.index('data/text/en/')]
    want = []
    for n in names:
        if not n.startswith(prefix) or n.endswith('/'):
            continue
        rel = n[len(prefix):]
        if rel.startswith('data/text/') or ('/' not in rel and rel.lower().endswith(('.exe', '.txt'))):
            want.append(n)
    if os.path.exists(gdir) and os.listdir(gdir):
        die(f'{gdir} 不是空目录')
    os.makedirs(gdir, exist_ok=True)
    real = os.path.realpath(gdir)
    if zipfile.is_zipfile(archive):
        z = zipfile.ZipFile(archive)
        for n in want:
            target = os.path.realpath(os.path.join(gdir, n[len(prefix):]))
            if not target.startswith(real + os.sep):
                die(f'压缩包里有越界路径: {n}')
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(n) as s, open(target, 'wb') as f:  # z.open 读完会校验 CRC，顺带验了完整性
                shutil.copyfileobj(s, f)
    else:  # rar / 7z 交给 bsdtar（默认拒绝 .. 和绝对路径）
        tmp = gdir + '.tmp'
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
        subprocess.run(['bsdtar', '-xf', archive, '-C', tmp] + want, check=True)
        for n in want:
            dst = os.path.join(gdir, n[len(prefix):])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(os.path.join(tmp, n), dst)
        shutil.rmtree(tmp)
    print(f'解出 {len(want)} 个文件到 {gdir}（只有 exe、说明 txt 和 data/text）')


def cmd_fetch(ver, local=None):
    d = vdir(ver)
    info = load_info(ver)
    dl = os.path.join(d, 'download')
    if os.path.exists(dl) and os.listdir(dl):
        die(f'{dl} 不是空的；要重下先人工删掉它')
    os.makedirs(dl, exist_ok=True)
    if local:
        out, size = os.path.join(dl, os.path.basename(local)), None
        shutil.copy2(local, out)
        info.setdefault('links', [{'source': '本地文件', 'url': os.path.abspath(local)}])
    else:
        out = None
        for lk in info.get('links', []):
            try:
                out, size = (mega_download if lk['source'] == 'MEGA' else http_download)(lk, dl)
                break
            except Exception as e:
                print(f'  {lk["source"]} 下载失败: {e}，换下一个')
                for f in os.listdir(dl):
                    os.remove(os.path.join(dl, f))
        if not out:
            die('所有链接都没下载成功；可以人工下好后用 --from 压缩包 继续')
        if size and os.path.getsize(out) != size:
            die(f'大小不对：应为 {size}，实际 {os.path.getsize(out)}')
    print(f'压缩包: {out}（{human(os.path.getsize(out))}）')
    gdir = os.path.join(d, 'game')
    extract(out, gdir)
    exe = game_exe(gdir)
    info.update({'status': 'fetched', 'archive': out, 'archive_sha256': sha256(out),
                 'exe': os.path.basename(exe), 'exe_sha256': sha256(exe)})
    save_info(ver, info)
    print(f'exe: {info["exe"]}  SHA-256 {info["exe_sha256"]}')
    print(f'下一步: python3 -I tools/update.py diff {ver}')


# ---------- diff：新旧文本对比 ----------

def load_rows(path):
    return jload(path) if os.path.exists(path) else []


def align(old, new, old_tr):
    """把新版每一行对应到旧版。返回 ([(新id, 种类, 旧id或None)], [删掉的旧id])。
    种类: same 原文没变 / es 只有西语变了 / changed 原文改了 / new 新增 / moved 别处有一模一样的原文（直接沿用译文）/ empty 空行"""
    sm = difflib.SequenceMatcher(None, [r['en'] for r in old], [r['en'] for r in new], autojunk=False)
    res, deleted = {}, []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            for k in range(i2 - i1):
                o, n = old[i1 + k], new[j1 + k]
                res[n['id']] = ('same' if o['es'] == n['es'] else 'es', o['id'])
        elif op == 'replace' and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):  # 等长替换：原地改句子，按位置一一对应
                res[new[j1 + k]['id']] = ('changed', old[i1 + k]['id'])
        else:
            olds = list(range(i1, i2))
            for j in range(j1, j2):
                n = new[j]
                best, score = None, 0.0
                for i in olds:
                    sm2 = difflib.SequenceMatcher(None, old[i]['en'] or old[i]['es'], n['en'] or n['es'])
                    if sm2.real_quick_ratio() < SIMILAR or sm2.quick_ratio() < SIMILAR:
                        continue
                    s = sm2.ratio()
                    if s > score:
                        best, score = i, s
                if best is not None and score >= SIMILAR:
                    olds.remove(best)
                    res[n['id']] = ('changed', old[best]['id'])
                else:
                    res[n['id']] = ('new', None)
            deleted += [old[i]['id'] for i in olds]
    # 原文和旧版别处某行完全一样、且那行译文唯一：算挪了位置，沿用译文
    by_text = {}
    for o in old:
        zh = (old_tr.get(o['id']) or {}).get('zh')
        if zh and not is_empty_row(o):
            by_text.setdefault((o['en'], o['es']), {}).setdefault(zh, o['id'])
    out = []
    for n in new:
        kind, oid = res[n['id']]
        if is_empty_row(n):
            kind = 'empty'
        elif kind in ('new', 'changed', 'es'):
            cand = by_text.get((n['en'], n['es']), {})
            if len(cand) == 1:
                kind, oid = 'moved', next(iter(cand.values()))
        out.append((n['id'], kind, oid))
    return out, deleted


def tr_files():
    return {os.path.basename(x)[:-5]: x for x in glob.glob(p('translations', '*.json'))}


def cmd_diff(ver):
    d = vdir(ver)
    info = load_info(ver)
    if os.path.isdir(os.path.join(d, 'old_translations')):
        die('已经 merge 过了（translations/ 已换成新行号），不能再 diff。要从头来：git checkout translations，'
            f'删掉 work/update/{ver}/old_translations，再跑 diff')
    gdir = os.path.join(d, 'game')
    if not os.path.isdir(os.path.join(gdir, 'data', 'text', 'en')):
        die(f'{gdir} 里没有 data/text/en，先跑 fetch')
    new_src = os.path.join(d, 'src')
    shutil.rmtree(new_src, ignore_errors=True)
    with contextlib.redirect_stdout(io.StringIO()):
        rtext.cmd_export(os.path.join(gdir, 'data', 'text'), new_src)
    st = state()
    old_src = p(st['src_dir'])
    trs = tr_files()
    al_all, summary, todo = {}, [], {}
    md = []
    for path in sorted(glob.glob(os.path.join(new_src, '*.json'))):
        name = os.path.basename(path)[:-5]
        new, old = jload(path), load_rows(os.path.join(old_src, name + '.json'))
        old_tr = {r['id']: r for r in jload(trs[name])} if name in trs else {}
        al, deleted = align(old, new, old_tr)
        al_all[name] = [list(x) for x in al]
        cnt = {k: 0 for k in ('new', 'changed', 'es', 'moved')}
        for _, kind, _ in al:
            if kind in cnt:
                cnt[kind] += 1
        oldb, newb = {r['id']: r for r in old}, {r['id']: r for r in new}
        skip = name.startswith(SKIP_FILES) or name not in trs
        summary.append((name, len(old), len(new), cnt, len(deleted), skip))
        if not any(cnt.values()) and not deleted and len(old) == len(new):
            continue
        md.append(f'\n## {name}（旧 {len(old)} 行 → 新 {len(new)} 行）' + ('　※ 这个文件还没开始翻，只列出不派单' if skip else ''))
        carried = {nid: (old_tr.get(oid) or {}).get('zh', '') for nid, kind, oid in al if kind in ('same', 'moved')}
        items = []
        for nid, kind, oid in al:
            n = newb[nid]
            if kind == 'new':
                md.append(f'- 新增 #{nid}　{n["en"]}' + (f'　｜西 {n["es"]}' if n['es'] != n['en'] else ''))
            elif kind in ('changed', 'es'):
                o = oldb[oid]
                if kind == 'changed':
                    md.append(f'- 改动 #{oid}→#{nid}　旧: {o["en"]}\n　　　　　　　新: {n["en"]}')
                else:
                    md.append(f'- 西语改动 #{oid}→#{nid}　{n["en"]}\n　　　　　　　旧西: {o["es"]}\n　　　　　　　新西: {n["es"]}')
            elif kind == 'moved' and oid != nid and name in trs:
                continue  # 只是行号挪了，不列
            else:
                continue
            if skip:
                continue
            it = {'id': nid, 'kind': '新增' if kind == 'new' else '改动', 'en': n['en'], 'es': n['es']}
            if kind != 'new':
                o = oldb[oid]
                it.update({'old_en': o['en'], 'old_es': o['es'], 'old_zh': (old_tr.get(oid) or {}).get('zh', '')})
            ctx = []
            for k in (nid - 2, nid - 1, nid + 1):
                if k in newb and not is_empty_row(newb[k]):
                    ctx.append({'id': k, 'en': newb[k]['en'], 'zh': carried.get(k, '')})
            it['ctx'] = ctx
            items.append(it)
        for oid in deleted:
            md.append(f'- 删除 旧#{oid}　{oldb[oid]["en"]}')
        if items:
            todo[name] = items
    # 任务文件 + 子代理提示词
    for sub in ('todo', 'prompts'):
        shutil.rmtree(os.path.join(d, sub), ignore_errors=True)
    os.makedirs(os.path.join(d, 'parts'), exist_ok=True)
    chunks = []
    for name, items in todo.items():
        for k in range(0, len(items), CHUNK):
            cid = f'{name}.{k // CHUNK + 1}'
            jsave(os.path.join(d, 'todo', cid + '.json'), items[k:k + CHUNK])
            chunks.append((cid, name, len(items[k:k + CHUNK])))
    batches, cur, n = [], [], 0
    for c in chunks:
        if cur and n + c[2] > BATCH:
            batches.append(cur); cur, n = [], 0
        cur.append(c); n += c[2]
    if cur:
        batches.append(cur)
    for bi, b in enumerate(batches, 1):
        write_prompt(ver, os.path.join(d, 'prompts', f'batch{bi}.md'), b)
    jsave(os.path.join(d, 'align.json'), al_all, indent=None)
    # 清单
    head = [f'# 待翻行清单：The Last Beta {st["current"]} → {ver}', '',
            f'旧文本 `{st["src_dir"]}`，新文本 `work/update/{ver}/src`。行号是新版的。', '',
            '| 文件 | 旧行数 | 新行数 | 新增 | 改动 | 西语改动 | 挪位沿用 | 删除 | 派单 |', '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    tot = {'new': 0, 'changed': 0, 'es': 0, 'del': 0, 'todo': 0}
    for name, lo, ln, cnt, nd, skip in summary:
        moved = cnt['moved']
        if not (cnt['new'] or cnt['changed'] or cnt['es'] or nd or lo != ln):
            continue
        k = len(todo.get(name, []))
        head.append(f'| `{name}` | {lo} | {ln} | {cnt["new"]} | {cnt["changed"]} | {cnt["es"]} | {moved} | {nd} | '
                    + ('不派（未开翻）' if skip else f'{k} 行') + ' |')
        tot['new'] += cnt['new']; tot['changed'] += cnt['changed']; tot['es'] += cnt['es']; tot['del'] += nd; tot['todo'] += k
    head.append(f'| **合计** | | | {tot["new"]} | {tot["changed"]} | {tot["es"]} | | {tot["del"]} | **{tot["todo"]} 行** |')
    head += ['', f'派给翻译子代理: {tot["todo"]} 行，{len(chunks)} 个任务文件，{len(batches)} 个子代理（提示词在 `work/update/{ver}/prompts/`）。']
    with open(os.path.join(d, '待翻行.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(head + md) + '\n')
    info.update({'status': 'diffed', 'old_version': st['current'], 'todo_rows': tot['todo'], 'batches': len(batches),
                 'counts': tot})
    save_info(ver, info)
    print('\n'.join(head))
    print(f'\n清单: {os.path.join(d, "待翻行.md")}')
    if batches:
        print('下一步: 每个 prompts/batchN.md 派一个翻译子代理；都交回后跑 python3 -I tools/update.py merge', ver)
    else:
        print('没有要翻的行。下一步: python3 -I tools/update.py merge', ver)


def write_prompt(ver, path, batch):
    rel = f'work/update/{ver}'
    lines = [f'你是《宝可梦重装上阵》（Pokémon Reloaded）简体中文汉化的译者。游戏出了新版本 {ver}，'
             '下面任务文件里是新增或原文改动的行，只翻这些。', '',
             f'仓库目录: {ROOT}', '',
             '开工前先读 `translations/STYLE.md`，必须遵守。专有名词查 `glossary/glossary.csv`、`glossary/places.tsv`、'
             '`translations/txt_character.json`（用 grep 查，不要整份读）。', '',
             '任务文件（JSON 数组）→ 你要写的译文文件：']
    for cid, name, n in batch:
        lines.append(f'- `{rel}/todo/{cid}.json`（{n} 行，源文件 {name}）→ `{rel}/parts/{cid}.json`')
    lines += ['', '每条有 `id`、`en`、`es`。`kind` 为「改动」的还带 `old_en`、`old_es`、`old_zh`：原文改过了，请以 old_zh 为底按新原文修改，'
              '没变的部分保持原来的译法和用词。`ctx` 是前后几行和它们现有的译文，只用来理解语境、统一称呼，不用翻。'
              '英文和西语不一致时以西语为准。', '',
              '译文文件格式：`[{"id": 行号, "zh": "译文"}]`，任务里每个 id 都要有。', '',
              '写完逐个校验，必须零错误：', '```',
              f'python3 -I tools/check_part.py {rel}/parts/<任务名>.json <源文件名> --src {rel}/src', '```', '',
              '不要改 translations/ 下的文件，不要动 git。最后回报：每个任务文件翻了几行、校验结果，有拿不准的译名列出来。']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


# ---------- merge：迁移旧译文 + 合并新译文 + 校验 ----------

def git(*args, check=True):
    return subprocess.run(['git', '-C', ROOT] + list(args), capture_output=True, text=True, check=check)


def run_check(part, name, src_dir):
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'check_part.py'), part, name, '--src', src_dir],
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def write_tr(path, rows, like):
    """按原文件的格式写：一行一条（like 以 '[\n{' 开头）或 indent=1；保证内容不变时逐字节一致。"""
    if like.startswith('[\n{'):
        text = '[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n]\n'
    else:
        text = json.dumps(rows, ensure_ascii=False, indent=1)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(path + '.tmp', path)


def cmd_merge(ver, force=False):
    d = vdir(ver)
    info = load_info(ver)
    if info.get('status') not in ('diffed', 'merged', 'built'):
        die('先跑 diff')
    snap = os.path.join(d, 'old_translations')  # 旧行号的译文快照；重跑 merge 一律从这里读
    if not os.path.isdir(snap):
        dirty = git('status', '--porcelain', '--', 'translations').stdout.strip()
        if dirty and not force:
            die('translations/ 有没提交的改动（可能有别的会话在翻）。先让它们提交，或确认后加 --force：\n' + dirty)
        pending = [x for x in glob.glob(p('work', 'parts', '*.json')) if not os.path.basename(x).startswith('_')]
        if pending and not force:
            die(f'work/parts/ 里还有 {len(pending)} 个按旧版行号写的译文没合并（{os.path.basename(pending[0])} 等）。'
                '先用 tools/merge_parts.py 合进 translations/ 并提交，再跑 merge；不然行号一换就对不上了')
        shutil.copytree(p('translations'), snap)
    trs = {os.path.basename(x)[:-5]: x for x in glob.glob(os.path.join(snap, '*.json'))}
    old_src_dir = p(state()['src_dir'])
    new_src = os.path.join(d, 'src')
    al_all = jload(os.path.join(d, 'align.json'))
    # 收子代理交回的译文
    parts, bad = {}, []
    for todo_path in sorted(glob.glob(os.path.join(d, 'todo', '*.json'))):
        cid = os.path.basename(todo_path)[:-5]
        name = cid.rsplit('.', 1)[0]
        part = os.path.join(d, 'parts', cid + '.json')
        want = {it['id'] for it in jload(todo_path)}
        if not os.path.exists(part):
            bad.append(f'{cid}: 还没交回')
            continue
        rc, out = run_check(part, name, new_src)
        if rc:
            bad.append(f'{cid}: 校验没过\n{out[-1200:]}')
            continue
        got = {r['id']: r['zh'] for r in jload(part) if r.get('zh') and r['id'] in want}
        if want - set(got):
            bad.append(f'{cid}: 缺 {len(want - set(got))} 行 {sorted(want - set(got))[:10]}')
        parts.setdefault(name, {}).update(got)
    if bad and not force:
        die('子代理译文还没齐：\n  ' + '\n  '.join(bad) + '\n（确认缺的行先回落英文的话，加 --force 继续）')
    touched = sorted(parts)  # 只查有新译文的文件，全量查要几十秒

    def term_count():
        if not touched:
            return 0, ''
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'term_check.py')] + touched,
                           capture_output=True, text=True)
        m = re.search(r'疑似译名不一致: (\d+)', r.stdout)
        return int(m.group(1)) if m else None, r.stdout.strip()
    term_before = info.get('term_before')
    if term_before is None:
        term_before = info['term_before'] = term_count()[0]
    report, errors = [], 0
    for name in sorted(set(trs) | set(parts)):
        if name not in al_all:
            print(f'  ! 新版没有 {name}，旧译文保留不动')
            continue
        like = open(trs[name], encoding='utf-8').read(3) if name in trs else '[\n '
        old_tr = {r['id']: r for r in jload(trs[name])} if name in trs else {}
        old_n = len(load_rows(os.path.join(old_src_dir, name + '.json')))
        dense = not old_tr or len(old_tr) >= old_n  # 原文件不收空行的（如 txt_attack_desc），新文件也不收
        new = {r['id']: r for r in jload(os.path.join(new_src, name + '.json'))}
        got = parts.get(name, {})
        rows, n_carry, n_new, n_left = [], 0, 0, 0
        for nid, kind, oid in al_all[name]:
            n = new[nid]
            row = {'id': nid, 'en': n['en'], 'es': n['es'], 'zh': ''}
            o = old_tr.get(oid) if oid is not None else None
            if kind in ('same', 'moved', 'empty') and o:
                row['zh'] = o.get('zh', '')
                if o.get('note'):
                    row['note'] = o['note']
                n_carry += bool(row['zh'])
            elif kind == 'empty' and not dense:
                continue
            if nid in got:
                row['zh'] = got[nid]
                row.pop('note', None)  # 原文变了，「官方原文」之类的备注不再成立
                n_new += 1
            elif kind in ('new', 'changed', 'es') and name in trs:
                n_left += 1
            rows.append(row)
        out = p('translations', name + '.json')
        write_tr(out, rows, like)
        rc, msg = run_check(out, name, new_src)
        errors += rc != 0
        report.append(f'  {name}: 沿用 {n_carry}，新译 {n_new}' + (f'，仍是英文 {n_left}' if n_left else '')
                      + ('' if rc == 0 else '\n' + msg[-1500:]))
    print('合并结果:')
    print('\n'.join(report))
    term_after, tc = term_count()
    print(f'术语检查（{"、".join(touched) or "无"}，疑似译名不一致）: 合并前 {term_before} → 合并后 {term_after}'
          + ('' if term_after is None or term_before is None or term_after <= term_before
             else f'　！多了 {term_after - term_before} 条，用 python3 -I tools/term_check.py --tsv 报告.tsv 看是哪些'))
    if errors:
        die('有文件校验没过，见上面')
    info['status'] = 'merged'
    save_info(ver, info)
    print(f'下一步: python3 -I tools/update.py build {ver}')


# ---------- build：试打补丁 ----------

class Tee(io.StringIO):
    def write(self, s):
        sys.__stdout__.write(s)
        return super().write(s)


def cmd_build(ver):
    import make_patch, gm8_repack as gm
    d = vdir(ver)
    info = load_info(ver)
    if info.get('status') not in ('merged', 'built'):
        die('先跑 merge')
    gdir = os.path.join(d, 'game')
    exe = game_exe(gdir)
    out = os.path.join(d, 'out')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    buf = Tee()
    with contextlib.redirect_stdout(buf):
        make_patch.build(gdir, out, exe_path=exe)
    log = buf.getvalue()
    with open(os.path.join(d, 'build.log'), 'w', encoding='utf-8') as f:
        f.write(log)
    if '没找到要改的片段' in log:
        die('新版 exe 里有补丁要改的代码找不到了（见上面「没找到要改的片段」），要人工看 tools/make_patch.py 的 FIXED_SUBS')
    # 复查：改过的 exe 能重新解开，新加的脚本和图集都在
    pexe = os.path.join(out, os.path.basename(exe))
    g = gm.GM80(open(pexe, 'rb').read())
    names = {gm.parse_script(b)[0] for b in g.blob_list('scripts') if gm.parse_script(b)}
    need = {b'zh_chars', b'zh_draw_text', b'zh_string_width'}
    if not need <= names:
        die(f'改过的 exe 里少了脚本: {need - names}')
    n_zh = len(os.listdir(os.path.join(out, 'data', 'text', 'zh')))
    # 旧版玩家用新译文打补丁还剩多少中文（译文按新行号存，旧版靠按英文原文找回）
    st = state()
    old_text = os.path.join(p(st['game_dir']), 'data', 'text')
    if st['current'] != ver and os.path.isdir(os.path.join(old_text, 'en')):
        trs = make_patch.load_translations()
        with contextlib.redirect_stdout(io.StringIO()):
            _, _, s_old = make_patch.zh_lines(old_text, trs)
            _, _, s_new = make_patch.zh_lines(os.path.join(gdir, 'data', 'text'), trs)
        a, b = sum(x for x, _ in s_old.values()), sum(x for x, _ in s_new.values())
        print(f'旧版 {st["current"]} 用新译文打补丁：中文 {a} 条（新版 {b} 条）')
        info['old_version_zh'] = a
    info.update({'status': 'built', 'patched_exe_sha256': sha256(pexe)})
    save_info(ver, info)
    print(f'\n✓ 试打通过：{pexe}（可重新解析，zh_* 脚本都在），data/text/zh/ {n_zh} 个文件')
    print(f'下一步: python3 -I tools/update.py release {ver}')


# ---------- release：补 KNOWN、改 README、提交推送 ----------

def cmd_release(ver, push=True):
    d = vdir(ver)
    info = load_info(ver)
    if info.get('status') != 'built':
        die('先跑 build')
    st = state()
    old = st['current']
    sha, exe = info['exe_sha256'], info['exe']
    # patch.py 的 KNOWN
    pp = p('patch.py')
    s = open(pp, encoding='utf-8').read()
    if sha not in s:
        m = re.search(r'KNOWN = \{\n(.*?)\n\}', s, re.S)
        s = s[:m.end(1)] + f"\n    '{sha}': 'The Last Beta {ver}'," + s[m.end(1):]
        open(pp, 'w', encoding='utf-8').write(s)
    # README：版本行、下载说明
    rp = p('README.md')
    r = open(rp, encoding='utf-8').read()
    r = re.sub(r'^- \*\*对应游戏版本：.*$',
               f'- **对应游戏版本：The Last Beta {ver}**（`{exe}`，SHA-256 `{sha[:8]}…{sha[-7:]}`）。'
               f'旧版 {old} 也能打，个别改过的句子会显示英文。', r, count=1, flags=re.M)
    r = re.sub(r'\*The Last Beta [\d.]+ Full\*', f'*The Last Beta {ver} Full*', r)
    open(rp, 'w', encoding='utf-8').write(r)
    # 工作区切到新版：旧文本留档，新文本成为 work/src
    old_src = p(st['src_dir'])
    keep = p('work', f'src-{old}')
    if os.path.isdir(old_src) and not os.path.exists(keep):
        shutil.copytree(old_src, keep)
    shutil.rmtree(p('work', 'src'), ignore_errors=True)
    shutil.copytree(os.path.join(d, 'src'), p('work', 'src'))
    jsave(STATE, {'current': ver, 'game_dir': os.path.relpath(os.path.join(d, 'game'), ROOT), 'src_dir': 'work/src',
                  'previous': {'version': old, 'game_dir': st['game_dir'], 'src_dir': os.path.relpath(keep, ROOT)}})
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'stats.py')], capture_output=True, check=True)
    c = info.get('counts', {})
    git('add', '--', 'translations', 'patch.py', 'README.md', 'glossary/人物.csv')
    msg = (f'跟进游戏新版本 The Last Beta {ver}：新增 {c.get("new", 0)} 行、改动 {c.get("changed", 0)} 行，'
           f'补上版本校验\n\n待翻行清单由 tools/update.py diff 生成，派单 {c.get("todo", 0)} 行。\n\n'
           'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
    cm = git('commit', '-m', msg, check=False)
    print(cm.stdout.strip() or cm.stderr.strip())
    if push:
        ps = git('push', 'origin', 'HEAD:main', check=False)
        if ps.returncode:
            die('推送失败（可能远端有新提交，先 git pull --rebase 再推）：\n' + ps.stderr)
        print('已推送 origin/main')
    info['status'] = 'released'
    save_info(ver, info)
    print(f'✓ {ver} 完成。KNOWN 已加 {sha[:12]}…，README 已更新。')


def cmd_status(ver=None):
    st = state()
    print('当前跟的版本:', st['current'], '| 游戏目录:', st['game_dir'], '| 文本:', st['src_dir'])
    vers = [ver] if ver else sorted((v for v in os.listdir(UPD) if re.fullmatch(r'\d+(\.\d+)+', v)), key=update_check.key) \
        if os.path.isdir(UPD) else []
    nxt = {'reported': 'fetch（要 hacking 同意）', 'fetched': 'diff', 'diffed': '派翻译子代理 → merge',
           'merged': 'build', 'built': 'release', 'released': '无', 'declined': '无（不跟）'}
    for v in vers:
        i = load_info(v)
        print(f'  {v}: {i.get("status", "?")} → 下一步 {nxt.get(i.get("status"), "?")}'
              + (f'，待翻 {i["todo_rows"]} 行' if 'todo_rows' in i else ''))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 0
    flag = lambda f: f in a
    opt = lambda f: a[a.index(f) + 1] if f in a else None
    pos = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--feed', '--from'))]
    cmd, rest = pos[0], pos[1:]
    if cmd == 'check':
        return cmd_check(opt('--feed'))
    if cmd == 'status':
        return cmd_status(rest[0] if rest else None)
    if not rest:
        die(f'{cmd} 要给版本号')
    ver = rest[0]
    if cmd == 'fetch':
        return cmd_fetch(ver, opt('--from'))
    if cmd == 'diff':
        return cmd_diff(ver)
    if cmd == 'merge':
        return cmd_merge(ver, flag('--force'))
    if cmd == 'build':
        return cmd_build(ver)
    if cmd == 'release':
        return cmd_release(ver, push=not flag('--no-push'))
    if cmd == 'decline':
        return cmd_decline(ver)
    die(f'不认识的命令 {cmd}')


if __name__ == '__main__':
    sys.exit(main() or 0)
