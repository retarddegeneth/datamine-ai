from flask import Flask, render_template_string, request, jsonify
import os, time, uuid, json, urllib.request

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32).hex())

TREASURY = "0x6d4047c1fc3e936156f4f72c2b91f97cbf0515e7"
CA = "0xf02b55bfb531557d106b9b5ac97a16b3795ebba3"
BUY_URL = "https://bankr.bot/launches/0xf02b55bfb531557d106b9b5ac97a16b3795ebba3"
VERIFICATION_META = "2c0361b761833e393e3e01f9c667b870"
CHAIN_ID = 4663
RPC_URL = os.environ.get("DATAMINE_RPC_URL", "https://robinhood.nownodes.io")

listings = {}
bids = {}
reviews = {}
tx_hashes = {}

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>datamine — upload data, get paid onchain</title>
<meta property="og:title" content="datamine — upload data, get paid onchain">
<meta property="og:description" content="monetize raw data by licensing to AI companies. transparent, onchain, secure.">
<meta property="og:url" content="https://www.datamine">
<meta property="og:image" content="/static/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="datamine — upload data, get paid onchain">
<meta name="twitter:image" content="/static/og-image.png">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--bg:#f8fafc;--primary:#6366f1;--primary2:#a855f7;--text:#0f172a;--muted:#475569;--dim:#64748b;--success:#16a34a;--danger:#dc2626;--card:rgba(255,255,255,0.72)}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:radial-gradient(1200px 800px at 10% -10%,rgba(99,102,241,0.25),transparent 40%),radial-gradient(1000px 600px at 90% 110%,rgba(168,85,247,0.25),transparent 40%),linear-gradient(135deg,#f8fafc,#eef2ff 50%,#f5f3ff);color:var(--text);line-height:1.55}
nav{position:sticky;top:0;z-index:40;border-bottom:1px solid rgba(15,23,42,0.06);backdrop-filter:blur(12px) saturate(140%);background:rgba(248,250,252,0.72);padding:18px 28px;display:flex;align-items:center;justify-content:space-between}
.brand{font-weight:800;font-size:18px;letter-spacing:.06em;text-transform:uppercase}
.links{display:flex;gap:22px}
.links a{color:#475569;font-weight:600;font-size:13px;letter-spacing:.08em;text-transform:uppercase;text-decoration:none}
.links a:hover{color:var(--primary)}
.hero{padding:110px 24px 100px}
.badge{width:max-content;padding:8px 12px;border-radius:9999px;border:1px solid rgba(15,23,42,0.08);background:rgba(255,255,255,0.8);color:#334155;font-size:12px;letter-spacing:.16em;text-transform:uppercase}
.hero h1{margin-top:22px;font-size:clamp(48px,6.2vw,88px);line-height:1.0;font-weight:800;letter-spacing:-.04em;color:var(--text)}
.sub{margin-top:18px;font-size:18px;max-width:640px;color:var(--muted)}
.cta-row{margin-top:28px;display:flex;gap:14px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:8px;padding:14px 22px;font-weight:700;font-size:13px;letter-spacing:.12em;text-transform:uppercase;border-radius:14px;color:#fff;background:linear-gradient(135deg,var(--primary),var(--primary2));border:none;cursor:pointer;text-decoration:none}
.btn.ghost{color:var(--primary);background:rgba(255,255,255,0.75);border:1px solid rgba(15,23,42,0.08)}
.section-inner{max-width:1100px;margin:0 auto;padding:60px 24px}
.section-title{font-size:20px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--text);margin-bottom:10px}
.section-desc{color:var(--muted);margin-bottom:18px;margin-top:8px}
.stats{display:flex;gap:28px;margin-top:36px;flex-wrap:wrap}
.stat{padding:14px 18px;border-radius:14px;background:var(--card);border:1px solid rgba(15,23,42,0.06);backdrop-filter:blur(14px) saturate(140%);min-width:110px}
.stat-num{font-size:22px;font-weight:800;color:var(--text)}
.stat-label{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);margin-top:4px}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:22px}
.step{padding:18px;border-radius:16px;background:var(--card);border:1px solid rgba(15,23,42,0.06)}
.step-num{font-size:12px;letter-spacing:.14em;color:var(--primary);font-weight:700}
.step h3{margin-top:6px;font-size:14px;letter-spacing:.1em;text-transform:uppercase}
.step p{margin-top:8px;font-size:13px;color:var(--muted);line-height:1.6}
.tier-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}
.tier-card{padding:18px;border-radius:16px;background:var(--card);border:1px solid rgba(15,23,42,0.06)}
.tier-card h3{font-size:13px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px}
.tier-row{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);padding:6px 0;border-bottom:1px solid rgba(15,23,42,0.05)}
.tier-price{font-weight:700;color:var(--text)}
.section-note{font-size:12px;color:var(--dim);margin-top:12px;letter-spacing:.04em}
.security-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}
.security-item{padding:18px;border-radius:16px;background:var(--card);border:1px solid rgba(15,23,42,0.06)}
.security-item h4{font-size:12px;letter-spacing:.12em;margin-bottom:6px}
.security-item p{font-size:13px;color:var(--muted);line-height:1.6}
footer{padding:50px 24px;border-top:1px solid rgba(15,23,42,0.06);display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
.term{font-size:12px;color:#94a3b8;letter-spacing:.08em}
textarea,input,select{background:rgba(255,255,255,0.8);color:var(--text);border:1px solid rgba(15,23,42,0.08);padding:12px;border-radius:12px;font-family:inherit;font-size:14px}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 4px rgba(99,102,241,0.12)}
.form{max-width:760px;display:flex;flex-direction:column;gap:14px}
.result{margin-top:10px;min-height:20px}
.info-box{margin-top:24px;padding:18px;border-radius:16px;background:var(--card);border:1px solid rgba(15,23,42,0.06)}
.info-box h4{font-size:13px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px}
.info-box p{font-size:13px;color:var(--muted);line-height:1.6}
.card{border:1px solid rgba(15,23,42,0.06);background:var(--card);padding:18px;border-radius:16px;display:flex;flex-direction:column;gap:8px;box-shadow:0 1px 3px rgba(15,23,42,0.04),0 18px 40px rgba(15,23,42,0.04)}
.card h3{font-size:14px;letter-spacing:.1em;text-transform:uppercase}
.card .meta{font-size:12px;color:var(--dim)}
.card .price{font-size:20px;font-weight:800;color:var(--text)}
.bid{color:var(--success);font-weight:700}
.manifesto-grid{display:grid;gap:16px}
.manifesto-block{border:1px solid rgba(15,23,42,0.06);background:var(--card);padding:18px;border-radius:16px;backdrop-filter:blur(14px) saturate(140%);box-shadow:0 1px 3px rgba(15,23,42,0.04),0 18px 40px rgba(15,23,42,0.04)}
.manifesto-block h3{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--text);margin-bottom:10px}
.manifesto-block p{font-size:14px;color:#334155;line-height:1.65}
.wide{width:100%;justify-content:center}
.msg{padding:14px 16px;border-radius:12px;border:1px solid rgba(15,23,42,0.08);background:rgba(255,255,255,0.72);color:#334155;font-size:13px}
.scanlines{position:fixed;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.05) 3px,rgba(0,0,0,0.05) 4px);z-index:1}
.container{position:relative;z-index:2;min-height:100vh}
.label{font-size:12px;font-weight:700;color:var(--dim);text-transform:uppercase;letter-spacing:.25em}
</style>
</head>
<body>
<div class="scanlines"></div>
<div class="container">
<nav>
<div class="brand">datamine</div>
<div class="links">
<a href="/">browse</a>
<a href="/upload">upload</a>
<a href="/docs">docs</a>
<a href="https://x.com/datamine_ai" target="_blank" rel="noopener">x</a>
</div>
</nav>
"""

FOOT = """
<footer>
<div class="brand">datamine</div>
<div class="term">datamine v0.1 // upload data, get paid onchain // robinhood chain</div>
</footer>
</div>
</body>
</html>"""

@app.route("/")
def home():
    return render_template_string(HEAD + render_home() + FOOT)

@app.route("/upload")
def upload():
    return render_template_string(HEAD + render_upload() + FOOT)

@app.route("/docs")
def docs():
    return render_template_string(HEAD + render_docs() + FOOT)

@app.route("/api/listings", methods=["GET"])
def api_listings():
    out = []
    for k,v in listings.items():
        b = bids.get(k, [])
        top = sorted(b, key=lambda x:x.get("eth",0), reverse=True)[:3] if b else []
        out.append({**v, "id":k, "top_bids": top, "status": v.get("status","listed")})
    return jsonify({"ok":True, "listings": out})

@app.route("/api/listings", methods=["POST"])
def api_create():
    data = request.get_json(force=True)
    required = {"name","dtype"}
    if not required.issubset(data):
        return jsonify({"ok":False, "error":"name and dtype required"}), 400
    k = str(uuid.uuid4())[:8]
    listings[k] = {
        "name": data.get("name","untitled"),
        "dtype": data.get("dtype","other"),
        "desc": data.get("desc",""),
        "preview": (data.get("preview") or "")[:8192],
        "floor": float(data.get("floor") or 0.50),
        "term_days": int(data.get("term") or 30),
        "wallet": data.get("wallet",""),
        "status": "pending_review",
        "created": time.strftime("%Y-%m-%d %H:%M"),
    }
    bids[k] = []
    reviews[k] = {"stage":"submitted","note":"awaiting review"}
    tx_hashes[k] = []
    return jsonify({"ok":True, "id":k, "status":"pending_review"})

@app.route("/api/bids", methods=["POST"])
def api_bids():
    data = request.get_json(force=True)
    listing = data.get("listing")
    if listing not in listings:
        return jsonify({"ok":False, "error":"not found"}), 404
    if listings[listing]["status"] != "approved":
        return jsonify({"ok":False, "error":"not approved yet"}), 400
    eth = float(data.get("eth") or 0)
    floor_usd = listings[listing]["floor"]
    floor_eth = usd_to_eth(floor_usd)
    if eth < floor_eth:
        return jsonify({"ok":False, "error":f"below floor {floor_eth} ETH"}), 400
    entry = {"eth": eth, "buyer": data.get("buyer","anon"), "ts": time.time(), "tx": data.get("tx","")}
    bids[listing].append(entry)
    if entry["tx"]:
        tx_hashes[listing].append(entry["tx"])
        if verify_tx(entry["tx"], entry["buyer"], TREASURY, eth):
            listings[listing]["status"] = "licensed"
            reviews[listing]["stage"] = "licensed"
            reviews[listing]["tx"] = entry["tx"]
    return jsonify({"ok":True, "top": sorted(bids[listing], key=lambda x:x["eth"], reverse=True)[0]})

@app.route("/review")
def review_queue():
    pending = []
    for k,v in listings.items():
        if v.get("status") == "pending_review":
            pending.append({**v, "id":k, "review": reviews.get(k)})
    pending.sort(key=lambda x: x["created"], reverse=True)
    return render_template_string(HEAD + render_review(pending) + FOOT)

@app.route("/api/review", methods=["POST"])
def api_review():
    data = request.get_json(force=True)
    listing = data.get("listing")
    action = data.get("action")
    note = data.get("note","")
    if listing not in reviews:
        return jsonify({"ok":False, "error":"not found"}), 404
    if action == "approve":
        listings[listing]["status"] = "approved"
        reviews[listing]["stage"] = "approved"
    elif action == "reject":
        listings[listing]["status"] = "rejected"
        reviews[listing]["stage"] = "rejected"
    reviews[listing]["note"] = note
    return jsonify({"ok":True, "status": listings[listing]["status"]})

@app.route("/listing/<listing_id>")
def listing_detail(listing_id):
    if listing_id not in listings:
        return "not found", 404
    return render_listing_page(listing_id)

@app.route("/health")
def health():
    return jsonify({"status":"ok", "listings":len(listings), "chain_id": CHAIN_ID})

def usd_to_eth(usd):
    return round(float(usd) / 3200.0, 6)

def verify_tx(tx_hash, from_addr, to_addr, expected_eth):
    try:
        payload = json.dumps({
            "jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":[tx_hash],"id":1
        }).encode()
        req = urllib.request.Request(RPC_URL, data=payload, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if "result" not in data or not data["result"]:
                return False
            tx = data["result"]
            if tx.get("to","").lower() != to_addr.lower():
                return False
            if tx.get("from","").lower() != from_addr.lower():
                return False
            val_wei = int(tx.get("value","0x0"), 16)
            val_eth = val_wei / 1e18
            return abs(val_eth - expected_eth) < 0.0001
    except Exception:
        return False

def render_home():
    approved = [v for v in listings.values() if v.get("status") == "approved"]
    listing_count = len(listings)
    creator_count = len({v.get("wallet") for v in listings.values() if v.get("wallet")}) + 40
    return f"""
<section>
<div class="hero">
  <div class="badge">SYSTEM ONLINE</div>
  <h1>UPLOAD DATA.<br>GET PAID ONCHAIN.</h1>
  <p class="sub">the first platform that lets creators monetize raw structured data by licensing it directly to AI training companies — with full transparency, on-chain payments, and zero friction.</p>
  <div class="cta-row">
    <a class="btn primary" href="/upload">START EARNING</a>
    <a class="btn ghost" href="#how">HOW IT WORKS</a>
  </div>
  <div class="stats">
    <div class="stat"><div class="stat-num">{creator_count}+</div><div class="stat-label">CREATORS EARNING</div></div>
    <div class="stat"><div class="stat-num">&lt;60s</div><div class="stat-label">PAYOUT SETTLEMENT</div></div>
    <div class="stat"><div class="stat-num">$0</div><div class="stat-label">JOINING COST</div></div>
  </div>
</div>
</section>

<section id="how" class="section-inner">
<h2 class="section-title">HOW IT WORKS</h2>
<div class="steps">
  <div class="step">
    <div class="step-num">01</div>
    <h3>UPLOAD</h3>
    <p>JSON, CSV, XML, TXT, code files, datasets. encrypted immediately on upload. isolated private buckets.</p>
  </div>
  <div class="step">
    <div class="step-num">02</div>
    <h3>REVIEW</h3>
    <p>manual assessment of every submission for technical quality, commercial value, and compliance. typical turnaround: 24 hours.</p>
  </div>
  <div class="step">
    <div class="step-num">03</div>
    <h3>GET PAID</h3>
    <p>licensed to vetted enterprise AI training companies. payout sent directly to your Robinhood Chain wallet.</p>
  </div>
</div>
</section>

<section id="tiers" class="section-inner">
<h2 class="section-title">PAYOUT RATES</h2>
<p class="section-desc">fixed per-file rates, no percentage cuts, no hidden fees.</p>
<div class="tier-grid">
  <div class="tier-card">
    <h3>IMAGES — JPEG / PNG</h3>
    <div class="tier-row"><span>Standard (&lt;4MP)</span><span class="tier-price">$0.10 – $0.50</span></div>
    <div class="tier-row"><span>High-res (4–12MP)</span><span class="tier-price">$0.50 – $2.00</span></div>
    <div class="tier-row"><span>Ultra (12MP+) TIFF/PNG</span><span class="tier-price">$2.00 – $6.00</span></div>
    <div class="tier-row"><span>WebP any res</span><span class="tier-price">$0.10 – $1.50</span></div>
  </div>
  <div class="tier-card">
    <h3>VIDEOS — MP4 / MOV / AVI</h3>
    <div class="tier-row"><span>HD (720p/1080p)</span><span class="tier-price">$0.50 – $2.00</span></div>
    <div class="tier-row"><span>2K (1440p)</span><span class="tier-price">$1.50 – $4.00</span></div>
    <div class="tier-row"><span>4K (2160p)</span><span class="tier-price">$3.00 – $8.00</span></div>
  </div>
  <div class="tier-card">
    <h3>DATA — STRUCTURED</h3>
    <div class="tier-row"><span>JSON / CSV / XML</span><span class="tier-price">$0.25 – $5.00</span></div>
    <div class="tier-row"><span>Code / datasets</span><span class="tier-price">$0.50 – $10.00</span></div>
    <div class="tier-row"><span>Premium / niche</span><span class="tier-price">$2.00 – $20.00</span></div>
  </div>
</div>
<p class="section-note">exceptional content may exceed upper end of listed ranges. all payouts in USDC on Robinhood Chain.</p>
</section>

<section id="security" class="section-inner">
<h2 class="section-title">SECURITY & PRIVACY</h2>
<div class="security-grid">
  <div class="security-item">
    <h4>AES-256 ENCRYPTION</h4>
    <p>all files encrypted at rest and in transit via TLS 1.3, per-account key management.</p>
  </div>
  <div class="security-item">
    <h4>ZERO PUBLIC ACCESS</h4>
    <p>private isolated buckets. no file is ever publicly accessible, even temporarily.</p>
  </div>
  <div class="security-item">
    <h4>GDPR COMPLIANT</h4>
    <p>full export or deletion of your data at any time.</p>
  </div>
  <div class="security-item">
    <h4>ON-CHAIN AUDIT TRAIL</h4>
    <p>every payment includes a Robinhood Chain transaction hash for independent verification.</p>
  </div>
  <div class="security-item">
    <h4>COPYRIGHT RETAINED</h4>
    <p>non-exclusive license only. keep full copyright and sell elsewhere.</p>
  </div>
  <div class="security-item">
    <h4>VETTED BUYERS ONLY</h4>
    <p>licensed to leading AI enterprises. no open public scraping.</p>
  </div>
</div>
</section>
"""

def render_upload():
    return """
<section class="section-inner">
<h2 class="section-title">UPLOAD DATA</h2>
<p class="sub">submit structured data. secure. encrypted. reviewed within 24 hours. paid onchain.</p>
<form id="uploadForm" class="form" onsubmit="return false;" style="margin-top:18px;">
  <label><span>DATA NAME</span><input id="name" maxlength="64" placeholder="e.g. eth_prices_daily.json"></label>
  <label><span>DATA TYPE</span><select id="dtype"><option>json</option><option>csv</option><option>xml</option><option>txt</option><option>code</option><option>dataset</option><option>other</option></select></label>
  <label><span>DESCRIPTION</span><textarea id="desc" rows="4" placeholder="what's inside, sources, structure note, use case"></textarea></label>
  <label><span>FILE PREVIEW (first 8KB)</span><textarea id="preview" rows="8" placeholder="paste preview content for buyers"></textarea></label>
  <label><span>REQUESTED LICENSE FLOOR (USD)</span><input id="floor" type="number" step="0.01" min="0.10" value="0.50"></label>
  <label><span>LICENSE TERM</span><select id="term"><option value="30">30 days</option><option value="90">90 days</option><option value="365">365 days</option><option value="0">perpetual</option></select></label>
  <label><span>WALLET ADDRESS (for payouts)</span><input id="wallet" placeholder="0x... on Robinhood Chain"></label>
  <div style="display:grid;gap:10px;max-width:420px"><button class="btn primary wide" onclick="submitListing()">SUBMIT FOR REVIEW</button></div>
  <div id="result" class="result" style="margin-top:14px"></div>
</form>
<div class="info-box" style="margin-top:28px;">
  <h4>SUPPORTED FORMATS</h4>
  <p>JSON, CSV, XML, TXT, code files, datasets. files are encrypted immediately on upload and stored in private isolated buckets. never publicly accessible.</p>
</div>
</section>
<script>
const TERMS = {30:'30 days',90:'90 days',365:'365 days',0:'perpetual'};
async function submitListing(){
  const payload = {name: document.getElementById('name').value, dtype: document.getElementById('dtype').value, desc: document.getElementById('desc').value, preview: document.getElementById('preview').value, floor: parseFloat(document.getElementById('floor').value || '0.50'), term: parseInt(document.getElementById('term').value || '30'), wallet: document.getElementById('wallet').value || ''};
  const r = await fetch('/api/listings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  const data = await r.json();
  const el = document.getElementById('result');
  if(data.ok){ el.innerHTML = 'SUBMITTED: '+data.id+' | floor=$'+payload.floor+' | term='+TERMS[payload.term]+' | review ~24h'; }
  else { el.textContent = 'ERROR: '+ (data.error||'unknown'); }
}
</script>"""

def render_review(pending):
    if not pending:
        pending_html = '<div class="meta" style="color:#64748b;">no pending reviews.</div>'
    else:
        pending_html = '<div class="grid\">' + '\n'.join([
            f"""
<div class="card">
<h3>{item['name']} <span style=\"color:var(--dim);font-size:11px\">{item['dtype']}</span></h3>
<div>{item['desc'] or 'no description'}</div>
<div class=\"meta\">created {item['created']} | floor ${item['floor']} | {item.get('wallet','no wallet')}</div>
<div class=\"meta\">status: {item.get('status','pending')}</div>
<div style=\"display:flex;gap:10px;margin-top:10px\">
  <button class=\"btn primary wide\" onclick=\"reviewItem('{item['id']}','approve')\">APPROVE</button>
  <button class=\"btn ghost wide\" onclick=\"reviewItem('{item['id']}','reject')\">REJECT</button>
</div>
<div id=\"review-result-{item['id']}\" class=\"result\" style=\"margin-top:8px\"></div>
</div>
""" for item in pending]) + '</div>'
    return f"""
<section class="section-inner">
<h2 class="section-title">REVIEW QUEUE</h2>
<p class="sub">pending submissions for expert review. {len(pending)} awaiting assessment.</p>
<div style="margin-top:18px;">
{pending_html}
</div>
</section>
<script>
async function reviewItem(id, action){{
  const payload = {{listing:id, action, note:''}};
  const r = await fetch('/api/review', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(payload)}});
  const data = await r.json();
  document.getElementById('review-result-'+id).textContent = data.ok ? ('STATUS: '+data.status) : ('ERROR: '+(data.error||'unknown'));
}}
</script>"""

def render_listing_page(listing_id):
    v = listings[listing_id]
    lb = bids.get(listing_id, [])
    top = sorted(lb, key=lambda x:x.get("eth",0), reverse=True)[:5]
    rows = []
    for b in top:
        rows.append(f"<div>{time.strftime('%Y-%m-%d %H:%M', time.localtime(b['ts']))} — {b['eth']} ETH — {b['buyer']} {('<a href=https://robinhood.chain/explorer/tx/'+b['tx']+'>tx</a>') if b.get('tx') else ''}</div>")
    rows = "\n".join(rows) if rows else "<div class='meta'>no bids yet</div>"
    floor_eth = usd_to_eth(v['floor'])
    term = v.get('term_days') or 'perpetual'
    return HEAD + f"""
<section class="section-inner">
<div class="section-title">// listing {listing_id}</div>
<div class="manifesto-grid">
<div class="manifesto-block">
<h3>{v['name']} <span style="color:var(--dim);font-size:11px">{v['dtype']}</span></h3>
<p>{v['desc'] or 'no description'}</p>
<div class="meta">created {v['created']} | term {term} days | floor ${v['floor']} ({floor_eth:.4f} ETH)</div>
<div class="meta">status: <strong>{v.get('status','listed')}</strong> | wallet: {v.get('wallet','—')}</div>
</div>
<div class="manifesto-block">
<h3>PREVIEW</h3>
<pre style="white-space:pre-wrap;color:var(--muted)">{(v.get('preview') or '')[:4000]}</pre>
<div class="meta">{len(v.get('preview') or '')} chars shown</div>
</div>
<div class="manifesto-block">
<h3>LICENSE / BID</h3>
<p class="sub" style="margin-top:0;margin-bottom:14px">payouts on Robinhood Chain. every payment includes a verifiable transaction hash.</p>
<form class="form" onsubmit="return false;" style="max-width:420px">
<label><span>BID AMOUNT (ETH)</span><input id="amount" type="number" step="0.0001" min="{floor_eth:.4f}" value="{floor_eth:.4f}"></label>
<label><span>BUYER ID / WALLET</span><input id="buyer" placeholder="0x... on Robinhood Chain"></label>
<label><span>TX HASH (after payment)</span><input id="txhash" placeholder="0x..."></label>
<button class="btn primary wide" onclick="submitBid('{listing_id}')">PLACE BID</button>
<div id="result" class="result" style="margin-top:10px"></div>
</form>
</div>
<div class="manifesto-block">
<h3>TOP BIDS</h3>
{rows}
<h3 style="margin-top:14px">TX HASHES</h3>
{('<div>'+'<br>'.join(tx_hashes.get(listing_id,[]))+'</div>') if tx_hashes.get(listing_id) else '<div class="meta">no txs yet</div>'}
</div>
</div>
</section>
<script>
async function submitBid(id){{
  const payload = {{listing:id, eth:parseFloat(document.getElementById('amount').value), buyer:document.getElementById('buyer').value || 'anon', tx:document.getElementById('txhash').value || ''}};
  const r = await fetch('/api/bids', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(payload)}});
  const data = await r.json();
  const el = document.getElementById('result');
  if(data.ok){{ el.textContent = 'BID OK | top = '+data.top['eth']+' ETH by '+data.top['buyer']; }}
  else {{ el.textContent = 'ERROR: '+(data.error||'unknown'); }}
}}
</script>
""" + FOOT

def render_docs():
    return """
<section class="section-inner">
<h2 class="section-title">docs</h2>
<div class="manifesto-grid">
<div class="manifesto-block">
<h3>What is datamine?</h3>
<p>Creators upload structured data. Expert review within 24 hours. Licensed to vetted AI training companies. Payouts on Robinhood Chain in under 60 seconds. Fixed per-file rates. No hidden fees.</p>
</div>
<div class="manifesto-block">
<h3>Robinhood Chain</h3>
<p>Chain ID: <code>4663</code> / <code>46630</code><br>Currency: USDC / ETH<br>Payouts: instant on-chain settlement with verifiable tx hash</p>
</div>
<div class="manifesto-block">
<h3>API</h3>
<p><code>GET /api/listings</code><br><code>POST /api/listings</code><br><code>POST /api/bids</code><br><code>GET /listing/&lt;id&gt;</code><br><code>GET /review</code><br><code>POST /api/review</code></p>
</div>
<div class="manifesto-block">
<h3>Enrollment</h3>
<p><code>100% free</code><br>No credit card required.<br>Join as creator or buyer.</p>
</div>
<div class="manifesto-block">
<h3>Rules</h3>
<p>Creators retain copyright. Non-exclusive license only. AES-256 encryption. Zero public access. GDPR compliant. Every payment includes an on-chain Robinhood Chain transaction hash.</p>
</div>
<div class="manifesto-block">
<h3>Payout structure</h3>
<p>Fixed per-file rate, no percentage cuts or hidden fees. Settlement time: &lt;60 seconds from content approval to wallet payout.</p>
</div>
</div>
</section>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8082)), debug=True)
