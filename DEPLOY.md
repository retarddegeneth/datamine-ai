# deploy datamine on render

## 1. fork/clone repo
fork https://github.com/retarddegeneth/datamine-ai to your github account

## 2. create render web service
- new web service on render
- connect your github repo
- build command: `pip install -r requirements.txt`
- start command: `gunicorn app:app`
- plan: free tier works for testing

## 3. environment variables
add these in render dashboard → environment:

| key | value | required |
|---|---|---|
| `SECRET_KEY` | any 32+ random chars | yes |
| `DATAMINE_RPC_URL` | your robinhood chain rpc endpoint | optional (defaults to public node) |
| `DATABASE_URL` | render postgres internal url | optional (defaults to sqlite) |
| `UPLOAD_DIR` | `uploads` | optional (defaults to `uploads/`) |

## 4. persistent storage
- for production: add render postgres addon (free tier available)
- sqlite works but resets on every deploy
- uploads directory is ephemeral on render free tier — for production use s3 or similar

## 5. domain setup (namecheap)
1. buy `datamine.ai` on namecheap
2. in render dashboard: add custom domain `datamine.ai`
3. render gives you a target domain (e.g. `datamine-ai.onrender.com`)
4. in namecheap: advanced dns → add cname record:
   - host: `www`
   - value: your render target domain
5. also add a redirect: `datamine.ai` → `www.datamine.ai`
6. wait 5-30 min for dns propagation

## 6. verify deployment
- `GET https://www.datamine.ai/api/listings` should return `[]`
- `POST https://www.datamine.ai/api/nonce` with body `{"wallet":"0x..."}` should return a nonce
- upload a test file via the upload page

## 7. features that work when live
- browse listings (`GET /api/listings`)
- upload data with file (`POST /api/listings` multipart)
- wallet verification (`POST /api/nonce` + `/api/verify-wallet`)
- place bids (`POST /api/bids`) — requires verified wallet
- payment prep (`POST /api/prepare-payment`) — returns tx details for signing
- view listing detail (`GET /listing/<id>`)

## 8. known limitations
- file storage is local/ephemeral on free render tier
- no smart contract escrow yet (payments are prepared tx, user signs manually)
- robinhood chain public rpc may be rate-limited
