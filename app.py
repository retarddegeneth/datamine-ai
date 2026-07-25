import os, json, sqlite3, hashlib, time, random, requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from eth_account import Account
from eth_account.messages import encode_defunct

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-me')

DB_PATH = os.environ.get('DATABASE_URL', 'datamine.db').replace('postgres://', 'postgresql://').replace('postgresql://', '') if os.environ.get('DATABASE_URL') else 'datamine.db'
UPLOAD_DIR = os.environ.get('UPLOAD_DIR', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS listings (
        id TEXT PRIMARY KEY, name TEXT, dtype TEXT, desc TEXT, preview TEXT,
        floor REAL, term INTEGER, wallet TEXT, status TEXT, created REAL,
        file_path TEXT, file_size INTEGER, verified INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bids (
        id TEXT PRIMARY KEY, listing_id TEXT, bidder TEXT, amount REAL, status TEXT, created REAL,
        tx_hash TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id TEXT PRIMARY KEY, listing_id TEXT, reviewer TEXT, rating INTEGER, comment TEXT, created REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS verifications (
        wallet TEXT PRIMARY KEY, nonce TEXT, verified INTEGER DEFAULT 0, verified_at REAL
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

def verify_signature(wallet, message, signature):
    try:
        message_hash = encode_defunct(text=message)
        recovered = Account.recover_message(message_hash, signature=signature)
        return recovered.lower() == wallet.lower()
    except:
        return False

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

@app.route('/uploads/<path:filename>')
def uploaded_files(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/api/listings', methods=['GET', 'POST'])
def listings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        if request.content_type and 'multipart/form-data' in request.content_type:
            lid = gen_id()
            name = request.form.get('name', '')
            dtype = request.form.get('dtype', 'json')
            desc = request.form.get('desc', '')
            preview = request.form.get('preview', '')
            floor = float(request.form.get('floor', '0.5'))
            term = int(request.form.get('term', '30'))
            wallet = request.form.get('wallet', '')
            
            file_path = None
            file_size = 0
            if 'file' in request.files:
                file = request.files['file']
                if file.filename:
                    ext = os.path.splitext(file.filename)[1]
                    safe_name = f"{lid}{ext}"
                    file_path = os.path.join(UPLOAD_DIR, safe_name)
                    file.save(file_path)
                    file_size = os.path.getsize(file_path)
            
            c.execute('''INSERT INTO listings 
                (id, name, dtype, desc, preview, floor, term, wallet, status, created, file_path, file_size)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (lid, name, dtype, desc, preview, floor, term, wallet, 'pending', time.time(), file_path, file_size))
            conn.commit()
            conn.close()
            return jsonify({'ok': True, 'id': lid})
        else:
            data = request.get_json(force=True)
            lid = gen_id()
            c.execute('''INSERT INTO listings 
                (id, name, dtype, desc, preview, floor, term, wallet, status, created, file_path, file_size)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (lid, data.get('name',''), data.get('dtype','json'), data.get('desc',''),
                 data.get('preview',''), data.get('floor',0.5), data.get('term',30),
                 data.get('wallet',''), 'pending', time.time(), None, 0))
            conn.commit()
            conn.close()
            return jsonify({'ok':True, 'id':lid})
    
    c.execute('SELECT * FROM listings ORDER BY created DESC')
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id':r[0],'name':r[1],'dtype':r[2],'desc':r[3],'preview':r[4],
        'floor':r[5],'term':r[6],'wallet':r[7],'status':r[8],'created':r[9],
        'file_path':r[10],'file_size':r[11],'verified':r[12]
    } for r in rows])

@app.route('/api/bids', methods=['POST'])
def bids():
    data = request.get_json(force=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    bidder = data.get('bidder', '').lower()
    c.execute('SELECT verified FROM verifications WHERE wallet=?', (bidder,))
    vrow = c.fetchone()
    if not vrow or not vrow[0]:
        conn.close()
        return jsonify({'ok': False, 'error': 'wallet not verified. sign message first.'}), 403
    
    bid = gen_id()
    c.execute('INSERT INTO bids VALUES (?,?,?,?,?,?,?)',
        (bid, data.get('listing_id',''), bidder, data.get('amount',0), 'pending', time.time(), None))
    conn.commit()
    conn.close()
    return jsonify({'ok':True, 'id':bid})

@app.route('/api/nonce', methods=['POST'])
def get_nonce():
    data = request.get_json(force=True)
    wallet = data.get('wallet', '').lower()
    nonce = gen_id()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO verifications (wallet, nonce, verified, verified_at)
        VALUES (?, ?, 0, ?)''', (wallet, nonce, time.time()))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'nonce': nonce})

@app.route('/api/verify-wallet', methods=['POST'])
def verify_wallet():
    data = request.get_json(force=True)
    wallet = data.get('wallet', '').lower()
    signature = data.get('signature', '')
    nonce = data.get('nonce', '')
    
    message = f"datamine verify: {nonce}"
    if verify_signature(wallet, message, signature):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO verifications (wallet, nonce, verified, verified_at)
            VALUES (?, ?, 1, ?)''', (wallet, nonce, time.time()))
        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'verified': True})
    return jsonify({'ok': False, 'error': 'invalid signature'}), 403

@app.route('/api/prepare-payment', methods=['POST'])
def prepare_payment():
    data = request.get_json(force=True)
    listing_id = data.get('listing_id')
    bidder = data.get('bidder', '').lower()
    amount = float(data.get('amount', 0))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT wallet, floor FROM listings WHERE id=?', (listing_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'ok': False, 'error': 'listing not found'}), 404
    
    seller, floor = row
    if amount < floor:
        return jsonify({'ok': False, 'error': f'bid below floor ${floor}'}), 400
    
    return jsonify({
        'ok': True,
        'to': seller,
        'amount': amount,
        'token': 'USDC',
        'chain': 'robinhood',
        'chainId': 4663,
        'message': f'pay ${amount} USDC to {seller} for listing {listing_id}'
    })

@app.route('/api/confirm-payment', methods=['POST'])
def confirm_payment():
    data = request.get_json(force=True)
    bid_id = data.get('bid_id')
    tx_hash = data.get('tx_hash')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE bids SET tx_hash=?, status=? WHERE id=?', (tx_hash, 'paid', bid_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

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
    listing = {
        'id':row[0],'name':row[1],'dtype':row[2],'desc':row[3],'preview':row[4],
        'floor':row[5],'term':row[6],'wallet':row[7],'status':row[8],'created':row[9],
        'file_path':row[10],'file_size':row[11],'verified':row[12]
    }
    bids_list = [{'id':r[0],'bidder':r[2],'amount':r[3],'status':r[4],'created':r[5],'tx_hash':r[6]} for r in bids_rows]
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
      {% if listing.file_path %}
      <div class="tier-row"><span>File</span><span><a href="/{{listing.file_path}}">download</a></span></div>
      <div class="tier-row"><span>Size</span><span>{{listing.file_size}} bytes</span></div>
      {% endif %}
      {% if listing.verified %}
      <div class="tier-row"><span>Verified</span><span class="bid">yes</span></div>
      {% endif %}
    </div>
    <h3 style="margin-top:28px">Preview</h3>
    <pre style="background:#0b0b0b;padding:14px;border:1px solid #333;overflow:auto">{{listing.preview}}</pre>
    <h3 style="margin-top:28px">Bids</h3>
    {% for b in bids %}
    <div class="tier-row"><span>{{b.bidder[:8]}}... {% if b.tx_hash %}<a href="https://robinhood.chainscan.io/tx/{{b.tx_hash}}" target="_blank">tx</a>{% endif %}</span><span class="tier-price">${{b.amount}}</span></div>
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
  <footer>datamine v0.3 // upload data, get paid onchain // robinhood chain</footer>
</div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
