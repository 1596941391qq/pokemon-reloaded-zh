#!/usr/bin/env python3
"""校验译文：控制符（# @ $..$ (&Z)）数量和原文一致、GBK 可编码、第二字节不落在 ASCII 区。
用法: python3 -I tools/check_part.py <part.json 或 translations/x.json> <源文件名>"""
import json, re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
part = json.load(open(sys.argv[1], encoding='utf-8'))
src = {r['id']: r for r in json.load(open(os.path.join(ROOT, 'work', 'src', sys.argv[2] + '.json'), encoding='utf-8'))}
TOK = re.compile(r'\$[A-Za-z0-9_]+\$|\(&[A-Z]\)')
errs = 0
for r in part:
    zh = r.get('zh', '')
    if not zh:
        continue
    s = src.get(r['id'])
    if s is None:
        print(f"[{r['id']}] 源文件里没有这个 id"); errs += 1; continue
    en = s['es'] if s['es'] else s['en']
    for ch in '#@':
        if zh.count(ch) != en.count(ch) and zh.count(ch) != s['en'].count(ch):
            print(f"[{r['id']}] '{ch}' 数量不符: 原文 {en.count(ch)} 译文 {zh.count(ch)}  | {zh[:60]}"); errs += 1
    a, b = sorted(TOK.findall(s['en'])), sorted(TOK.findall(zh))
    if a != b and sorted(TOK.findall(s['es'])) != b:
        print(f"[{r['id']}] 占位符不符: 原文 {a} 译文 {b}  | {zh[:60]}"); errs += 1
    try:
        bs = zh.encode('gbk')
    except UnicodeEncodeError as e:
        print(f"[{r['id']}] 有 GBK 编不了的字: {zh[e.start:e.end]!r}"); errs += 1; continue
    for ch in zh:
        if ord(ch) >= 0x80:
            cb = ch.encode('gbk')
            if len(cb) == 2 and cb[1] < 0x80:
                print(f"[{r['id']}] 生僻字（第二字节在 ASCII 区）: {ch}"); errs += 1
    if re.search(r'[A-Za-z]{4,}', re.sub(TOK, '', zh)) and not re.search(r'[一-鿿]', zh):
        print(f"[{r['id']}] 看起来没翻: {zh[:60]}")
print(f'{len(part)} 条，错误 {errs}')
sys.exit(1 if errs else 0)
