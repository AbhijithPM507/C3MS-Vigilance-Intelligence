import os
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

load_dotenv()

logger = logging.getLogger(__name__)

_RPC_URL = os.getenv("WEB3_RPC_URL", "")
_PRIVATE_KEY = os.getenv("WEB3_PRIVATE_KEY", "")
_CONTRACT_ADDRESS = os.getenv("ANCHOR_CONTRACT_ADDRESS", "")
_TIMEOUT = int(os.getenv("WEB3_TX_TIMEOUT", "30"))

_executor = ThreadPoolExecutor(max_workers=1)

_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "_hash", "type": "string"}],
        "name": "anchorHash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "string", "name": "hashValue", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "HashAnchored",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "getAnchorCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "index", "type": "uint256"}],
        "name": "getAnchor",
        "outputs": [
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "anchors",
        "outputs": [
            {"internalType": "string", "name": "hashValue", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def _get_contract():
    if not all([_RPC_URL, _PRIVATE_KEY, _CONTRACT_ADDRESS]):
        logger.warning("Web3 env vars not fully configured")
        return None

    w3 = Web3(Web3.HTTPProvider(_RPC_URL, request_kwargs={"timeout": _TIMEOUT}))

    if not w3.is_connected():
        logger.error("Cannot connect to RPC node at %s", _RPC_URL)
        return None

    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(_CONTRACT_ADDRESS),
        abi=_ABI,
    )
    return w3, contract


def anchor_hash_onchain(latest_hash: str) -> bool:
    future = _executor.submit(_anchor_sync, latest_hash)
    try:
        return future.result(timeout=_TIMEOUT + 10)
    except TimeoutError:
        logger.error("Web3 anchor timed out after %ds for hash %s", _TIMEOUT + 10, latest_hash)
        return False
    except Exception as exc:
        logger.error("Web3 anchor failed for hash %s: %s", latest_hash, exc)
        return False


def _anchor_sync(latest_hash: str) -> bool:
    result = _get_contract()
    if result is None:
        return False

    w3, contract = result
    account = w3.eth.account.from_key(_PRIVATE_KEY)

    tx = contract.functions.anchorHash(latest_hash).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 80000,
        "gasPrice": w3.eth.gas_price,
    })

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=_TIMEOUT)

    if receipt.status == 1:
        logger.info("Hash %s anchored on-chain at tx %s", latest_hash, receipt.transaction_hash.hex())
        return True

    logger.error("On-chain anchor transaction reverted for hash %s", latest_hash)
    return False
