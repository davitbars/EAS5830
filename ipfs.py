import requests
import json

def pin_to_ipfs(data):
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
	url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
	headers = {
		'pinata_api_key': '34cd47ef1ef4e03e3c95',
		'pinata_secret_api_key': 'd2477409a29932dba2eda98ac6b9cd9842cebbd4cce8af6218bd02a248e1ad58'

	}
	payload = {
		'pinataContent' : data
	}
	response = requests.post(url, headers=headers, json=payload)
	response.raise_for_status()
	cid = response.json()["IpfsHash"]
	return cid

def get_from_ipfs(cid,content_type="json"):
	assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
	url = f"https://gateway.pinata.cloud/ipfs/{cid}"
	response = requests.get(url)
	response.raise_for_status()
	data = response.json()
	assert isinstance(data,dict), f"get_from_ipfs should return a dict"
	return data
