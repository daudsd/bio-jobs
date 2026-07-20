#!/usr/bin/env python3
"""
Daily job scraper for Zarqa Chaudhary — finn.no + arbeidsplassen.nav.no
Jobs are stored in seen_jobs.json. HTML is built from that file.
"""

import urllib.request, re, json, os, time
from urllib.parse import quote
from datetime import date

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

JOBS_FILE = os.path.join(os.path.dirname(__file__), 'seen_jobs.json')
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
    html = fetch('https://www.finn.no/job/fulltime/search.html?q=' + quote(query))
    jobs = []
    for finnkode, body in re.findall(r'<article[^>]*id="card-(\d+)"[^>]*>(.*?)</article>', html, re.DOTALL):
        text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body)).strip()
        jobs.append({'id': finnkode, 'text': text[:300],
                     'url': f'https://www.finn.no/job/fulltime/ad.html?finnkode={finnkode}',
                     'source': 'finn.no'})
    return jobs

def scrape_nav(query):
    html = fetch('https://arbeidsplassen.nav.no/stillinger?q=' + quote(query))
    jobs = []
    for uuid, body in re.findall(r'href="/stillinger/stilling/([a-f0-9\-]{36})"[^>]*>(.*?)</a>', html, re.DOTALL):
        text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body)).strip()
        if text:
            jobs.append({'id': uuid, 'text': text[:300],
                         'url': f'https://arbeidsplassen.nav.no/stillinger/stilling/{uuid}',
                         'source': 'nav.no'})
    return jobs

# ── Filtering & categorisation ────────────────────────────────────────────────

def is_relevant(text):
    t = text.lower()
    return not any(kw in t for kw in IRRELEVANT_KEYWORDS)

def categorize(text):
    t = text.lower()
    if any(k in t for k in ['food', 'mat', 'næringsmiddel', 'meieri', 'dairy', 'røros']):
        return 'food'
    if any(k in t for k in ['pharma', 'legemiddel', 'gmp', 'steril', 'agilera', 'curida', 'halden']):
        return 'pharma'
    if any(k in t for k in ['biotek', 'enzym', 'arctic', 'qrill', 'epax', 'denomega', 'omega']):
        return 'biotech'
    return 'research'

# ── JSON store ────────────────────────────────────────────────────────────────

def load_jobs():
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE) as f:
            return json.load(f)  # list of job dicts
    return []

def save_jobs(jobs):
    with open(JOBS_FILE, 'w') as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

# ── HTML builder ──────────────────────────────────────────────────────────────

CARD = '''  <div class="card{cls}" data-cat="{cat}" data-date="{added}">
    <h3>{num}. {title} <span class="badge">{source}</span></h3>
    <div class="meta">📍 {source} &nbsp;|&nbsp; 🗓 {added}</div>
    <div class="summary">{summary}</div>
    <a href="{url}" target="_blank" rel="noopener noreferrer">View Job</a>
  </div>'''

HTML = '''<!DOCTYPE html>
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
    .sep {{ width: 1px; background: #ddd; margin: 0 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.2rem; padding: 1.5rem 2rem; max-width: 1200px; margin: 0 auto; }}
    .card {{ background: white; border-radius: 10px; padding: 1.2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #0d3b6e;
            display: flex; flex-direction: column; gap: 0.5rem; }}
    .card.best {{ border-left-color: #27ae60; }}
    .card h3 {{ font-size: 1rem; color: #0d3b6e; }}
    .card .meta {{ font-size: 0.82rem; color: #555; }}
    .card .summary {{ font-size: 0.88rem; line-height: 1.5; flex: 1; }}
    .card a {{ display: inline-block; padding: 6px 14px; background: #0d3b6e;
              color: white; border-radius: 6px; text-decoration: none;
              font-size: 0.85rem; width: fit-content; margin-top: auto; }}
    .card a:hover {{ background: #1a5fa8; }}
  </style>
</head>
<body>
<header>
  <h1>🧪 Biotech & Lab Jobs in Norway</h1>
  <p>Zarqa Chaudhary — MSc Applied Biotechnology, University of Iceland &nbsp;|&nbsp; Updated: {date}</p>
</header>
<div class="filters">
  <button class="active" onclick="filter('all',this)">All ({total})</button>
  <button onclick="filter('pharma',this)">Pharma / QC</button>
  <button onclick="filter('food',this)">Food Industry</button>
  <button onclick="filter('biotech',this)">Biotech</button>
  <button onclick="filter('research',this)">Research</button>
  <span class="sep"></span>
  <button onclick="filterDate(0,this)">Today</button>
  <button onclick="filterDate(7,this)">This Week</button>
  <button onclick="filterDate(30,this)">This Month</button>
</div>
<div class="grid" id="grid">
{cards}
</div>
<footer style="text-align:center;padding:1.5rem;font-size:0.8rem;color:#888;border-top:1px solid #ddd;margin-top:1rem;">
  Auto-updated daily · finn.no &amp; arbeidsplassen.nav.no · {date}
</footer>
<script>
  let activeCat = 'all', activeDays = null;
  function applyFilters() {{
    const now = new Date();
    document.querySelectorAll('.card').forEach(card => {{
      const catOk = activeCat === 'all' || card.dataset.cat === activeCat;
      const dateOk = activeDays === null ||
        (now - new Date(card.dataset.date)) / 86400000 <= activeDays + 1;
      card.style.display = catOk && dateOk ? 'flex' : 'none';
    }});
  }}
  function filter(cat, btn) {{
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeCat = cat; activeDays = null; applyFilters();
  }}
  function filterDate(days, btn) {{
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeCat = 'all'; activeDays = days; applyFilters();
  }}
</script>
</body>
</html>'''

def build_html(jobs):
    cards = []
    for i, j in enumerate(jobs, 1):
        cls = ' best' if any(k in j['text'].lower() for k in ['omega-3', 'enzym', 'spray', 'lipid', 'food', 'mat']) else ''
        cards.append(CARD.format(
            cls=cls, cat=j['category'], added=j['added'], num=i,
            title=j['title'], source=j['source'],
            summary=j['text'][:180], url=j['url']
        ))
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(HTML.format(date=TODAY, total=len(jobs), cards='\n'.join(cards)))
    print(f'jobs.html built with {len(jobs)} jobs.')

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    jobs = load_jobs()
    known_ids = {j['id'] for j in jobs}
    new_count = 0

    for query in FINN_QUERIES:
        for j in scrape_finn(query):
            if j['id'] not in known_ids and is_relevant(j['text']):
                jobs.append({
                    'id': j['id'], 'title': j['text'][:80].strip(),
                    'text': j['text'], 'url': j['url'],
                    'source': j['source'], 'category': categorize(j['text']),
                    'added': TODAY,
                })
                known_ids.add(j['id'])
                new_count += 1
        time.sleep(0.5)

    for query in NAV_QUERIES:
        for j in scrape_nav(query):
            if j['id'] not in known_ids and is_relevant(j['text']):
                jobs.append({
                    'id': j['id'], 'title': j['text'][:80].strip(),
                    'text': j['text'], 'url': j['url'],
                    'source': j['source'], 'category': categorize(j['text']),
                    'added': TODAY,
                })
                known_ids.add(j['id'])
                new_count += 1
        time.sleep(0.5)

    print(f'New jobs: {new_count} | Total: {len(jobs)}')
    jobs.sort(key=lambda j: j['added'], reverse=True)
    save_jobs(jobs)
    build_html(jobs)

if __name__ == '__main__':
    main()
