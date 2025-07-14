import json
from typing import Type

from web3 import Web3
from web3.contract import Contract
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider


def connect_to_eth():
    alchemy_token = "L8vIJ0aH3-PGvxyaY4hchy26XqhnxcTS"
    url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"  # FILL THIS IN
    w3 = Web3(HTTPProvider(url))

    # Check connection
    if w3.is_connected():
        print("Connected to blockchain!")
    else:
        print("Failed to connect to blockchain.")

    # assert w3.is_connected(), f"Failed to connect to provider at {url}"
    return w3

def connect_with_middleware(abi_json, address):
    with open(abi_json, "r") as f:
        abi = json.load(f)

    alchemy_token = "L8vIJ0aH3-PGvxyaY4hchy26XqhnxcTS"
    url = f"https://bnb-testnet.g.alchemy.com/v2/NTObxaMRy4SosrZX-0oOb/{alchemy_token}"
    w3 = Web3(HTTPProvider(url))

    # Check connection
    if w3.is_connected():
        print("Connected to blockchain!")
    else:
        print("Failed to connect to blockchain.")

    # assert w3.is_connected(), f"Failed to connect to provider at {url}"

    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    contract = w3.eth.contract(address=address, abi=abi)

    return w3, contract


if __name__ == "__main__":

    abi_json = "NFT.abi"
    address = "0x85ac2e065d4526FBeE6a2253389669a12318A412"

    w3, contract = connect_with_middleware(abi_json, address)

    # Replace with your private key and account address
    # If the file is empty, it will raise an exception
    filename = "secret_key.txt"
    with open(filename, "r") as f:
        private_key = f.readlines()
    assert (len(private_key) > 0), "Your account secret_key.txt is empty"

    account = w3.eth.account.from_key(private_key[0])

    # Replace with your NFT metadata URI
    token_uri = "ipfs://QmXZFDDDTvFXd8mjfMRisyT6SNpAu9BHHHXWggmtkTaaEb"

    # Get the minting function from your contract (e.g., 'mintNFT', 'safeMint')
    # The arguments will depend on your specific smart contract's minting function
    hashedIpfsUrl = w3.keccak(text = token_uri);
    mint_function = contract.functions.claim(account.address, hashedIpfsUrl)

    # Build the transaction
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price # Or a custom gas price
    gas_limit = 200000 # Estimate or set a reasonable gas limit

    transaction = mint_function.build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gasPrice': gas_price,
        'gas': gas_limit
    })

    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key[0])
    txn_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

    # Wait for the transaction to be mined and get the receipt
    txn_receipt = w3.eth.wait_for_transaction_receipt(txn_hash)
    print(f"Transaction successful! Transaction hash: {txn_receipt.transactionHash.hex()}")