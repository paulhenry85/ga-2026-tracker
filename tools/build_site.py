"""Wrap the tracker page (page.html, the same page the Claude dashboard shows) into a standalone
index.html that loads its numbers from data/*.json. Run: python3 tools/build_site.py"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
page = (ROOT / "page.html").read_text()

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Georgia 2026 Tracker</title>
<meta name="robots" content="noindex, nofollow">
<style>
:root {
  --font-anthropic-sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-anthropic-serif: Georgia, "Times New Roman", serif;
  --color-fg: #1B2430; --color-fg-muted: #5D6673; --color-bg: #F7F5F0; --color-panel: #FFFFFF;
  --color-border-line: #E2DED5; --color-ok: #2E7D4F; --color-warn: #B26B00; --color-bad: #B3261E;
  --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 12px; --cds-gap-lg: 20px;
  --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 16px; --cds-pad-xl: 24px;
  --cds-radius: 8px; --cds-dur-slow: 300ms; --cds-font-weight-medium: 500;
  --cds-font-size-caption: 12px; --cds-font-size-body: 14px; --cds-font-size-heading: 18px; --cds-font-size-title: 24px;
}
[hidden] { display: none !important; }
html, body { margin: 0; background: #0A0F24; color: #E8ECFF; font-family: var(--font-anthropic-sans); }
#dash-root { max-width: 1280px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
.site-updated { max-width: 1280px; margin: 0 auto; padding: 8px 16px 24px; font-size: 12px; color: #9AA6C8; box-sizing: border-box; }
</style>
<script src="vendor/d3.min.js"></script>
<script>
// Minimal stand-in for the Claude dashboard runtime: the page calls dash.data(id), dash.onData(fn),
// dash.calc(id, {inputs, fn}) and dash.setLink(name). Data comes from data/<id>.json.
(function () {
  const IDS = ['statewide', 'senate', 'house', 'chambers', 'ga_ev_counties', 'ga_ev_days', 'ga_ev_county_days', 'ga_ev_history'];
  const store = {}; const calcs = {}; const subs = [];
  IDS.forEach((id) => { store[id] = { status: 'loading', data: [] }; });
  const fire = () => subs.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
  const rows = (v) => (Array.isArray(v) ? v : (v && (v.rows || v.data || v.results)) || []);
  window.dash = {
    data(id) {
      if (calcs[id]) {
        const c = calcs[id];
        if (!c.inputs.every((i) => store[i] && store[i].status === 'ok')) return { status: 'loading', data: [] };
        try { return { status: 'ok', data: c.fn(...c.inputs.map((i) => store[i].data)) }; } catch (e) { return { status: 'error', data: [], message: String(e) }; }
      }
      return store[id] || { status: 'missing', data: [] };
    },
    onData(fn) { subs.push(fn); try { fn(); } catch (e) { console.error(e); } },
    calc(id, spec) { calcs[id] = spec; },
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
    colors: ['#1F5FBF', '#C0352B', '#8C5A2B', '#5D6673', '#2E7D4F', '#7A4FB3', '#B26B00', '#011936'],
    refresh() {}, params() { return {}; }, setParams() {}, resetParams() {},
  };
  const bust = '?t=' + Math.floor(Date.now() / 60000);
  Promise.all(IDS.map((id) => fetch('data/' + id + '.json' + bust).then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((j) => { store[id] = { status: 'ok', data: rows(j) }; })
    .catch((e) => { store[id] = { status: 'error', data: [], message: String(e) }; })))
    .then(fire);
  let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(fire, 150); });
  fetch('data/updated.json' + bust).then((r) => r.json()).then((u) => {
    const el = document.querySelector('.site-updated'); if (el && u && u.at) el.textContent = 'Data last synced ' + new Date(u.at).toLocaleString('en-US', { timeZone: 'America/New_York', dateStyle: 'medium', timeStyle: 'short' }) + ' ET';
  }).catch(() => {});
})();
</script>
</head>
<body>
<div id="dash-root">
"""
TAIL = """
</div>
<div class="site-updated"></div>
</body>
</html>
"""
(ROOT / "index.html").write_text(HEAD + page + TAIL)
print("wrote index.html")
