# -*- coding: utf-8 -*-
"""ArtifactData 가 내놓은 **도구 결과 원문**에서 types 문서를 꺼내 data/brief/schedule.json 으로

클라우드 예약 작업이 `ArtifactData list types` 를 out_dir 없이 부르면 결과가 230KB 쯤이라
Claude Code 가 그 결과를 파일로 저장해 두고 경로만 알려 준다. 이 스크립트는 그 파일을 그대로 읽는다 —
사람(모델)이 옮겨 적지 않으므로 글자가 틀릴 일이 없다.

  python scripts/dump_to_schedule.py <도구 결과가 저장된 파일>

원문 안의 `{"id": ..., "data": {t, rows, o, at}}` 덩어리를 전부 찾아 쓴다. 감싼 글(머리말 · 경계 줄)은 무시한다.
⚠ 타입 문서를 하나도 못 찾으면 **쓰지 않고 exit 2** — 빈 사본으로 메일이 나가지 않게
"""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'brief', 'schedule.json')


def blobs(text):
    dec = json.JSONDecoder()
    i = 0
    while True:
        i = text.find('{', i)
        if i < 0:
            return
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            i += 1
            continue
        yield obj
        i = end


def walk(o):
    """중첩돼 있어도 {t:{id..}, rows:[..]} 꼴을 모두 찾는다"""
    if isinstance(o, dict):
        if isinstance(o.get('t'), dict) and o['t'].get('id') and isinstance(o.get('rows'), list):
            yield o
            return
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def main():
    if len(sys.argv) < 2:
        sys.exit('사용법: python scripts/dump_to_schedule.py <파일>')
    text = io.open(sys.argv[1], encoding='utf-8', errors='replace').read()
    docs = {}
    for b in blobs(text):
        for d in walk(b):
            docs[d['t']['id']] = d
    if not docs:
        print('타입 문서를 하나도 못 찾았습니다 — 사본을 그대로 둡니다')
        sys.exit(2)
    ds = sorted(docs.values(), key=lambda d: d.get('o', 0))
    types = [d['t'] for d in ds]
    rows = [r for d in ds for r in d['rows']]
    synced = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    new = {'v': 2, 'at': max((d.get('at') or '') for d in ds), 'synced': synced, 'types': types, 'rows': rows}
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(new, ensure_ascii=False, indent=0) + '\n')
    print('갱신 — 타입 %d · 줄 %d · 마지막 변경 %s' % (len(types), len(rows), new['at']))


if __name__ == '__main__':
    main()
