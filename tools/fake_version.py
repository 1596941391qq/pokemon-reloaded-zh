#!/usr/bin/env python3
"""用现有版本造一个「假新版本」，测 tools/update.py 整条流水线（不联网下载、不运行任何 exe）。

用法: python3 -I tools/fake_version.py <现有游戏目录> <输出目录> [--ver 1.9.2.3]
产出: <输出目录>/Proyecto Reloaded The Last Beta <ver> Full.zip 和 feed.json（假的博客订阅，下载链接沿用 1.9.2.2 的真链接，
      所以 check 查到的文件名和大小是 1.9.2.2 那份的）。

改动：剧情对话插两行（一行全新、一行与第 1 行一模一样）、删一行、改两句英文（一句已译、一句未译）、只改一句西语；
菜单改一句已译的英文；道具名末尾加两个；还没开翻的考试题改一行；exe 改 PE 时间戳让 SHA-256 变。
之后按 README「更新流程」跑：check --feed、fetch --from、diff、派子代理、merge、build、release --no-push。
建议在仓库的临时克隆里跑，别在正式仓库里跑。
"""
import json, os, struct, sys, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtext  # noqa: E402

REV = {bytes([b]).decode('cp1252'): e for e, b in rtext.ESC}
MEGA_1922 = 'https://mega.nz/file/RrsDjDQY#5hOsjq7HIYsNX30JkeHzPGCl12ZO8yugdcz_f7gqLCA'


def enc(text):
    return rtext.crypt(''.join(REV.get(c, c) for c in text).encode('cp1252'), rtext.ENC)


def main():
    game, out_dir = sys.argv[1], sys.argv[2]
    ver = sys.argv[sys.argv.index('--ver') + 1] if '--ver' in sys.argv else '1.9.2.3'
    T = os.path.join(game, 'data', 'text')

    def load(lang, name):
        return rtext.read_lines(os.path.join(T, lang, name + '.dll'))

    files = {}
    en, es = load('en', 'txt_dialog'), load('es', 'txt_dialog')
    en[10 - 1] = enc('Please wait just a moment...')
    es[20 - 1] = enc('¡Buenas, $prota$!')
    en[5000 - 1] = enc(rtext.decode_line(en[5000 - 1]).replace('I think we are even now', 'I think we are even now, friend'))
    del en[3000 - 1], es[3000 - 1]
    en.insert(11, en[0]); es.insert(11, es[0])
    en.insert(5, enc('Welcome to the new version of Reloaded!'))
    es.insert(5, enc('¡Bienvenido a la nueva versión de Reloaded!'))
    files['txt_dialog'] = (en, es)
    en, es = load('en', 'txt_menu'), load('es', 'txt_menu')
    en[7 - 1] = enc('Exit the game?#Any unsaved progress will be lost.')
    files['txt_menu'] = (en, es)
    en, es = load('en', 'txt_obj'), load('es', 'txt_obj')
    en += [enc('Reload Charm'), enc('Mystery Ticket Z')]
    es += [enc('Amuleto Recarga'), enc('Ticket Misterioso Z')]
    files['txt_obj'] = (en, es)
    en, es = load('en', 'txt_exam'), load('es', 'txt_exam')
    en[3 - 1] = enc('Question number three')
    files['txt_exam'] = (en, es)

    exe = [f for f in os.listdir(game) if f.lower().endswith('.exe')][0]
    data = bytearray(open(os.path.join(game, exe), 'rb').read())
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    struct.pack_into('<I', data, pe + 8, struct.unpack_from('<I', data, pe + 8)[0] + 1)
    os.makedirs(out_dir, exist_ok=True)
    zpath = os.path.join(out_dir, f'Proyecto Reloaded The Last Beta {ver} Full.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(f'Proyecto Reloaded The Last Beta {ver} Full.exe', bytes(data))
        for f in os.listdir(game):
            if f.lower().endswith('.txt'):
                z.write(os.path.join(game, f), f)
        for root, _, fs in os.walk(T):
            for f in fs:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, game)
                lang, name = os.path.basename(root), f[:-4]
                if f.endswith('.dll') and name in files and lang in ('en', 'es'):
                    z.writestr(arc, b'\r\n'.join(files[name][0 if lang == 'en' else 1]) + b'\r\n')
                else:
                    z.write(full, arc)
        z.writestr('data/audio/config.ini', b'1')  # 解包时应被跳过
        z.writestr('data/attack_pkmn/Aprendizaje de Ataques.exe', b'MZ not a real exe')  # 应被跳过
    html = (f'<p>Nueva versión.</p><span>Descargar The Last Beta {ver}:</span> <a href="{MEGA_1922}">Link</a> | '
            '<a href="https://store-eu-par-2.gofile.io/download/web/d09e641b-252f-407e-b5fa-205b0d01e904/'
            f'Proyecto%20Reloaded%20The%20Last%20Beta%20{ver}%20Full.zip">Alternativo</a><br>'
            '<a href="https://cold2.gofile.io/download/web/e2ab7686-c5bd-44e0-8e78-247fa81cf945/Librer%C3%ADasReloaded.rar">'
            'Librerías Reloaded</a>')
    feed = {'feed': {'entry': [{'title': {'$t': f'The Last Beta {ver}'}, 'content': {'$t': html},
                                'published': {'$t': '2026-11-20T10:00:00.000+01:00'},
                                'link': [{'rel': 'alternate', 'href': 'https://pokemon-reloaded.blogspot.com/fake-test'}]}]}}
    with open(os.path.join(out_dir, 'feed.json'), 'w', encoding='utf-8') as f:
        json.dump(feed, f, ensure_ascii=False)
    print('写出', zpath, os.path.getsize(zpath))
    print('写出', os.path.join(out_dir, 'feed.json'))


if __name__ == '__main__':
    main()
