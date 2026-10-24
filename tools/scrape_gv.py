"""Pull county early vote totals from georgiavotes.com (built from the GA SOS absentee file).
Totals only. Writes gv_raw.json: {updated, max_vote_day, counties:[{county, total, mail, in_person, reg_pct, rows:[{dt,cur,cmp}]}]}"""
import json, re, sys, time, urllib.request, concurrent.futures as cf
OUT = sys.argv[1] if len(sys.argv) > 1 else 'gv_raw.json'
def get(u):
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u), timeout=40) as r: return r.read().decode('utf-8')
        except Exception as e:
            err = e; time.sleep(2 + a * 3)
    raise err
def payload(t):
    s = ''
    for c in re.findall(r'self\.__next_f\.push\((\[.*?\])\)</script>', t, re.S):
        j = json.loads(c)
        if len(j) > 1 and isinstance(j[1], str): s += j[1]
    return s
def num(x): return int(x.replace(',', ''))
def one(i):
    t = get(f'https://georgiavotes.com/county?c={i}')
    s = payload(t)
    txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<script.*?</script>|<style.*?</style>', '', t)))
    m = re.search(r'([\d,]+) people in (.+?) County have voted early in the 2026 general election , ([\d.]+)% of the county', txt)
    m2 = re.search(r'([\d,]+) voted by mail and ([\d,]+) early in person', txt)
    k = s.find('"rows":[')
    rows = json.loads(s[k + 7: s.find(']', k) + 1]) if k >= 0 else []
    mv = re.search(r'"maxVoteDay":"([\d-]+)"', s)
    up = re.search(r'Last updated ([\d-]+ [\d:]+)', txt)
    if not m:
        return {'c': i, 'error': 'no summary', 'name': re.search(r'Choose a Co.{0,5}', txt) and None}
    return {'c': i, 'county': m.group(2), 'total': num(m.group(1)), 'reg_pct': float(m.group(3)),
            'mail': num(m2.group(1)) if m2 else None, 'in_person': num(m2.group(2)) if m2 else None,
            'rows': [{'dt': r['dt'], 'cur': r['cur'], 'cmp': r['cmp']} for r in rows],
            'max_vote_day': mv.group(1) if mv else None, 'updated': up.group(1) if up else None}
with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(one, range(1, 160)))
bad = [r for r in res if 'error' in r]
ok = [r for r in res if 'error' not in r]
json.dump({'updated': ok[0]['updated'] if ok else None, 'max_vote_day': ok[0]['max_vote_day'] if ok else None, 'counties': ok, 'errors': bad}, open(OUT, 'w'))
print(len(ok), 'counties;', len(bad), 'errors', bad[:3], 'updated', ok[0]['updated'] if ok else None)
