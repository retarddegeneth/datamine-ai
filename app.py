import os, json, sqlite3, hashlib, time, random, requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-me')

DB_PATH = os.environ.get('DATABASE_URL', 'datamine.db').replace('postgres://', 'postgresql://').replace('postgresql://', '') if os.environ.get('DATABASE_URL') else 'datamine.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS listings (
        id TEXT PRIMARY KEY, name TEXT, dtype TEXT, desc TEXT, preview TEXT,
        floor REAL, term INTEGER, wallet TEXT, status TEXT, created REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bids (
        id TEXT PRIMARY KEY, listing_id TEXT, bidder TEXT, amount REAL, status TEXT, created REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id TEXT PRIMARY KEY, listing_id TEXT, reviewer TEXT, rating INTEGER, comment TEXT, created REAL
    )''')
    conn.commit()
    conn.close()

init_db()

RPC_URL = os.environ.get('DATAMINE_RPC_URL', 'https://robinhood.nownodes.io')
ETH_PRICE_API = 'https://api.coinbase.com/v2/exchange-rates?currency=ETH'

def get_eth_price():
    try:
        r = requests.get(ETH_PRICE_API, timeout=5)
        return float(r.json()['data']['rates']['USD'])
    except:
        return 3200.0

def usd_to_eth(usd):
    return round(usd / get_eth_price(), 6)

def gen_id():
    return hashlib.sha256(str(time.time() + random.random()).encode()).hexdigest()[:16]

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/upload')
def upload_page():
    return send_from_directory('.', 'upload.html')

@app.route('/docs')
def docs_page():
    return send_from_directory('.', 'docs.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/api/listings', methods=['GET', 'POST'])
def listings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.get_json(force=True)
        lid = gen_id()
        c.execute('INSERT INTO listings VALUES (?,?,?,?,?,?,?,?,?,?)',
            (lid, data.get('name',''), data.get('dtype','json'), data.get('desc',''),
             data.get('preview',''), data.get('floor',0.5), data.get('term',30),
             data.get('wallet',''), 'pending', time.time()))
        conn.commit()
        conn.close()
        return jsonify({'ok':True, 'id':lid})
    c.execute('SELECT * FROM listings ORDER BY created DESC')
    rows = c.fetchall()
    conn.close()
    return jsonify([{'id':r[0],'name':r[1],'dtype':r[2],'desc':r[3],'preview':r[4],
                     'floor':r[5],'term':r[6],'wallet':r[7],'status':r[8],'created':r[9]} for r in rows])

@app.route('/api/bids', methods=['POST'])
def bids():
    data = request.get_json(force=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    bid = gen_id()
    c.execute('INSERT INTO bids VALUES (?,?,?,?,?,?)',
        (bid, data.get('listing_id',''), data.get('bidder',''), data.get('amount',0), 'pending', time.time()))
    conn.commit()
    conn.close()
    return jsonify({'ok':True, 'id':bid})

@app.route('/listing/<lid>')
def listing_detail(lid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM listings WHERE id=?', (lid,))
    row = c.fetchone()
    c.execute('SELECT * FROM bids WHERE listing_id=? ORDER BY amount DESC', (lid,))
    bids_rows = c.fetchall()
    c.execute('SELECT * FROM reviews WHERE listing_id=? ORDER BY created DESC', (lid,))
    revs = c.fetchall()
    conn.close()
    if not row:
        return 'not found', 404
    listing = {'id':row[0],'name':row[1],'dtype':row[2],'desc':row[3],'preview':row[4],
               'floor':row[5],'term':row[6],'wallet':row[7],'status':row[8],'created':row[9]}
    bids_list = [{'id':r[0],'bidder':r[2],'amount':r[3],'status':r[4],'created':r[5]} for r in bids_rows]
    reviews_list = [{'id':r[0],'reviewer':r[2],'rating':r[3],'comment':r[4],'created':r[5]} for r in revs]
    return render_template_string(DETAIL_TEMPLATE, listing=listing, bids=bids_list, reviews=reviews_list)

DETAIL_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="canonical" href="https://www.datamine.ai/listing/{{listing.id}}">
<link rel="icon" href="/static/favicon.png">
<title>{{listing.name}} — datamine</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="scanlines"></div>
<div class="container">
  <nav class="nav">
    <div class="brand">datamine</div>
    <div class="links">
      <a href="/">[browse]</a>
      <a href="/upload">[upload]</a>
      <a href="/docs">[docs]</a>
    </div>
  </nav>
  <section class="section-inner">
    <h2 class="section-title">{{listing.name}}</h2>
    <p class="sub">{{listing.desc}}</p>
    <div class="tier-card" style="margin-top:18px">
      <div class="tier-row"><span>Type</span><span>{{listing.dtype}}</span></div>
      <div class="tier-row"><span>Floor</span><span class="tier-price">${{listing.floor}}</span></div>
      <div class="tier-row"><span>Term</span><span>{{listing.term}} days</span></div>
      <div class="tier-row"><span>Status</span><span>{{listing.status}}</span></div>
      <div class="tier-row"><span>Wallet</span><span>{{listing.wallet}}</span></div>
    </div>
    <h3 style="margin-top:28px">Preview</h3>
    <pre style="background:#0b0b0b;padding:14px;border:1px solid #333;overflow:auto">{{listing.preview}}</pre>
    <h3 style="margin-top:28px">Bids</h3>
    {% for b in bids %}
    <div class="tier-row"><span>{{b.bidder[:8]}}...</span><span class="tier-price">${{b.amount}}</span></div>
    {% else %}
    <p>No bids yet.</p>
    {% endfor %}
    <h3 style="margin-top:28px">Reviews</h3>
    {% for r in reviews %}
    <div class="tier-row"><span>{{r.reviewer[:8]}}... — {{r.comment}}</span><span>{{r.rating}}/5</span></div>
    {% else %}
    <p>No reviews yet.</p>
    {% endfor %}
  </section>
  <footer>datamine v0.2 // upload data, get paid onchain // robinhood chain</footer>
</div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
