# Solana Program First Deployment Timestamp

## System Flow
1. The user inputs:
   - `program_id`
   - Network: `mainnet` or `devnet`
   - Optional: enable verbose logging
2. `solana_logics.py` contains all major HTTP calls and core logics.
3. Two implemented ways to retrieve the first deployment transaction of a program and the block timestamp:
   - Using **Helius Endpoint** (direct call).
   - Using **Solana RPC Endpoint** (requires pagination to find the first transaction).
4. The entry function `get_program_first_deployment_timestamp` **randomly selects** either the Helius or the Solana RPC ways:
   - Helps avoid rate limits.
   - Improves robustness.
5. Before making actual HTTP calls:
   - The system **checks Redis cache** for existing results.
   - If not cached, it randomly selects an available endpoint to query transaction history using `getSignaturesForAddress`.

---
## Setup Instructions
```
# Install Python dependencies
pip3 install -r requirements.txt

# Install Redis (if you don't have it)
brew install redis
brew services start redis

# Optional: start Redis server on terminal
redis-server
```

---
## Usage Instructions
### List all command options
```
python3 main.py -h
```

### Get the first deployment timestamp
#### On **Devnet**
```
python3 main.py -p "2bgdxMTFkhmbGLD1skpM4fDPoVkARNRrGbB5wQFMuJkS"
```

#### On **Mainnet**
```
python3 main.py -p "yds9z6gRFsmzcCK372KSE6iDXArrN99CSrkEmPTokCB" -m
```

#### On **Mainnet with verbose logging**
```
python3 main.py -p "yds9z6gRFsmzcCK372KSE6iDXArrN99CSrkEmPTokCB" -m -v

```

---
## Run Unit Tests
### Run all tests
```
python3 -m unittest logics.tests.test_solana_logics
```

### Run for a specific test class
```
python3 -m unittest logics.tests.test_solana_logics.TestGetFirstDeploymentTimeByHelius
```

---
## Further improvements

### Prod install considerations
1. Save the Helius API key to the cloud secret manager
2. Redis hostname and port should support both prod and dev env
### Logic
1. If Solana RPC call reaches the max of 100 page calls, we will exception to let the user knew
2. If the program has tons of transactions, the Solana RPC call will take a huge amount of time (because of rate limit)
    to trace the first one. To improve it, probably use Helius, QuickNode or Alchemy third party API to get it.

---
## References
- [Solana RPC - getSignaturesForAddress](https://solana.com/docs/rpc/http/getsignaturesforaddress)
- [Helius Docs - getSignaturesForAddress](https://docs.helius.dev/rpc/http/getsignaturesforaddress)
