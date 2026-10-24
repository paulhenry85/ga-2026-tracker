"""Fill Georgia 2026 Tracker race results from the Georgia Secretary of State's results export.

Usage: python3 build_results.py EXPORT.json CUR_DIR OUT_DIR [calls.json]
  EXPORT.json  https://results.sos.ga.gov/cdn/results/Georgia/export-11032026GeneralAndSpecialElection.json
  CUR_DIR      holds the current statewide.json, senate.json and house.json from the dashboard
  OUT_DIR      gets the updated statewide.json, senate.json and house.json
  calls.json   optional: {"<race or district>": {"winner": "D"|"R", "called_by": "AP"}} for races a
               news desk has called; a call already stored in CUR_DIR is kept.
Each row is matched to the export by its ballot_id. Vote totals and percentages come only from the export.
reporting = precincts fully reporting as a percent of precincts participating for that contest.
"""
import json, os, sys, datetime as dt

exp, cur, out = sys.argv[1], sys.argv[2], sys.argv[3]
calls = json.load(open(sys.argv[4])) if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else {}
d = json.load(open(exp))
items = {b['id']: b for b in d['results']['ballotItems']}
as_of = d.get('createdAt') or dt.datetime.now(dt.timezone.utc).isoformat()
os.makedirs(out, exist_ok=True)
summary = []
for f, key in (('statewide', 'race'), ('senate', 'district'), ('house', 'district')):
    rows = json.load(open(os.path.join(cur, f + '.json')))
    for r in rows:
        b = items.get(r.get('ballot_id'))
        if not b:
            summary.append(f'no ballot item for {r[key]}')
            continue
        dv = sum(o.get('voteCount') or 0 for o in b['ballotOptions'] if o.get('politicalParty') == 'Dem')
        rv = sum(o.get('voteCount') or 0 for o in b['ballotOptions'] if o.get('politicalParty') == 'Rep')
        ov = sum(o.get('voteCount') or 0 for o in b['ballotOptions'] if o.get('politicalParty') not in ('Dem', 'Rep'))
        tot = dv + rv + ov
        part, rep = b.get('precinctsParticipating'), b.get('precinctsReporting')
        r['as_of'] = as_of
        if not tot:
            continue  # nothing counted yet: leave the row as it is
        r.update(dem_votes=dv, rep_votes=rv, other_votes=ov,
                 dem_pct=round(100 * dv / tot, 1), rep_pct=round(100 * rv / tot, 1),
                 reporting=round(100 * rep / part, 1) if part else None)
        r['margin'] = round(r['dem_pct'] - r['rep_pct'], 1)
        r['leader'] = 'D' if dv > rv else 'R' if rv > dv else None
        c = calls.get(r[key])
        if c and c.get('winner') in ('D', 'R'):
            r.update(status='Called', winner=c['winner'], leader=c['winner'], called_by=c.get('called_by') or 'AP')
        elif r.get('status') == 'Called' and r.get('winner'):
            r['leader'] = r['winner']  # keep an earlier call
        elif r.get('contested') is False:
            r.update(status='Called', winner=r['leader'], called_by='Uncontested')
        else:
            r['status'] = 'Counting'
    json.dump(rows, open(os.path.join(out, f + '.json'), 'w'))
    n = sum(1 for r in rows if r.get('dem_votes') is not None)
    summary.append(f"{f}: {n} of {len(rows)} with votes, {sum(1 for r in rows if r.get('status') == 'Called')} called")
print('; '.join(summary))
