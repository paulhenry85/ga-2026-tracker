"""Build the Georgia early vote datasets from gv_raw.json (Georgia Votes, built from GA SOS absentee files).
Day k of 2026 early voting = 12 Oct + k (day 1 = 13 Oct). Comparisons line up by days before Election Day (every year votes on a Tuesday, so weekdays match):
2026 day k is 12 Oct + k; the 2022 comparison is 17 Oct 2022 + k (2022 voting opened a day earlier, on 17 Oct,
so its first day is inside 2026 day 1), and 2024 is 14 Oct 2024 + k.
Mail versus in-person split is known only for the latest snapshot; earlier days keep a split once a refresh has
recorded it (kept from the previous output) or once the state files are loaded (split_overrides.json)."""
import json, sys, os, datetime as dt
raw, outdir = sys.argv[1], sys.argv[2]
prev_dir = sys.argv[3] if len(sys.argv) > 3 else None
g = json.load(open(raw)); C = g['counties']
D0 = dt.date(2026, 10, 12); H0 = dt.date(2022, 10, 17)
maxd = dt.date.fromisoformat(g['max_vote_day']); last_day = (maxd - D0).days
def at(c, d, k): return next((r[k] for r in c['rows'] if r['dt'] == d.isoformat()), None)
prev = {}
if prev_dir and os.path.exists(os.path.join(prev_dir, 'ga_ev_county_days.json')):
    for r in json.load(open(os.path.join(prev_dir, 'ga_ev_county_days.json'))):
        if r.get('mail') is not None: prev[(r['day'], r['county'])] = r
ovr = {}
if os.path.exists(os.path.join(os.path.dirname(raw), 'split_overrides.json')):
    for r in json.load(open(os.path.join(os.path.dirname(raw), 'split_overrides.json'))): ovr[(r['day'], r['county'])] = r
cd, days = [], []
for k in range(1, last_day + 1):
    d = D0 + dt.timedelta(days=k); tot = ip = ml = 0; split = True
    for c in C:
        t = at(c, d, 'cur'); name = c['county']
        reg = c['total'] / (c['reg_pct'] / 100) if c['reg_pct'] else None
        row = {'date': d.isoformat(), 'day': k, 'county': name, 'in_person': None, 'mail': None, 'total': t,
               'turnout_pct': round(t / reg * 100, 1) if reg and t is not None else None, 'posted_day': True, 'county_report': False}
        src = ovr.get((k, name)) or (prev.get((k, name)) if k != last_day else None)
        if k == last_day and c['mail'] is not None: row.update(in_person=c['in_person'], mail=c['mail'], total=c['total'])
        elif src and src.get('total') == t: row.update(in_person=src['in_person'], mail=src['mail'])
        cd.append(row)
        tot += t or 0
        if row['mail'] is None: split = False
        else: ip += row['in_person']; ml += row['mail']
    days.append({'date': d.isoformat(), 'day': k, 'in_person': ip if split else None, 'mail': ml if split else None, 'total': tot,
                 'basis': 'Georgia Secretary of State absentee voter file, via Georgia Votes', 'partial': False})
reg_sw = round(sum(c['total'] / (c['reg_pct'] / 100) for c in C if c['reg_pct']))
lastd = (D0 + dt.timedelta(days=last_day)).isoformat()
counties = [{'county': 'STATEWIDE', 'in_person': sum(c['in_person'] for c in C), 'mail': sum(c['mail'] for c in C), 'total': sum(c['total'] for c in C),
             'registered': reg_sw, 'turnout_pct': round(sum(c['total'] for c in C) / reg_sw * 100, 1), 'as_of': lastd, 'day': last_day,
             'posted_day': True, 'partial': False, 'counties_posted': len(C), 'county_report': False,
             'source': 'Georgia Secretary of State absentee voter file (accepted ballots with a return date), compiled by Georgia Votes',
             'source_url': 'https://georgiavotes.com/county'}]
for c in sorted(C, key=lambda c: c['county']):
    counties.append({'county': c['county'], 'in_person': c['in_person'], 'mail': c['mail'], 'total': c['total'], 'turnout_pct': c['reg_pct'],
                     'as_of': lastd, 'day': last_day, 'posted_day': True, 'county_report': False})
hist = []
hist_path = os.path.join(os.path.dirname(raw), 'history_2024.json')
for k in range(1, 19):
    d26 = D0 + dt.timedelta(days=k); s = 0; ok = True
    for c in C:
        t = at(c, d26, 'cmp')
        if t is None: ok = False; continue
        s += t
        hist.append({'year': 2022, 'day': k, 'date': (H0 + dt.timedelta(days=k)).isoformat(), 'county': c['county'], 'registered': None, 'in_person': None, 'mail': None, 'total': t})
    if ok: hist.append({'year': 2022, 'day': k, 'date': (H0 + dt.timedelta(days=k)).isoformat(), 'county': 'STATEWIDE', 'registered': None, 'in_person': None, 'mail': None, 'total': s})
if os.path.exists(hist_path): hist += json.load(open(hist_path))
os.makedirs(outdir, exist_ok=True)
for n, v in [('ga_ev_counties', counties), ('ga_ev_days', days), ('ga_ev_county_days', cd), ('ga_ev_history', hist)]:
    json.dump(v, open(os.path.join(outdir, n + '.json'), 'w'), separators=(',', ':'))
print('days', last_day, 'latest', lastd, 'statewide', counties[0]['total'], 'hist rows', len(hist), 'cd rows', len(cd))
for d in days: print(d['day'], d['date'], d['total'], next((h['total'] for h in hist if h['year']==2022 and h['day']==d['day'] and h['county']=='STATEWIDE'), None))
