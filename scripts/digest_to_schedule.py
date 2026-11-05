# -*- coding: utf-8 -*-
"""아티팩트의 아침 메일용 요약(brief/digest) → data/brief/schedule.json

Total Scheduler 아티팩트(https://claude.ai/artifact/NwsJhhJrS4211TVWdX8CRK)는 저장할 때마다
`brief/digest` 문서에 **어제 ~ 45일 뒤** 일정을 작게 묶어 둔다 (v2):
  {v, built, at, from, to, types:[{id,name,adapter}],
   ev:[[날짜, 타입id, 이슈, 제목, 시즌, oi, 담당, DUE], ...],   ← 문자열·정수 8칸 고정, 객체 없음
   n, h, hd:{날짜: 그 날짜 사건들의 해시}}
클라우드 예약 작업은 남이 쓴 문서를 파일로 받을 수 없어(실측) 이 문서를 **옮겨 적는다**.

  python scripts/digest_to_schedule.py _sync/digest.json

대조 (FNV-1a 32bit, UTF-16 단위 — 페이지의 JSON.stringify 와 같은 문자열 위에서):
  · 전체 h 가 맞으면 → 그대로 갱신, exit 0
  · 안 맞으면 날짜별 hd 로 **틀린 날짜를 찾아 출력**하고 exit 2 — 작업이 그 날짜만 고쳐 다시 돌린다
  · `--accept-partial` 이면 맞는 날짜만 새 것으로, 틀린 날짜는 **직전 사본의 그 날짜**로 채워 갱신, exit 3
  · 형식이 아니면 exit 4 (사본을 건드리지 않는다)
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
    h = 0x811c9dc5
    for (u,) in struct.iter_unpack('<H', s.encode('utf-16-le')):
        h ^= u
        h = (h * 0x01000193) & 0xffffffff
    return '%08x' % h


def js(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def row_of(x):
    date_, tid, label, ti, sc, oi, who, due = x[:8]
    info = []
    if who:
        info.append({'l': '담당', 'v': who})
    if due:
        info.append({'l': 'DUE', 'v': due})
    return {'t': tid, 'ti': ti, 'sc': sc, 'd': [{'l': label, 'v': date_, 'oi': oi}], 'info': info}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    partial = '--accept-partial' in sys.argv
    if not args:
        sys.exit('사용법: python scripts/digest_to_schedule.py <digest.json> [--accept-partial]')
    d = json.load(io.open(args[0], encoding='utf-8'))
    if isinstance(d, dict) and 'ev' not in d and isinstance(d.get('data'), dict):
        d = d['data']
    ev, types, hd = d.get('ev'), d.get('types'), d.get('hd') or {}
    if (not isinstance(ev, list) or not isinstance(types, list) or not types
            or any(not isinstance(x, list) or len(x) != 8 for x in ev)):
        print('형식이 아닙니다 (ev 는 8칸 배열의 목록이어야 함) — 사본을 그대로 둡니다')
        sys.exit(4)
    by = {}
    for x in ev:
        by.setdefault(x[0], []).append(x)
    bad = sorted(k for k in set(hd) | set(by) if fnv(js(by.get(k, []))) != hd.get(k, fnv('[]')))
    whole = d.get('n') == len(ev) and fnv(js(ev)) == d.get('h')
    if not whole and not bad:
        bad = ['(전체)']
    if bad and not partial:
        print('대조 실패 — 틀린 날짜 %d개: %s' % (len(bad), ', '.join(bad)))
        for k in bad[:5]:
            print('  %s : 옮긴 것 %d건 · 해시 %s / 원본 %s' % (k, len(by.get(k, [])), fnv(js(by.get(k, []))), hd.get(k, '-')))
        print('그 날짜의 사건들만 원본과 한 글자씩 다시 맞춰 주세요. 사본은 그대로 둡니다')
        sys.exit(2)

    keep = set(bad)
    rows = [row_of(x) for x in ev if x[0] not in keep]
    if keep and os.path.exists(OUT):          # 틀린 날짜는 어제 사본의 그 날짜로
        old = json.load(io.open(OUT, encoding='utf-8'))
        for r in old.get('rows', []):
            ds = [x for x in r.get('d') or [] if x.get('v') in keep]
            if ds:
                rows.append(dict(r, d=ds))
    synced = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    new = {'v': 3, 'at': d.get('at') or d.get('built', ''), 'built': d.get('built', ''), 'synced': synced,
           'from': d.get('from', ''), 'to': d.get('to', ''), 'stale_days': sorted(keep),
           'types': [{'id': t['id'], 'name': t.get('name', ''), 'adapter': t.get('adapter', '')} for t in types],
           'rows': rows}
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(new, ensure_ascii=False, indent=0) + '\n')
    print('갱신 — 일정 %d건 · %s ~ %s%s' % (len(rows), new['from'], new['to'],
          (' · 못 맞춘 날짜 %d개는 직전 사본 사용: %s' % (len(keep), ', '.join(sorted(keep)))) if keep else ''))
    sys.exit(3 if keep else 0)


if __name__ == '__main__':
    main()
