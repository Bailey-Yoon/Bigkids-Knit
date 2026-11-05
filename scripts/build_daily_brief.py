# -*- coding: utf-8 -*-
"""Total Scheduler — 매일 아침 「오늘의 일정」 브리핑 (RSS 피드)

GitHub Actions 가 평일 아침에 돌린다 (.github/workflows/daily-brief.yml).
읽는 것 : reports/tools/total-scheduler/seed.json   (스케줄러가 보여주는 그 스냅샷)
쓰는 것 : data/brief/feed.xml                        (항목 1개짜리 RSS)

메일은 여기서 보내지 않는다. 회사 메일 계정을 GitHub 에 둘 수 없어서,
Power Automate(회사 Microsoft 365)가 이 피드를 지켜보다가 새 항목이 올라오면
그 제목·본문으로 팀 메일을 보낸다. 그래서 메일은 회사 메일 시스템 안에서만 오간다.

  · 주말은 만들지 않는다
  · 연차표에 '휴일·공지' 가 걸린 날(신정·추석 등)도 만들지 않는다 — 단 '근무' 가 든 공지는 근무일이다
  · 만들지 않는 날은 피드를 건드리지 않는다 → 직전 항목은 이미 보냈으므로 메일이 다시 나가지 않는다
  · 같은 날 두 번 돌아도 guid·pubDate 가 같아 메일이 두 번 나가지 않는다

손으로 시험:  python scripts/build_daily_brief.py --date 2026-11-06 --html out.html
"""
import argparse
import html
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, 'reports', 'tools', 'total-scheduler', 'seed.json')
FEED = os.path.join(ROOT, 'data', 'brief', 'feed.xml')

KST = timezone(timedelta(hours=9))
WD = '월화수목금토일'
AHEAD = 7                       # 앞으로 며칠치를 같이 보여줄지

SITE = 'https://bailey-yoon.github.io/Bigkids-Knit/'
APP_ART = 'https://claude.ai/artifact/NwsJhhJrS4211TVWdX8CRK'
APP_SITE = SITE + 'reports/tools/total-scheduler/'
FEED_URL = SITE + 'data/brief/feed.xml'

# 스케줄러와 같은 색 (막대 색) — 메일은 CSS 변수를 못 쓰므로 값으로 박는다
C_LEAVE = '#00695c'
C_DG = {'C2': '#5e35b1', 'C3': '#9936b5'}
C_TC = {'C2': '#cc0000', 'C3': '#c25700', 'C4': '#857700'}
C_DG_DEF, C_TC_DEF = '#5e35b1', '#cc0000'

# 스케줄러의 SHORT_LBL 과 같은 표
SHORT = {
    'PCMS/BA Due Date': 'BA Due', 'CMS Due Date': 'CMS Due', 'PO Due Date': 'PO Due',
    'APEX Map/ Drill': 'APEX Map', 'APEX Map/Drill': 'APEX Map',
    'Apex Map/Drill Due Date': 'APEX Map', 'Map/Drilled in APEX?': 'APEX Map',
    'Strike-Off Ready Date': 'Strike-Off', 'Vendor Align Due Date': 'Vendor Align',
    'Vendor Pre-ISU': 'Pre-ISU', 'Fabric Commit Due Date': 'Fabric Commit',
}


def short(l):
    if l in SHORT:
        return SHORT[l]
    if l.lower().endswith(' due date'):
        return l[:-9] + ' Due'
    if l.lower().endswith(' date'):
        return l[:-5]
    return l


def season(sc):
    """'2027 C2' → ("C2'27", 'C2') · 'C227 APR W4' → ("C2'27", 'C2')"""
    sc = (sc or '').strip()
    p = sc.split()
    if len(p) == 2 and p[0].isdigit() and len(p[0]) == 4:
        return p[1] + "'" + p[0][2:], p[1]
    if len(sc) >= 4 and sc[0] == 'C' and sc[1].isdigit() and sc[2:4].isdigit():
        return 'C' + sc[1] + "'" + sc[2:4], 'C' + sc[1]
    return sc, ''


def md(d):
    return '%d/%d' % (d.month, d.day)


def mdw(d):
    return '%d/%d (%s)' % (d.month, d.day, WD[d.weekday()])


def esc(s):
    return html.escape(str(s), quote=True)


def load():
    o = json.load(open(SEED, encoding='utf-8'))
    types = {t['id']: t for t in o.get('types', [])}
    ev = []
    for r in o.get('rows', []):
        t = types.get(r.get('t'))
        if not t:
            continue
        for d in r.get('d') or []:
            try:
                dd = date.fromisoformat(d['v'])
            except Exception:
                continue
            ev.append({'ad': t.get('adapter') or '', 'label': d.get('l', ''), 'date': dd,
                       'oi': d.get('oi', 999) if d.get('oi') is not None else 999,
                       'ti': r.get('ti', ''), 'sc': r.get('sc', ''),
                       'info': {i.get('l'): i.get('v') for i in (r.get('info') or [])}})
    return o, ev


# ⚠ Outlook(데스크톱)은 span 의 padding·margin 을 무시한다 — 배지 글자가 색 면 끝에 딱 붙고
#   뒤 글자와도 붙어 "짜투리" 처럼 보였다 (2026-11-05 첫 메일). 색 면 안팎을 **공백 문자**로 띄운다
SP = '&nbsp;'


def chip(text, color):
    return ('<span style="background:%s;color:#ffffff;font-size:11px;font-weight:700;'
            'border-radius:3px;padding:1px 6px;white-space:nowrap">%s%s%s</span>%s') % (
                color, SP, esc(text), SP, SP + SP)


def dg_color(sc):
    return C_DG.get(season(sc)[1], C_DG_DEF)


def tc_color(sc):
    return C_TC.get(season(sc)[1], C_TC_DEF)


def leave_line(e):
    return '<b>%s</b> <span style="color:#6e6d77">%s</span>' % (esc(e['ti']), esc(e['label']))


def dg_block(evs):
    """같은 마감끼리 묶는다 (스케줄러의 펼친 날과 같다 — 그리드 열 순서대로)"""
    g = {}
    for e in evs:
        k = e['label']
        g.setdefault(k, {'oi': e['oi'], 'list': []})
        g[k]['oi'] = min(g[k]['oi'], e['oi'])
        g[k]['list'].append(e)
    out = []
    for k in sorted(g, key=lambda k: (g[k]['oi'], k)):
        L = sorted(g[k]['list'], key=lambda e: (e['sc'], e['ti']))
        items = ''.join('<div style="margin:2px 0">%s%s</div>' % (chip(season(e['sc'])[0], dg_color(e['sc'])), esc(e['ti']))
                        for e in L)
        out.append('<div style="margin:6px 0 8px"><div style="font-weight:700;color:#1d1c22">%s '
                   '<span style="font-weight:400;color:#6e6d77">%d건</span></div>%s</div>' % (esc(short(k)), len(L), items))
    return ''.join(out)


def tc_block(evs):
    L = sorted(evs, key=lambda e: (e['sc'], e['ti']))
    out = []
    for e in L:
        who = e['info'].get('담당') or ''
        due = e['info'].get('DUE') or ''
        extra = []
        if due:
            try:
                extra.append('~' + md(date.fromisoformat(due)))
            except Exception:
                pass
        if who:
            extra.append(who)
        out.append('<div style="margin:2px 0">%s%s%s</div>' % (
            chip(season(e['sc'])[0], tc_color(e['sc'])), esc(e['ti']),
            (' <span style="color:#6e6d77">· %s</span>' % esc(' · '.join(extra))) if extra else ''))
    return ''.join(out)


def section(title, body, color='#1d1c22'):
    return ('<tr><td style="padding:16px 20px 4px;border-top:1px solid #e7e5ee">'
            '<div style="font-size:15px;font-weight:700;color:%s;margin-bottom:6px">%s</div>%s</td></tr>') % (color, esc(title), body)


def none(text='없음'):
    return '<div style="color:#6e6d77">%s</div>' % esc(text)


def build(today, o, ev):
    """(제목, 본문 HTML) — 만들지 않는 날이면 None"""
    if today.weekday() >= 5:
        return None, '주말'
    on = [e for e in ev if e['date'] == today]
    hol = [e for e in on if e['ad'] == 'leave' and '공지' in e['label'] and '근무' not in e['ti']]
    if hol:
        return None, '휴일 (' + ', '.join(e['ti'] for e in hol) + ')'

    lv = [e for e in on if e['ad'] == 'leave' and '공지' not in e['label']]
    notice = [e for e in on if e['ad'] == 'leave' and '공지' in e['label']]
    dg = [e for e in on if e['ad'] == 'ba']
    tc = [e for e in on if e['ad'] == 'tna']

    end = today + timedelta(days=AHEAD)
    nxt = [e for e in ev if today < e['date'] <= end]

    # ── 오늘 ──
    rows = []
    t_lv = (''.join('<div style="margin:2px 0">%s</div>' % leave_line(e) for e in sorted(lv, key=lambda e: e['ti']))
            if lv else none('오늘 연차인 사람은 없습니다'))
    if notice:
        t_lv += ''.join('<div style="margin:2px 0;color:#8a4b00">공지 · %s</div>' % esc(e['ti']) for e in notice)
    rows.append(section('오늘 연차', t_lv, C_LEAVE))
    rows.append(section('오늘 마감 · Due Date Grid', dg_block(dg) if dg else none('오늘 마감은 없습니다'), C_DG_DEF))
    rows.append(section('오늘 시작 · Target Calendar', tc_block(tc) if tc else none(), C_TC_DEF))

    # ── 앞으로 7일 ──
    by = {}
    for e in nxt:
        if e['ad'] == 'ba':
            by.setdefault(e['date'], []).append(e)
    if by:
        b = ''
        for d in sorted(by):
            n = (d - today).days
            b += ('<div style="margin:10px 0 2px"><span style="background:%s;color:#ffffff;'
                  'font-size:11px;font-weight:700;border-radius:999px;padding:1px 8px;white-space:nowrap">'
                  '%sD-%d%s</span>%s<b>%s</b></div>%s') % ('#c25700' if n <= 2 else '#5f5e68', SP, n, SP, SP + SP,
                                                       esc(mdw(d)), dg_block(by[d]))
    else:
        b = none('앞으로 %d일 안에 마감이 없습니다' % AHEAD)
    rows.append(section('앞으로 %d일 · Due Date Grid' % AHEAD, b, C_DG_DEF))

    lvn = {}
    for e in nxt:
        if e['ad'] == 'leave' and '공지' not in e['label'] and e['date'].weekday() < 5:
            lvn.setdefault(e['date'], []).append(e)
    hn = sorted({(e['date'], e['ti']) for e in nxt if e['ad'] == 'leave' and '공지' in e['label']})
    b = ''
    for d in sorted(lvn):
        b += '<div style="margin:2px 0"><b>%s</b>&nbsp;&nbsp;&nbsp;%s</div>' % (
            esc(mdw(d)), ' · '.join(leave_line(e) for e in sorted(lvn[d], key=lambda e: e['ti'])))
    for d, ti in hn:
        b += '<div style="margin:2px 0;color:#8a4b00"><b>%s</b>&nbsp;&nbsp;&nbsp;공지 · %s</div>' % (
            esc(mdw(d)), esc(ti))
    rows.append(section('앞으로 %d일 · 연차' % AHEAD, b or none(), C_LEAVE))

    tcn = {}
    for e in nxt:
        if e['ad'] == 'tna':
            tcn.setdefault(e['date'], []).append(e)
    b = ''
    for d in sorted(tcn):
        b += '<div style="margin:8px 0 2px"><b>%s</b></div>%s' % (esc(mdw(d)), tc_block(tcn[d]))
    rows.append(section('앞으로 %d일 · Target Calendar 시작' % AHEAD, b or none(), C_TC_DEF))

    at = str(o.get('at', ''))[:10]
    try:
        stale = (today - date.fromisoformat(at)).days
    except Exception:
        stale = None
    warn = ''
    if stale is not None and stale >= 14:
        warn = ('<div style="margin-top:6px;color:#8a4b00">⚠ 일정 스냅샷이 %d일 전 것입니다. '
                '엑셀이 바뀌었다면 스냅샷 갱신이 필요합니다.</div>') % stale

    foot = ('<tr><td style="padding:14px 20px 18px;border-top:1px solid #e7e5ee;font-size:12px;color:#6e6d77;line-height:1.6">'
            '일정 스냅샷 <b style="color:#4a4954">%s</b> 기준 · 매일 평일 아침 자동 발송<br>'
            '전체 일정 보기: <a href="%s" style="color:#0277bd">Total Scheduler</a> '
            '(<a href="%s" style="color:#0277bd">사이트판</a>)%s</td></tr>') % (esc(at or '?'), APP_ART, APP_SITE, warn)

    head = ('<tr><td style="background:#eef4fa;padding:18px 20px">'
            '<div style="font-size:11px;letter-spacing:2px;font-weight:700;color:#014b7e">BIG KIDS 2팀 · TOTAL SCHEDULER</div>'
            '<div style="font-size:22px;font-weight:700;color:#1d1c22;margin-top:4px">%s 오늘의 일정</div>'
            '<div style="font-size:13px;color:#4a4954;margin-top:4px">연차 %d명 · 오늘 마감 %d건 · 앞으로 %d일 마감 %d건</div>'
            '</td></tr>') % (esc(mdw(today)), len(lv), len(dg), AHEAD, sum(len(v) for v in by.values()))

    body = ('<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" '
            'style="max-width:680px;background:#ffffff;border:1px solid #e7e5ee;border-collapse:separate;'
            "font-family:'Malgun Gothic','Apple SD Gothic Neo','Segoe UI',sans-serif;font-size:14px;line-height:1.55;color:#1d1c22\">"
            '%s%s%s</table>') % (head, ''.join(rows), foot)

    title = '[2팀 일정] %s 오늘의 일정 · 연차 %d · 마감 %d' % (mdw(today), len(lv), len(dg))
    return title, body


def write_feed(today, title, body, test=False):
    # ⚠ 게시 시각은 **실제로 만든 시각**이어야 한다. 06:00 같은 고정값을 쓰면, GitHub 예약 실행이
    #   늦어져 플로가 그 사이 한 번 피드를 본 경우 "이미 지난 항목" 으로 보고 건너뛸 수 있다.
    #   같은 날 두 번 보내지 않는 건 main() 의 guid 검사가 맡는다
    #   ⚠ 그리고 GitHub Pages 는 파일을 **최대 10분 캐시**한다 (max-age=600). 그동안 플로는 옛 피드를
    #   보면서 '여기까지 봤다' 시각만 앞으로 옮기므로, 뒤늦게 보이는 항목은 게시 시각이 그보다 과거라
    #   새 항목으로 치지 않는다 (2026-11-05 시험 메일 2통이 이렇게 빠졌다). 그래서 **15분 뒤 시각**을 적는다
    made = datetime.now(KST).replace(microsecond=0)
    pub = made + timedelta(minutes=15)
    gid = today.isoformat()
    if test:   # Power Automate 연결 시험용 — 지금 시각의 새 항목이라 플로가 바로 반응한다
        gid += '-test-' + made.strftime('%H%M%S')
        title = '[테스트] ' + title
    pub_s = pub.strftime('%a, %d %b %Y %H:%M:%S +0900')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0"><channel>\n'
           '<title>Big Kids 2팀 · 오늘의 일정</title>\n'
           '<link>%s</link>\n'
           '<description>Total Scheduler 스냅샷으로 만드는 평일 아침 브리핑</description>\n'
           '<language>ko</language>\n'
           '<lastBuildDate>%s</lastBuildDate>\n'
           '<item>\n'
           '<title>%s</title>\n'
           '<link>%s</link>\n'
           '<guid isPermaLink="false">d76-2team-brief-%s</guid>\n'
           '<pubDate>%s</pubDate>\n'
           '<description><![CDATA[%s]]></description>\n'
           '</item>\n'
           '</channel></rss>\n') % (APP_SITE, pub_s, esc(title), APP_ART, gid, pub_s,
                                     body.replace(']]>', ']]&gt;'))
    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    with open(FEED, 'w', encoding='utf-8', newline='\n') as f:
        f.write(xml)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (기본: 오늘 KST)')
    ap.add_argument('--test', action='store_true', help='연결 시험: 지금 시각으로 새 항목을 올린다 (제목에 [테스트])')
    ap.add_argument('--html', help='본문을 이 파일로도 저장 (미리보기용, 피드는 건드리지 않음)')
    a = ap.parse_args()
    today = date.fromisoformat(a.date) if a.date else datetime.now(KST).date()
    o, ev = load()
    title, body = build(today, o, ev)
    if title is None and a.test:
        # 시험은 주말·휴일에도 돌아야 한다 — 가장 가까운 다음 근무일 내용으로 만든다
        d = today
        while title is None:
            d += timedelta(days=1)
            title, body = build(d, o, ev)
        today = d
    if title is None:
        print('%s — 만들지 않음: %s' % (today, body))
        return
    print(title)
    if a.html:
        with open(a.html, 'w', encoding='utf-8') as f:
            f.write('<!doctype html><meta charset="utf-8"><title>%s</title>'
                    '<body style="margin:0;padding:20px;background:#f3f2f6">%s</body>' % (esc(title), body))
        return
    # 같은 날 정기 항목이 이미 있으면 다시 쓰지 않는다 — 다시 쓰면 게시 시각이 바뀌어 메일이 또 나간다
    if not a.test and os.path.exists(FEED):
        if ('d76-2team-brief-%s</guid>' % today.isoformat()) in open(FEED, encoding='utf-8').read():
            print('%s — 이미 만든 날: 피드 유지' % today)
            return
    write_feed(today, title, body, test=a.test)
    print('피드 갱신:', FEED)


if __name__ == '__main__':
    main()
