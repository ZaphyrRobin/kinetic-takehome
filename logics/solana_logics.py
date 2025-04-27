import datetime
import json
import logging
import random
import requests
from requests.models import Response
import time
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple
from utils.datetime_utils import get_utc_timestamp
from utils.decorator_utils import retry
from settings import cache
from settings import HELIUS_API_KEY
from settings import HELIUS_DEV_NET_NAME
from settings import HELIUS_MAIN_NET_NAME


logger = logging.getLogger(__name__)


def get_helius_endpoint(is_mainnet: bool = True) -> str:
    """Get the Helius RPC endpoint"""
    env_name = HELIUS_MAIN_NET_NAME if is_mainnet else HELIUS_DEV_NET_NAME
    return f"https://{env_name}.helius-rpc.com/?api-key={HELIUS_API_KEY}"


def get_raw_rpc_endpoint(is_mainnet: bool = True) -> str:
    """Get the raw RPC endpoint"""
    env_name = "mainnet-beta" if is_mainnet else "devnet"
    return f"https://api.{env_name}.solana.com"


def get_signatures_for_address_call(url: str, parameters: List[Any]) -> Response:
    """
    HTTP call of Solana getSignaturesForAddress method
    Args:
        parameters: parameters for the method
        url: endpoint url
    """
    return requests.post(
        url=url,
        headers={"Content-Type":"application/json"},
        data=json.dumps({
            "method":"getSignaturesForAddress",
            "jsonrpc":"2.0",
            "id":"1",
            "params":parameters
        })
    )


@retry(Exception, tries=3, delay=0.5)
def get_program_first_deployment_time_by_helius(program_id: str, is_mainnet: bool = False) -> Optional[int]:
    """
    Get the first transactions of a program by calling helius.
    Args:
        program_id: program id
        is_mainnet: mainnet or devnet
    Output:
        unix timestamp. (return None if invalid)
    """
    url = get_helius_endpoint(is_mainnet)
    logging.info(f"Helius RPC call - Start the calling with {program_id}")
    try:
        response = get_signatures_for_address_call(url, [program_id])
    except Exception as e:
        logging.exception(f"Helius RPC call - get the program deployment time has error {e}")
        return None

    # Parsing the JSON response
    try:
        result = response.json()["result"]
        if len(result) < 1:
            raise Exception("This program has no transactions!")
        # Get the last transaction as it's the first deployment transaction
        deploy_time = result[-1]["blockTime"]
        logging.info(f"Helius RPC call - End of the calling with time {deploy_time}")
        return deploy_time
    except Exception as e:
        logging.exception(f"Helius RPC call - JSON parsing has error {e}")
        return None


@retry(Exception, tries=3, delay=0.5)
def get_first_transaction_for_program(
    program_id: str,
    before_transaction: str = None,
    is_mainnet: bool = False,
    limit: int = 1000,
) -> Optional[Tuple[int, str]]:
    """
    Get the first transactions of a program by calling raw RPC.
    Args:
        program_id: program id
        is_mainnet: mainnet or devnet
        limit: batch call limit size. Default is 1000, refer to https://solana.com/docs/rpc/http/getsignaturesforaddress
        before_transaction:
            None - ignore this, we will get all transactions with the limit size
            Valid string - it will only search the transactions before this one with the limit size
    Output:
        Tuple of oldest transaction unix timestamp and datetime. (return None if invalid)
    """
    url = get_raw_rpc_endpoint(is_mainnet)
    parameters = [program_id]
    optional_param = {}
    if before_transaction:
        optional_param["before"] = before_transaction
    if limit:
        optional_param["limit"] = limit
    if optional_param:
        parameters.append(optional_param)

    logging.info(f"Raw RPC calling - Start the calling with {parameters}")
    try:
        response = get_signatures_for_address_call(url, parameters)
    except Exception as e:
        logging.exception(f"Raw RPC calling - get transaction history has error {e}")
        return None, None

    # Parsing the JSON response
    try:
        result = response.json()["result"]
        # If it's empty, meaning there is no tx before the before_transaction
        # we response 0, "" to make it different from the invalid cases.
        if len(result) == 0:
            return 0, ""
        oldest_tx_data = result[-1]
        unix_timestamp = oldest_tx_data["blockTime"]
        signature = oldest_tx_data["signature"]
        logging.info(f"Raw RPC calling - End the calling timestamp: {unix_timestamp}, signature: {signature}")
        return unix_timestamp, signature
    except Exception as e:
        logging.exception(f"Raw RPC calling - JSON parsing of transaction history response has error {e}")
    return None, None


def check_is_first_deploy_tx_in_rpc_call(timestamp: int, tx_hash: str) -> bool:
    """
    Check if the transaction is the first deployed one by
    refer to the standard we setup in get_first_transaction_for_program
    Args:
        timestamp: timestamp of a transaction
        tx_hash: transaction hash (signature)
    Output:
        boolean of if it's the first transaction for this program
    """
    return timestamp == 0 and tx_hash == ""


def get_program_first_deployment_time_by_rpc(program_id: str, is_mainnet: bool = False, limit: int = 1000) -> Optional[int]:
    """
    Get the first deployment timestamp of a program by calling Raw RPC
    We need to looping search it to get the first deployment transaction. Everytime passing the "before transaction" as 
    a cursor.
    Args:
        program_id: program id
        is_mainnet: mainnet or devnet
        limit: for development only, it limits the page size.
    Output:
        unix timestamp
    """
    oldest_tx_timestamp, oldest_tx_hash = get_first_transaction_for_program(program_id, is_mainnet=is_mainnet, limit=limit)
    if oldest_tx_hash is None:
        logging.error(f"Raw RPC calling - failed because of no valid transactions")
        return None

    # If it's over 1000 * 100, we like to pause and let engineer to interve, to prevent infinite looping
    max_page_count = 100
    page_counter = 1
    time.sleep(1)
    tx_timestamp, tx_hash = get_first_transaction_for_program(program_id, before_transaction=oldest_tx_hash, is_mainnet=is_mainnet, limit=limit)
    while page_counter < max_page_count:
        # Check if no extra transactions before the oldest_tx_hash, then return the values
        if check_is_first_deploy_tx_in_rpc_call(tx_timestamp, tx_hash):
            return oldest_tx_timestamp
        else:
            # Add a time sleep just to avoid it reaches the rate limit
            if is_mainnet:
                time.sleep(5)
            oldest_tx_timestamp, oldest_tx_hash = tx_timestamp, tx_hash
            tx_timestamp, tx_hash = get_first_transaction_for_program(program_id, before_transaction=tx_hash, is_mainnet=is_mainnet, limit=limit)
        page_counter += 1

    if page_counter >= max_page_count and not check_is_first_deploy_tx_in_rpc_call(tx_timestamp, tx_hash):
        logging.error("Raw RPC calling - Error - cannot find the first deployment transaction after 100 pages search!")
    return None


def get_program_first_deployment_timestamp(program_id: str, is_mainnet: bool = False) -> Optional[Tuple[int, datetime.datetime]]:
    """
    Get the first deployment timestamp of a program
    We randomize to call either the Helius or Raw RPC to make it robust and avoid rate limit
    Args:
        program_id: program id
        is_mainnet: mainnet or devnet
    Output:
        Tuple of unix timestamp and readable datetime in UTC
    """
    # Try to get the value from the cache
    cache_key = f"program_first_deployment_timestamp:{program_id}:{is_mainnet}"
    value = cache.get(cache_key)
    if value:
        value = int(value.decode()) if isinstance(value, bytes) else int(value)
        logging.info(f"Get from cache - program_id: {program_id}, is_mainnet: {is_mainnet}, value: {value}")
        return value, get_utc_timestamp(value)

    # Randomly pick one endpoint to get the onchain data
    funcs = [
        get_program_first_deployment_time_by_helius,
        get_program_first_deployment_time_by_rpc,
    ]
    func = random.choice(funcs)
    logging.info(f"Pick RPC calling func: {func}, program_id: {program_id}, is_mainnet: {is_mainnet}")

    try:
        unix_timestamp = func(program_id, is_mainnet)
        if not unix_timestamp:
            raise Exception(f"invalid timestamp")
    except Exception as e:
        logging.exception(f"Get program first deployment time failed with error {e} on program_id {program_id}")
        return None, None

    # Set the value to the cache
    cache.set(cache_key, unix_timestamp)
    logging.info(f"Set the cache - program_id: {program_id}, is_mainnet: {is_mainnet}, value: {unix_timestamp}")
    return unix_timestamp, get_utc_timestamp(unix_timestamp)
