#!/usr/bin/env python3
"""检查作者博客有没有发新版本（读 Blogger 的 Atom 订阅），和 patch.py 里已支持的版本对比。
用法: python3 tools/update_check.py   → 打印最新版本号；有新版本时退出码 10。"""
import json, os, re, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = 'https://pokemon-reloaded.blogspot.com/feeds/posts/default?alt=json&max-results=25'
VER = re.compile(r'The Last Beta\s*v?(1\.\d+(?:\.\d+){0,2})', re.I)


def known():
    s = open(os.path.join(ROOT, 'patch.py'), encoding='utf-8').read()
    return set(re.findall(r"'The Last Beta (\d+(?:\.\d+)+)'", s))


def key(v):
    return tuple(int(x) for x in v.split('.'))


def main():
    data = json.loads(urllib.request.urlopen(urllib.request.Request(FEED, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read())
    seen = {}
    for e in data['feed'].get('entry', []):
        text = e['title']['$t'] + ' ' + e.get('content', {}).get('$t', '')[:20000]
        for v in VER.findall(text):
            seen.setdefault(v, (e['published']['$t'][:10], e['title']['$t']))
    if not seen:
        print('没在最近的文章里找到版本号'); return 1
    latest = max(seen, key=key)
    k = known()
    print('博客最新版本:', latest, seen[latest])
    print('补丁已支持:', ', '.join(sorted(k, key=key)))
    if all(key(latest) > key(x) for x in k):
        print('→ 有新版本，需要更新汉化'); return 10
    print('→ 没有新版本'); return 0


if __name__ == '__main__':
    sys.exit(main())
