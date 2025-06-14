import redis

HELIUS_MAIN_NET_NAME = "mainnet"
HELIUS_DEV_NET_NAME = "devnet"

cache = redis.Redis(host='localhost', port=6379, db=0) # When deploy to the prod, need to add prod host and port
