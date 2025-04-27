import redis

HELIUS_API_KEY = "60ee1555-5946-477b-b61f-f5a9283e6a0f" # Move to cloud secret manager in prod env later
HELIUS_MAIN_NET_NAME = "mainnet"
HELIUS_DEV_NET_NAME = "devnet"

cache = redis.Redis(host='localhost', port=6379, db=0) # When deploy to the prod, need to add prod host and port
