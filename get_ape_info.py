from web3 import Web3
from web3.providers.rpc import HTTPProvider
import requests
import json

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.to_checksum_address(bayc_address)

# You will need the ABI to connect to the contract
# The file 'abi.json' has the ABI for the bored ape contract
# In general, you can get contract ABIs from etherscan
# https://api.etherscan.io/api?module=contract&action=getabi&address=0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D
with open('ape_abi.json', 'r') as f:
    abi = json.load(f)

############################
# Connect to an Ethereum node
api_url = f"https://mainnet.infura.io/v3/640ced34883a487d9d99fc6b0f24f9de"  # YOU WILL NEED TO PROVIDE THE URL OF AN ETHEREUM NODE
provider = HTTPProvider(api_url)
web3 = Web3(provider)


def get_ape_info(ape_id):
    assert isinstance(ape_id, int), f"{ape_id} is not an int"
    assert 0 <= ape_id, f"{ape_id} must be at least 0"
    assert 9999 >= ape_id, f"{ape_id} must be less than 10,000"

    data = {'owner': "", 'image': "", 'eyes': ""}

    # YOUR CODE HERE
    contract = web3.eth.contract(address=contract_address, abi=abi)
    owner = contract.functions.ownerOf(ape_id).call()
    token_uri = contract.functions.tokenURI(ape_id).call()
    if token_uri.startswith("ipfs://"):
        ipfs_hash = token_uri.replace("ipfs://", "")
        metadata_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
    else:
        metadata_url = token_uri
    
    response = requests.get(metadata_url)
    metadata = response.json()
    image = metadata.get("image", "")

    eyes = ""
    for attr in metadata.get("attributes", []):
        if attr.get("trait_type") == "Eyes":
            eyes = attr.get("value", "")
            break

    data['owner'] = owner
    data['image'] = image
    data['eyes'] = eyes

    assert isinstance(data, dict), f'get_ape_info{ape_id} should return a dict'
    assert all([a in data.keys() for a in
                ['owner', 'image', 'eyes']]), f"return value should include the keys 'owner','image' and 'eyes'"
    return data
