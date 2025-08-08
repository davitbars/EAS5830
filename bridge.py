from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]



def scan_blocks(chain, contract_info="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    # This is different from Bridge IV where chain was "avax" or "bsc"
    w3_src = connect_to('source')
    w3_dst = connect_to('destination')

    # Load contract metadata
    contracts = get_contract_info("source", contract_info), get_contract_info("destination", contract_info)
    info_src, info_dst = contracts

    with open(contract_info, 'r') as f:
        all_info = json.load(f)
    private_key = all_info["warden_private_key"]
    warden_address = w3_src.eth.account.from_key(private_key).address

    # Load contracts
    source_contract = w3_src.eth.contract(address=info_src["address"], abi=info_src["abi"])
    dest_contract = w3_dst.eth.contract(address=info_dst["address"], abi=info_dst["abi"])

    latest_block = connect_to(chain).eth.block_number
    from_block = max(0, latest_block - 5)
    to_block = latest_block

    if chain == "source":
        print("Listening for Deposit events on source (Avalanche)...")
        events = source_contract.events.Deposit().get_logs(fromBlock=from_block, toBlock=to_block)

        for e in events:
            token = e.args.token
            recipient = e.args.recipient
            amount = e.args.amount

            print(f"Deposit event detected: token={token}, recipient={recipient}, amount={amount}")

            tx = dest_contract.functions.wrap(token, recipient, amount).build_transaction({
                'from': warden_address,
                'nonce': w3_dst.eth.get_transaction_count(warden_address),
                'gas': 500000,
                'gasPrice': w3_dst.eth.gas_price
            })
            signed_tx = w3_dst.eth.account.sign_transaction(tx, private_key=private_key)
            tx_hash = w3_dst.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"wrap() called on destination: tx_hash={tx_hash.hex()}")

    elif chain == "destination":
        print("Listening for Unwrap events on destination (BSC)...")
        events = dest_contract.events.Unwrap().get_logs(fromBlock=from_block, toBlock=to_block)

        for e in events:
            underlying_token = e.args.underlying_token
            recipient = e.args.to
            amount = e.args.amount

            print(f"Unwrap event detected: token={underlying_token}, recipient={recipient}, amount={amount}")

            tx = source_contract.functions.withdraw(underlying_token, recipient, amount).build_transaction({
                'from': warden_address,
                'nonce': w3_src.eth.get_transaction_count(warden_address),
                'gas': 500000,
                'gasPrice': w3_src.eth.gas_price
            })
            signed_tx = w3_src.eth.account.sign_transaction(tx, private_key=private_key)
            tx_hash = w3_src.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"withdraw() called on source: tx_hash={tx_hash.hex()}")
