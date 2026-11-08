#!/usr/bin/env python3
"""宝可梦重装上阵（Pokémon Reloaded）简体中文补丁 —— 一键打补丁。

用法：
  - 打包好的 exe：把「重装上阵中文补丁.exe」放进游戏文件夹双击；或者双击后把游戏文件夹拖进窗口回车。
  - 源码：python patch.py "D:\\Games\\Proyecto Reloaded"（或双击 安装中文补丁.bat）

做的事：
  1. 第一次运行时把原版 exe、lan.txt、config.ini 备份到游戏目录下的「原版备份」文件夹；
  2. 以备份的原版为底，生成中文 exe、data/text/zh/ 文本，并把语言默认设为简体中文。
重复运行（比如更新了译文）总是从原版备份重新生成，不会越改越乱。
恢复原版：把「原版备份」里的文件拷回原处即可。
只需要 Python 3.8+，不用装任何第三方库。
"""
import hashlib, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import make_patch  # noqa: E402

KNOWN = {
    '772d5d458878ff13cee270e5ad6870d9e33e22d92ee8076fd8298e1febf07630': 'The Last Beta 1.9.2.2',
}
BACKUP = '原版备份'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


FROZEN = getattr(sys, 'frozen', False)
SELF = os.path.basename(sys.executable).lower() if FROZEN else ''


def is_game_dir(d):
    return os.path.isdir(os.path.join(d, 'data', 'text', 'en'))


def game_exes(d):
    """游戏文件夹里的 exe（不算补丁自己）。"""
    return [f for f in os.listdir(d) if f.lower().endswith('.exe') and f.lower() != SELF and '补丁' not in f]


def main():
    if len(sys.argv) >= 2:
        game = sys.argv[1]
    else:
        here = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
        found = next((d for d in (here, os.getcwd()) if is_game_dir(d)), None)
        if found:
            print('找到游戏文件夹:', found)
            game = found
        else:
            game = input('把游戏文件夹拖进这个窗口（或输入路径），然后按回车：').strip().strip('"')
    game = os.path.abspath(game)
    if not os.path.isdir(os.path.join(game, 'data', 'text', 'en')):
        sys.exit(f'没找到 {game}\\data\\text\\en —— 请选择游戏本体所在的文件夹（里面有 .exe 和 data 文件夹）。')
    exes = game_exes(game)
    if len(exes) != 1:
        sys.exit(f'游戏文件夹里应该只有一个 .exe，现在是: {exes}')
    exe = exes[0]
    bdir = os.path.join(game, BACKUP)
    os.makedirs(bdir, exist_ok=True)
    src_exe = os.path.join(bdir, exe)
    if not os.path.exists(src_exe):
        h = sha256(os.path.join(game, exe))
        if h not in KNOWN:
            print('! 这个 exe 不是已测试的版本（支持: ' + '、'.join(KNOWN.values()) + '）。')
            if input('  仍要继续吗？[y/N] ').strip().lower() != 'y':
                sys.exit(1)
        else:
            print('游戏版本:', KNOWN[h])
        shutil.copy2(os.path.join(game, exe), src_exe)
        for f in ('lan.txt', 'config.ini'):
            p = os.path.join(game, 'data', 'text', f)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(bdir, f))
        print('已备份原版到', bdir)
    else:
        print('使用已有的原版备份:', src_exe)
    # lan.txt 用备份里的原版，避免重复追加
    lan_bak = os.path.join(bdir, 'lan.txt')
    if os.path.exists(lan_bak):
        shutil.copy2(lan_bak, os.path.join(game, 'data', 'text', 'lan.txt'))
    make_patch.build(game, game, exe_path=src_exe)
    print('\n完成！直接运行游戏即可，默认就是简体中文；也可以在游戏的语言选项里切换。')


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e.code if isinstance(e.code, str) else '已取消。')
    except Exception as e:  # 打包版要把错误留在窗口里给玩家看
        import traceback
        traceback.print_exc()
        print('\n出错了，请把上面的内容截图发给作者。')
    if FROZEN or len(sys.argv) < 2:
        input('\n按回车键关闭窗口……')
