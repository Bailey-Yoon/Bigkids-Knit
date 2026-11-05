#!/usr/bin/env bash
# 오늘의 일정 브리핑 — .github/workflows/daily-brief.yml 이 부른다.
# 워크플로 파일은 지금 토큰(public_repo)으로 push 할 수 없어 손으로 고쳐야 한다.
# 그래서 로직은 전부 여기 두고 워크플로는 이 파일을 부르기만 한다 — 고칠 일은 여기서.
#
#   bash scripts/daily_brief.sh          평일 아침 정기 실행
#   bash scripts/daily_brief.sh true     연결 시험: 지금 시각의 [테스트] 항목
set -euo pipefail

if [ "${1:-false}" = "true" ]; then
  python scripts/build_daily_brief.py --test
else
  python scripts/build_daily_brief.py
fi

if [ -z "$(git status --porcelain -- data/brief)" ]; then
  echo "변경 없음 — 커밋 생략 (주말·휴일이거나 이미 만든 날)"
  exit 0
fi

git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add data/brief/feed.xml
git commit -m "오늘의 일정 브리핑 $(TZ=Asia/Seoul date +%Y-%m-%d)"

# 원자재 워크플로와 겹치면 push 가 밀릴 수 있다 — 받아서 다시 올린다
for i in 1 2 3; do
  git push && exit 0
  git pull --rebase
done
exit 1
