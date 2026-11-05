# -*- coding: utf-8 -*-
"""아티팩트의 아침 메일용 요약(brief/digest) → data/brief/schedule.json

Total Scheduler 아티팩트(https://claude.ai/artifact/NwsJhhJrS4211TVWdX8CRK)는 저장할 때마다
`brief/digest` 문서에 **어제 ~ 45일 뒤** 일정을 작게 묶어 둔다:
  {built, at, from, to, types:[{id,name,adapter}], ev:[[날짜, 타입id, 이슈, 제목, 시즌, oi, {담당,DUE}?]], n, h}
클라우드 예약 작업이 이 문서를 읽어 파일로 옮겨 적은 뒤 이 스크립트를 돌린다.

  python scripts/digest_to_schedule.py _sync/digest.json

⚠ 옮겨 적다 한 글자라도 틀리면 h(FNV-1a, UTF-16 단위)가 어긋난다 → **사본을 바꾸지 않고 exit 2**.
  n(건수)도 대조한다. 틀린 사본으로 메일을 보내느니 어제 사본으로 보내는 편이 낫다
⚠ h 는 페이지의 JSON.stringify(ev) 위에서 계산한다. 여기서는 json.dumps(separators=(',',':'),
  ensure_ascii=False) 로 같은 문자열을 다시 만든다 (정수·문자열·객체만 있어 두 쪽이 같다)
"""
import io
import json
import os
import struct
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'brief', 'schedule.json')


def fnv(s):
    b = s.encode('utf-16-le')
    h = 0x811c9dc5
    for (u,) in struct.iter_unpack('<H', b):
        h ^= u
        h = (h * 0x01000193) & 0xffffffff
    return '%08x' % h


def main():
    if len(sys.argv) < 2:
        sys.exit('사용법: python scripts/digest_to_schedule.py <digest.json>')
    d = json.load(io.open(sys.argv[1], encoding='utf-8'))
    if isinstance(d, dict) and 'ev' not in d and isinstance(d.get('data'), dict):
        d = d['data']
    ev, types = d.get('ev'), d.get('types')
    if not isinstance(ev, list) or not isinstance(types, list) or not types:
        print('형식이 아닙니다 (ev/types 없음) — 사본을 그대로 둡니다')
        sys.exit(2)
    got = fnv(json.dumps(ev, ensure_ascii=False, separators=(',', ':')))
    if d.get('n') != len(ev) or got != d.get('h'):
        print('대조 실패 — 건수 %s/%s · 해시 %s/%s. 옮겨 적은 내용이 원본과 다릅니다. 사본을 그대로 둡니다'
              % (len(ev), d.get('n'), got, d.get('h')))
        sys.exit(2)
    ty = {t['id']: t for t in types}
    rows = []
    for x in ev:
        date_, tid, label, ti, sc, oi = x[:6]
        if tid not in ty:
            continue
        info = [{'l': k, 'v': v} for k, v in (x[6].items() if len(x) > 6 and isinstance(x[6], dict) else [])]
        rows.append({'t': tid, 'ti': ti, 'sc': sc, 'd': [{'l': label, 'v': date_, 'oi': oi}], 'info': info})
    synced = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    new = {'v': 3, 'at': d.get('at') or d.get('built', ''), 'built': d.get('built', ''), 'synced': synced,
           'from': d.get('from', ''), 'to': d.get('to', ''),
           'types': [{'id': t['id'], 'name': t.get('name', ''), 'adapter': t.get('adapter', '')} for t in types],
           'rows': rows}
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(new, ensure_ascii=False, indent=0) + '\n')
    print('갱신 — 일정 %d건 · %s ~ %s · 요약 생성 %s' % (len(rows), new['from'], new['to'], new['built']))


if __name__ == '__main__':
    main()
