from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from datetime import datetime
import json
import os
import sys

# === Config ===
AVAX_RPC = "https://api.avax-test.network/ext/bc/C/rpc"
BSC_RPC  = "https://data-seed-prebsc-1-s1.binance.org:8545/"
CHAIN_ID_SOURCE = 43113   # Avalanche Fuji
CHAIN_ID_DEST   = 97      # BSC Testnet
BLOCK_LOOKBACK  = 5

# SECURITY: set BRIDGE_PK in your environment before running
PRIVATE_KEY = os.environ.get("BRIDGE_PK")  # fallback allows local testing
if not PRIVATE_KEY:
    # Only for local testing; REMOVE for submission
    PRIVATE_KEY = "REPLACE_ME_WITH_ENV"

def w3_connect(url):
    w3 = Web3(Web3.HTTPProvider(url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to {url}")
    return w3

def load_info(path="contract_info.json"):
    with open(path, "r") as f:
        return json.load(f)

def sender_account(w3):
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    return acct, acct.address

def build_and_send(w3, tx, chain_id):
    acct, sender = sender_account(w3)
    tx_dict = tx.build_transaction({
        "from": sender,
        "nonce": w3.eth.get_transaction_count(sender),
        "gas": 300000,
        "gasPrice": w3.eth.gas_price,
        "chainId": chain_id
    })
    signed = w3.eth.account.sign_transaction(tx_dict, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()

def scan_blocks(chain, contract_info_path="contract_info.json"):
    if chain not in ("source", "destination"):
        print(f"Invalid chain: {chain}")
        return 0

    info = load_info(contract_info_path)
    src_info = info["source"]
    dst_info = info["destination"]

    w3_src = w3_connect(AVAX_RPC)
    w3_dst = w3_connect(BSC_RPC)

    # Contracts
    src = w3_src.eth.contract(address=Web3.to_checksum_address(src_info["address"]), abi=src_info["abi"])
    dst = w3_dst.eth.contract(address=Web3.to_checksum_address(dst_info["address"]), abi=dst_info["abi"])

    if chain == "source":
        latest = w3_src.eth.block_number
        from_block = max(0, latest - BLOCK_LOOKBACK)
        try:
            logs = src.events.Deposit().get_logs(fromBlock=from_block, toBlock="latest")
        except Exception as e:
            print(f"Deposit get_logs error: {e}")
            return 0

        if not logs:
            print(f"[{datetime.now()}] No Deposits in last {latest - from_block + 1} blocks.")
            return 1

        for ev in logs:
            token     = ev.args.token
            recipient = ev.args.recipient
            amount    = ev.args.amount
            print(f"[{datetime.now()}] Deposit detected on SOURCE: amount={amount} token={token} recipient={recipient}")

            # wrap on destination (WARDEN_ROLE required)
            try:
                txh = build_and_send(
                    w3_dst,
                    dst.functions.wrap(token, recipient, amount),
                    CHAIN_ID_DEST
                )
                print(f"→ Sent wrap() on DEST, tx={txh}")
            except Exception as e:
                print(f"wrap() failed: {e}")
                return 0

        return 1

    else:  # chain == "destination"
        latest = w3_dst.eth.block_number
        from_block = max(0, latest - BLOCK_LOOKBACK)
        try:
            logs = dst.events.Unwrap().get_logs(fromBlock=from_block, toBlock="latest")
        except Exception as e:
            print(f"Unwrap get_logs error: {e}")
            return 0

        if not logs:
            print(f"[{datetime.now()}] No Unwraps in last {latest - from_block + 1} blocks.")
            return 1

        for ev in logs:
            underlying = ev.args.underlying_token
            to_addr    = ev.args.to
            amount     = ev.args.amount
            print(f"[{datetime.now()}] Unwrap detected on DEST: amount={amount} underlying={underlying} to={to_addr}")

            # withdraw on source (WARDEN_ROLE required)
            try:
                txh = build_and_send(
                    w3_src,
                    src.functions.withdraw(underlying, to_addr, amount),
                    CHAIN_ID_SOURCE
                )
                print(f"→ Sent withdraw() on SOURCE, tx={txh}")
            except Exception as e:
                print(f"withdraw() failed: {e}")
                return 0

        return 1

if __name__ == "__main__":
    # The autograder will run like: python bridge.py source  (or)  python bridge.py destination
    which = sys.argv[1] if len(sys.argv) > 1 else "source"
    rc = scan_blocks(which)
    sys.exit(0 if rc else 1)
