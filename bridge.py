from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware  # Necessary for POA chains
from datetime import datetime
import json
import pandas as pd

def connect_to(chain):
    if chain == 'source':  # The source contract chain is AVAX
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is BSC
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet

    if chain in ['source', 'destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # Inject the POA compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
    Load the contract_info file into a dictionary.
    """
    try:
        with open(contract_info, 'r') as f:
            contracts = json.load(f)
    except Exception as e:
        print(f"Failed to read contract info\nPlease contact your instructor\n{e}")
        return 0
    return contracts[chain]


def scan_blocks(chain, contract_info="contract_info.json"):
    """
    Scan the last 5 blocks of the source and destination chains.
    Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain.
    When Deposit events are found on the source chain, call the 'wrap' function on the destination chain.
    When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain.
    """
    # Load contract info
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return 0

    contract_data = get_contract_info(chain, contract_info)
    contract_address = contract_data["address"]
    abi = contract_data["abi"]

    # Connect to the chain
    w3 = connect_to(chain)
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Get the latest block range
    end_block = w3.eth.block_number
    start_block = end_block - 5

    # Setup filters for Deposit (source) and Unwrap (destination) events
    if chain == 'source':
        event_filter = contract.events.Deposit.createFilter(fromBlock=start_block, toBlock=end_block)
    elif chain == 'destination':
        event_filter = contract.events.Unwrap.createFilter(fromBlock=start_block, toBlock=end_block)

    events = event_filter.get_all_entries()

    for evt in events:
        if chain == 'source':
            # Handle Deposit event on the source chain (Avalanche)
            print(f"Deposit event detected: {evt.args}")
            # Call wrap() function on destination chain (BSC)
            wrap(evt.args)
        elif chain == 'destination':
            # Handle Unwrap event on the destination chain (BSC)
            print(f"Unwrap event detected: {evt.args}")
            # Call withdraw() function on source chain (AVAX)
            withdraw(evt.args)


def wrap(event_data):
    """
    Function to mint wrapped tokens on the destination side (BSC)
    """
    # Extract event data
    token_address = event_data['token']
    recipient = event_data['to']
    amount = event_data['amount']

    # Implement logic to mint wrapped tokens on the destination contract (BSC)
    print(f"Minting {amount} wrapped tokens of {token_address} to {recipient}")


def withdraw(event_data):
    """
    Function to release the "real" tokens on the source side (AVAX)
    """
    # Extract event data
    token_address = event_data['token']
    recipient = event_data['to']
    amount = event_data['amount']

    # Implement logic to release the original tokens on the source contract (AVAX)
    print(f"Releasing {amount} tokens of {token_address} to {recipient}")


def main():
    # Call scan_blocks for both source (Avalanche) and destination (BSC) chains
    scan_blocks('source')  # Listen for Deposit events on source (Avalanche)
    scan_blocks('destination')  # Listen for Unwrap events on destination (BSC)


if __name__ == "__main__":
    main()
