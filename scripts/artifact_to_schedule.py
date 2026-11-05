# -*- coding: utf-8 -*-
"""아티팩트 공유 저장소 → data/brief/schedule.json  (아침 메일이 읽는 사본)

Total Scheduler 는 아티팩트(https://claude.ai/artifact/NwsJhhJrS4211TVWdX8CRK)의
공유 저장소(db)가 정본이다. GitHub 는 그 저장소를 직접 못 읽으므로, 클라우드 예약 작업이
평일 아침 ArtifactData 로 `types` 컬렉션을 파일로 받아 두고 이 스크립트를 돌린다.

  python scripts/artifact_to_schedule.py <받은 폴더>/types

받은 폴더에는 문서마다 <타입id>.json 이 있다: {t: 타입, rows: [...], o: 순서, at: 마지막 변경}.
결과는 예전 seed.json 과 같은 꼴 {at, synced, types, rows} 이라 build_daily_brief.py 가 그대로 읽는다.

⚠ 받은 문서가 0개면 **쓰지 않고 실패**한다 — 읽기가 막힌 걸 "일정이 하나도 없다" 로 바꿔 쓰면
  다음 날 메일이 텅 빈 채로 나간다. 직전 사본을 그대로 두는 편이 낫다
"""
import glob
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'brief', 'schedule.json')


def main():
    if len(sys.argv) < 2:
        sys.exit('사용법: python scripts/artifact_to_schedule.py <폴더>/types')
    docs = []
    for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.json'))):
        d = json.load(io.open(p, encoding='utf-8'))
        if isinstance(d, dict) and 'data' in d and 't' not in d:   # 감싼 꼴로 저장된 경우
            d = d['data']
        if isinstance(d, dict) and isinstance(d.get('t'), dict) and isinstance(d.get('rows'), list):
            docs.append(d)
    if not docs:
        sys.exit('문서를 하나도 못 읽었습니다 — schedule.json 을 그대로 둡니다')
    docs.sort(key=lambda d: d.get('o', 0))
    types = [d['t'] for d in docs]
    rows = [r for d in docs for r in d['rows']]
    at = max((d.get('at') or '') for d in docs)
    old = {}
    if os.path.exists(OUT):
        old = json.load(io.open(OUT, encoding='utf-8'))
    synced = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
    new = {'v': 2, 'at': at, 'synced': synced, 'types': types, 'rows': rows}
    same = old.get('types') == types and old.get('rows') == rows and old.get('at') == at
    if same and old.get('synced') == synced:
        print('변경 없음 — 타입 %d · 줄 %d' % (len(types), len(rows)))
        return
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(new, ensure_ascii=False, indent=0) + '\n')
    print('%s — 타입 %d · 줄 %d · 마지막 변경 %s' % ('동기화 날짜만 갱신' if same else '갱신', len(types), len(rows), at))


if __name__ == '__main__':
    main()
