import json
from typing import Type

from web3 import Web3
from web3.contract import Contract
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider

'''
If you use one of the suggested infrastructure providers, the url will be of the form
now_url  = f"https://eth.nownodes.io/{now_token}"
alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"
infura_url = f"https://mainnet.infura.io/v3/{infura_token}"
'''

def connect_to_eth():
	alchemy_token = "L8vIJ0aH3-PGvxyaY4hchy26XqhnxcTS"
	url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"  # FILL THIS IN
	w3 = Web3(HTTPProvider(url))
	assert w3.is_connected(), f"Failed to connect to provider at {url}"
	return w3


def connect_with_middleware(contract_json):
	with open(contract_json, "r") as f:
		d = json.load(f)
		d = d['bsc']
		address = d['address']
		abi = d['abi']

	# TODO complete this method
	# The first section will be the same as "connect_to_eth()" but with a BNB url

	alchemy_token = "L8vIJ0aH3-PGvxyaY4hchy26XqhnxcTS"
	url = f"https://bnb-testnet.g.alchemy.com/v2/NTObxaMRy4SosrZX-0oOb/{alchemy_token}"  # FILL THIS IN
	w3 = Web3(HTTPProvider(url))

	assert w3.is_connected(), f"Failed to connect to provider at {url}"

	# The second section requires you to inject middleware into your w3 object and
	# create a contract object. Read more on the docs pages at https://web3py.readthedocs.io/en/stable/middleware.html
	# and https://web3py.readthedocs.io/en/stable/web3.contract.html

	# contract = 0

	w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
	contract = w3.eth.contract(address=address, abi=abi)

	return w3, contract


if __name__ == "__main__":

	connect_to_eth()

'''
	w3_ether = connect_to_eth()

	print(f"connect_to_eth: {w3_ether.is_connected()}")
	print(f"latest block: {w3_ether.eth.get_block('latest')}")

	contract_json = "contract_info.json"
	w3_middleware, contract = connect_with_middleware(contract_json)

	print(f"connect_with_middleware: {w3_middleware.is_connected()}")
	try:
		print(f"Current value from contract: {contract.all_events()}")
	except Exception as e:
		print(f"Error calling getValue: {e}")

'''