#!/usr/bin/env python3
"""
Daily job scraper for Zarqa Chaudhary — finn.no + arbeidsplassen.nav.no
Scrapes new biotech/lab jobs in Norway and rebuilds jobs.html automatically.
Run manually: python3 scrape.py
Runs automatically: via GitHub Actions every day at 07:00 UTC
"""

import urllib.request, re, json, os, time
from urllib.parse import quote
from datetime import date

# ── Config ────────────────────────────────────────────────────────────────────

FINN_QUERIES = [
    'laboratorium bioteknologi', 'QC analytiker', 'GMP laboratorium',
    'analytisk kjemi laboratorium', 'næringsmiddel laboratorium',
    'laboratorieingeniør', 'bioteknologi industri', 'food science norway',
    'prosessingeniør pharma', 'enzym laboratorium', 'omega-3 produksjon',
    'SINTEF laboratorium', 'Sterility Assurance', 'pesticidanalyser',
    'Curida', 'HP Halden Pharma', 'ArcticZymes', 'Agilera Pharma',
    'NIVA laboratorium', 'Fagansvarlig biologiske', 'QRILL', 'Epax', 'Denomega',
]

NAV_QUERIES = [
    'bioteknologi laboratorium', 'QC analytiker', 'GMP laboratorium',
    'analytisk kjemi', 'næringsmiddel laboratorium', 'laboratorieingeniør',
    'spray drying', 'frysetørking', 'omega-3', 'marin bioteknologi',
]

IRRELEVANT_KEYWORDS = [
    'phd', 'doktorgrad', 'professor', 'førsteamanuensis', 'universitetslektor',
    'stipendiat', 'captain', 'skipper', 'renholder', 'sjåfør', 'driver',
    'butikk', 'retail', 'salg', 'sales', 'marketing', 'kommunikasjon',
    'økonomi', 'regnskap', 'jus', 'advokat', 'psykolog', 'sykepleier',
    'lege', 'tannlege', 'barnehage', 'lærer', 'rektor', 'kokk', 'restaurant',
    'offshore vessel', 'marine superintendent', 'eksplosiv', 'sprengstoff',
    'administrativ koordinator', 'administrative coordinator',
    'ukraina', 'batterigjenvinning', 'avløpsrensing', 'biogass',
    'faghandel', 'xrf', 'geologisk',
]

SEEN_FILE = os.path.join(os.path.dirname(__file__), 'seen_jobs.json')
HTML_FILE = os.path.join(os.path.dirname(__file__), 'jobs.html')
TODAY = str(date.today())

# ── Scrapers ──────────────────────────────────────────────────────────────────

def fetch(url, retries=3):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if i == retries - 1:
                print(f'  FETCH ERROR {url[:60]}: {e}')
                return ''
            time.sleep(2)
    return ''

def scrape_finn(query):
    url = 'https://www.finn.no/job/fulltime/search.html?q=' + quote(query)
    html = fetch(url)
    jobs = []
    for finnkode, body in re.findall(r'<article[^>]*id="card-(\d+)"[^>]*>(.*?)</article>', html, re.DOTALL):
        text = re.sub(r'<[^>]+>', ' ', body)
        text = re.sub(r'\s+', ' ', text).strip()
        jobs.append({
            'id': finnkode,
            'text': text[:300],
            'url': f'https://www.finn.no/job/fulltime/ad.html?finnkode={finnkode}',
            'source': 'finn.no',
        })
    return jobs

def scrape_nav(query):
    url = 'https://arbeidsplassen.nav.no/stillinger?q=' + quote(query)
    html = fetch(url)
    jobs = []
    for uuid, body in re.findall(r'href="/stillinger/stilling/([a-f0-9\-]{36})"[^>]*>(.*?)</a>', html, re.DOTALL):
        text = re.sub(r'<[^>]+>', ' ', body)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            jobs.append({
                'id': uuid,
                'text': text[:300],
                'url': f'https://arbeidsplassen.nav.no/stillinger/stilling/{uuid}',
                'source': 'nav.no',
            })
    return jobs

# ── Filtering ─────────────────────────────────────────────────────────────────

def is_relevant(job):
    text_lower = job['text'].lower()
    for kw in IRRELEVANT_KEYWORDS:
        if kw in text_lower:
            return False
    return True

def categorize(text):
    t = text.lower()
    if any(k in t for k in ['food', 'mat', 'næringsmiddel', 'meieri', 'dairy', 'salsus', 'nortura', 'røros']):
        return 'food'
    if any(k in t for k in ['pharma', 'legemiddel', 'gmp', 'steril', 'radioaktiv', 'agilera', 'curida', 'halden']):
        return 'pharma'
    if any(k in t for k in ['biotek', 'enzym', 'arctic', 'qrill', 'epax', 'denomega', 'omega']):
        return 'biotech'
    return 'research'

# ── HTML generation ───────────────────────────────────────────────────────────

CARD_TEMPLATE = '''  <div class="card{cls}" data-cat="{cat}" data-date="{added}">
    <h3>{num}. {title} <span class="badge">{badge}</span></h3>
    <div class="meta">📍 {meta} &nbsp;|&nbsp; 🗓 Added: {added}</div>
    <div class="summary">{summary}</div>
    <div class="relevant">{relevant}</div>
    <a href="{url}" target="_blank" rel="noopener noreferrer">View Job</a>
  </div>'''

HTML_SHELL = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Biotech & Lab Jobs in Norway — Zarqa Chaudhary</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f9; color: #222; }}
    header {{ background: #0d3b6e; color: white; padding: 2rem; text-align: center; }}
    header h1 {{ font-size: 1.8rem; margin-bottom: 0.4rem; }}
    header p {{ font-size: 0.95rem; opacity: 0.85; }}
    .badge {{ display: inline-block; background: #f0a500; color: #000;
             font-size: 0.75rem; font-weight: bold; padding: 2px 8px;
             border-radius: 12px; margin-left: 6px; vertical-align: middle; }}
    .filters {{ display: flex; gap: 0.6rem; flex-wrap: wrap;
               padding: 1.2rem 2rem; background: #fff; border-bottom: 1px solid #ddd; }}
    .filters button {{ padding: 6px 14px; border: 1px solid #0d3b6e; border-radius: 20px;
                      background: white; color: #0d3b6e; cursor: pointer; font-size: 0.85rem; }}
    .filters button.active, .filters button:hover {{ background: #0d3b6e; color: white; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.2rem; padding: 1.5rem 2rem; max-width: 1200px; margin: 0 auto; }}
    .card {{ background: white; border-radius: 10px; padding: 1.2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #0d3b6e;
            display: flex; flex-direction: column; gap: 0.5rem; }}
    .card.best {{ border-left-color: #27ae60; }}
    .card.warn {{ border-left-color: #e67e22; }}
    .card h3 {{ font-size: 1rem; color: #0d3b6e; }}
    .card .meta {{ font-size: 0.82rem; color: #555; }}
    .card .summary {{ font-size: 0.88rem; line-height: 1.5; }}
    .card .relevant {{ font-size: 0.82rem; color: #27ae60; font-style: italic; }}
    .card a {{ margin-top: auto; display: inline-block; padding: 6px 14px;
              background: #0d3b6e; color: white; border-radius: 6px;
              text-decoration: none; font-size: 0.85rem; width: fit-content; }}
    .card a:hover {{ background: #1a5fa8; }}
  </style>
</head>
<body>
<header>
  <h1>🧪 Biotech & Lab Jobs in Norway</h1>
  <p>Zarqa Chaudhary — MSc Applied Biotechnology, University of Iceland &nbsp;|&nbsp; Last updated: {date}</p>
</header>
<div class="filters">
  <button class="active" onclick="filter('all', this)">All ({total})</button>
  <button onclick="filter('pharma', this)">Pharma / QC</button>
  <button onclick="filter('food', this)">Food Industry</button>
  <button onclick="filter('biotech', this)">Biotech</button>
  <button onclick="filter('research', this)">Research</button>
  <span style="width:1px;background:#ddd;margin:0 4px;"></span>
  <button onclick="filterDate(0, this)">Today</button>
  <button onclick="filterDate(7, this)">This Week</button>
  <button onclick="filterDate(30, this)">This Month</button>
</div>
<div class="grid" id="grid">
{cards}
</div>
<footer style="text-align:center;padding:1.5rem;font-size:0.8rem;color:#888;border-top:1px solid #ddd;margin-top:1rem;">
  Auto-updated daily from finn.no &amp; arbeidsplassen.nav.no &nbsp;|&nbsp; {date}
</footer>
<script>
  let activeCat = 'all', activeDays = null;
  function applyFilters() {{
    const now = new Date();
    document.querySelectorAll('.card').forEach(card => {{
      const catOk = activeCat === 'all' || card.dataset.cat === activeCat;
      let dateOk = true;
      if (activeDays !== null) {{
        const added = new Date(card.dataset.date);
        dateOk = (now - added) / 86400000 <= activeDays + 1;
      }}
      card.style.display = (catOk && dateOk) ? 'flex' : 'none';
    }});
  }}
  function filter(cat, btn) {{
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeCat = cat; activeDays = null;
    applyFilters();
  }}
  function filterDate(days, btn) {{
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeCat = 'all'; activeDays = days;
    applyFilters();
  }}
</script>
</body>
</html>'''

def build_card(num, job):
    text = job['text']
    cat = categorize(text)
    title = text[:60].strip().rstrip(',').strip()
    badge = job['source']
    meta = f"Source: {job['source']}"
    summary = text[:180].strip()
    relevant = '✅ Matched by automated search — verify relevance'
    cls = ' best' if any(k in text.lower() for k in ['omega-3', 'enzym', 'spray', 'lipid', 'food', 'mat']) else ''
    added = job.get('added', TODAY)
    return CARD_TEMPLATE.format(
        cls=cls, cat=cat, num=num, title=title, badge=badge,
        meta=meta, summary=summary, relevant=relevant, url=job['url'], added=added
    )

# ── Main ──────────────────────────────────────────────────────────────────────

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            data = json.load(f)
            # support both old list format and new dict format
            if isinstance(data, list):
                return {k: '2026-07-01' for k in data}
            return data
    return {}

def save_seen(seen):
    with open(SEEN_FILE, 'w') as f:
        json.dump(seen, f, indent=2)

def main():
    seen = load_seen()  # {id: date_string}
    all_jobs = []
    seen_this_run = {}

    print(f'Scraping finn.no ({len(FINN_QUERIES)} queries)...')
    for q in FINN_QUERIES:
        jobs = scrape_finn(q)
        for j in jobs:
            if j['id'] not in seen_this_run and is_relevant(j):
                j['added'] = seen.get(j['id'], TODAY)
                seen_this_run[j['id']] = j['added']
                all_jobs.append(j)
        print(f'  [{q}] -> {len(jobs)} results')
        time.sleep(0.5)

    print(f'\nScraping nav.no ({len(NAV_QUERIES)} queries)...')
    for q in NAV_QUERIES:
        jobs = scrape_nav(q)
        for j in jobs:
            if j['id'] not in seen_this_run and is_relevant(j):
                j['added'] = seen.get(j['id'], TODAY)
                seen_this_run[j['id']] = j['added']
                all_jobs.append(j)
        print(f'  [{q}] -> {len(jobs)} results')
        time.sleep(0.5)

    new_count = sum(1 for jid in seen_this_run if jid not in seen)
    print(f'\nTotal jobs found: {len(all_jobs)} ({new_count} new)')

    seen.update(seen_this_run)
    save_seen(seen)

    # sort: newest first
    all_jobs.sort(key=lambda j: j['added'], reverse=True)

    cards = '\n'.join(build_card(i + 1, j) for i, j in enumerate(all_jobs))
    html = HTML_SHELL.format(date=TODAY, total=len(all_jobs), cards=cards)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'jobs.html rebuilt with {len(all_jobs)} jobs.')

if __name__ == '__main__':
    main()
