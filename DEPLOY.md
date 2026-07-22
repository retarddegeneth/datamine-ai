# deploy datamine.ai on render
- fork/clone https://github.com/retarddegeneth/datamine-ai
- new web service on render
- build: pip install -r requirements.txt
- start: gunicorn app:app
- env: SECRET_KEY = any 32+ random chars
- optional: DATAMINE_RPC_URL = Robinhood Chain node endpoint
- optional addon: free postgres for persistence
- domain: Namecheap Advanced DNS CNAME/A to render-provided domain
